"""Tests for schemasnap.snapshot module."""

import json
import pytest
from pathlib import Path

import schemasnap.snapshot as snap


SAMPLE_SCHEMA = {
    "tables": {
        "users": {
            "columns": {
                "id": {"type": "integer", "primary_key": True},
                "email": {"type": "varchar", "nullable": False},
            }
        }
    }
}


@pytest.fixture(autouse=True)
def tmp_snapshot_dir(tmp_path, monkeypatch):
    """Redirect snapshot storage to a temp directory for each test."""
    monkeypatch.setattr(snap, "SNAPSHOT_DIR", tmp_path / ".schemasnap" / "snapshots")


def test_compute_schema_hash_is_deterministic():
    h1 = snap.compute_schema_hash(SAMPLE_SCHEMA)
    h2 = snap.compute_schema_hash(SAMPLE_SCHEMA)
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex digest


def test_compute_schema_hash_differs_on_change():
    modified = json.loads(json.dumps(SAMPLE_SCHEMA))
    modified["tables"]["users"]["columns"]["name"] = {"type": "varchar", "nullable": True}
    assert snap.compute_schema_hash(SAMPLE_SCHEMA) != snap.compute_schema_hash(modified)


def test_capture_snapshot_creates_file():
    path = snap.capture_snapshot("staging", SAMPLE_SCHEMA, label="initial")
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["env"] == "staging"
    assert data["label"] == "initial"
    assert data["schema"] == SAMPLE_SCHEMA
    assert len(data["schema_hash"]) == 64


def test_capture_snapshot_filename_contains_env_and_hash():
    path = snap.capture_snapshot("production", SAMPLE_SCHEMA)
    expected_hash_prefix = snap.compute_schema_hash(SAMPLE_SCHEMA)[:8]
    assert "production" in path.name
    assert expected_hash_prefix in path.name


def test_load_snapshot_round_trip():
    saved_path = snap.capture_snapshot("dev", SAMPLE_SCHEMA)
    loaded = snap.load_snapshot(saved_path)
    assert loaded["schema"] == SAMPLE_SCHEMA


def test_load_snapshot_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        snap.load_snapshot(Path("/nonexistent/snapshot.json"))


def test_list_snapshots_empty_when_no_dir():
    assert snap.list_snapshots() == []


def test_list_snapshots_filtered_by_env():
    snap.capture_snapshot("staging", SAMPLE_SCHEMA)
    snap.capture_snapshot("production", SAMPLE_SCHEMA)
    staging_snaps = snap.list_snapshots("staging")
    assert all("staging" in p.name for p in staging_snaps)
    assert len(staging_snaps) == 1


def test_latest_snapshot_returns_most_recent():
    snap.capture_snapshot("staging", SAMPLE_SCHEMA)
    snap.capture_snapshot("staging", SAMPLE_SCHEMA)
    latest = snap.latest_snapshot("staging")
    assert latest is not None
    all_snaps = snap.list_snapshots("staging")
    assert latest == all_snaps[-1]


def test_latest_snapshot_none_when_missing():
    assert snap.latest_snapshot("nonexistent") is None
