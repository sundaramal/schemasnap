"""Tests for schemasnap.search."""
import json
import os
from pathlib import Path

import pytest

from schemasnap.search import SearchConfig, SearchResult, search_snapshots, _env_from_filename


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: str, env: str, schema: dict, ts: str = "2024-01-01T00-00-00") -> str:
    data = {"env": env, "schema": schema, "hash": "abc123"}
    filename = f"{env}_{ts}_abc123.json"
    path = Path(directory) / filename
    path.write_text(json.dumps(data))
    return str(path)


SAMPLE_SCHEMA = {
    "users": {"columns": {"id": "integer", "email": "varchar", "password_hash": "varchar"}},
    "orders": {"columns": {"id": "integer", "user_id": "integer", "total": "numeric"}},
    "products": {"columns": {"id": "integer", "name": "varchar", "price": "numeric"}},
}


@pytest.fixture
def snap_dir(tmp_path):
    _write_snapshot(str(tmp_path), "prod", SAMPLE_SCHEMA, "2024-06-01T00-00-00")
    _write_snapshot(str(tmp_path), "staging", SAMPLE_SCHEMA, "2024-06-01T00-00-00")
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Unit tests for _env_from_filename
# ---------------------------------------------------------------------------

def test_env_from_filename_basic():
    assert _env_from_filename("prod_2024-01-01T00-00-00_abc123.json") == "prod"


def test_env_from_filename_staging():
    assert _env_from_filename("staging_2024-06-01T12-00-00_def456.json") == "staging"


# ---------------------------------------------------------------------------
# Table search
# ---------------------------------------------------------------------------

def test_search_by_table_pattern_returns_matches(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, table_pattern="users")
    results = search_snapshots(cfg)
    assert all(r.table == "users" for r in results)
    assert len(results) == 2  # prod + staging


def test_search_table_pattern_case_insensitive(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, table_pattern="ORDERS")
    results = search_snapshots(cfg)
    assert all(r.table == "orders" for r in results)


def test_search_no_pattern_returns_all_tables(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir)
    results = search_snapshots(cfg)
    table_names = {r.table for r in results}
    assert table_names == {"users", "orders", "products"}


def test_search_nonexistent_table_returns_empty(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, table_pattern="nonexistent_xyz")
    results = search_snapshots(cfg)
    assert results == []


# ---------------------------------------------------------------------------
# Column search
# ---------------------------------------------------------------------------

def test_search_by_column_pattern_returns_matches(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, column_pattern="email")
    results = search_snapshots(cfg)
    assert all(r.column == "email" for r in results)
    assert all(r.match_type == "column" for r in results)


def test_search_column_pattern_finds_across_tables(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, column_pattern="id")
    results = search_snapshots(cfg)
    tables_with_id = {r.table for r in results}
    assert tables_with_id == {"users", "orders", "products"}


def test_search_sensitive_column(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, column_pattern="password")
    results = search_snapshots(cfg)
    assert len(results) > 0
    assert all(r.column == "password_hash" for r in results)


# ---------------------------------------------------------------------------
# Environment filtering
# ---------------------------------------------------------------------------

def test_search_filters_by_env(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, env="prod", table_pattern="users")
    results = search_snapshots(cfg)
    assert all(r.env == "prod" for r in results)
    assert len(results) == 1


def test_search_empty_dir_returns_empty(tmp_path):
    cfg = SearchConfig(snapshot_dir=str(tmp_path), table_pattern="users")
    results = search_snapshots(cfg)
    assert results == []


def test_search_result_contains_snapshot_file(snap_dir):
    cfg = SearchConfig(snapshot_dir=snap_dir, env="prod", table_pattern="orders")
    results = search_snapshots(cfg)
    assert len(results) == 1
    assert "prod" in results[0].snapshot_file
