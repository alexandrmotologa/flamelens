"""FlameLens: Interactive Memory Profiler & Terminal FlameGraph Engine."""

__version__ = "0.1.1"

from flamelens.config import ProfilerConfig
from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackNode, StackTree

__all__ = [
    "ProfilerConfig",
    "StackFrame",
    "StackNode",
    "StackTree",
    "__version__",
]
