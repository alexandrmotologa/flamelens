# FlameLens Architecture

FlameLens is structured around a pipeline that decouples allocation event collection from aggregation and presentation.

```
+------------------------------------+
| Allocation Sources                 |
|  - Python 3.12 sys.monitoring      |
|  - Python tracemalloc hooks        |
|  - JDK Flight Recorder (.jfr)      |
|  - Brendan Gregg Folded Stacks     |
+-----------------+------------------+
                  |
                  v
+------------------------------------+
| Aggregation Engine                 |
|  - StackFrame Normalizer           |
|  - Prefix Tree (Trie) Aggregator   |
|  - Generational Leak Detector      |
|  - Differential Diff Engine        |
+-----------------+------------------+
                  |
                  v
+------------------------------------+
| Visualization & Export Targets     |
|  - Terminal ASCII FlameGraph       |
|  - Interactive Textual TUI App     |
|  - Standalone SVG / HTML Exporter  |
|  - Collapsed Stack Writer          |
+------------------------------------+
```

## 1. Profiling and event collection

### Python 3.12 monitoring hooks

Python 3.12 introduced PEP 669 (`sys.monitoring`), providing low overhead event notification for Python runtimes. FlameLens registers a tool ID with `sys.monitoring.use_tool_id()` and listens for function entry and exit events.

When tracking allocations:
- Function calls update the active thread stack context.
- Memory allocations are captured through `tracemalloc` snapshots or sampled byte counter deltas.
- Thread safety is preserved through thread-local call stacks.

### Probabilistic Poisson sampling

Tracing every allocation introduces overhead in high-throughput loops. FlameLens includes a Poisson allocation sampler. Rather than checking heap state on every instruction, it samples allocations after a random byte interval drawn from an exponential distribution with mean sampling interval S (default: 512 KB). This mirrors the low-overhead approach used in production profilers such as Google tcmalloc and Go runtime heap profilers.

## 2. Trie stack aggregation

Call stacks form naturally into a prefix tree where each node represents a code location (filename, function name, line number).

```
Root (100 MB)
 |-- worker.process (90 MB)
 |    |-- db.fetch_records (60 MB)
 |    \-- json.parse (30 MB)
 \-- healthcheck.status (10 MB)
```

Each tree node maintains:
- `inclusive_bytes`: total memory allocated by this function and all functions it called.
- `self_bytes`: memory allocated directly in the body of this function (leaf allocations).
- `call_count`: number of times this call sequence appeared in the profile.
- `children`: map of frame signature to child `StackNode`.

The Trie provides methods for:
- Breadth-first and depth-first traversal.
- Subtree pruning below a configurable percentage threshold (e.g. ignoring frames under 0.5% total allocation).
- Subtree zooming: rebasing the root of the tree onto any chosen node, recalculating inclusive percentages relative to that node.

## 3. Generational leak detection

Standard profilers report total allocated bytes, conflating short-lived temporary objects with persistent leaks. FlameLens addresses this by taking periodic checkpoints combined with forced garbage collection sweeps (`gc.collect(0)`, `gc.collect(1)`, `gc.collect(2)`).

Objects that survive multiple collection sweeps migrate into generation 2. When an allocation site increases its retained bytes monotonically across three or more collection checkpoints, the leak detector flags it as an immortal growth site and isolates its call stack.

## 4. Differential FlameGraph engine

To diagnose performance regressions between software releases, FlameLens provides differential analysis. Given baseline tree B and candidate tree C:
- For each frame key, calculate `delta_bytes = candidate_bytes - baseline_bytes`.
- Relative change percentage: `delta_percent = delta_bytes / baseline_total_bytes * 100`.
- Color mapping: nodes with positive delta receive warm reddish tints, while nodes with negative delta receive cool bluish tints. Unchanged nodes stay gray.

## 5. Visual presentation layers

- Terminal ASCII renderer: generates structured text trees with byte totals, percentages, and bottleneck annotations. Compatible with standard pipelines, grep, and CI log collectors.
- Textual TUI: interactive full-terminal interface supporting arrow key navigation, search filtering with regex, sub-tree drill down, and stack inspector panels.
- HTML exporter: generates self-contained interactive SVGs readable in any web browser without external JavaScript CDNs.
