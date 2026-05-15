"""Unit tests for schemasnap.snapshot_compare_chain."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.snapshot_compare_chain import (
    ChainLink,
    CompareChainResult,
    compare_snapshot_chain,
)


def _write_snapshot(directory: Path, env: str, tag: str, schema: dict) -> None:
    data = {"environment": env, "schema": schema}
    filename = f"{env}_{tag}.json"
    (directory / filename).write_text(json.dumps(data))


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_empty_dir_returns_empty_chain(snap_dir: Path) -> None:
    result = compare_snapshot_chain(str(snap_dir), "prod")
    assert result.env == "prod"
    assert result.total_links == 0
    assert result.changed_links == 0


def test_single_snapshot_no_links(snap_dir: Path) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"users": {"id": "int"}})
    result = compare_snapshot_chain(str(snap_dir), "prod")
    assert result.total_links == 0


def test_two_identical_snapshots_no_changes(snap_dir: Path) -> None:
    schema = {"users": {"id": "int", "name": "text"}}
    _write_snapshot(snap_dir, "prod", "001", schema)
    _write_snapshot(snap_dir, "prod", "002", schema)
    result = compare_snapshot_chain(str(snap_dir), "prod")
    assert result.total_links == 1
    assert result.changed_links == 0
    assert not result.links[0].has_changes


def test_two_different_snapshots_detects_change(snap_dir: Path) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"users": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"users": {"id": "int", "email": "text"}})
    result = compare_snapshot_chain(str(snap_dir), "prod")
    assert result.changed_links == 1
    assert result.links[0].has_changes


def test_three_snapshots_two_links(snap_dir: Path) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"a": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"a": {"id": "int"}, "b": {"x": "text"}})
    _write_snapshot(snap_dir, "prod", "003", {"a": {"id": "int"}, "b": {"x": "text"}})
    result = compare_snapshot_chain(str(snap_dir), "prod")
    assert result.total_links == 2
    assert result.changed_links == 1


def test_limit_restricts_number_of_snapshots(snap_dir: Path) -> None:
    for i in range(1, 6):
        _write_snapshot(snap_dir, "prod", f"{i:03d}", {"t": {"id": "int"}})
    result = compare_snapshot_chain(str(snap_dir), "prod", limit=3)
    # limit=3 => 3 files => 2 links
    assert result.total_links == 2


def test_env_isolation(snap_dir: Path) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "staging", "001", {"t": {"id": "int"}})
    result = compare_snapshot_chain(str(snap_dir), "prod")
    assert result.total_links == 1


def test_summary_string_format(snap_dir: Path) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int", "name": "text"}})
    result = compare_snapshot_chain(str(snap_dir), "prod")
    s = result.summary()
    assert "env=prod" in s
    assert "links=1" in s
    assert "changed=1" in s


def test_chain_link_from_to_fields(snap_dir: Path) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int"}})
    result = compare_snapshot_chain(str(snap_dir), "prod")
    link = result.links[0]
    assert "001" in link.from_file
    assert "002" in link.to_file
