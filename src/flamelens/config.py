"""Configuration models for FlameLens profiling and analysis."""

from pydantic import BaseModel, Field


class ProfilerConfig(BaseModel):
    """Configuration options for allocation profiling, quality gates, and aggregation."""

    sample_rate: int = Field(
        default=0,
        description="Sampling interval in bytes for Poisson sampler. 0 enables exact tracking.",
    )
    max_depth: int = Field(
        default=64,
        ge=1,
        le=512,
        description="Maximum call stack depth to record.",
    )
    threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=100.0,
        description="Minimum percentage of total memory for a frame to appear in reports.",
    )
    leak_detect: bool = Field(
        default=False,
        description="Enable generational garbage collection retention tracking.",
    )
    checkpoints: int = Field(
        default=5,
        ge=2,
        le=50,
        description="Number of GC evaluation checkpoints during profiling.",
    )
    min_growth_mb: float = Field(
        default=1.0,
        ge=0.01,
        description="Minimum net memory increase in megabytes to qualify as a leak candidate.",
    )
    max_mem_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="Maximum permissible memory budget in MB for CI quality gates (0 disables).",
    )
    max_leak_rate_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="Maximum permissible leak rate in MB per checkpoint for CI quality gates.",
    )
    fail_on_leak: bool = Field(
        default=False,
        description="Exit with non-zero error code if any leak candidates are identified.",
    )
    spike_threshold_mb: float = Field(
        default=5.0,
        ge=0.1,
        description="Memory surge threshold in megabytes to trigger a high-watermark spike snapshot.",
    )
    include_internal: bool = Field(
        default=False,
        description="Whether to include flamelens and standard library internal frames.",
    )
    ignore_patterns: list[str] = Field(
        default_factory=lambda: ["flamelens", "site-packages", "threading.py", "importlib"],
        description="Substrings of filenames or modules to ignore from stack traces.",
    )
