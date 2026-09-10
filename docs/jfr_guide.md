# Java Flight Recorder (JFR) Integration

FlameLens includes a native binary parser for JDK Flight Recorder (`.jfr`) files. You can analyze memory allocation profiles from Java services without installing JDK developer tools or desktop viewers like Java Mission Control.

## Recording JFR files in Java

JDK Flight Recorder is built into standard OpenJDK and Oracle JDK distributions (Java 11, 17, 21+).

### 1. Enable JFR at process launch

Add the following JVM options when starting your Java application:

```bash
java -XX:+FlightRecorder \
     -XX:StartFlightRecording=duration=60s,filename=service_allocations.jfr,settings=profile \
     -jar target/my-service.jar
```

### 2. Capture dynamically via jcmd

To record an already running Java process:

```bash
# Find the PID
jcmd

# Start a 60 second memory profiling session
jcmd <PID> JFR.start duration=60s filename=/tmp/heap.jfr settings=profile
```

## Supported JFR events

FlameLens parses key JVM memory allocation events:

- `jdk.ObjectAllocationInNewTLAB`: object allocated inside a newly created Thread-Local Allocation Buffer. Contains allocation size and TLAB size.
- `jdk.ObjectAllocationOutsideTLAB`: large object allocated directly in Java heap outside TLAB boundaries.
- `jdk.OldObjectSample`: live objects retained during garbage collection pauses (used for heap retention analysis).

The parser decodes the constant pool, parses the event stream, resolves method names and stack traces, and converts them into the FlameLens Trie data structure.

## Visualizing JFR files in FlameLens

View the interactive terminal TUI:

```bash
flamelens view service_allocations.jfr
```

Or print an ASCII summary to stdout:

```bash
flamelens view service_allocations.jfr --format ascii
```

Export directly to Brendan Gregg folded stacks:

```bash
flamelens export service_allocations.jfr --format folded -o java_allocs.folded
```

Export to a standalone interactive HTML flame graph:

```bash
flamelens export service_allocations.jfr --format html -o java_flame.html
```
