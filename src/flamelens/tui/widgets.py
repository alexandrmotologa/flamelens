"""Custom Textual widgets for interactive flamegraph exploration."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Static

from flamelens.core.stack_tree import StackNode
from flamelens.render.ascii_flame import format_bytes


class BreadcrumbBar(Static):
    """Displays current zoom hierarchy breadcrumbs."""

    def update_path(self, path: list[str]) -> None:
        """Render path segments with arrow separators."""
        if not path:
            self.update(Text("Zoom: Root", style="bold cyan"))
            return

        text = Text("Zoom: ", style="bold cyan")
        for i, segment in enumerate(path):
            if i > 0:
                text.append(" > ", style="dim")
            text.append(segment, style="bold yellow" if i == len(path) - 1 else "white")
        self.update(text)


class DetailsPanel(Static):
    """Inspector sidebar showing detailed allocation metrics for selected node."""

    def update_node(self, node: StackNode | None, total_bytes: int) -> None:
        """Render metrics table and top child allocation sites."""
        if not node:
            self.update(Panel("Select a node to inspect details", title="Details"))
            return

        pct = (node.inclusive_bytes / total_bytes) * 100.0 if total_bytes > 0 else 0.0
        self_pct = (node.self_bytes / total_bytes) * 100.0 if total_bytes > 0 else 0.0

        table = Table.grid(padding=(0, 1))
        table.add_column("Key", style="bold cyan")
        table.add_column("Value", style="white")

        table.add_row("Function", node.frame.name)
        table.add_row("File", node.frame.short_filename)
        table.add_row("Line", str(node.frame.line_number) if node.frame.line_number else "N/A")
        table.add_row("Inclusive", f"{format_bytes(node.inclusive_bytes)} ({pct:.1f}%)")
        table.add_row("Self", f"{format_bytes(node.self_bytes)} ({self_pct:.1f}%)")
        table.add_row("Call count", str(node.call_count))

        # Top 5 child functions
        content = Vertical(table)
        children = node.sorted_children()
        if children:
            child_table = Table(title="Top Allocating Children", show_header=True)
            child_table.add_column("Child Function", style="yellow")
            child_table.add_column("Inclusive", justify="right")
            for c in children[:5]:
                c_pct = (
                    (c.inclusive_bytes / node.inclusive_bytes) * 100.0
                    if node.inclusive_bytes > 0
                    else 0.0
                )
                child_table.add_row(
                    c.frame.name, f"{format_bytes(c.inclusive_bytes)} ({c_pct:.1f}%)"
                )
            content = Vertical(table, Static(""), child_table)

        self.update(Panel(content, title=f"Frame: {node.frame.name}", border_style="gold1"))
