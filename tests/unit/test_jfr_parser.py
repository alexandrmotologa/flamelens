"""Unit tests for Java Flight Recorder (.jfr) binary parser."""

import struct

import pytest

from flamelens.profiler.jfr_parser import JFRParseError, parse_jfr_file


def test_jfr_binary_header_parsing(tmp_path):
    # Construct synthetic valid JFR chunk header
    # Magic: FLR\0, Version: 2.0, ChunkSize: 1024, CP_offset: 68, Meta_offset: 120
    header = struct.pack(
        ">4sHHQQQ",
        b"FLR\x00",
        2,
        0,
        1024,
        68,
        120,
    )
    # Add dummy constant pool data with Java package names
    payload = (
        header
        + b"\x00" * 40
        + b"org.apache.kafka.Producer.send\x00java.util.concurrent.Future.get\x00"
    )
    file_path = tmp_path / "test.jfr"
    file_path.write_bytes(payload)

    tree = parse_jfr_file(file_path)
    assert tree.total_bytes > 0
    assert tree.root.frame.name == "JVM Heap Allocations"


def test_jfr_text_dump_parsing(tmp_path):
    sample_text = """
jdk.ObjectAllocationInNewTLAB {
  startTime = 10:15:30.120
  allocationSize = 65536 bytes
  tlabSize = 1048576 bytes
  stackTrace = [
    at java.util.Arrays.copyOf(Arrays.java:3332)
    at java.lang.AbstractStringBuilder.ensureCapacityInternal(AbstractStringBuilder.java:124)
    at com.example.service.OrderService.processOrders(OrderService.java:88)
  ]
}
"""
    file_path = tmp_path / "events.jfr"
    file_path.write_text(sample_text, encoding="utf-8")

    tree = parse_jfr_file(file_path)
    assert tree.total_bytes == 65536
    matches = tree.search_nodes("OrderService")
    assert len(matches) > 0


def test_jfr_invalid_file(tmp_path):
    file_path = tmp_path / "invalid.jfr"
    file_path.write_bytes(b"CORRUPTED_NON_JFR_HEADER")

    with pytest.raises(JFRParseError):
        parse_jfr_file(file_path)
