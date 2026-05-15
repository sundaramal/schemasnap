"""Unit tests for schemasnap.snapshot_index."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.snapshot_index import build_index, IndexEntry, SnapshotIndex


# ------------------------------------------------------------------ helpers

def _write_snapshot(directory: Path, env: str, schema_hash: str, schema: dict) -> Path:
    filename = f"snapshot_{env}_{schema_hash}.json"
    path = directory / filename
    payload = {
        "environment": env,
        "schema_hash": schema_hash,
        "schema": schema,
    }
    path.write_text(json.dumps(payload))
    return path


@pytest.fixture()
def snap_dir(tmp_path):
    _write_snapshot(tmp_path, "prod", "aabbcc1122", {"users": {"id": "int"}, "orders": {"id": "int"}})
    _write_snapshot(tmp_path, "staging", "ddeeff3344", {"users": {"id": "int"}})
    _write_snapshot(tmp_path, "prod", "11223344aa", {"users": {"id": "int"}})
    return tmp_path


# ------------------------------------------------------------------ tests

def test_build_index_counts_all_entries(snap_dir):
    idx = build_index(snap_dir)
    assert len(idx.entries) == 3


def test_build_index_empty_dir(tmp_path):
    idx = build_index(tmp_path)
    assert idx.entries == []


def test_envs_returns_sorted_unique(snap_dir):
    idx = build_index(snap_dir)
    assert idx.envs() == ["prod", "staging"]


def test_by_env_filters_correctly(snap_dir):
    idx = build_index(snap_dir)
    prod = idx.by_env("prod")
    assert all(e.env == "prod" for e in prod)
    assert len(prod) == 2


def test_by_env_unknown_returns_empty(snap_dir):
    idx = build_index(snap_dir)
    assert idx.by_env("dev") == []


def test_by_hash_full_match(snap_dir):
    idx = build_index(snap_dir)
    entry = idx.by_hash("aabbcc1122")
    assert entry is not None
    assert entry.schema_hash == "aabbcc1122"


def test_by_hash_prefix_match(snap_dir):
    idx = build_index(snap_dir)
    entry = idx.by_hash("dde")
    assert entry is not None
    assert entry.env == "staging"


def test_by_hash_no_match_returns_none(snap_dir):
    idx = build_index(snap_dir)
    assert idx.by_hash("zzz") is None


def test_table_count_populated(snap_dir):
    idx = build_index(snap_dir)
    prod_entries = idx.by_env("prod")
    counts = {e.schema_hash: e.table_count for e in prod_entries}
    assert counts["aabbcc1122"] == 2


def test_to_dict_structure(snap_dir):
    idx = build_index(snap_dir)
    d = idx.to_dict()
    assert "environments" in d
    assert "total_snapshots" in d
    assert d["total_snapshots"] == 3
    assert "entries" in d
    assert isinstance(d["entries"], list)


def test_invalid_json_file_is_skipped(tmp_path):
    (tmp_path / "snapshot_bad_abc.json").write_text("not json{{{")
    idx = build_index(tmp_path)
    assert len(idx.entries) == 0
