"""Unit tests for schemasnap.snapshot_patch."""
from __future__ import annotations

import pytest

from schemasnap.diff import diff_snapshots
from schemasnap.snapshot_patch import apply_patch, PatchResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _snap(schema: dict) -> dict:
    return {"environment": "test", "schema": schema}


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_apply_patch_adds_table():
    base = _snap({"users": {"id": "int"}})
    frm = _snap({"users": {"id": "int"}})
    to = _snap({"users": {"id": "int"}, "orders": {"order_id": "int"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    result = apply_patch(base, diff)
    assert result.success
    assert "orders" in result.patched_schema["schema"]
    assert any("add:orders" in a for a in result.applied)


def test_apply_patch_removes_table():
    base = _snap({"users": {"id": "int"}, "legacy": {"x": "text"}})
    frm = _snap({"users": {"id": "int"}, "legacy": {"x": "text"}})
    to = _snap({"users": {"id": "int"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    result = apply_patch(base, diff)
    assert result.success
    assert "legacy" not in result.patched_schema["schema"]


def test_apply_patch_modifies_column():
    base = _snap({"users": {"id": "int", "name": "varchar(50)"}})
    frm = _snap({"users": {"id": "int", "name": "varchar(50)"}})
    to = _snap({"users": {"id": "int", "name": "varchar(255)"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    result = apply_patch(base, diff)
    assert result.success
    assert result.patched_schema["schema"]["users"]["name"] == "varchar(255)"


def test_apply_patch_no_changes_returns_same_schema():
    base = _snap({"users": {"id": "int"}})
    frm = _snap({"users": {"id": "int"}})
    to = _snap({"users": {"id": "int"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    result = apply_patch(base, diff)
    assert result.success
    assert result.patched_schema["schema"] == base["schema"]
    assert result.applied == []


def test_apply_patch_remove_missing_table_fails_by_default():
    base = _snap({"users": {"id": "int"}})
    frm = _snap({"users": {"id": "int"}, "ghost": {"x": "int"}})
    to = _snap({"users": {"id": "int"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    result = apply_patch(base, diff)
    assert not result.success
    assert "ghost" in result.message


def test_apply_patch_remove_missing_table_skipped_with_allow_missing():
    base = _snap({"users": {"id": "int"}})
    frm = _snap({"users": {"id": "int"}, "ghost": {"x": "int"}})
    to = _snap({"users": {"id": "int"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    result = apply_patch(base, diff, allow_missing=True)
    assert result.success
    assert any("remove:ghost" in s for s in result.skipped)


def test_apply_patch_does_not_mutate_base():
    base = _snap({"users": {"id": "int"}})
    original_schema = dict(base["schema"])
    frm = _snap({"users": {"id": "int"}})
    to = _snap({"users": {"id": "int"}, "orders": {"order_id": "int"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    apply_patch(base, diff)
    assert base["schema"] == original_schema


def test_patch_result_preserves_metadata():
    base = _snap({"users": {"id": "int"}})
    base["environment"] = "production"
    base["captured_at"] = "2024-01-01T00:00:00"
    frm = _snap({"users": {"id": "int"}})
    to = _snap({"users": {"id": "int", "email": "text"}})
    diff = diff_snapshots(frm["schema"], to["schema"])
    result = apply_patch(base, diff)
    assert result.patched_schema["environment"] == "production"
    assert result.patched_schema["captured_at"] == "2024-01-01T00:00:00"
