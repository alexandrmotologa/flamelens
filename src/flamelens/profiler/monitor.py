"""Low-overhead allocation monitor using PEP 669 sys.monitoring and tracemalloc."""

from __future__ import annotations

import linecache
import os
import re
import sys
import threading
import tracemalloc
from contextlib import contextmanager
from types import CodeType, FrameType
from typing import Generator

from flamelens.config import ProfilerConfig
from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackTree
from flamelens.profiler.sampler import PoissonSampler
from flamelens.profiler.spike_detector import SpikeDetector, SpikeIncident


class AllocationMonitor:
    """Monitors memory allocations using Python 3.12+ sys.monitoring and tracemalloc."""

    def __init__(self, config: ProfilerConfig | None = None) -> None:
        self.config = config or ProfilerConfig()
        self.churn_tree = StackTree(root_name="Total Allocation Churn")
        self.retained_tree = StackTree(root_name="Live Retained Memory")
        self.tree = self.churn_tree
        self.sampler = PoissonSampler(sample_rate=self.config.sample_rate)
        self.spike_detector = SpikeDetector(threshold_mb=self.config.spike_threshold_mb)

        self._tool_id: int | None = None
        self._is_active = False
        self._lock = threading.Lock()

        # Cache mapping (filename, lineno) -> function qualified name
        self._line_to_func: dict[tuple[str, int], str] = {}
        self._func_name_cache: dict[tuple[str, int], str] = {}
        self._file_exists_cache: dict[str, bool] = {}
        self._seen_codes: set[int] = set()

    @property
    def spikes(self) -> list[SpikeIncident]:
        return self.spike_detector.spikes

    def _on_py_start(self, code: CodeType, offset: int) -> None:
        """Index code object lines to resolve accurate function qualified names."""
        code_id = id(code)
        if code_id in self._seen_codes:
            return
        self._seen_codes.add(code_id)

        fn = code.co_filename
        if self._should_ignore_filename(fn):
            return

        qualname = code.co_qualname
        try:
            for _, _, lineno in code.co_lines():
                if lineno is not None:
                    self._line_to_func[(fn, lineno)] = qualname
        except Exception:
            pass

    def _acquire_monitoring_tool(self) -> int | None:
        """Acquire an available sys.monitoring tool ID."""
        if not hasattr(sys, "monitoring"):
            return None

        for tool_id in range(3, 6):
            try:
                sys.monitoring.use_tool_id(tool_id, "flamelens")
                return tool_id
            except ValueError:
                continue
        return None

    def record_current_allocation(self, size: int, frame: FrameType | None = None) -> None:
        """Directly record an allocation event with the current call stack."""
        if size <= 0 or not self.sampler.should_sample(size):
            return

        if frame is None:
            try:
                frame = sys._getframe(1)
            except ValueError:
                return

        raw_frames: list[StackFrame] = []
        curr = frame
        depth = 0

        while curr and depth < self.config.max_depth:
            code = curr.f_code
            fn = code.co_filename
            name = code.co_qualname
            ln = curr.f_lineno

            if not self._should_ignore_filename(fn):
                raw_frames.append(StackFrame(name=name, filename=fn, line_number=ln))
                depth += 1

            curr = curr.f_back

        if raw_frames:
            stack = list(reversed(raw_frames))
            self.churn_tree.insert_stack(stack, size)

        # Check for spike event
        if tracemalloc.is_tracing():
            curr_mem, peak_mem = tracemalloc.get_traced_memory()
            self.spike_detector.check(curr_mem, peak_mem, frame=frame)

    def start(self) -> None:
        """Start tracking memory allocations and runtime call events."""
        with self._lock:
            if self._is_active:
                return

            self._is_active = True
            self.churn_tree = StackTree(root_name="Total Allocation Churn")
            self.retained_tree = StackTree(root_name="Live Retained Memory")
            self.tree = self.churn_tree

            # Start tracemalloc with specified stack depth
            if not tracemalloc.is_tracing():
                tracemalloc.start(self.config.max_depth)

            # Register sys.monitoring for indexing code objects
            self._tool_id = self._acquire_monitoring_tool()
            if self._tool_id is not None:
                events = sys.monitoring.events.PY_START
                sys.monitoring.set_events(self._tool_id, events)
                sys.monitoring.register_callback(
                    self._tool_id, sys.monitoring.events.PY_START, self._on_py_start
                )

    def stop(self) -> StackTree:
        """Stop tracking and finalize both churn and retained StackTrees."""
        with self._lock:
            if not self._is_active:
                return self.tree

            # Collect snapshot of retained memory allocations
            if tracemalloc.is_tracing():
                snapshot = tracemalloc.take_snapshot()
                self._process_snapshot(snapshot)
                tracemalloc.stop()

            # Deregister monitoring tool
            if self._tool_id is not None:
                try:
                    sys.monitoring.set_events(self._tool_id, 0)
                    sys.monitoring.free_tool_id(self._tool_id)
                except Exception:
                    pass
                self._tool_id = None

            self._is_active = False
            # Select tree with highest captured allocation volume
            if self.retained_tree.total_bytes > self.churn_tree.total_bytes:
                self.tree = self.retained_tree
            else:
                self.tree = self.churn_tree
            return self.tree

    @contextmanager
    def profile(self) -> Generator[AllocationMonitor, None, None]:
        """Context manager to profile allocations in a scoped block."""
        self.start()
        try:
            yield self
        finally:
            self.stop()

    def _resolve_function_name(self, filename: str, lineno: int) -> str:
        """Determine human-friendly function name for a source line with caching."""
        key = (filename, lineno)
        if key in self._func_name_cache:
            return self._func_name_cache[key]

        if key in self._line_to_func:
            func_name = self._line_to_func[key]
            self._func_name_cache[key] = func_name
            return func_name

        exists = self._file_exists_cache.get(filename)
        if exists is None:
            exists = os.path.exists(filename)
            self._file_exists_cache[filename] = exists

        if exists:
            line = linecache.getline(filename, lineno).strip()
            m = re.match(r"^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)", line)
            if m:
                func_name = m.group(1)
                self._func_name_cache[key] = func_name
                return func_name

        stem = os.path.splitext(os.path.basename(filename))[0]
        func_name = f"{stem}:{lineno}"
        self._func_name_cache[key] = func_name
        return func_name

    def _should_ignore_filename(self, filename: str) -> bool:
        """Fast check to ignore internal or test framework files."""
        if self.config.include_internal:
            return False

        if "flamelens" in filename or "monitor.py" in filename:
            return True

        if "site-packages" in filename or "importlib" in filename:
            return True

        for pattern in self.config.ignore_patterns:
            if pattern in filename:
                return True

        return False

    def _process_snapshot(self, snapshot: tracemalloc.Snapshot) -> None:
        """Aggregate tracemalloc traces into both retained and churn trees."""
        for trace in snapshot.traces:
            allocated_bytes = trace.size
            if allocated_bytes <= 0:
                continue

            if not self.sampler.should_sample(allocated_bytes):
                continue

            frames: list[StackFrame] = []
            for raw_frame in trace.traceback:
                fn = raw_frame.filename
                if self._should_ignore_filename(fn):
                    continue

                ln = raw_frame.lineno
                func_name = self._resolve_function_name(fn, ln)
                frames.append(
                    StackFrame(
                        name=func_name,
                        filename=fn,
                        line_number=ln,
                    )
                )

            if frames:
                self.retained_tree.insert_stack(frames, allocated_bytes)
                if self.churn_tree.total_bytes < self.retained_tree.total_bytes:
                    self.churn_tree.insert_stack(frames, allocated_bytes)
