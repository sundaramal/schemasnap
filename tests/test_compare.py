"""Tests for the compare module."""

import json
import os
import pytest

from schemasnap.snapshot import capture_snapshot
from schemasnap.compare import compare_environments, compare_and_report, CompareResult


SCHEMA_A = {
    "users": {"id": "INTEGER", "name": "TEXT"},
    "orders": {"id": "INTEGER", "amount": "REAL"},
}

SCHEMA_B = {
    "users": {"id": "INTEGER", "name": "TEXT", "email": "TEXT"},
    "orders": {"id": "INTEGER", "amount": "REAL"},
}

SCHEMA_SAME = dict(SCHEMA_A)


@pytest.fixture
def snapshot_dir(tmp_path):
    capture_snapshot(SCHEMA_A, "staging", str(tmp_path))
    capture_snapshot(SCHEMA_B, "production", str(tmp_path))
    capture_snapshot(SCHEMA_SAME, "dev", str(tmp_path))
    return str(tmp_path)


def test_compare_environments_returns_compare_result(snapshot_dir):
    result = compare_environments("staging", "production", snapshot_dir)
    assert isinstance(result, CompareResult)


def test_compare_environments_detects_changes(snapshot_dir):
    result = compare_environments("staging", "production", snapshot_dir)
    assert result.has_changes is True


def test_compare_environments_no_changes_when_same(snapshot_dir):
    result = compare_environments("staging", "dev", snapshot_dir)
    assert result.has_changes is False


def test_compare_environments_sets_env_names(snapshot_dir):
    result = compare_environments("staging", "production", snapshot_dir)
    assert result.source_env == "staging"
    assert result.target_env == "production"


def test_compare_environments_raises_if_no_snapshot(tmp_path):
    with pytest.raises(FileNotFoundError):
        compare_environments("nonexistent", "production", str(tmp_path))


def test_compare_environments_diff_contains_modified_table(snapshot_dir):
    result = compare_environments("staging", "production", snapshot_dir)
    assert "users" in result.diff.modified


def test_compare_and_report_text_writes_file(snapshot_dir, tmp_path):
    output_path = str(tmp_path / "report.txt")
    compare_and_report("staging", "production", snapshot_dir, "text", output_path)
    assert os.path.exists(output_path)
    content = open(output_path).read()
    assert "staging" in content or "production" in content


def test_compare_and_report_json_writes_valid_json(snapshot_dir, tmp_path):
    output_path = str(tmp_path / "report.json")
    compare_and_report("staging", "production", snapshot_dir, "json", output_path)
    with open(output_path) as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_compare_and_report_returns_result(snapshot_dir):
    result = compare_and_report("staging", "production", snapshot_dir)
    assert isinstance(result, CompareResult)
    assert result.has_changes is True
