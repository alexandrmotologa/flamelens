"""Rendering engines for terminal ASCII and HTML flamegraphs."""

from flamelens.render.ascii_flame import render_ascii_flamegraph
from flamelens.render.colors import FlameColorPalette
from flamelens.render.html_exporter import export_to_html
from flamelens.render.speedscope import export_to_speedscope

__all__ = [
    "FlameColorPalette",
    "export_to_html",
    "export_to_speedscope",
    "render_ascii_flamegraph",
]
