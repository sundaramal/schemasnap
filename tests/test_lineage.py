"""Tests for schemasnap.lineage and schemasnap.cmd_lineage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.lineage import (
    LineageEntry,
    load_lineage,
    record_lineage,
    get_parent,
    lineage_chain,
)
from schemasnap.cmd_lineage import cmd_lineage


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> str:
    return str(tmp_path)


def _entry(snapshot_file: str, parent_file=None, env="prod", schema_hash="abc", timestamp="2024-01-01T00:00:00") -> LineageEntry:
    return LineageEntry(
        snapshot_file=snapshot_file,
        parent_file=parent_file,
        env=env,
        schema_hash=schema_hash,
        timestamp=timestamp,
    )


def test_load_lineage_empty_when_no_file(tmp_dir):
    assert load_lineage(tmp_dir) == []


def test_record_and_load_roundtrip(tmp_dir):
    e = _entry("snap_v1.json")
    record_lineage(tmp_dir, e)
    loaded = load_lineage(tmp_dir)
    assert len(loaded) == 1
    assert loaded[0].snapshot_file == "snap_v1.json"
    assert loaded[0].parent_file is None


def test_record_multiple_entries(tmp_dir):
    record_lineage(tmp_dir, _entry("snap_v1.json"))
    record_lineage(tmp_dir, _entry("snap_v2.json", parent_file="snap_v1.json"))
    entries = load_lineage(tmp_dir)
    assert len(entries) == 2


def test_get_parent_returns_correct_entry(tmp_dir):
    record_lineage(tmp_dir, _entry("snap_v1.json"))
    record_lineage(tmp_dir, _entry("snap_v2.json", parent_file="snap_v1.json"))
    entry = get_parent(tmp_dir, "snap_v2.json")
    assert entry is not None
    assert entry.parent_file == "snap_v1.json"


def test_get_parent_returns_none_for_unknown(tmp_dir):
    assert get_parent(tmp_dir, "nonexistent.json") is None


def test_lineage_chain_returns_ancestry(tmp_dir):
    record_lineage(tmp_dir, _entry("snap_v1.json"))
    record_lineage(tmp_dir, _entry("snap_v2.json", parent_file="snap_v1.json"))
    record_lineage(tmp_dir, _entry("snap_v3.json", parent_file="snap_v2.json"))
    chain = lineage_chain(tmp_dir, "snap_v3.json")
    assert [e.snapshot_file for e in chain] == ["snap_v3.json", "snap_v2.json", "snap_v1.json"]


def test_lineage_chain_empty_for_unknown(tmp_dir):
    assert lineage_chain(tmp_dir, "ghost.json") == []


def _make_args(tmp_dir, lineage_cmd, **kwargs):
    ns = argparse.Namespace(lineage_cmd=lineage_cmd, snapshot_dir=tmp_dir, as_json=False, **kwargs)
    return ns


def test_cmd_lineage_list_returns_zero(tmp_dir):
    record_lineage(tmp_dir, _entry("snap_v1.json"))
    args = _make_args(tmp_dir, "list")
    assert cmd_lineage(args) == 0


def test_cmd_lineage_list_json(tmp_dir, capsys):
    record_lineage(tmp_dir, _entry("snap_v1.json", env="staging"))
    args = _make_args(tmp_dir, "list", as_json=True)
    cmd_lineage(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data[0]["env"] == "staging"


def test_cmd_lineage_show_returns_one_when_missing(tmp_dir):
    args = _make_args(tmp_dir, "show", snapshot_file="ghost.json")
    assert cmd_lineage(args) == 1


def test_cmd_lineage_chain_json(tmp_dir, capsys):
    record_lineage(tmp_dir, _entry("snap_v1.json"))
    record_lineage(tmp_dir, _entry("snap_v2.json", parent_file="snap_v1.json"))
    args = _make_args(tmp_dir, "chain", snapshot_file="snap_v2.json", as_json=True)
    assert cmd_lineage(args) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2
