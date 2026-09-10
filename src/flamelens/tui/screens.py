"""Modal screens for FlameLens TUI."""

from rich.panel import Panel
from rich.table import Table
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpModal(ModalScreen):
    """Help modal listing keyboard shortcuts and controls."""

    def compose(self) -> ComposeResult:
        table = Table(title="Keyboard Navigation", show_header=True)
        table.add_column("Key", style="bold cyan", justify="center")
        table.add_column("Action", style="white")

        table.add_row("↑ / ↓", "Navigate through call frames")
        table.add_row("Enter", "Zoom into selected frame (rebase as root)")
        table.add_row("Escape", "Zoom out to previous root or reset zoom")
        table.add_row("m", "Toggle between Allocation Churn and Retained Heap")
        table.add_row("/", "Focus search bar (highlights matching frames)")
        table.add_row("d", "Toggle details panel")
        table.add_row("?", "Show this help screen")
        table.add_row("q", "Quit FlameLens")

        panel = Panel(
            table,
            title="FlameLens Controls",
            border_style="yellow",
            subtitle="Press Escape or Enter to close",
        )
        with Middle():
            with Center():
                yield Static(panel)

    def on_key(self, event) -> None:
        if event.key in ("escape", "enter", "q", "question_mark"):
            self.dismiss()
