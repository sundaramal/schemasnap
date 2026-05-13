"""Tests for schemasnap.cmd_validate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from schemasnap.cmd_validate import add_validate_subparsers, cmd_validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        rules="rules.json",
        snapshot=None,
        env="production",
        snapshot_dir="snapshots",
        format="text",
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def snap_and_rules(tmp_path: Path):
    """Write a valid snapshot + matching rules file; return (snap_path, rules_path)."""
    schema = {
        "environment": "production",
        "schema": {
            "users": {"id": "integer", "email": "varchar"},
        },
    }
    snap = tmp_path / "snap_production_abc123.json"
    snap.write_text(json.dumps(schema))

    rules = [{"table_pattern": "users", "required_columns": ["id", "email"]}]
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps(rules))
    return snap, rules_file


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------

def test_add_validate_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_validate_subparsers(sub)
    args = parser.parse_args(["validate", "--rules", "r.json"])
    assert hasattr(args, "func")


# ---------------------------------------------------------------------------
# cmd_validate
# ---------------------------------------------------------------------------

def test_cmd_validate_returns_zero_on_pass(snap_and_rules):
    snap, rules = snap_and_rules
    args = _make_args(snapshot=str(snap), rules=str(rules))
    assert cmd_validate(args) == 0


def test_cmd_validate_returns_two_on_failure(tmp_path):
    bad = {
        "environment": "production",
        "schema": {"users": {"id": "integer"}},  # missing 'email'
    }
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(bad))
    rules = [{"table_pattern": "users", "required_columns": ["id", "email"]}]
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps(rules))
    args = _make_args(snapshot=str(snap), rules=str(rules_file))
    assert cmd_validate(args) == 2


def test_cmd_validate_returns_one_when_snapshot_missing(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text("[]")
    args = _make_args(snapshot=str(tmp_path / "nonexistent.json"), rules=str(rules_file))
    assert cmd_validate(args) == 1


def test_cmd_validate_returns_one_when_rules_missing(snap_and_rules):
    snap, _ = snap_and_rules
    args = _make_args(snapshot=str(snap), rules="/no/such/rules.json")
    assert cmd_validate(args) == 1


def test_cmd_validate_json_output(snap_and_rules, capsys):
    snap, rules = snap_and_rules
    args = _make_args(snapshot=str(snap), rules=str(rules), format="json")
    rc = cmd_validate(args)
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["passed"] is True
    assert data["violations"] == []


def test_cmd_validate_uses_latest_when_no_snapshot(snap_and_rules):
    snap, rules = snap_and_rules
    snap_dir = str(snap.parent)
    with patch("schemasnap.cmd_validate.latest_snapshot", return_value=str(snap)) as mock_latest:
        args = _make_args(snapshot=None, rules=str(rules), snapshot_dir=snap_dir, env="production")
        rc = cmd_validate(args)
    mock_latest.assert_called_once_with(snap_dir, "production")
    assert rc == 0


def test_cmd_validate_returns_one_when_no_latest(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text("[]")
    with patch("schemasnap.cmd_validate.latest_snapshot", return_value=None):
        args = _make_args(snapshot=None, rules=str(rules_file),
                          snapshot_dir=str(tmp_path), env="production")
        assert cmd_validate(args) == 1
