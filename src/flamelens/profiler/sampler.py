"""Probabilistic allocation sampler based on exponential distribution (Poisson process)."""

import math
import random


class PoissonSampler:
    """Probabilistic memory allocation sampler.

    Samples allocations at random intervals drawn from an exponential distribution
    with mean equal to the configured sample_rate in bytes. This allows profiling
    high-throughput workloads while keeping runtime overhead low.
    """

    def __init__(self, sample_rate: int = 0) -> None:
        self.sample_rate = max(0, sample_rate)
        self._bytes_until_sample = self._next_interval()
        self.total_allocated = 0
        self.sample_count = 0

    def _next_interval(self) -> int:
        """Draw next sampling threshold from an exponential distribution."""
        if self.sample_rate <= 0:
            return 0
        u = random.random()
        # Avoid log(0)
        while u == 0.0:
            u = random.random()
        return max(1, int(-math.log(u) * self.sample_rate))

    def should_sample(self, size: int) -> bool:
        """Check if an allocation of the given size in bytes triggers a sample."""
        self.total_allocated += size

        if self.sample_rate <= 0:
            # Exact tracing mode: capture every event
            self.sample_count += 1
            return True

        if size >= self._bytes_until_sample:
            self._bytes_until_sample = self._next_interval()
            self.sample_count += 1
            return True

        self._bytes_until_sample -= size
        return False
