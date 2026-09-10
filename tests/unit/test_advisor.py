"""Unit tests for Advisor bottleneck diagnosis and recommendations."""

from flamelens.analysis.advisor import Advisor
from flamelens.core.frame import StackFrame
from flamelens.core.stack_tree import StackTree


def test_advisor_identifies_culprits_and_remedies():
    tree = StackTree()
    f_root = StackFrame(name="main")
    f_cache = StackFrame(name="UserSessionCache.store")
    f_json = StackFrame(name="ResponseParser.json_decode")
    f_leaf = StackFrame(name="buffer_allocator")

    # 50MB in session cache (unbounded storage), 30MB in json parser, 20MB in buffer
    tree.insert_stack([f_root, f_cache], 50 * 1024 * 1024)
    tree.insert_stack([f_root, f_json], 30 * 1024 * 1024)
    tree.insert_stack([f_root, f_leaf], 20 * 1024 * 1024)

    report = Advisor.analyze(tree, min_impact_pct=15.0)
    assert report.total_bytes == 100 * 1024 * 1024
    assert len(report.culprits) >= 2

    culprit_names = [c.frame.name for c in report.culprits]
    assert "UserSessionCache.store" in culprit_names
    assert "ResponseParser.json_decode" in culprit_names

    # Check categories and recommendations
    cache_culprit = next(c for c in report.culprits if c.frame.name == "UserSessionCache.store")
    assert cache_culprit.category == "Unbounded Storage / Cache"
    assert "maxsize" in cache_culprit.recommendation

    json_culprit = next(c for c in report.culprits if c.frame.name == "ResponseParser.json_decode")
    assert json_culprit.category == "Data Parsing Overhead"

    formatted = report.format_report()
    assert "FlameLens Optimization Advisory" in formatted
    assert "UserSessionCache.store" in formatted
