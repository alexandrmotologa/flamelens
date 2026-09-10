"""Prefix-tree (Trie) aggregating stack frames into hierarchical allocation metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from flamelens.core.frame import StackFrame


@dataclass
class StackNode:
    """Node in the Trie representing a specific call frame at a specific depth."""

    frame: StackFrame
    inclusive_bytes: int = 0
    self_bytes: int = 0
    call_count: int = 0
    children: dict[str, StackNode] = field(default_factory=dict)
    parent_signature: str | None = None

    @property
    def identifier(self) -> str:
        """Stable frame identifier."""
        return self.frame.identifier

    @property
    def inclusive_mb(self) -> float:
        """Inclusive allocation formatted in megabytes."""
        return self.inclusive_bytes / (1024 * 1024)

    @property
    def self_mb(self) -> float:
        """Self allocation formatted in megabytes."""
        return self.self_bytes / (1024 * 1024)

    def get_or_create_child(self, frame: StackFrame) -> StackNode:
        """Retrieve existing child by frame identifier or initialize a new one."""
        key = frame.identifier
        if key not in self.children:
            self.children[key] = StackNode(
                frame=frame,
                parent_signature=self.frame.identifier,
            )
        return self.children[key]

    def sorted_children(self, key_metric: str = "inclusive_bytes") -> list[StackNode]:
        """Return children sorted descending by chosen metric."""
        return sorted(
            self.children.values(),
            key=lambda node: getattr(node, key_metric),
            reverse=True,
        )

    def to_dict(self) -> dict[str, Any]:
        """Recursively serialize node to dictionary."""
        return {
            "frame": self.frame.to_dict(),
            "inclusive_bytes": self.inclusive_bytes,
            "self_bytes": self.self_bytes,
            "call_count": self.call_count,
            "children": {k: child.to_dict() for k, child in self.children.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], parent_signature: str | None = None) -> StackNode:
        """Recursively deserialize node from dictionary."""
        frame = StackFrame.from_dict(data.get("frame", {}))
        node = cls(
            frame=frame,
            inclusive_bytes=int(data.get("inclusive_bytes", 0)),
            self_bytes=int(data.get("self_bytes", 0)),
            call_count=int(data.get("call_count", 0)),
            parent_signature=parent_signature,
        )
        for child_dict in data.get("children", {}).values():
            child_node = cls.from_dict(child_dict, parent_signature=frame.identifier)
            node.children[child_node.identifier] = child_node
        return node


class StackTree:
    """Trie structure storing aggregated stack traces and memory metrics."""

    def __init__(self, root_name: str = "root") -> None:
        self.root: StackNode = StackNode(frame=StackFrame(name=root_name))
        self.total_bytes: int = 0
        self.total_allocations: int = 0

    def insert_stack(self, frames: list[StackFrame], allocated_bytes: int) -> None:
        """Insert a call stack (caller to callee order) with its allocated bytes."""
        if not frames:
            return

        self.total_bytes += allocated_bytes
        self.total_allocations += 1

        self.root.inclusive_bytes += allocated_bytes
        self.root.call_count += 1

        current = self.root
        for frame in frames:
            current = current.get_or_create_child(frame)
            current.inclusive_bytes += allocated_bytes
            current.call_count += 1

        current.self_bytes += allocated_bytes

    def find_node_by_identifier(self, identifier: str) -> StackNode | None:
        """Search tree for a node matching the given frame identifier."""
        if self.root.identifier == identifier:
            return self.root

        stack = [self.root]
        while stack:
            node = stack.pop()
            if node.identifier == identifier:
                return node
            stack.extend(node.children.values())
        return None

    def search_nodes(self, query: str) -> list[StackNode]:
        """Find all nodes whose frame name, filename, or signature contains query string."""
        q = query.lower()
        results: list[StackNode] = []
        stack = [self.root]

        while stack:
            node = stack.pop()
            if node != self.root:
                match = (
                    q in node.frame.name.lower()
                    or q in node.frame.filename.lower()
                    or q in node.frame.identifier.lower()
                )
                if match:
                    results.append(node)
            stack.extend(node.children.values())

        return sorted(results, key=lambda n: n.inclusive_bytes, reverse=True)

    def prune(self, threshold_pct: float) -> StackTree:
        """Return a new StackTree containing only nodes meeting the threshold percentage."""
        if self.total_bytes == 0 or threshold_pct <= 0:
            return self

        min_bytes = int(self.total_bytes * (threshold_pct / 100.0))
        pruned_tree = StackTree(root_name=self.root.frame.name)
        pruned_tree.total_bytes = self.total_bytes
        pruned_tree.total_allocations = self.total_allocations

        def _copy_pruned(source: StackNode, target: StackNode) -> None:
            target.inclusive_bytes = source.inclusive_bytes
            target.self_bytes = source.self_bytes
            target.call_count = source.call_count
            for child in source.children.values():
                if child.inclusive_bytes >= min_bytes:
                    new_child = target.get_or_create_child(child.frame)
                    _copy_pruned(child, new_child)

        _copy_pruned(self.root, pruned_tree.root)
        return pruned_tree

    def zoom_subnode(self, identifier: str) -> StackTree | None:
        """Rebase the tree with the selected node as root, recalculating relative metrics."""
        target = self.find_node_by_identifier(identifier)
        if not target:
            return None

        zoomed_tree = StackTree(root_name=target.frame.name)
        zoomed_tree.total_bytes = target.inclusive_bytes
        zoomed_tree.total_allocations = target.call_count

        def _copy_tree(src: StackNode, dst: StackNode) -> None:
            dst.inclusive_bytes = src.inclusive_bytes
            dst.self_bytes = src.self_bytes
            dst.call_count = src.call_count
            for child in src.children.values():
                new_child = dst.get_or_create_child(child.frame)
                _copy_tree(child, new_child)

        _copy_tree(target, zoomed_tree.root)
        return zoomed_tree

    def to_folded_stacks(self) -> str:
        """Export stack tree to Brendan Gregg folded format (frameA;frameB count)."""
        lines: list[str] = []

        def _walk(node: StackNode, path: list[str]) -> None:
            current_path = path + [node.frame.name] if node != self.root else path
            if node.self_bytes > 0 and current_path:
                lines.append(f"{';'.join(current_path)} {node.self_bytes}")
            for child in node.children.values():
                _walk(child, current_path)

        _walk(self.root, [])
        return "\n".join(lines)

    @classmethod
    def from_folded_stacks(cls, content: str) -> StackTree:
        """Construct a StackTree from Brendan Gregg collapsed stack text."""
        tree = cls()
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue

            stack_str, count_str = parts
            try:
                allocated_bytes = int(count_str)
            except ValueError:
                continue

            frames = [
                StackFrame.from_raw_string(token) for token in stack_str.split(";") if token.strip()
            ]
            if frames:
                tree.insert_stack(frames, allocated_bytes)

        return tree

    def to_dict(self) -> dict[str, Any]:
        """Serialize tree to dictionary."""
        return {
            "total_bytes": self.total_bytes,
            "total_allocations": self.total_allocations,
            "root": self.root.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StackTree:
        """Deserialize tree from dictionary."""
        tree = cls()
        tree.total_bytes = int(data.get("total_bytes", 0))
        tree.total_allocations = int(data.get("total_allocations", 0))
        if "root" in data:
            tree.root = StackNode.from_dict(data["root"])
        return tree

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize tree to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> StackTree:
        """Deserialize tree from JSON string."""
        return cls.from_dict(json.loads(json_str))
