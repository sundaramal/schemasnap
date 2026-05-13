"""Tests for schemasnap.validate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.validate import (
    ValidationRule,
    ValidationViolation,
    ValidationReport,
    load_rules,
    validate_snapshot,
    validate_snapshot_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def simple_snapshot():
    return {
        "environment": "test",
        "schema": {
            "users": {"id": "integer", "email": "varchar", "created_at": "timestamp"},
            "orders": {"id": "integer", "user_id": "integer", "total": "numeric"},
        },
    }


@pytest.fixture()
def rules_file(tmp_path: Path) -> Path:
    rules = [
        {
            "table_pattern": "users",
            "required_columns": ["id", "email"],
            "forbidden_columns": ["password"],
            "min_column_count": 2,
        },
        {
            "table_pattern": "orders",
            "required_columns": ["id"],
            "max_column_count": 10,
        },
    ]
    p = tmp_path / "rules.json"
    p.write_text(json.dumps(rules))
    return p


# ---------------------------------------------------------------------------
# Unit tests for validate_snapshot
# ---------------------------------------------------------------------------

def test_no_violations_when_rules_satisfied(simple_snapshot):
    rules = [ValidationRule(table_pattern="users", required_columns=["id", "email"])]
    violations = validate_snapshot(simple_snapshot, rules)
    assert violations == []


def test_missing_required_column_raises_violation(simple_snapshot):
    rules = [ValidationRule(table_pattern="users", required_columns=["id", "ssn"])]
    violations = validate_snapshot(simple_snapshot, rules)
    assert len(violations) == 1
    assert "ssn" in violations[0].message
    assert violations[0].table == "users"


def test_forbidden_column_raises_violation(simple_snapshot):
    rules = [ValidationRule(table_pattern="users", forbidden_columns=["email"])]
    violations = validate_snapshot(simple_snapshot, rules)
    assert any("email" in v.message for v in violations)


def test_min_column_count_violation(simple_snapshot):
    rules = [ValidationRule(table_pattern="orders", min_column_count=10)]
    violations = validate_snapshot(simple_snapshot, rules)
    assert len(violations) == 1
    assert "min" in violations[0].message


def test_max_column_count_violation(simple_snapshot):
    rules = [ValidationRule(table_pattern="users", max_column_count=2)]
    violations = validate_snapshot(simple_snapshot, rules)
    assert len(violations) == 1
    assert "max" in violations[0].message


def test_wildcard_pattern_matches_all_tables(simple_snapshot):
    rules = [ValidationRule(table_pattern="*", required_columns=["id"])]
    violations = validate_snapshot(simple_snapshot, rules)
    assert violations == []


def test_non_matching_pattern_skips_table(simple_snapshot):
    rules = [ValidationRule(table_pattern="payments", required_columns=["amount"])]
    violations = validate_snapshot(simple_snapshot, rules)
    assert violations == []


# ---------------------------------------------------------------------------
# load_rules
# ---------------------------------------------------------------------------

def test_load_rules_roundtrip(rules_file):
    rules = load_rules(rules_file)
    assert len(rules) == 2
    assert rules[0].table_pattern == "users"
    assert "email" in rules[0].required_columns
    assert "password" in rules[0].forbidden_columns
    assert rules[1].max_column_count == 10


# ---------------------------------------------------------------------------
# validate_snapshot_file
# ---------------------------------------------------------------------------

def test_validate_snapshot_file_passed(tmp_path, simple_snapshot, rules_file):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(simple_snapshot))
    report = validate_snapshot_file(snap, load_rules(rules_file))
    assert report.passed


def test_validate_snapshot_file_failed(tmp_path, rules_file):
    bad_snapshot = {
        "environment": "test",
        "schema": {
            "users": {"id": "integer"},  # missing 'email'
        },
    }
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(bad_snapshot))
    report = validate_snapshot_file(snap, load_rules(rules_file))
    assert not report.passed
    assert any("email" in v.message for v in report.violations)


# ---------------------------------------------------------------------------
# ValidationReport.summary
# ---------------------------------------------------------------------------

def test_summary_ok_when_passed():
    r = ValidationReport(snapshot_file="snap.json")
    assert r.summary().startswith("OK")


def test_summary_fail_when_violations():
    r = ValidationReport(
        snapshot_file="snap.json",
        violations=[ValidationViolation("users", 0, "missing 'id'")],
    )
    assert r.summary().startswith("FAIL")
    assert "users" in r.summary()
