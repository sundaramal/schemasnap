"""Tests for schemasnap.baseline module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from schemasnap.baseline import (
    BaselineEntry,
    BASELINE_FILENAME,
    load_baselines,
    save_baseline,
    get_baseline,
    set_baseline_from_snapshot,
    compare_to_baseline,
)


@pytest.fixture()
def tmp_dir(tmp_path):
    return str(tmp_path)


def _write_snapshot(path: Path, schema_hash: str) -> str:
    data = {"hash": schema_hash, "tables": {}}
    path.write_text(json.dumps(data))
    return str(path)


def test_load_baselines_empty_when_no_file(tmp_dir):
    assert load_baselines(tmp_dir) == {}


def test_save_and_load_baseline_roundtrip(tmp_dir):
    entry = BaselineEntry(env="prod", snapshot_file="snap.json", hash="abc123", set_at="2024-01-01T00:00:00Z")
    save_baseline(tmp_dir, entry)
    loaded = load_baselines(tmp_dir)
    assert "prod" in loaded
    assert loaded["prod"].hash == "abc123"
    assert loaded["prod"].snapshot_file == "snap.json"


def test_save_baseline_overwrites_existing(tmp_dir):
    e1 = BaselineEntry(env="prod", snapshot_file="snap1.json", hash="aaa", set_at="2024-01-01T00:00:00Z")
    e2 = BaselineEntry(env="prod", snapshot_file="snap2.json", hash="bbb", set_at="2024-06-01T00:00:00Z")
    save_baseline(tmp_dir, e1)
    save_baseline(tmp_dir, e2)
    result = get_baseline(tmp_dir, "prod")
    assert result.hash == "bbb"


def test_save_baseline_preserves_other_envs(tmp_dir):
    e_prod = BaselineEntry(env="prod", snapshot_file="p.json", hash="p1", set_at="2024-01-01T00:00:00Z")
    e_stg = BaselineEntry(env="staging", snapshot_file="s.json", hash="s1", set_at="2024-01-01T00:00:00Z")
    save_baseline(tmp_dir, e_prod)
    save_baseline(tmp_dir, e_stg)
    baselines = load_baselines(tmp_dir)
    assert "prod" in baselines
    assert "staging" in baselines


def test_get_baseline_returns_none_for_unknown_env(tmp_dir):
    assert get_baseline(tmp_dir, "unknown") is None


def test_set_baseline_from_snapshot(tmp_dir, tmp_path):
    snap_file = _write_snapshot(tmp_path / "snap_prod_abc.json", "deadbeef")
    with patch("schemasnap.baseline.load_snapshot", return_value={"hash": "deadbeef", "tables": {}}):
        entry = set_baseline_from_snapshot(tmp_dir, "prod", snap_file)
    assert entry.hash == "deadbeef"
    assert entry.env == "prod"
    assert get_baseline(tmp_dir, "prod").hash == "deadbeef"


def test_compare_to_baseline_no_drift(tmp_dir, tmp_path):
    snap_file = str(tmp_path / "current.json")
    save_baseline(tmp_dir, BaselineEntry(env="prod", snapshot_file="old.json", hash="cafebabe", set_at="2024-01-01T00:00:00Z"))
    with patch("schemasnap.baseline.load_snapshot", return_value={"hash": "cafebabe"}):
        assert compare_to_baseline(tmp_dir, "prod", snap_file) is True


def test_compare_to_baseline_drift_detected(tmp_dir, tmp_path):
    snap_file = str(tmp_path / "current.json")
    save_baseline(tmp_dir, BaselineEntry(env="prod", snapshot_file="old.json", hash="cafebabe", set_at="2024-01-01T00:00:00Z"))
    with patch("schemasnap.baseline.load_snapshot", return_value={"hash": "00000000"}):
        assert compare_to_baseline(tmp_dir, "prod", snap_file) is False


def test_compare_to_baseline_raises_when_no_baseline(tmp_dir, tmp_path):
    snap_file = str(tmp_path / "current.json")
    with patch("schemasnap.baseline.load_snapshot", return_value={"hash": "anything"}):
        with pytest.raises(ValueError, match="No baseline set"):
            compare_to_baseline(tmp_dir, "prod", snap_file)


def test_baseline_file_is_valid_json(tmp_dir):
    entry = BaselineEntry(env="dev", snapshot_file="d.json", hash="123", set_at="2024-01-01T00:00:00Z")
    save_baseline(tmp_dir, entry)
    raw = Path(tmp_dir, BASELINE_FILENAME).read_text()
    parsed = json.loads(raw)
    assert "dev" in parsed
