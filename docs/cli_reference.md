# FlameLens CLI Reference

FlameLens provides a unified command line interface built with Typer.

```text
Usage: flamelens [OPTIONS] COMMAND [ARGS]...
```

## Commands

### `profile`

Execute a target Python script and record memory allocations.

```bash
flamelens profile <script_path> [OPTIONS] [-- SCRIPT_ARGS...]
```

Options:
- `-o, --output PATH`: destination path for JSON profile data (default: `profile.json`).
- `--sample-rate INT`: Poisson sampling byte interval in bytes (default: `0` for full tracking, or e.g. `524288` for 512 KB sampling).
- `--leak-detect / --no-leak-detect`: enable generational garbage collection tracking (default: false).
- `--checkpoints INT`: number of GC evaluation checkpoints during execution (default: `5`).
- `--max-depth INT`: maximum stack depth to record (default: `64`).
- `--threshold FLOAT`: minimum percentage of total memory for a frame to be included (default: `0.1`).
- `--max-mem FLOAT`: fail if peak memory exceeds threshold in MB (CI quality gate).
- `--max-leak-rate FLOAT`: fail if growth between checkpoints exceeds threshold in MB (CI quality gate).
- `--fail-on-leak`: exit with code 2 if any memory leak candidates are detected.

Examples:

```bash
# Profile a web worker script and save the profile
flamelens profile server.py -o server_profile.json

# Profile with memory leak detection over 10 GC checkpoints
flamelens profile worker.py --leak-detect --checkpoints 10

# CI pipeline enforcement: fail build if peak memory exceeds 250 MB
flamelens profile worker.py --max-mem 250.0 --fail-on-leak
```

### `view`

Display a previously generated profile, collapsed stack file, or JFR recording.

```bash
flamelens view <profile_path> [OPTIONS]
```

Options:
- `-f, --format [tui|ascii]`: display mode (default: `tui`).
- `-m, --metric [churn|retained]`: select memory perspective (default: `churn`).
- `--threshold FLOAT`: minimum allocation percentage to display (default: `0.5`).
- `--max-depth INT`: maximum call depth to render in ASCII mode (default: `16`).

Examples:

```bash
# Open interactive terminal TUI in dual-metric churn view
flamelens view profile.json

# View live retained heap allocations in ASCII tree
flamelens view profile.json --metric retained --format ascii

# View a Java Flight Recorder binary recording
flamelens view flight_recording.jfr
```

### `diff`

Compute and display the differential allocation graph between two profiles.

```bash
flamelens diff <baseline_path> <candidate_path> [OPTIONS]
```

Options:
- `-f, --format [tui|ascii]`: display format (default: `ascii`).
- `-o, --output PATH`: optional path to write diff JSON report.

Examples:

```bash
# Compare release v1.0 vs v1.1
flamelens diff v1_profile.json v2_profile.json

# Output ASCII differential to stdout
flamelens diff baseline.json regression.json --format ascii
```

### `analyze`

Analyze top allocation culprits and generate actionable code optimization recommendations.

```bash
flamelens analyze <profile_path> [OPTIONS]
```

Options:
- `--metric [churn|retained]`: analysis perspective (default: `churn`).
- `--min-impact-pct FLOAT`: minimum percentage of total allocations to flag (default: `10.0`).

Example:

```bash
flamelens analyze profile.json
```

Output example:

```text
================================================================================
                    TOP ALLOCATION CULPRITS & ADVISOR
================================================================================
Profile: profile.json (Total tracked: 142.5 MB)

1. [72.4 MB | 50.8% of total] data_loader.py:parse_all_records:42
   Self memory: 65.1 MB (45.7% exclusive)
   Remediation advice:
   - High self-allocation detected in parse_all_records. Consider replacing intermediate list accumulations with generator expressions.
   - Use streaming iterators to avoid materializing large datasets in memory.

2. [28.2 MB | 19.8% of total] cache.py:memoize_query:18
   Self memory: 28.2 MB (19.8% exclusive)
   Remediation advice:
   - Function memoize_query appears to cache results. Verify that an eviction policy or maxsize is configured on this cache.
================================================================================
```

### `spikes`

Display detected allocation spikes where memory surged abruptly during execution.

```bash
flamelens spikes <profile_path>
```

Example:

```bash
flamelens spikes profile.json
```

Output example:

```text
SPIKE INCIDENTS DETECTED: 1
--------------------------------------------------------------------------------
Spike #1: +12.4 MB surge at 2026-09-11T01:05:22.124890
Top frame at surge:
  image_processor.py:decompress_raw_buffer:112
--------------------------------------------------------------------------------
```

### `leaks`

Analyze a profile for generational memory retention and print identified leak candidates.

```bash
flamelens leaks <profile_path> [OPTIONS]
```

Options:
- `--min-growth-mb FLOAT`: minimum memory growth in megabytes to trigger an alert (default: `1.0`).

Example:

```bash
flamelens leaks profile.json
```

Output example:

```text
LEAK CANDIDATES DETECTED: 2
--------------------------------------------------------------------------------
1. OrderSessionCache (order_service.py:142)
   Initial retained: 4.2 MB
   Final retained:   49.8 MB (+45.6 MB net growth over 5 checkpoints)
   Survived GC generations: Gen 0 -> Gen 1 -> Gen 2 (Immortal)

2. ResponseBuffer (http_client.py:88)
   Initial retained: 1.1 MB
   Final retained:   14.3 MB (+13.2 MB net growth over 5 checkpoints)
--------------------------------------------------------------------------------
```

### `export`

Convert a profile, folded stack file, or JFR recording into another format.

```bash
flamelens export <input_path> [OPTIONS]
```

Options:
- `-f, --format [html|folded|json|speedscope]`: target export format (default: `html`).
- `-m, --metric [churn|retained]`: memory metric to export (default: `churn`).
- `-o, --output PATH`: destination file path (default: `flame_report.html`, `profile.speedscope.json`, or stdout).

Examples:

```bash
# Export self-contained HTML flame graph
flamelens export profile.json --format html -o report.html

# Export official Speedscope JSON format to inspect at speedscope.app
flamelens export profile.json --format speedscope -o profile.speedscope.json

# Convert JFR recording to Brendan Gregg folded stacks
flamelens export recording.jfr --format folded -o recording.folded
```
