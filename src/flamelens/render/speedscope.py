"""Speedscope (https://www.speedscope.app) JSON format exporter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackNode, StackTree


def export_to_speedscope(
    tree: StackTree,
    output_path: str | Path,
    name: str = "FlameLens Memory Profile",
) -> None:
    """Serialize StackTree into the official Speedscope file format."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Frame dictionary to establish unique indexed pool
    frame_indices: dict[str, int] = {}
    shared_frames: list[dict[str, Any]] = []

    def _get_frame_index(frame: StackFrame) -> int:
        key = frame.identifier
        if key not in frame_indices:
            idx = len(shared_frames)
            frame_indices[key] = idx
            shared_frames.append(
                {
                    "name": frame.name,
                    "file": frame.short_filename,
                    "line": frame.line_number if frame.line_number > 0 else None,
                }
            )
        return frame_indices[key]

    samples: list[list[int]] = []
    weights: list[int] = []

    def _collect_samples(node: StackNode, current_path: list[int]) -> None:
        frame_idx = _get_frame_index(node.frame)
        path_with_node = current_path + [frame_idx]

        # If node has self allocations, emit a sample
        if node.self_bytes > 0:
            samples.append(path_with_node)
            weights.append(node.self_bytes)

        for child in node.children.values():
            _collect_samples(child, path_with_node)

    # Walk children of root
    for child in tree.root.children.values():
        _collect_samples(child, [])

    # If no self-bytes recorded, emit root summary sample
    if not samples and tree.total_bytes > 0:
        root_idx = _get_frame_index(tree.root.frame)
        samples.append([root_idx])
        weights.append(tree.total_bytes)

    speedscope_doc = {
        "$schema": "https://www.speedscope.app/file-format-schema.json",
        "version": "0.0.1",
        "exporter": "flamelens@0.1.0",
        "name": name,
        "activeProfileIndex": 0,
        "profiles": [
            {
                "type": "sampled",
                "name": name,
                "unit": "bytes",
                "startValue": 0,
                "endValue": tree.total_bytes,
                "samples": samples,
                "weights": weights,
            }
        ],
        "shared": {
            "frames": shared_frames,
        },
    }

    path.write_text(json.dumps(speedscope_doc, indent=2), encoding="utf-8")
