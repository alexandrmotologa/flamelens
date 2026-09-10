"""Unit tests for StackTree Trie aggregation and serialization."""

from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackTree


def test_stack_tree_insertion_and_metrics():
    tree = StackTree()
    f1 = StackFrame(name="main", filename="app.py", line_number=10)
    f2 = StackFrame(name="process", filename="worker.py", line_number=25)
    f3 = StackFrame(name="allocate_buffer", filename="buffer.py", line_number=50)

    tree.insert_stack([f1, f2, f3], 1024 * 1024)  # 1 MB
    tree.insert_stack([f1, f2], 512 * 1024)  # 0.5 MB

    assert tree.total_bytes == 1572864
    assert tree.total_allocations == 2

    # Check root metrics
    assert tree.root.inclusive_bytes == 1572864
    assert tree.root.call_count == 2

    # Check child nodes
    main_node = tree.root.children[f1.identifier]
    assert main_node.inclusive_bytes == 1572864
    assert main_node.self_bytes == 0

    proc_node = main_node.children[f2.identifier]
    assert proc_node.inclusive_bytes == 1572864
    assert proc_node.self_bytes == 512 * 1024

    buf_node = proc_node.children[f3.identifier]
    assert buf_node.inclusive_bytes == 1024 * 1024
    assert buf_node.self_bytes == 1024 * 1024


def test_folded_stacks_roundtrip():
    folded_input = "main;worker;parse 4096\nmain;worker;execute 8192\nmain;logger 1024\n"

    tree = StackTree.from_folded_stacks(folded_input)
    assert tree.total_bytes == 13312
    assert tree.total_allocations == 3

    exported = tree.to_folded_stacks()
    assert "main;worker;parse 4096" in exported
    assert "main;worker;execute 8192" in exported
    assert "main;logger 1024" in exported


def test_pruning_and_zooming():
    tree = StackTree()
    f_root = StackFrame(name="root_job")
    f_heavy = StackFrame(name="heavy_task")
    f_light = StackFrame(name="light_task")

    tree.insert_stack([f_root, f_heavy], 9900)
    tree.insert_stack([f_root, f_light], 100)

    # 10% threshold should prune light_task (1%)
    pruned = tree.prune(10.0)
    assert f_heavy.identifier in pruned.root.children[f_root.identifier].children
    assert f_light.identifier not in pruned.root.children[f_root.identifier].children

    # Zoom into heavy_task
    zoomed = tree.zoom_subnode(f_heavy.identifier)
    assert zoomed is not None
    assert zoomed.root.frame.name == "heavy_task"
    assert zoomed.total_bytes == 9900


def test_json_serialization():
    tree = StackTree()
    f = StackFrame(name="entrypoint", filename="main.py", line_number=1)
    tree.insert_stack([f], 2048)

    json_str = tree.to_json()
    reloaded = StackTree.from_json(json_str)

    assert reloaded.total_bytes == 2048
    assert f.identifier in reloaded.root.children


def test_search_nodes():
    tree = StackTree()
    tree.insert_stack([StackFrame(name="handle_order"), StackFrame(name="query_db")], 5000)
    tree.insert_stack([StackFrame(name="handle_order"), StackFrame(name="render_json")], 2000)

    matches = tree.search_nodes("db")
    assert len(matches) == 1
    assert matches[0].frame.name == "query_db"
