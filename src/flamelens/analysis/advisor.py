"""Automated bottleneck diagnosis and remediation advisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackNode, StackTree
from flamelens.render.ascii_flame import format_bytes


@dataclass
class CulpritRecord:
    """Represents an identified memory allocation culprit with remediation recommendations."""

    frame: StackFrame
    inclusive_bytes: int
    self_bytes: int
    impact_pct: float
    call_count: int
    category: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame.to_dict(),
            "inclusive_bytes": self.inclusive_bytes,
            "inclusive_formatted": format_bytes(self.inclusive_bytes),
            "self_bytes": self.self_bytes,
            "self_formatted": format_bytes(self.self_bytes),
            "impact_pct": round(self.impact_pct, 2),
            "call_count": self.call_count,
            "category": self.category,
            "recommendation": self.recommendation,
        }


@dataclass
class AnalysisReport:
    """Comprehensive analysis report with prioritized optimization recommendations."""

    total_bytes: int
    total_allocations: int
    culprits: list[CulpritRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_bytes": self.total_bytes,
            "total_formatted": format_bytes(self.total_bytes),
            "total_allocations": self.total_allocations,
            "culprits": [c.to_dict() for c in self.culprits],
        }

    def format_report(self) -> str:
        """Produce clean human-readable diagnostic report."""
        if not self.culprits:
            return "No prominent memory allocation bottlenecks detected."

        lines = [
            f"FlameLens Optimization Advisory ({len(self.culprits)} bottlenecks identified)",
            f"Total Memory Profiled: {format_bytes(self.total_bytes)} across {self.total_allocations} samples",
            "=" * 80,
        ]

        for i, c in enumerate(self.culprits, 1):
            lines.append(f"{i}. [{c.category.upper()}] {c.frame.display_name}")
            lines.append(
                f"   Impact: {format_bytes(c.inclusive_bytes)} ({c.impact_pct:.1f}% of total) | "
                f"Self: {format_bytes(c.self_bytes)} | Calls: {c.call_count}"
            )
            lines.append(f"   Recommendation: {c.recommendation}")
            lines.append("-" * 80)

        return "\n".join(lines)


class Advisor:
    """Inspects StackTree profiles and infers actionable optimization advice."""

    @classmethod
    def _determine_category_and_recommendation(
        cls,
        name: str,
        inclusive_bytes: int,
        self_bytes: int,
        impact_pct: float,
    ) -> tuple[str, str]:
        lower_name = name.lower()

        if "cache" in lower_name or "dict" in lower_name or "store" in lower_name:
            category = "Unbounded Storage / Cache"
            rec = "Ensure collections have size bounds (e.g. functools.lru_cache(maxsize=1024) or TTL expiry)."
        elif "json" in lower_name or "parse" in lower_name or "load" in lower_name or "decode" in lower_name:
            category = "Data Parsing Overhead"
            rec = "Consider streaming parsers (like ijson) or optimized C-extensions (orjson/msgpack) to reduce churn."
        elif "append" in lower_name or "extend" in lower_name or "list" in lower_name:
            category = "Eager Collection Growth"
            rec = "Replace eager list accumulation with generators (`yield`) or itertools to stream elements."
        elif "concat" in lower_name or "join" in lower_name or "str" in lower_name:
            category = "String Allocation Churn"
            rec = "Avoid repetitive string concatenation with `+`. Use `''.join()` or StringIO."
        elif self_bytes > (inclusive_bytes * 0.5) and impact_pct > 25.0:
            category = "Dominant Allocation Leaf"
            rec = "Direct memory allocation hotspot. Use memoryview, pre-allocated buffers, or vectorization."
        else:
            category = "High Memory Call Path"
            rec = "Refactor function to stream chunks or evaluate lazy loading for child dependencies."

        return category, rec

    @classmethod
    def analyze(cls, tree: StackTree, min_impact_pct: float = 10.0) -> AnalysisReport:
        """Scan StackTree and return prioritized list of allocation culprits."""
        total_bytes = tree.total_bytes
        if total_bytes == 0:
            return AnalysisReport(total_bytes=0, total_allocations=0)

        culprits_map: dict[str, CulpritRecord] = {}

        def _traverse(node: StackNode) -> None:
            if node != tree.root:
                pct = (node.inclusive_bytes / total_bytes) * 100.0
                if pct >= min_impact_pct:
                    cat, rec = cls._determine_category_and_recommendation(
                        node.frame.name,
                        node.inclusive_bytes,
                        node.self_bytes,
                        pct,
                    )
                    record = CulpritRecord(
                        frame=node.frame,
                        inclusive_bytes=node.inclusive_bytes,
                        self_bytes=node.self_bytes,
                        impact_pct=pct,
                        call_count=node.call_count,
                        category=cat,
                        recommendation=rec,
                    )
                    # Keep highest impact if frame appears in multiple stacks
                    key = node.frame.identifier
                    if (
                        key not in culprits_map
                        or culprits_map[key].inclusive_bytes < record.inclusive_bytes
                    ):
                        culprits_map[key] = record

            for child in node.children.values():
                _traverse(child)

        _traverse(tree.root)

        # Sort descending by impact percentage
        sorted_culprits = sorted(
            culprits_map.values(),
            key=lambda c: (c.self_bytes, c.inclusive_bytes),
            reverse=True,
        )

        return AnalysisReport(
            total_bytes=total_bytes,
            total_allocations=tree.total_allocations,
            culprits=sorted_culprits,
        )
