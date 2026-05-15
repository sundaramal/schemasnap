"""Unit tests for schemasnap.snapshot_summary."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.snapshot_summary import (
    SnapshotSummary,
    compute_summary,
    render_summary_json,
    render_summary_text,
)


@pytest.fixture()
def snap_file(tmp_path: Path) -> Path:
    data = {
        "environment": "staging",
        "hash": "abc123",
        "schema": {
            "users": {"id": "int", "email": "varchar", "created_at": "timestamp"},
            "orders": {"id": "int", "user_id": "int"},
        },
    }
    p = tmp_path / "snap.json"
    p.write_text(json.dumps(data))
    return p


def test_compute_summary_table_count(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    assert s.table_count == 2


def test_compute_summary_column_count(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    assert s.column_count == 5


def test_compute_summary_environment(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    assert s.environment == "staging"


def test_compute_summary_hash(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    assert s.snapshot_hash == "abc123"


def test_compute_summary_tables_sorted(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    assert s.tables == ["orders", "users"]


def test_compute_summary_column_counts_by_table(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    assert s.column_counts_by_table == {"users": 3, "orders": 2}


def test_render_summary_text_contains_env(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    text = render_summary_text(s)
    assert "staging" in text


def test_render_summary_text_contains_table_names(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    text = render_summary_text(s)
    assert "users" in text
    assert "orders" in text


def test_render_summary_json_is_valid(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    parsed = json.loads(render_summary_json(s))
    assert parsed["table_count"] == 2
    assert parsed["column_count"] == 5


def test_render_summary_json_tables_list(snap_file: Path) -> None:
    s = compute_summary(snap_file)
    parsed = json.loads(render_summary_json(s))
    assert "orders" in parsed["tables"]
    assert "users" in parsed["tables"]


def test_compute_summary_empty_schema(tmp_path: Path) -> None:
    data = {"environment": "prod", "hash": "000", "schema": {}}
    p = tmp_path / "empty.json"
    p.write_text(json.dumps(data))
    s = compute_summary(p)
    assert s.table_count == 0
    assert s.column_count == 0
    assert s.tables == []
