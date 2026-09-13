<p align="center">
  <img src="docs/images/logo.png?raw=true" alt="FlameLens Logo" width="140" style="border-radius: 28px;" />
</p>

<h1 align="center">flamelens</h1>

<p align="center">
  <strong>Interactive memory allocation profiler and terminal FlameGraph engine.</strong>
</p>

<p align="center">
  <a href="https://github.com/alexandrmotologa/flamelens/actions"><img src="https://img.shields.io/badge/CI-passing-2ea44f?style=flat-square&logo=githubactions&logoColor=white" alt="CI Status" /></a>
  <a href="https://pypi.org/project/flamelens/"><img src="https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue?style=flat-square&logo=python&logoColor=white" alt="Python Support" /></a>
  <a href="https://speedscope.app"><img src="https://img.shields.io/badge/speedscope-compatible-f59e0b?style=flat-square" alt="Speedscope Compatible" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-informational?style=flat-square" alt="License" /></a>
</p>

<br />

flamelens analyzes heap allocations in Python 3.12+ applications and Java Flight Recorder (JFR) recordings. It renders interactive FlameGraphs directly in your terminal, detects objects retained across garbage collection cycles, and generates differential graphs between baseline and regression runs.

## Key features

- Low overhead tracking: uses Python 3.12 PEP 669 monitoring and tracemalloc to trace allocations with minimal runtime drag.
- Dual-metric mode: switch between allocation churn (throughput volume) and retained heap (live memory leaks).
- Interactive terminal UI: zoom into subtrees, toggle metrics with the 'm' key, search functions with live highlighting, and inspect call sites using Textual.
- Compact ASCII rendering: prints non-interactive flame charts to stdout for quick reviews in CI logs and remote shells.
- Bottleneck and culprit advisor: automatically isolates functions driving more than 50% of allocations and outputs targeted code refactoring advice.
- CI/CD quality gates: enforces memory limits with `--max-mem` and `--max-leak-rate`, returning non-zero exit codes to fail builds on memory regressions.
- High-watermark spike detection: captures isolated stack traces during abrupt memory surges for instant root cause diagnosis.
- Memory leak detection: identifies allocation sites whose net retained bytes increase monotonically across garbage collection cycles.
- JFR binary ingestion: parses JDK Flight Recorder allocation events from Java 21+ services without external dependencies.
- Speedscope compatibility: exports directly to the speedscope.app JSON schema for browser-based flame chart sharing.
- Differential flame graphs: compares two profiles side by side to pinpoint regressions and optimizations.
- Folded stack compatibility: imports and exports Brendan Gregg collapsed stack files (`funcA;funcB 4096`).
- Standalone HTML export: outputs single-file interactive SVG and HTML charts for sharing.

## Installation

flamelens requires Python 3.12 or newer.

```bash
pip install flamelens
```

Or install with `uv`:

```bash
uv pip install flamelens
```

For local development:

```bash
git clone https://github.com/alexandrmotologa/flamelens.git
cd flamelens
uv pip install -e ".[dev]"
```

## Quick start

### 1. Profile a Python script

Profile memory allocations while running your script:

```bash
flamelens profile app.py --output profile.json
```

Run with automatic garbage collection leak detection enabled:

```bash
flamelens profile app.py --leak-detect --checkpoints 5
```

### 2. View in the interactive terminal UI

Launch the interactive Textual viewer:

```bash
flamelens view profile.json
```

Keyboard controls in the TUI:
- Up / Down: navigate between caller and callee depths
- Left / Right: move across sibling functions
- Enter: zoom into the selected call frame
- Escape: reset zoom to the root
- /: open search to highlight function names
- d: toggle function details panel
- q: exit the application

### 3. Print an ASCII FlameGraph to stdout

Render directly in standard terminal output:

```bash
flamelens view profile.json --format ascii
```

<p align="center">
  <img src="docs/images/terminal_flamegraph.png?raw=true" alt="FlameLens ASCII FlameGraph" width="100%" />
</p>

### 4. Compare profiles with FlameDiff

Compare a baseline profile with a candidate profile:

```bash
flamelens diff baseline.json candidate.json
```

Blocks with increased allocations appear in red, while optimized frames appear in blue:

<p align="center">
  <img src="docs/images/diff_flamegraph.png?raw=true" alt="FlameLens FlameDiff Comparison" width="100%" />
</p>

### 5. Parse Java Flight Recorder (.jfr) files

Inspect memory allocations from Java services:

```bash
flamelens view recording.jfr
```

### 6. Export to interactive HTML or Speedscope
 
Generate a self-contained HTML file or export to Speedscope JSON:

```bash
# Standalone interactive SVG/HTML
flamelens export profile.json --format html --output report.html

# Speedscope JSON format (open at https://www.speedscope.app)
flamelens export profile.json --format speedscope --output profile.speedscope.json
```

<p align="center">
  <img src="docs/images/flamegraph.png?raw=true" alt="FlameLens Standalone Interactive HTML FlameGraph" width="100%" />
</p>

### 7. Run Top Culprit and Bottleneck Advisor

Analyze profile data to pinpoint functions consuming disproportionate memory and view targeted refactoring advice:

```bash
flamelens analyze profile.json
```

<p align="center">
  <img src="docs/images/advisor_report.png?raw=true" alt="FlameLens Optimization Advisory Report" width="100%" />
</p>

### 8. Enforce CI/CD quality gates

Fail CI pipeline builds if an application exceeds a peak memory threshold or leaks memory:

```bash
flamelens profile worker.py --max-mem 250.0 --max-leak-rate 2.0 --fail-on-leak
```

### 9. Inspect memory spikes

Review sudden memory surges recorded during execution:

```bash
flamelens spikes profile.json
```

## Architecture overview

FlameLens consists of four core components:

1. Profiler engine (`flamelens.profiler`): gathers allocation events through Python 3.12 `sys.monitoring` and `tracemalloc`, or through the binary parser for JDK Flight Recorder.
2. Stack aggregation tree (`flamelens.core.stack_tree`): a prefix tree (Trie) aggregating stack frames into hierarchical metrics (inclusive bytes, exclusive bytes, call frequency).
3. Leak detector (`flamelens.core.leak_detector`): triggers generational collection checkpoints to measure object survival across generations 0, 1, and 2.
4. Renderers (`flamelens.render` and `flamelens.tui`): terminal layout engines providing ANSI 256 color palettes, Textual widgets, and standalone HTML exporters.

Read more in the [architecture guide](docs/architecture.md).

## Documentation

- [Architecture Guide](docs/architecture.md): design details of the trie aggregator and monitoring hooks
- [CLI Reference](docs/cli_reference.md): commands, arguments, and configuration flags
- [Memory Leak Detection](docs/memory_leaks.md): generational analysis and retention tracking
- [Java Flight Recorder Guide](docs/jfr_guide.md): recording and analyzing JVM memory events

## Contributing

Contributions are welcome. Please run tests and the linter before submitting a pull request:

```bash
ruff check src/ tests/
pytest tests/ -v
```

## License

MIT License. See [LICENSE](LICENSE) for details.