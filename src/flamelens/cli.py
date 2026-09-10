"""FlameLens CLI: Profiler, TUI viewer, Differential engine, and Exporter."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from flamelens import __version__
from flamelens.config import ProfilerConfig
from flamelens.core.differential import compare_trees
from flamelens.core.folded import load_folded_file, save_folded_file
from flamelens.core.leak_detector import LeakDetector
from flamelens.core.stack_tree import StackTree
from flamelens.profiler.jfr_parser import parse_jfr_file
from flamelens.profiler.monitor import AllocationMonitor
from flamelens.render.ascii_flame import render_ascii_flamegraph
from flamelens.render.html_exporter import export_to_html
from flamelens.tui.app import FlameLensApp

app = typer.Typer(
    name="flamelens",
    help="Interactive memory profiler and terminal FlameGraph engine.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(
            f"[bold orange1]FlameLens[/bold orange1] version [bold white]{__version__}[/bold white]"
        )
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """FlameLens: Low-overhead memory profiler and terminal flamegraph visualizer."""
    pass


def _load_profile(path: Path) -> StackTree:
    """Load profile tree from JSON, JFR, or Brendan Gregg folded stack files."""
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {path}")
        raise typer.Exit(code=1)

    suffix = path.suffix.lower()
    if suffix == ".jfr":
        return parse_jfr_file(path)
    elif suffix in (".folded", ".txt", ".stacks"):
        return load_folded_file(path)
    else:
        # Default to JSON
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            # Handle both raw StackTree dict and wrapped profile dict with leak reports
            if "tree" in data:
                return StackTree.from_dict(data["tree"])
            return StackTree.from_dict(data)
        except Exception:
            # Fallback to folded
            return load_folded_file(path)


@app.command()
def profile(
    script: Annotated[Path, typer.Argument(help="Target Python script to execute and profile.")],
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Output path for JSON profile data.")
    ] = Path("profile.json"),
    sample_rate: Annotated[
        int,
        typer.Option(
            "--sample-rate", help="Poisson sampling byte interval (0 for exact tracking)."
        ),
    ] = 0,
    leak_detect: Annotated[
        bool, typer.Option("--leak-detect", help="Enable generational GC retention tracking.")
    ] = False,
    checkpoints: Annotated[
        int, typer.Option("--checkpoints", help="Number of GC evaluation checkpoints.")
    ] = 5,
    max_depth: Annotated[
        int, typer.Option("--max-depth", help="Maximum stack depth to record.")
    ] = 64,
    threshold: Annotated[
        float, typer.Option("--threshold", help="Minimum allocation percentage to report.")
    ] = 0.1,
    format_mode: Annotated[
        str,
        typer.Option("-f", "--format", help="Display mode after execution (ascii, tui, or none)."),
    ] = "ascii",
    script_args: Annotated[
        Optional[list[str]], typer.Argument(help="Arguments forwarded to the profiled script.")
    ] = None,
) -> None:
    """Execute a target Python script and record memory allocations."""
    if not script.exists():
        console.print(f"[bold red]Error:[/bold red] Script not found: {script}")
        raise typer.Exit(code=1)

    config = ProfilerConfig(
        sample_rate=sample_rate,
        leak_detect=leak_detect,
        checkpoints=checkpoints,
        max_depth=max_depth,
        threshold=threshold,
    )

    # Prepare argv for the target script
    original_argv = list(sys.argv)
    target_argv = [str(script)] + (script_args or [])

    monitor = AllocationMonitor(config=config)
    leak_detector = LeakDetector(config=config) if leak_detect else None

    console.print(f"[bold cyan]Profiling execution of:[/bold cyan] {script}...")

    try:
        sys.argv = target_argv
        if leak_detector:
            leak_detector.start()

        monitor.start()

        # Run script in its own namespace as __main__
        try:
            runpy.run_path(str(script), run_name="__main__")
        finally:
            tree = monitor.stop()
            leak_report = leak_detector.stop() if leak_detector else None

    finally:
        sys.argv = original_argv

    # Save output data
    payload = {
        "tree": tree.to_dict(),
        "total_bytes": tree.total_bytes,
        "total_allocations": tree.total_allocations,
    }
    if leak_report:
        payload["leak_report"] = leak_report.to_dict()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"[green]Profile saved to:[/green] {output}")

    if leak_report and leak_report.candidates:
        console.print(leak_report.format_summary())

    if format_mode == "ascii":
        console.print("\n" + render_ascii_flamegraph(tree, max_depth=16, threshold_pct=threshold))
    elif format_mode == "tui":
        tui_app = FlameLensApp(tree)
        tui_app.run()


@app.command()
def view(
    profile_path: Annotated[
        Path, typer.Argument(help="Path to profile JSON, JFR, or folded stack file.")
    ],
    format_mode: Annotated[
        str, typer.Option("-f", "--format", help="Viewer format (tui or ascii).")
    ] = "tui",
    threshold: Annotated[
        float, typer.Option("--threshold", help="Minimum percentage to render.")
    ] = 0.5,
    max_depth: Annotated[int, typer.Option("--max-depth", help="Maximum depth to display.")] = 16,
) -> None:
    """Inspect and visualize a previously recorded profile or JFR binary."""
    tree = _load_profile(profile_path)

    if format_mode == "ascii":
        output = render_ascii_flamegraph(tree, max_depth=max_depth, threshold_pct=threshold)
        console.print(output)
    else:
        tui_app = FlameLensApp(tree)
        tui_app.run()


@app.command()
def diff(
    baseline: Annotated[
        Path, typer.Argument(help="Path to baseline profile (JSON, JFR, or folded).")
    ],
    candidate: Annotated[
        Path, typer.Argument(help="Path to candidate profile (JSON, JFR, or folded).")
    ],
    format_mode: Annotated[
        str, typer.Option("-f", "--format", help="Diff output format (ascii or json).")
    ] = "ascii",
    output: Annotated[
        Optional[Path], typer.Option("-o", "--output", help="Optional path to save diff report.")
    ] = None,
) -> None:
    """Compute and display allocation differential between two profiles (FlameDiff)."""
    base_tree = _load_profile(baseline)
    cand_tree = _load_profile(candidate)

    diff_tree = compare_trees(base_tree, cand_tree)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(diff_tree.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]Diff saved to:[/green] {output}")

    if format_mode == "ascii":
        console.print(diff_tree.render_ascii())


@app.command()
def leaks(
    profile_path: Annotated[Path, typer.Argument(help="Path to profile JSON file.")],
    min_growth_mb: Annotated[
        float, typer.Option("--min-growth-mb", help="Minimum memory growth in MB.")
    ] = 1.0,
) -> None:
    """Analyze profile data for generational memory retention and leak candidates."""
    if not profile_path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {profile_path}")
        raise typer.Exit(code=1)

    data = json.loads(profile_path.read_text(encoding="utf-8"))
    leak_data = data.get("leak_report")

    if not leak_data or not leak_data.get("candidates"):
        console.print("[yellow]No memory leaks detected in profile.[/yellow]")
        return

    candidates = leak_data["candidates"]
    console.print(f"[bold red]LEAK CANDIDATES DETECTED: {len(candidates)}[/bold red]")
    console.print("=" * 80)

    for i, c in enumerate(candidates, 1):
        if c.get("growth_mb", 0) < min_growth_mb:
            continue
        tag = " [IMMORTAL]" if c.get("is_immortal") else ""
        frame = c.get("frame", {})
        console.print(f"[bold yellow]{i}. {frame.get('name', 'Unknown')}[/bold yellow]{tag}")
        console.print(f"   File: {frame.get('filename')}:{frame.get('line_number')}")
        console.print(
            f"   Growth: +{c.get('growth_mb')} MB ({c.get('initial_bytes', 0)} B -> {c.get('final_bytes', 0)} B)"
        )
        console.print(f"   Consecutive increases: {c.get('consecutive_increases')}")
        console.print("-" * 80)


@app.command()
def export(
    input_path: Annotated[Path, typer.Argument(help="Input profile, folded stack, or JFR file.")],
    output: Annotated[Path, typer.Option("-o", "--output", help="Output file destination.")] = Path(
        "flame_report.html"
    ),
    format_mode: Annotated[
        str, typer.Option("-f", "--format", help="Export target format (html, folded, json).")
    ] = "html",
    title: Annotated[
        str, typer.Option("--title", help="Title for HTML export report.")
    ] = "FlameLens Memory Profile",
) -> None:
    """Convert and export profile into standalone HTML, collapsed stacks, or JSON."""
    tree = _load_profile(input_path)

    if format_mode == "html":
        export_to_html(tree, output, title=title)
        console.print(f"[green]Standalone interactive HTML exported to:[/green] {output}")
    elif format_mode == "folded":
        save_folded_file(tree, output)
        console.print(f"[green]Brendan Gregg folded stacks saved to:[/green] {output}")
    elif format_mode == "json":
        output.write_text(tree.to_json(), encoding="utf-8")
        console.print(f"[green]JSON profile saved to:[/green] {output}")
    else:
        console.print(f"[bold red]Error:[/bold red] Unsupported export format: {format_mode}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
