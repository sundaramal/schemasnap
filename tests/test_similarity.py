"""Tests for schemasnap.similarity and schemasnap.cmd_similarity."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pytest

from schemasnap.similarity import SimilarityReport, compute_similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap(schema: dict) -> dict:
    return {"schema": schema}


_TABLE_A = {"columns": {"id": "int", "name": "text"}}
_TABLE_B = {"columns": {"id": "int", "name": "text", "email": "text"}}


# ---------------------------------------------------------------------------
# compute_similarity unit tests
# ---------------------------------------------------------------------------

def test_identical_snapshots_score_one():
    schema = {"users": _TABLE_A, "orders": _TABLE_A}
    report = compute_similarity(_snap(schema), _snap(schema))
    assert report.overall_score == pytest.approx(1.0)


def test_completely_different_tables():
    snap_a = _snap({"users": _TABLE_A})
    snap_b = _snap({"products": _TABLE_A})
    report = compute_similarity(snap_a, snap_b)
    assert report.overall_score == pytest.approx(0.0)
    assert "users" in report.only_in_a
    assert "products" in report.only_in_b


def test_partial_column_overlap():
    snap_a = _snap({"users": _TABLE_A})
    snap_b = _snap({"users": _TABLE_B})
    report = compute_similarity(snap_a, snap_b)
    # table present in both -> present_score = 1.0
    # column jaccard: 2 common / 3 union
    expected_col = 2 / 3
    expected_overall = (1.0 + expected_col) / 2
    assert report.overall_score == pytest.approx(expected_overall)
    assert report.table_scores["users"] == pytest.approx(expected_col)


def test_empty_snapshots_score_one():
    report = compute_similarity(_snap({}), _snap({}))
    assert report.overall_score == pytest.approx(1.0)


def test_only_in_sets_populated():
    snap_a = _snap({"a": _TABLE_A, "shared": _TABLE_A})
    snap_b = _snap({"b": _TABLE_A, "shared": _TABLE_A})
    report = compute_similarity(snap_a, snap_b, env_a="prod", env_b="staging")
    assert "a" in report.only_in_a
    assert "b" in report.only_in_b
    assert "shared" not in report.only_in_a
    assert "shared" not in report.only_in_b
    assert report.env_a == "prod"
    assert report.env_b == "staging"


def test_summary_contains_env_names():
    report = SimilarityReport(
        env_a="prod", env_b="dev", overall_score=0.75,
        table_scores={"users": 0.9},
        only_in_a=set(), only_in_b={"logs"},
    )
    text = report.summary()
    assert "prod" in text
    assert "dev" in text
    assert "75.00%" in text
    assert "users" in text


# ---------------------------------------------------------------------------
# cmd_similarity integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path / "snapshots"


def _write_snap(directory: Path, env: str, schema: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{env}_20240101T000000_abc123.json"
    path.write_text(json.dumps({"env": env, "schema": schema}))
    return path


def _make_args(snap_dir: Path, env_a: str, env_b: str,
               fmt: str = "text", threshold: float | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        snapshot_dir=str(snap_dir),
        env_a=env_a,
        env_b=env_b,
        format=fmt,
        threshold=threshold,
    )


def test_cmd_similarity_missing_snapshot_returns_one(snap_dir, capsys):
    from schemasnap.cmd_similarity import cmd_similarity
    _write_snap(snap_dir, "prod", {"users": _TABLE_A})
    args = _make_args(snap_dir, "prod", "staging")
    rc = cmd_similarity(args)
    assert rc == 1
    assert "staging" in capsys.readouterr().err


def test_cmd_similarity_text_output(snap_dir, capsys):
    from schemasnap.cmd_similarity import cmd_similarity
    _write_snap(snap_dir, "prod", {"users": _TABLE_A})
    _write_snap(snap_dir, "staging", {"users": _TABLE_A})
    args = _make_args(snap_dir, "prod", "staging", fmt="text")
    rc = cmd_similarity(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "100.00%" in out


def test_cmd_similarity_json_output(snap_dir, capsys):
    from schemasnap.cmd_similarity import cmd_similarity
    _write_snap(snap_dir, "prod", {"users": _TABLE_A})
    _write_snap(snap_dir, "staging", {"users": _TABLE_B})
    args = _make_args(snap_dir, "prod", "staging", fmt="json")
    rc = cmd_similarity(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "overall_score" in data
    assert data["env_a"] == "prod"


def test_cmd_similarity_threshold_fail(snap_dir, capsys):
    from schemasnap.cmd_similarity import cmd_similarity
    _write_snap(snap_dir, "prod", {"users": _TABLE_A})
    _write_snap(snap_dir, "staging", {"products": _TABLE_A})
    args = _make_args(snap_dir, "prod", "staging", threshold=0.5)
    rc = cmd_similarity(args)
    assert rc == 1


def test_cmd_similarity_threshold_pass(snap_dir):
    from schemasnap.cmd_similarity import cmd_similarity
    _write_snap(snap_dir, "prod", {"users": _TABLE_A})
    _write_snap(snap_dir, "staging", {"users": _TABLE_A})
    args = _make_args(snap_dir, "prod", "staging", threshold=0.99)
    rc = cmd_similarity(args)
    assert rc == 0
