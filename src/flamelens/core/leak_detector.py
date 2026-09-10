"""Generational memory leak detector tracking allocation retention across GC sweeps."""

from __future__ import annotations

import gc
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any

from flamelens.config import ProfilerConfig
from flamelens.core.frame import StackFrame


@dataclass
class CheckpointRecord:
    """Snapshot record taken at a specific checkpoint."""

    index: int
    timestamp: float
    retained_by_site: dict[str, int]
    call_stacks: dict[str, list[StackFrame]]
    gc_counts: tuple[int, int, int]


@dataclass
class LeakCandidate:
    """An allocation site exhibiting monotonic memory growth across GC sweeps."""

    site_key: str
    frame: StackFrame
    initial_bytes: int
    final_bytes: int
    growth_bytes: int
    checkpoints_observed: int
    consecutive_increases: int
    call_stack: list[StackFrame] = field(default_factory=list)
    is_immortal: bool = False

    @property
    def growth_mb(self) -> float:
        """Net growth in megabytes."""
        return self.growth_bytes / (1024 * 1024)

    @property
    def initial_mb(self) -> float:
        """Initial bytes in megabytes."""
        return self.initial_bytes / (1024 * 1024)

    @property
    def final_mb(self) -> float:
        """Final bytes in megabytes."""
        return self.final_bytes / (1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        """Serialize candidate to dictionary."""
        return {
            "site_key": self.site_key,
            "frame": self.frame.to_dict(),
            "initial_bytes": self.initial_bytes,
            "final_bytes": self.final_bytes,
            "growth_bytes": self.growth_bytes,
            "growth_mb": round(self.growth_mb, 2),
            "checkpoints_observed": self.checkpoints_observed,
            "consecutive_increases": self.consecutive_increases,
            "is_immortal": self.is_immortal,
            "call_stack": [f.to_dict() for f in self.call_stack],
        }


@dataclass
class LeakReport:
    """Comprehensive leak evaluation report across all checkpoints."""

    candidates: list[LeakCandidate] = field(default_factory=list)
    checkpoints_count: int = 0
    total_leaked_bytes: int = 0

    @property
    def total_leaked_mb(self) -> float:
        """Total estimated leaked memory in megabytes."""
        return self.total_leaked_bytes / (1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to dictionary."""
        return {
            "checkpoints_count": self.checkpoints_count,
            "total_leaked_bytes": self.total_leaked_bytes,
            "total_leaked_mb": round(self.total_leaked_mb, 2),
            "candidates": [c.to_dict() for c in self.candidates],
        }

    def format_summary(self) -> str:
        """Format human-readable leak diagnostic summary."""
        if not self.candidates:
            return "No memory leaks detected across generational GC checkpoints."

        lines = [
            f"LEAK CANDIDATES DETECTED: {len(self.candidates)}",
            f"Total estimated retained growth: {self.total_leaked_mb:.2f} MB over {self.checkpoints_count} checkpoints",
            "-" * 80,
        ]

        for i, candidate in enumerate(self.candidates, 1):
            immortal_tag = " [IMMORTAL OBJECTS]" if candidate.is_immortal else ""
            lines.append(f"{i}. {candidate.frame.display_name}{immortal_tag}")
            lines.append(
                f"   Initial: {candidate.initial_mb:.2f} MB -> Final: {candidate.final_mb:.2f} MB "
                f"(+{candidate.growth_mb:.2f} MB growth)"
            )
            lines.append(
                f"   Observed monotonic growth across {candidate.consecutive_increases} checkpoints"
            )
            if candidate.call_stack:
                caller_preview = " -> ".join(f.name for f in candidate.call_stack[-4:])
                lines.append(f"   Call path: {caller_preview}")
            lines.append("")

        lines.append("-" * 80)
        return "\n".join(lines)


class LeakDetector:
    """Tracks object longevity across generational GC sweeps and flags monotonic growth."""

    def __init__(self, config: ProfilerConfig | None = None) -> None:
        self.config = config or ProfilerConfig()
        self.checkpoints: list[CheckpointRecord] = []
        self._is_active = False

    def start(self) -> None:
        """Start leak detection session and record baseline checkpoint."""
        if not tracemalloc.is_tracing():
            tracemalloc.start(self.config.max_depth)
        self.checkpoints.clear()
        self._is_active = True
        self.take_checkpoint()

    def take_checkpoint(self) -> CheckpointRecord:
        """Force generational GC collection and record retained allocations."""
        # Trigger explicit GC collections to collect temporary objects
        gc.collect(0)
        gc.collect(1)
        gc.collect(2)

        gc_counts = gc.get_count()
        snapshot = tracemalloc.take_snapshot()

        retained: dict[str, int] = {}
        call_stacks: dict[str, list[StackFrame]] = {}

        for trace in snapshot.traces:
            if trace.size <= 0:
                continue

            frames: list[StackFrame] = []
            for raw_frame in trace.traceback:
                fn = raw_frame.filename
                if self._should_ignore(fn):
                    continue
                frames.append(
                    StackFrame(
                        name=f"{raw_frame.filename}:{raw_frame.lineno}",
                        filename=raw_frame.filename,
                        line_number=raw_frame.lineno,
                    )
                )

            if not frames:
                continue

            leaf = frames[-1]
            site_key = leaf.identifier
            retained[site_key] = retained.get(site_key, 0) + trace.size
            if site_key not in call_stacks:
                call_stacks[site_key] = frames

        record = CheckpointRecord(
            index=len(self.checkpoints),
            timestamp=time.time(),
            retained_by_site=retained,
            call_stacks=call_stacks,
            gc_counts=gc_counts,
        )
        self.checkpoints.append(record)
        return record

    def analyze(self) -> LeakReport:
        """Evaluate recorded checkpoints for monotonic memory retention."""
        if len(self.checkpoints) < 2:
            return LeakReport(checkpoints_count=len(self.checkpoints))

        min_growth_bytes = int(self.config.min_growth_mb * 1024 * 1024)
        candidates: list[LeakCandidate] = []
        total_leaked = 0

        # Collect all observed site keys
        all_sites: set[str] = set()
        for cp in self.checkpoints:
            all_sites.update(cp.retained_by_site.keys())

        for site_key in all_sites:
            history = [cp.retained_by_site.get(site_key, 0) for cp in self.checkpoints]

            # Calculate consecutive increases
            consecutive_increases = 0
            is_monotonic = True
            for i in range(len(history) - 1):
                if history[i + 1] > history[i]:
                    consecutive_increases += 1
                elif history[i + 1] < history[i]:
                    is_monotonic = False

            initial_bytes = history[0]
            final_bytes = history[-1]
            growth = final_bytes - initial_bytes

            # Minimum criteria: positive growth exceeding threshold and at least 2 increases
            if growth >= min_growth_bytes and consecutive_increases >= 2:
                # Find representative call stack and leaf frame
                call_stack: list[StackFrame] = []
                for cp in reversed(self.checkpoints):
                    if site_key in cp.call_stacks:
                        call_stack = cp.call_stacks[site_key]
                        break

                leaf_frame = call_stack[-1] if call_stack else StackFrame(name=site_key)

                # Objects persisting across all checkpoints into Gen 2 are flagged immortal
                is_immortal = is_monotonic and (initial_bytes > 0)

                candidate = LeakCandidate(
                    site_key=site_key,
                    frame=leaf_frame,
                    initial_bytes=initial_bytes,
                    final_bytes=final_bytes,
                    growth_bytes=growth,
                    checkpoints_observed=len(history),
                    consecutive_increases=consecutive_increases,
                    call_stack=call_stack,
                    is_immortal=is_immortal,
                )
                candidates.append(candidate)
                total_leaked += growth

        # Sort descending by growth
        candidates.sort(key=lambda c: c.growth_bytes, reverse=True)

        return LeakReport(
            candidates=candidates,
            checkpoints_count=len(self.checkpoints),
            total_leaked_bytes=total_leaked,
        )

    def stop(self) -> LeakReport:
        """Finalize leak detection session and produce report."""
        if not self._is_active:
            return self.analyze()

        self.take_checkpoint()
        report = self.analyze()
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        self._is_active = False
        return report

    def _should_ignore(self, filename: str) -> bool:
        """Ignore internal flamelens and standard framework frames."""
        if self.config.include_internal:
            return False

        if "flamelens" in filename or "leak_detector.py" in filename:
            return True
        if "site-packages" in filename or "importlib" in filename:
            return True

        for pattern in self.config.ignore_patterns:
            if pattern in filename:
                return True
        return False
