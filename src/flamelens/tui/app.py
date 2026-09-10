"""Interactive Terminal UI application for exploring FlameLens profiles."""

from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Tree
from textual.widgets.tree import TreeNode

from flamelens.core.stack_tree import StackNode, StackTree
from flamelens.render.ascii_flame import format_bytes
from flamelens.render.colors import FlameColorPalette
from flamelens.tui.screens import HelpModal
from flamelens.tui.widgets import BreadcrumbBar, DetailsPanel


class FlameLensApp(App):
    """Main Textual application for interactive FlameGraph analysis."""

    CSS = """
    Screen {
        background: #121212;
    }
    #top-bar {
        height: auto;
        padding: 0 1;
        background: #1e1e1e;
        border-bottom: solid #333333;
    }
    #search-input {
        margin: 0 1;
        display: none;
    }
    #search-input.visible {
        display: block;
    }
    #main-container {
        height: 1fr;
    }
    #tree-view {
        width: 2fr;
        border-right: solid #333333;
        background: #181818;
    }
    #details-panel {
        width: 1fr;
        padding: 1;
        background: #151515;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("/", "toggle_search", "Search"),
        Binding("enter", "zoom_in", "Zoom In"),
        Binding("escape", "zoom_out", "Zoom Out"),
        Binding("m", "toggle_metric", "Toggle Churn/Retained"),
        Binding("d", "toggle_details", "Toggle Details"),
        Binding("question_mark", "help", "Help"),
    ]

    def __init__(
        self,
        tree: StackTree,
        retained_tree: StackTree | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.churn_tree = tree
        self.retained_tree = retained_tree or tree
        self.active_metric = "churn"  # or "retained"
        self.original_tree = self.churn_tree
        self.current_tree = self.churn_tree
        self.zoom_history: list[StackTree] = []
        self.zoom_path: list[str] = ["Root (Churn)"]
        self.selected_node: StackNode | None = None
        self.search_filter: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="top-bar"):
            yield BreadcrumbBar(id="breadcrumbs")
            yield Input(placeholder="Search function or file...", id="search-input")
        with Horizontal(id="main-container"):
            yield Tree("Root", id="tree-view")
            yield DetailsPanel(id="details-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize tree and breadcrumbs on application startup."""
        self._refresh_tree_view()
        breadcrumbs = self.query_one(BreadcrumbBar)
        breadcrumbs.update_path(self.zoom_path)

    def _refresh_tree_view(self) -> None:
        """Populate Textual Tree widget from current StackTree data."""
        tree_widget = self.query_one("#tree-view", Tree)
        tree_widget.clear()

        total = self.current_tree.total_bytes
        root_node = self.current_tree.root
        tree_widget.root.data = root_node
        tree_widget.root.label = Text(
            f"{root_node.frame.name} [{format_bytes(root_node.inclusive_bytes)}]",
            style="bold yellow",
        )

        def _populate(parent_widget_node: TreeNode[StackNode], node: StackNode) -> None:
            for child in node.sorted_children():
                pct = (child.inclusive_bytes / total) * 100.0 if total > 0 else 0.0

                label = Text()
                # Apply warm color based on allocation percentage
                hex_color = FlameColorPalette.get_warm_color(pct)
                label.append(child.frame.display_name, style=f"bold {hex_color}")
                label.append(
                    f" [{format_bytes(child.inclusive_bytes)}, {pct:.1f}%]", style="dim white"
                )

                # Match highlight
                if self.search_filter and self.search_filter.lower() in child.frame.name.lower():
                    label.stylize("reverse bold magenta")

                child_widget_node = parent_widget_node.add(label, data=child)
                if child.children:
                    _populate(child_widget_node, child)

        _populate(tree_widget.root, root_node)
        tree_widget.root.expand()

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Update details panel when user selects a frame in the tree."""
        if event.node and event.node.data:
            self.selected_node = event.node.data
            panel = self.query_one(DetailsPanel)
            panel.update_node(self.selected_node, self.current_tree.total_bytes)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter tree dynamically as search query changes."""
        self.search_filter = event.value.strip()
        self._refresh_tree_view()

    def action_toggle_search(self) -> None:
        """Toggle visibility and focus of the search bar."""
        search_input = self.query_one("#search-input", Input)
        if search_input.has_class("visible"):
            search_input.remove_class("visible")
            self.search_filter = ""
            self.query_one("#tree-view").focus()
            self._refresh_tree_view()
        else:
            search_input.add_class("visible")
            search_input.focus()

    def action_zoom_in(self) -> None:
        """Zoom into the selected sub-node and rebase the tree."""
        if not self.selected_node or self.selected_node == self.current_tree.root:
            return

        zoomed = self.current_tree.zoom_subnode(self.selected_node.identifier)
        if zoomed:
            self.zoom_history.append(self.current_tree)
            self.zoom_path.append(self.selected_node.frame.name)
            self.current_tree = zoomed
            self._refresh_tree_view()

            breadcrumbs = self.query_one(BreadcrumbBar)
            breadcrumbs.update_path(self.zoom_path)

    def action_zoom_out(self) -> None:
        """Step back to previous zoom level."""
        if self.zoom_history:
            self.current_tree = self.zoom_history.pop()
            self.zoom_path.pop()
            self._refresh_tree_view()

            breadcrumbs = self.query_one(BreadcrumbBar)
            breadcrumbs.update_path(self.zoom_path)

    def action_toggle_metric(self) -> None:
        """Switch between allocation churn and live retained heap trees."""
        if self.active_metric == "churn":
            self.active_metric = "retained"
            self.current_tree = self.retained_tree
            self.zoom_history.clear()
            self.zoom_path = ["Root (Retained)"]
        else:
            self.active_metric = "churn"
            self.current_tree = self.churn_tree
            self.zoom_history.clear()
            self.zoom_path = ["Root (Churn)"]

        self._refresh_tree_view()
        breadcrumbs = self.query_one(BreadcrumbBar)
        breadcrumbs.update_path(self.zoom_path)

    def action_toggle_details(self) -> None:
        """Toggle visibility of the details panel."""
        panel = self.query_one("#details-panel")
        panel.display = not panel.display

    def action_help(self) -> None:
        """Show keyboard shortcuts modal."""
        self.push_screen(HelpModal())
