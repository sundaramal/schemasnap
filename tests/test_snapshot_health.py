"""Tests for schemasnap.snapshot_health and cmd_snapshot_health."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.snapshot_health import (
    HealthIssue,
    HealthReport,
    run_health_checks,
    render_health_text,
    render_health_json,
)
from schemasnap.cmd_snapshot_health import add_snapshot_health_subparsers, cmd_snapshot_health
import argparse


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: Path, filename: str, payload: dict) -> Path:
    import json as _json
    p = directory / filename
    p.write_text(_json.dumps(payload))
    return p


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


def _good_snap(env: str = "prod", schema: dict | None = None) -> dict:
    return {
        "environment": env,
        "captured_at": "2024-01-01T00:00:00",
        "schema_hash": f"abc{env}",
        "schema": schema if schema is not None else {"users": {"id": "int"}},
    }


# ---------------------------------------------------------------------------
# HealthReport helpers
# ---------------------------------------------------------------------------

def test_health_report_passed_when_no_issues():
    r = HealthReport()
    assert r.passed is True


def test_health_report_fails_on_error_issue():
    r = HealthReport(issues=[HealthIssue(level="error", code="X", message="bad")])
    assert r.passed is False


def test_health_report_passes_with_warn_only():
    r = HealthReport(issues=[HealthIssue(level="warn", code="W", message="meh")])
    assert r.passed is True


def test_summary_contains_status(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc.json", _good_snap())
    r = run_health_checks(snap_dir)
    assert "PASS" in r.summary()


# ---------------------------------------------------------------------------
# run_health_checks
# ---------------------------------------------------------------------------

def test_empty_dir_returns_no_issues(snap_dir: Path):
    r = run_health_checks(snap_dir)
    assert r.issues == []


def test_good_snapshot_no_issues(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", _good_snap())
    r = run_health_checks(snap_dir)
    assert r.issues == []


def test_empty_schema_produces_warn(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", _good_snap(schema={}))
    r = run_health_checks(snap_dir)
    codes = [i.code for i in r.issues]
    assert "EMPTY_SCHEMA" in codes
    assert all(i.level == "warn" for i in r.issues if i.code == "EMPTY_SCHEMA")


def test_missing_metadata_produces_error(snap_dir: Path):
    bad = {"schema": {"t": {}}}
    _write_snapshot(snap_dir, "snap_prod_abc123.json", bad)
    r = run_health_checks(snap_dir)
    codes = [i.code for i in r.issues]
    assert "MISSING_METADATA" in codes
    assert r.passed is False


def test_duplicate_hash_produces_warn(snap_dir: Path):
    snap = _good_snap()
    _write_snapshot(snap_dir, "snap_prod_abc123.json", snap)
    _write_snapshot(snap_dir, "snap_prod_abc456.json", snap)  # same hash
    r = run_health_checks(snap_dir)
    codes = [i.code for i in r.issues]
    assert "DUPLICATE_HASH" in codes


# ---------------------------------------------------------------------------
# render helpers
# ---------------------------------------------------------------------------

def test_render_text_contains_summary(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", _good_snap())
    r = run_health_checks(snap_dir)
    text = render_health_text(r)
    assert "PASS" in text or "FAIL" in text


def test_render_json_is_valid(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", _good_snap())
    r = run_health_checks(snap_dir)
    obj = json.loads(render_health_json(r))
    assert "passed" in obj
    assert "issues" in obj


# ---------------------------------------------------------------------------
# cmd_snapshot_health
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = {"snap_dir": ".", "fmt": "text", "strict": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_snapshot_health_missing_dir_returns_1(tmp_path: Path):
    args = _make_args(snap_dir=str(tmp_path / "no_such_dir"))
    assert cmd_snapshot_health(args) == 1


def test_cmd_snapshot_health_pass_returns_zero(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", _good_snap())
    args = _make_args(snap_dir=str(snap_dir))
    assert cmd_snapshot_health(args) == 0


def test_cmd_snapshot_health_error_returns_two(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", {"schema": {}})
    args = _make_args(snap_dir=str(snap_dir))
    assert cmd_snapshot_health(args) == 2


def test_cmd_snapshot_health_strict_warn_returns_one(snap_dir: Path):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", _good_snap(schema={}))
    args = _make_args(snap_dir=str(snap_dir), strict=True)
    result = cmd_snapshot_health(args)
    assert result == 1


def test_add_snapshot_health_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_health_subparsers(sub)
    args = parser.parse_args(["snapshot-health", "/some/dir"])
    assert hasattr(args, "func")


def test_cmd_snapshot_health_json_fmt(snap_dir: Path, capsys):
    _write_snapshot(snap_dir, "snap_prod_abc123.json", _good_snap())
    args = _make_args(snap_dir=str(snap_dir), fmt="json")
    rc = cmd_snapshot_health(args)
    captured = capsys.readouterr()
    obj = json.loads(captured.out)
    assert "passed" in obj
    assert rc == 0
