"""Rendering engines for terminal ASCII and HTML flamegraphs."""

from flamelens.render.ascii_flame import render_ascii_flamegraph
from flamelens.render.colors import FlameColorPalette

__all__ = ["FlameColorPalette", "render_ascii_flamegraph"]
