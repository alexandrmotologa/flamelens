# flamelens

Interactive memory allocation profiler and terminal FlameGraph engine.

flamelens analyzes heap allocations in Python 3.12+ applications and Java Flight Recorder (JFR) recordings. It renders interactive FlameGraphs directly in your terminal, detects objects retained across garbage collection cycles, and generates differential graphs between baseline and regression runs.

## Key features

- Low overhead tracking: uses Python 3.12 PEP 669 monitoring and tracemalloc to trace allocations with minimal runtime drag.
- Interactive terminal UI: zoom into subtrees, search functions with live highlighting, and inspect call sites using Textual.
- Compact ASCII rendering: prints non-interactive flame charts to stdout for quick reviews in CI logs and remote shells.
- Memory leak detection: identifies allocation sites whose net retained bytes increase monotonically across garbage collection cycles.
- JFR binary ingestion: parses JDK Flight Recorder allocation events from Java 21+ services without external dependencies.
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

Output example:

```text
Root: 120.0 MB total allocated
├── OrderController.handle [105.0 MB, 87.5%]
│   ├── OrderCommandService.execute [90.0 MB, 75.0%]
│   │   ├── Hibernate.loadLazyList [80.0 MB, 66.7%] (Bottleneck)
│   │   └── Order.create [10.0 MB, 8.3%]
│   └── AuthFilter.validate [15.0 MB, 12.5%]
└── HealthCheck.ping [15.0 MB, 12.5%]
```

### 4. Compare profiles with FlameDiff

Compare a baseline profile with a candidate profile:

```bash
flamelens diff baseline.json regression.json
```

Blocks with increased allocations appear in red, while optimized frames appear in blue.

### 5. Parse Java Flight Recorder (.jfr) files

Inspect memory allocations from Java services:

```bash
flamelens view recording.jfr
```

### 6. Export to interactive HTML

Generate a self-contained HTML file:

```bash
flamelens export profile.json --format html --output report.html
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
