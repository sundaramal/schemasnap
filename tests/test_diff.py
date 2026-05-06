"""Tests for schemasnap.diff module."""

import pytest

from schemasnap.diff import SchemaDiff, diff_snapshots


OLD_SNAPSHOT = {
    "hash": "aabbccdd1122",
    "schema": {
        "users": {"columns": ["id", "email", "created_at"]},
        "posts": {"columns": ["id", "title", "body"]},
        "legacy": {"columns": ["id", "data"]},
    },
}

NEW_SNAPSHOT = {
    "hash": "eeff99887766",
    "schema": {
        "users": {"columns": ["id", "email", "created_at", "updated_at"]},
        "posts": {"columns": ["id", "title", "body"]},
        "comments": {"columns": ["id", "post_id", "content"]},
    },
}


def test_diff_detects_added_table():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="staging")
    assert "comments" in result.added_tables


def test_diff_detects_removed_table():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="staging")
    assert "legacy" in result.removed_tables


def test_diff_detects_modified_table_column_added():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="staging")
    assert "users" in result.modified_tables
    assert "updated_at" in result.modified_tables["users"]["added_columns"]


def test_diff_unchanged_table_not_in_modified():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="staging")
    assert "posts" not in result.modified_tables


def test_diff_has_changes_true_when_differences():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="staging")
    assert result.has_changes is True


def test_diff_has_changes_false_when_identical():
    result = diff_snapshots(OLD_SNAPSHOT, OLD_SNAPSHOT, env="prod")
    assert result.has_changes is False


def test_diff_env_stored():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="production")
    assert result.env == "production"


def test_diff_hashes_stored():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="staging")
    assert result.old_hash == OLD_SNAPSHOT["hash"]
    assert result.new_hash == NEW_SNAPSHOT["hash"]


def test_summary_no_changes():
    result = diff_snapshots(OLD_SNAPSHOT, OLD_SNAPSHOT, env="dev")
    assert "No schema changes" in result.summary()


def test_summary_with_changes():
    result = diff_snapshots(OLD_SNAPSHOT, NEW_SNAPSHOT, env="staging")
    summary = result.summary()
    assert "added" in summary.lower()
    assert "legacy" in summary
    assert "comments" in summary
    assert "updated_at" in summary


def test_diff_empty_snapshots():
    result = diff_snapshots({}, {}, env="test")
    assert not result.has_changes
    assert result.old_hash == ""
    assert result.new_hash == ""
