"""Tests for cmd_lineage_graph."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_lineage_graph import (
    _build_edges,
    _render_dot,
    _render_mermaid,
    add_lineage_graph_subparsers,
    cmd_lineage_graph,
)
from schemasnap.lineage import LineageEntry, record_lineage


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def _make_args(tmp_dir: Path, fmt: str = "mermaid", env: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(dir=str(tmp_dir), fmt=fmt, env=env)


def _populate(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, LineageEntry(
        snapshot_hash="aaaa1111bbbb2222",
        environment="prod",
        parent_hash=None,
        captured_at="2024-01-01T00:00:00",
    ))
    record_lineage(tmp_dir, LineageEntry(
        snapshot_hash="cccc3333dddd4444",
        environment="prod",
        parent_hash="aaaa1111bbbb2222",
        captured_at="2024-01-02T00:00:00",
    ))


def test_add_lineage_graph_subparsers_registers_command() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_lineage_graph_subparsers(sub)
    args = parser.parse_args(["lineage-graph", "--dir", "/tmp"])
    assert hasattr(args, "func")


def test_add_lineage_graph_subparsers_default_fmt() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_lineage_graph_subparsers(sub)
    args = parser.parse_args(["lineage-graph", "--dir", "/tmp"])
    assert args.fmt == "mermaid"


def test_cmd_lineage_graph_missing_dir_returns_1(tmp_dir: Path) -> None:
    args = _make_args(tmp_dir / "nonexistent")
    assert cmd_lineage_graph(args) == 1


def test_cmd_lineage_graph_mermaid_returns_zero(tmp_dir: Path, capsys) -> None:
    _populate(tmp_dir)
    args = _make_args(tmp_dir, fmt="mermaid")
    rc = cmd_lineage_graph(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "graph TD" in out


def test_cmd_lineage_graph_dot_returns_zero(tmp_dir: Path, capsys) -> None:
    _populate(tmp_dir)
    args = _make_args(tmp_dir, fmt="dot")
    rc = cmd_lineage_graph(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "digraph lineage" in out
    assert "->" in out


def test_cmd_lineage_graph_json_output(tmp_dir: Path, capsys) -> None:
    _populate(tmp_dir)
    args = _make_args(tmp_dir, fmt="json")
    rc = cmd_lineage_graph(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "nodes" in data
    assert "edges" in data
    assert any(e["parent"] == "aaaa1111" for e in data["edges"])


def test_cmd_lineage_graph_env_filter(tmp_dir: Path, capsys) -> None:
    _populate(tmp_dir)
    record_lineage(tmp_dir, LineageEntry(
        snapshot_hash="eeee5555ffff6666",
        environment="staging",
        parent_hash=None,
        captured_at="2024-01-01T00:00:00",
    ))
    args = _make_args(tmp_dir, fmt="json", env="staging")
    cmd_lineage_graph(args)
    data = json.loads(capsys.readouterr().out)
    assert "eeee5555" in data["nodes"]
    assert "aaaa1111" not in data["nodes"]


def test_build_edges_skips_root_entries() -> None:
    entries = [
        LineageEntry(snapshot_hash="aabbccdd1122", environment="prod", parent_hash=None, captured_at=""),
        LineageEntry(snapshot_hash="eeff00112233", environment="prod", parent_hash="aabbccdd1122", captured_at=""),
    ]
    edges = _build_edges(entries)
    assert len(edges) == 1
    assert edges[0] == ("aabbccdd", "eeff0011")


def test_render_dot_contains_all_nodes() -> None:
    nodes = ["abc", "def"]
    edges = [("abc", "def")]
    result = _render_dot(edges, nodes)
    assert '"abc"' in result
    assert '"def"' in result
    assert '"abc" -> "def"' in result


def test_render_mermaid_contains_arrow() -> None:
    result = _render_mermaid([("aaa", "bbb")], ["aaa", "bbb"])
    assert "aaa --> bbb" in result
