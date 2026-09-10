"""Non-interactive terminal ASCII and Unicode flamegraph generator."""

from __future__ import annotations

from flamelens.core.stack_tree import StackNode, StackTree
from flamelens.render.colors import FlameColorPalette


def format_bytes(num_bytes: int) -> str:
    """Format byte count into readable KB, MB, or GB."""
    if abs(num_bytes) >= 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
    if abs(num_bytes) >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    if abs(num_bytes) >= 1024:
        return f"{num_bytes / 1024:.2f} KB"
    return f"{num_bytes} B"


def render_ascii_flamegraph(
    tree: StackTree,
    max_depth: int = 16,
    threshold_pct: float = 0.5,
    use_color: bool = True,
) -> str:
    """Render StackTree into a formatted terminal ASCII tree with allocation metrics."""
    total_bytes = tree.total_bytes
    if total_bytes == 0:
        return "Empty profile (0 bytes allocated)."

    reset_code = "\033[0m" if use_color else ""
    lines: list[str] = []

    # Root header
    lines.append(
        f"FlameLens Profile: {format_bytes(total_bytes)} total allocated across "
        f"{tree.total_allocations} samples"
    )
    lines.append("=" * 80)

    def _render_node(node: StackNode, prefix: str, is_last: bool, depth: int) -> None:
        if depth > max_depth:
            return

        pct = (node.inclusive_bytes / total_bytes) * 100.0 if total_bytes > 0 else 0.0
        if pct < threshold_pct:
            return

        connector = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        color_prefix = FlameColorPalette.get_warm_ansi(pct) if use_color else ""

        # Bottleneck marker if this node represents > 50% of allocations or large self-bytes
        is_bottleneck = pct >= 50.0 and node.self_bytes > (node.inclusive_bytes * 0.4)
        tag = " [BOTTLENECK]" if is_bottleneck else ""

        # Progress bar representation: e.g. [████░░░░░░] 40.0%
        bar_width = 10
        filled = int((pct / 100.0) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        line_str = (
            f"{prefix}{connector}{color_prefix}{node.frame.display_name} "
            f"[{format_bytes(node.inclusive_bytes)}, {pct:.1f}%] [{bar}]{tag}{reset_code}"
        )
        lines.append(line_str)

        sorted_children = node.sorted_children()
        filtered_children = [
            c
            for c in sorted_children
            if ((c.inclusive_bytes / total_bytes) * 100.0) >= threshold_pct
        ]

        for i, child in enumerate(filtered_children):
            _render_node(
                child,
                child_prefix,
                is_last=(i == len(filtered_children) - 1),
                depth=depth + 1,
            )

    # Render direct children of root
    root_children = [
        c
        for c in tree.root.sorted_children()
        if ((c.inclusive_bytes / total_bytes) * 100.0) >= threshold_pct
    ]

    for i, child in enumerate(root_children):
        _render_node(
            child,
            prefix="",
            is_last=(i == len(root_children) - 1),
            depth=1,
        )

    if not root_children:
        lines.append("No call frames met the threshold criteria.")

    lines.append("=" * 80)
    return "\n".join(lines)
