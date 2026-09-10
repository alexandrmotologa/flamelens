"""Differential FlameGraph comparison engine (FlameDiff)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackNode, StackTree
from flamelens.render.ascii_flame import format_bytes
from flamelens.render.colors import FlameColorPalette


@dataclass
class DiffNode:
    """Represents a node with comparative allocation metrics between two profiles."""

    frame: StackFrame
    baseline_bytes: int = 0
    candidate_bytes: int = 0
    delta_bytes: int = 0
    delta_pct: float = 0.0
    children: dict[str, DiffNode] = field(default_factory=dict)

    @property
    def identifier(self) -> str:
        return self.frame.identifier

    def sorted_children(self) -> list[DiffNode]:
        """Return children sorted descending by absolute delta magnitude."""
        return sorted(self.children.values(), key=lambda n: abs(n.delta_bytes), reverse=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame.to_dict(),
            "baseline_bytes": self.baseline_bytes,
            "candidate_bytes": self.candidate_bytes,
            "delta_bytes": self.delta_bytes,
            "delta_pct": round(self.delta_pct, 2),
            "children": {k: c.to_dict() for k, c in self.children.items()},
        }


class DiffTree:
    """Comparative tree mapping allocation deltas between baseline and candidate profiles."""

    def __init__(self, baseline_total: int, candidate_total: int) -> None:
        self.baseline_total = baseline_total
        self.candidate_total = candidate_total
        self.delta_total = candidate_total - baseline_total
        self.root: DiffNode = DiffNode(
            frame=StackFrame(name="Root Differential"),
            baseline_bytes=baseline_total,
            candidate_bytes=candidate_total,
            delta_bytes=self.delta_total,
            delta_pct=((self.delta_total / baseline_total * 100.0) if baseline_total > 0 else 0.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_total": self.baseline_total,
            "candidate_total": self.candidate_total,
            "delta_total": self.delta_total,
            "root": self.root.to_dict(),
        }

    def render_ascii(
        self, max_depth: int = 16, min_delta_bytes: int = 1024, use_color: bool = True
    ) -> str:
        """Render differential tree to terminal ASCII."""
        lines = [
            f"FlameLens Diff: Baseline {format_bytes(self.baseline_total)} -> "
            f"Candidate {format_bytes(self.candidate_total)} "
            f"({'+' if self.delta_total >= 0 else ''}{format_bytes(self.delta_total)})",
            "=" * 80,
        ]

        reset = "\033[0m" if use_color else ""
        max_abs_delta = max(1, abs(self.delta_total))

        def _render_node(node: DiffNode, prefix: str, is_last: bool, depth: int) -> None:
            if depth > max_depth or abs(node.delta_bytes) < min_delta_bytes:
                return

            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            color_code = (
                FlameColorPalette.get_diff_ansi(node.delta_bytes, max_abs_delta)
                if use_color
                else ""
            )
            sign = "+" if node.delta_bytes > 0 else ""
            delta_str = f"{sign}{format_bytes(node.delta_bytes)}"

            line_str = (
                f"{prefix}{connector}{color_code}{node.frame.display_name} "
                f"[{delta_str}, {node.delta_pct:+.1f}%] "
                f"(Base: {format_bytes(node.baseline_bytes)}, Cand: {format_bytes(node.candidate_bytes)})"
                f"{reset}"
            )
            lines.append(line_str)

            sorted_kids = [
                c for c in node.sorted_children() if abs(c.delta_bytes) >= min_delta_bytes
            ]
            for i, child in enumerate(sorted_kids):
                _render_node(
                    child,
                    child_prefix,
                    is_last=(i == len(sorted_kids) - 1),
                    depth=depth + 1,
                )

        root_kids = [
            c for c in self.root.sorted_children() if abs(c.delta_bytes) >= min_delta_bytes
        ]
        for i, child in enumerate(root_kids):
            _render_node(child, prefix="", is_last=(i == len(root_kids) - 1), depth=1)

        if not root_kids:
            lines.append("No significant allocation changes detected.")

        lines.append("=" * 80)
        return "\n".join(lines)


def compare_trees(baseline: StackTree, candidate: StackTree) -> DiffTree:
    """Construct a DiffTree comparing baseline and candidate StackTree profiles."""
    diff_tree = DiffTree(baseline.total_bytes, candidate.total_bytes)

    def _merge_nodes(
        base_node: StackNode | None, cand_node: StackNode | None, target_diff: DiffNode
    ) -> None:
        # Collect all child keys present in either node
        base_children = base_node.children if base_node else {}
        cand_children = cand_node.children if cand_node else {}
        all_keys = set(base_children.keys()) | set(cand_children.keys())

        for key in all_keys:
            b_child = base_children.get(key)
            c_child = cand_children.get(key)

            frame = c_child.frame if c_child else b_child.frame  # type: ignore
            b_bytes = b_child.inclusive_bytes if b_child else 0
            c_bytes = c_child.inclusive_bytes if c_child else 0
            delta = c_bytes - b_bytes

            pct = (delta / b_bytes * 100.0) if b_bytes > 0 else (100.0 if c_bytes > 0 else 0.0)

            diff_child = DiffNode(
                frame=frame,
                baseline_bytes=b_bytes,
                candidate_bytes=c_bytes,
                delta_bytes=delta,
                delta_pct=pct,
            )
            target_diff.children[key] = diff_child
            _merge_nodes(b_child, c_child, diff_child)

    _merge_nodes(baseline.root, candidate.root, diff_tree.root)
    return diff_tree
