# Detecting Python Memory Leaks with FlameLens

Memory leaks in garbage-collected runtimes like Python rarely stem from unmanaged pointers. Instead, they occur when references to obsolete objects are retained in long-lived data structures, such as module-level caches, event listeners, or cyclical closures.

## How generational garbage collection works in Python

CPython manages memory through reference counting supplemented by a cyclic garbage collector. The collector divides non-referenced objects into three generations based on survival counts:

- Generation 0: newly allocated objects. Inspected frequently.
- Generation 1: objects that survived one collection cycle.
- Generation 2: long-lived objects that survived two or more collection cycles.

When an application leaks memory, objects escape Generation 0 and Generation 1, settling into Generation 2 where garbage collection occurs least frequently.

## The FlameLens leak detection model

Standard profilers take a single snapshot at process exit. This approach fails to distinguish between:
1. High-throughput temporary allocations that are collected promptly.
2. Legitimate long-lived allocations, such as configuration trees and loaded models.
3. Creeping memory leaks where data structures grow continuously.

FlameLens solves this by observing memory across scheduled checkpoints during program execution:

```text
Time -------->
Checkpoint 1: gc.collect() -> Record surviving allocation sites S1
Checkpoint 2: gc.collect() -> Record surviving allocation sites S2
Checkpoint 3: gc.collect() -> Record surviving allocation sites S3
...
Checkpoint N: gc.collect() -> Record surviving allocation sites Sn
```

### Detection criteria

An allocation site is classified as a leak candidate if all of the following hold:
1. Monotonic growth: `bytes(S_{i+1}) > bytes(S_i)` for at least 3 consecutive checkpoints.
2. Generational promotion: surviving objects migrate into Generation 2.
3. Growth threshold: total net byte increase exceeds the configured threshold (default: 1 MB).

## Running leak detection

Run your script with the `--leak-detect` flag:

```bash
flamelens profile worker.py --leak-detect --checkpoints 5 --output leak_profile.json
```

Then display the leak summary:

```bash
flamelens leaks leak_profile.json
```

## Common leak patterns and remedies

### 1. Global unbounded caches

```python
# Bad: dictionary grows indefinitely with every request
cache = {}

def handle_request(req_id, data):
    cache[req_id] = process(data)
```

Remedy: use an LRU cache or bounded cache structure (`functools.lru_cache(maxsize=1024)`).

### 2. Lingering callbacks and listeners

```python
# Bad: observer retains reference to worker instance
class Worker:
    def __init__(self, dispatcher):
        dispatcher.register_listener(self.on_event)
```

Remedy: use weak references (`weakref.WeakMethod` or `weakref.ref`) or implement an explicit teardown method.
