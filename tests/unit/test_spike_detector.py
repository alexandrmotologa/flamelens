"""Unit tests for SpikeDetector."""

from flamelens.profiler.spike_detector import SpikeDetector


def test_spike_detector_triggers_on_large_surges():
    # Set threshold to 1 MB
    detector = SpikeDetector(threshold_mb=1.0)

    # Initial state: 100 KB (no spike)
    inc1 = detector.check(100 * 1024, 100 * 1024)
    assert inc1 is None
    assert len(detector.spikes) == 0

    # Normal increment: +200 KB (no spike)
    inc2 = detector.check(300 * 1024, 300 * 1024)
    assert inc2 is None
    assert len(detector.spikes) == 0

    # Surge: from 300 KB to 2.5 MB (+2.2 MB >= 1.0 MB threshold)
    inc3 = detector.check(2500 * 1024, 2500 * 1024)
    assert inc3 is not None
    assert len(detector.spikes) == 1
    assert inc3.delta_bytes == 2200 * 1024
    assert inc3.delta_mb > 2.0

    d = inc3.to_dict()
    assert "timestamp" in d
    assert d["delta_mb"] > 2.0
