"""Configuration models for FlameLens profiling and analysis."""

from pydantic import BaseModel, Field


class ProfilerConfig(BaseModel):
    """Configuration options for allocation profiling and aggregation."""

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
    include_internal: bool = Field(
        default=False,
        description="Whether to include flamelens and standard library internal frames.",
    )
    ignore_patterns: list[str] = Field(
        default_factory=lambda: ["flamelens", "site-packages/pytest", "threading.py"],
        description="Substrings of filenames or modules to ignore from stack traces.",
    )
