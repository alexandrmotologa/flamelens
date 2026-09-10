"""Utilities for reading and writing Brendan Gregg collapsed stack format."""

from pathlib import Path

from flamelens.core.stack_tree import StackTree


def load_folded_file(filepath: str | Path) -> StackTree:
    """Read a collapsed stack file and parse it into a StackTree."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Folded stack file not found: {path}")

    content = path.read_text(encoding="utf-8")
    return StackTree.from_folded_stacks(content)


def save_folded_file(tree: StackTree, filepath: str | Path) -> None:
    """Write StackTree data to a collapsed stack file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = tree.to_folded_stacks()
    path.write_text(content, encoding="utf-8")
