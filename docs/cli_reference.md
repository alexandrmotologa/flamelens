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

Examples:

```bash
# Profile a web worker script and save the profile
flamelens profile server.py -o server_profile.json

# Profile with memory leak detection over 10 GC checkpoints
flamelens profile worker.py --leak-detect --checkpoints 10
```

### `view`

Display a previously generated profile, collapsed stack file, or JFR recording.

```bash
flamelens view <profile_path> [OPTIONS]
```

Options:
- `-f, --format [tui|ascii]`: display mode (default: `tui`).
- `--threshold FLOAT`: minimum allocation percentage to display (default: `0.5`).
- `--max-depth INT`: maximum call depth to render in ASCII mode (default: `16`).

Examples:

```bash
# Open interactive terminal TUI
flamelens view profile.json

# Print non-interactive ASCII flame graph to stdout
flamelens view profile.json --format ascii

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
- `-f, --format [html|folded|json]`: target export format (default: `html`).
- `-o, --output PATH`: destination file path (default: `flame_report.html` or stdout).

Examples:

```bash
# Export self-contained HTML flame graph
flamelens export profile.json --format html -o report.html

# Convert JFR recording to Brendan Gregg folded stacks
flamelens export recording.jfr --format folded -o recording.folded
```
