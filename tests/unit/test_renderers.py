"""Unit tests for ASCII rendering and color palettes."""

from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackTree
from flamelens.render.ascii_flame import format_bytes, render_ascii_flamegraph
from flamelens.render.colors import FlameColorPalette


def test_color_palettes():
    # Warm scale checks
    low_color = FlameColorPalette.get_warm_color(0.0)
    high_color = FlameColorPalette.get_warm_color(100.0)
    assert low_color.startswith("#")
    assert high_color.startswith("#")
    assert low_color != high_color

    # Diff scale checks
    red = FlameColorPalette.get_diff_color(500, 1000)
    blue = FlameColorPalette.get_diff_color(-500, 1000)
    neutral = FlameColorPalette.get_diff_color(0, 1000)
    assert red in FlameColorPalette.DIFF_INCREASE_HEX
    assert blue in FlameColorPalette.DIFF_REDUCTION_HEX
    assert neutral == FlameColorPalette.DIFF_NEUTRAL_HEX


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048) == "2.00 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.00 MB"
    assert format_bytes(3 * 1024 * 1024 * 1024) == "3.00 GB"


def test_ascii_flamegraph_rendering():
    tree = StackTree()
    f1 = StackFrame(name="OrderController.handle")
    f2 = StackFrame(name="Hibernate.loadLazyList")
    f3 = StackFrame(name="AuthFilter.validate")

    tree.insert_stack([f1, f2], 80 * 1024 * 1024)  # 80 MB
    tree.insert_stack([f1, f3], 20 * 1024 * 1024)  # 20 MB

    rendered = render_ascii_flamegraph(tree, use_color=False)

    assert "OrderController.handle" in rendered
    assert "Hibernate.loadLazyList" in rendered
    assert "AuthFilter.validate" in rendered
    assert "80.00 MB" in rendered
    assert "20.00 MB" in rendered
    assert "100.00 MB" in rendered
    assert "80.0%" in rendered


def test_ascii_empty_tree():
    tree = StackTree()
    output = render_ascii_flamegraph(tree)
    assert "Empty profile" in output
