"""Tests for schemasnap.lineage and schemasnap.cmd_lineage."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.lineage import (
    LineageEntry,
    _lineage_path,
    load_lineage,
    record_lineage,
    get_parent,
    get_children,
)


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def _entry(child: str, parent: str | None = None) -> LineageEntry:
    return LineageEntry(child_hash=child, parent_hash=parent)


# ---------------------------------------------------------------------------
# load_lineage
# ---------------------------------------------------------------------------

def test_load_lineage_empty_when_no_file(tmp_dir: Path) -> None:
    assert load_lineage(tmp_dir) == []


def test_record_and_load_roundtrip(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="abc", parent_hash="000")
    entries = load_lineage(tmp_dir)
    assert len(entries) == 1
    assert entries[0].child_hash == "abc"
    assert entries[0].parent_hash == "000"


def test_record_multiple_entries(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="aaa", parent_hash=None)
    record_lineage(tmp_dir, child_hash="bbb", parent_hash="aaa")
    record_lineage(tmp_dir, child_hash="ccc", parent_hash="bbb")
    entries = load_lineage(tmp_dir)
    assert len(entries) == 3
    assert entries[2].child_hash == "ccc"


def test_record_stores_metadata(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="x1", metadata={"env": "prod"})
    entries = load_lineage(tmp_dir)
    assert entries[0].metadata == {"env": "prod"}


def test_lineage_file_is_jsonl(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="h1", parent_hash="h0")
    record_lineage(tmp_dir, child_hash="h2", parent_hash="h1")
    lines = _lineage_path(tmp_dir).read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "child_hash" in obj


# ---------------------------------------------------------------------------
# get_parent
# ---------------------------------------------------------------------------

def test_get_parent_returns_entry(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="child1", parent_hash="parent1")
    entries = load_lineage(tmp_dir)
    result = get_parent(entries, "child1")
    assert result is not None
    assert result.parent_hash == "parent1"


def test_get_parent_returns_none_for_unknown(tmp_dir: Path) -> None:
    entries = load_lineage(tmp_dir)
    assert get_parent(entries, "unknown") is None


def test_get_parent_latest_write_wins(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="c", parent_hash="old_parent")
    record_lineage(tmp_dir, child_hash="c", parent_hash="new_parent")
    entries = load_lineage(tmp_dir)
    result = get_parent(entries, "c")
    assert result is not None
    assert result.parent_hash == "new_parent"


# ---------------------------------------------------------------------------
# get_children
# ---------------------------------------------------------------------------

def test_get_children_returns_all_matching(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="b1", parent_hash="root")
    record_lineage(tmp_dir, child_hash="b2", parent_hash="root")
    record_lineage(tmp_dir, child_hash="b3", parent_hash="other")
    entries = load_lineage(tmp_dir)
    children = get_children(entries, "root")
    assert len(children) == 2
    hashes = {e.child_hash for e in children}
    assert hashes == {"b1", "b2"}


def test_get_children_empty_when_no_match(tmp_dir: Path) -> None:
    record_lineage(tmp_dir, child_hash="only", parent_hash="p")
    entries = load_lineage(tmp_dir)
    assert get_children(entries, "nobody") == []


# ---------------------------------------------------------------------------
# cmd_lineage
# ---------------------------------------------------------------------------

def test_cmd_lineage_record_success(tmp_dir: Path) -> None:
    from schemasnap.cmd_lineage import cmd_lineage_record
    import argparse

    snap_file = tmp_dir / "snap_prod_abc123.json"
    snap_file.write_text(json.dumps({"environment": "prod", "hash": "abc123", "schema": {}}))

    args = argparse.Namespace(
        snapshot=str(snap_file),
        parent=None,
        snap_dir=str(tmp_dir),
    )
    rc = cmd_lineage_record(args)
    assert rc == 0
    entries = load_lineage(tmp_dir)
    assert any(e.child_hash == "abc123" for e in entries)


def test_cmd_lineage_record_missing_snapshot(tmp_dir: Path) -> None:
    from schemasnap.cmd_lineage import cmd_lineage_record
    import argparse

    args = argparse.Namespace(
        snapshot=str(tmp_dir / "nonexistent.json"),
        parent=None,
        snap_dir=str(tmp_dir),
    )
    rc = cmd_lineage_record(args)
    assert rc == 1


def test_cmd_lineage_list_empty(tmp_dir: Path, capsys: pytest.CaptureFixture) -> None:
    from schemasnap.cmd_lineage import cmd_lineage_list
    import argparse

    args = argparse.Namespace(snap_dir=str(tmp_dir), fmt="text")
    rc = cmd_lineage_list(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No lineage" in captured.out


def test_cmd_lineage_list_json(tmp_dir: Path, capsys: pytest.CaptureFixture) -> None:
    from schemasnap.cmd_lineage import cmd_lineage_list
    import argparse

    record_lineage(tmp_dir, child_hash="deadbeef", parent_hash=None)
    args = argparse.Namespace(snap_dir=str(tmp_dir), fmt="json")
    rc = cmd_lineage_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["child"] == "deadbeef"
