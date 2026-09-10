"""High-watermark memory spike detection and snapshot isolation."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from types import FrameType
from typing import Any

from flamelens.core.frame import StackFrame


@dataclass
class SpikeIncident:
    """Represents a rapid surge in memory allocation exceeding the configured threshold."""

    timestamp: float
    delta_bytes: int
    current_bytes: int
    peak_bytes: int
    call_stack: list[StackFrame] = field(default_factory=list)

    @property
    def delta_mb(self) -> float:
        return self.delta_bytes / (1024 * 1024)

    @property
    def current_mb(self) -> float:
        return self.current_bytes / (1024 * 1024)

    @property
    def peak_mb(self) -> float:
        return self.peak_bytes / (1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "delta_bytes": self.delta_bytes,
            "delta_mb": round(self.delta_mb, 2),
            "current_bytes": self.current_bytes,
            "current_mb": round(self.current_mb, 2),
            "peak_bytes": self.peak_bytes,
            "peak_mb": round(self.peak_mb, 2),
            "call_stack": [f.to_dict() for f in self.call_stack],
        }


class SpikeDetector:
    """Monitors memory increments and isolates stack traces at surge moments."""

    def __init__(self, threshold_mb: float = 5.0) -> None:
        self.threshold_bytes = int(threshold_mb * 1024 * 1024)
        self.last_checked_bytes = 0
        self.spikes: list[SpikeIncident] = []

    def check(
        self, current_bytes: int, peak_bytes: int, frame: FrameType | None = None
    ) -> SpikeIncident | None:
        """Evaluate whether current memory constitutes an allocation spike."""
        delta = current_bytes - self.last_checked_bytes
        self.last_checked_bytes = current_bytes

        if delta >= self.threshold_bytes:
            # Capture current call stack
            if frame is None:
                try:
                    frame = sys._getframe(1)
                except ValueError:
                    frame = None

            call_stack: list[StackFrame] = []
            curr = frame
            depth = 0
            while curr and depth < 32:
                code = curr.f_code
                fn = code.co_filename
                if "flamelens" not in fn and "site-packages" not in fn:
                    call_stack.append(
                        StackFrame(
                            name=code.co_qualname,
                            filename=fn,
                            line_number=curr.f_lineno,
                        )
                    )
                    depth += 1
                curr = curr.f_back

            incident = SpikeIncident(
                timestamp=time.time(),
                delta_bytes=delta,
                current_bytes=current_bytes,
                peak_bytes=peak_bytes,
                call_stack=list(reversed(call_stack)),
            )
            self.spikes.append(incident)
            return incident

        return None
