"""Unit tests for AllocationMonitor and PEP 669 sys.monitoring."""

from flamelens.config import ProfilerConfig
from flamelens.profiler.monitor import AllocationMonitor


def sample_allocation_workload(storage: list):
    """Synthetic workload allocating memory in nested functions and retaining it."""

    def inner_alloc():
        # Allocate 2MB bytearray and keep reference in storage
        buf = bytearray(2 * 1024 * 1024)
        storage.append(buf)
        return len(buf)

    return inner_alloc()


def test_allocation_monitor_captures_nested_allocations():
    config = ProfilerConfig(sample_rate=0, include_internal=True)
    monitor = AllocationMonitor(config=config)
    retained: list = []

    with monitor.profile():
        result = sample_allocation_workload(retained)
        assert result == 2 * 1024 * 1024

    assert monitor.tree.total_bytes >= 2 * 1024 * 1024
    assert monitor.tree.total_allocations > 0

    # Search for inner_alloc in the captured tree
    matches = monitor.tree.search_nodes("inner_alloc")
    assert len(matches) > 0
    assert matches[0].inclusive_bytes >= 2 * 1024 * 1024


def test_allocation_monitor_clean_start_stop():
    monitor = AllocationMonitor()
    monitor.start()
    x = [i for i in range(1000)]
    assert len(x) == 1000
    tree = monitor.stop()

    assert tree is not None
    # Stopping twice is safe
    tree2 = monitor.stop()
    assert tree2 is not None


def test_allocation_monitor_record_current_allocation():
    monitor = AllocationMonitor()
    monitor.record_current_allocation(1024 * 1024)
    assert monitor.tree.total_bytes == 1024 * 1024
