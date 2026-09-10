"""Unit tests for differential FlameGraph analysis and HTML export."""

from flamelens.core.differential import compare_trees
from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackTree
from flamelens.render.html_exporter import export_to_html


def test_compare_trees_detects_regressions_and_optimizations():
    f_root = StackFrame(name="app")
    f_order = StackFrame(name="order_service")
    f_auth = StackFrame(name="auth_filter")

    # Baseline: order_service = 10MB, auth_filter = 10MB, total = 20MB
    base = StackTree()
    base.insert_stack([f_root, f_order], 10 * 1024 * 1024)
    base.insert_stack([f_root, f_auth], 10 * 1024 * 1024)

    # Candidate: order_service = 25MB (+15MB), auth_filter = 4MB (-6MB), total = 29MB
    cand = StackTree()
    cand.insert_stack([f_root, f_order], 25 * 1024 * 1024)
    cand.insert_stack([f_root, f_auth], 4 * 1024 * 1024)

    diff = compare_trees(base, cand)
    assert diff.baseline_total == 20 * 1024 * 1024
    assert diff.candidate_total == 29 * 1024 * 1024
    assert diff.delta_total == 9 * 1024 * 1024

    # Check root child
    root_child = diff.root.children[f_root.identifier]
    order_diff = root_child.children[f_order.identifier]
    auth_diff = root_child.children[f_auth.identifier]

    assert order_diff.delta_bytes == 15 * 1024 * 1024
    assert order_diff.delta_pct == 150.0  # +150%

    assert auth_diff.delta_bytes == -6 * 1024 * 1024
    assert auth_diff.delta_pct == -60.0  # -60%

    ascii_out = diff.render_ascii(use_color=False)
    assert "+15.00 MB" in ascii_out
    assert "-6.00 MB" in ascii_out
    assert "FlameLens Diff" in ascii_out


def test_html_export_generates_file(tmp_path):
    tree = StackTree()
    tree.insert_stack([StackFrame(name="main"), StackFrame(name="work")], 1024 * 1024)

    out_file = tmp_path / "flame_test.html"
    export_to_html(tree, out_file, title="Test Run")

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Test Run" in content
    assert "main" in content
    assert "work" in content
