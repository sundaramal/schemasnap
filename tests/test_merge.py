"""Tests for schemasnap.merge."""
from __future__ import annotations

import json
import os

import pytest

from schemasnap.merge import MergeResult, merge_schemas, merge_snapshot_files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRIMARY_SCHEMA = {
    "users": {"columns": {"id": "int", "name": "text"}},
    "orders": {"columns": {"id": "int", "amount": "numeric"}},
}

SECONDARY_SCHEMA = {
    "users": {"columns": {"id": "int", "name": "text", "email": "text"}},
    "products": {"columns": {"id": "int", "sku": "text"}},
}


def _write_snapshot(path: str, env: str, schema: dict) -> None:
    with open(path, "w") as fh:
        json.dump({"environment": env, "schema": schema, "hash": "abc"}, fh)


# ---------------------------------------------------------------------------
# merge_schemas
# ---------------------------------------------------------------------------


def test_merge_tables_only_in_primary():
    result = merge_schemas(PRIMARY_SCHEMA, SECONDARY_SCHEMA)
    assert "orders" in result.tables_only_in_primary


def test_merge_tables_only_in_secondary():
    result = merge_schemas(PRIMARY_SCHEMA, SECONDARY_SCHEMA)
    assert "products" in result.tables_only_in_secondary


def test_merge_conflicted_table_uses_primary():
    result = merge_schemas(PRIMARY_SCHEMA, SECONDARY_SCHEMA)
    assert "users" in result.tables_conflicted
    # Primary definition should win
    assert result.merged_schema["users"] == PRIMARY_SCHEMA["users"]


def test_merge_identical_tables_not_conflicted():
    schema_a = {"foo": {"columns": {"id": "int"}}}
    schema_b = {"foo": {"columns": {"id": "int"}}}
    result = merge_schemas(schema_a, schema_b)
    assert "foo" in result.tables_identical
    assert result.conflict_count == 0


def test_merge_result_contains_all_tables():
    result = merge_schemas(PRIMARY_SCHEMA, SECONDARY_SCHEMA)
    assert set(result.merged_schema.keys()) == {"users", "orders", "products"}


def test_merge_env_names_stored():
    result = merge_schemas({}, {}, primary_env="prod", secondary_env="staging")
    assert result.primary_env == "prod"
    assert result.secondary_env == "staging"


def test_merge_empty_schemas_returns_empty():
    result = merge_schemas({}, {})
    assert result.merged_schema == {}
    assert result.conflict_count == 0


def test_merge_does_not_mutate_inputs():
    import copy
    primary_copy = copy.deepcopy(PRIMARY_SCHEMA)
    secondary_copy = copy.deepcopy(SECONDARY_SCHEMA)
    merge_schemas(PRIMARY_SCHEMA, SECONDARY_SCHEMA)
    assert PRIMARY_SCHEMA == primary_copy
    assert SECONDARY_SCHEMA == secondary_copy


def test_summary_contains_env_names():
    result = merge_schemas({}, {}, primary_env="prod", secondary_env="dev")
    s = result.summary()
    assert "prod" in s
    assert "dev" in s


# ---------------------------------------------------------------------------
# merge_snapshot_files
# ---------------------------------------------------------------------------


def test_merge_snapshot_files(tmp_path):
    p_file = str(tmp_path / "snap_prod.json")
    s_file = str(tmp_path / "snap_staging.json")
    _write_snapshot(p_file, "prod", PRIMARY_SCHEMA)
    _write_snapshot(s_file, "staging", SECONDARY_SCHEMA)

    result = merge_snapshot_files(p_file, s_file)

    assert result.primary_env == "prod"
    assert result.secondary_env == "staging"
    assert "orders" in result.merged_schema
    assert "products" in result.merged_schema
    assert "users" in result.tables_conflicted
