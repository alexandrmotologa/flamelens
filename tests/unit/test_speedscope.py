"""Unit tests for Speedscope JSON format exporter."""

import json

from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackTree
from flamelens.render.speedscope import export_to_speedscope


def test_speedscope_export_matches_schema(tmp_path):
    tree = StackTree()
    f1 = StackFrame(name="app", filename="main.py", line_number=10)
    f2 = StackFrame(name="worker", filename="tasks.py", line_number=45)
    f3 = StackFrame(name="query_db", filename="db.py", line_number=120)

    tree.insert_stack([f1, f2, f3], 1048576)  # 1 MB
    tree.insert_stack([f1, f2], 524288)  # 0.5 MB

    out_file = tmp_path / "speedscope.json"
    export_to_speedscope(tree, out_file, name="Benchmark")

    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))

    assert data["$schema"] == "https://www.speedscope.app/file-format-schema.json"
    assert data["exporter"].startswith("flamelens@")
    assert data["name"] == "Benchmark"
    assert len(data["profiles"]) == 1

    profile = data["profiles"][0]
    assert profile["type"] == "sampled"
    assert profile["unit"] == "bytes"
    assert profile["endValue"] == 1572864
    assert len(profile["samples"]) >= 2
    assert sum(profile["weights"]) == 1572864

    # Check shared frames
    shared_frames = data["shared"]["frames"]
    assert len(shared_frames) >= 3
    frame_names = [f["name"] for f in shared_frames]
    assert "app" in frame_names
    assert "worker" in frame_names
    assert "query_db" in frame_names
