"""Unit tests for generational memory leak detector."""

from flamelens.config import ProfilerConfig
from flamelens.core.leak_detector import LeakDetector


class LeakingSessionCache:
    """Synthetic class retaining data across cycles."""

    def __init__(self) -> None:
        self.entries: list[bytearray] = []

    def allocate(self, size_kb: int = 256) -> None:
        self.entries.append(bytearray(size_kb * 1024))


def test_leak_detector_identifies_monotonic_growth():
    # Configure with small threshold so test runs fast
    config = ProfilerConfig(min_growth_mb=0.1, include_internal=False)
    detector = LeakDetector(config=config)

    cache = LeakingSessionCache()

    detector.start()  # Checkpoint 0

    # Iteration 1
    cache.allocate(256)
    detector.take_checkpoint()  # Checkpoint 1

    # Iteration 2
    cache.allocate(256)
    detector.take_checkpoint()  # Checkpoint 2

    # Iteration 3
    cache.allocate(256)
    report = detector.stop()  # Final checkpoint + analysis

    assert report.checkpoints_count >= 3
    assert len(report.candidates) >= 1

    top_candidate = report.candidates[0]
    assert top_candidate.growth_bytes >= 256 * 1024
    assert top_candidate.consecutive_increases >= 2

    summary = report.format_summary()
    assert "LEAK CANDIDATES DETECTED" in summary

    report_dict = report.to_dict()
    assert "candidates" in report_dict
    assert report_dict["total_leaked_bytes"] > 0
