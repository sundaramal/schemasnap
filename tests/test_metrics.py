"""Tests for schemasnap.metrics and schemasnap.cmd_metrics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.metrics import (
    SnapshotMetrics,
    collect_metrics,
    render_metrics_json,
    render_metrics_text,
)
from schemasnap.cmd_metrics import add_metrics_subparsers, cmd_metrics
from schemasnap.snapshot import capture_snapshot


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    d = tmp_path / "snapshots"
    d.mkdir()
    return d


def _schema(tables: dict) -> dict:
    return tables


def test_collect_metrics_empty_dir(snap_dir: Path) -> None:
    m = collect_metrics(snap_dir, env="prod")
    assert m.total_snapshots == 0
    assert m.total_tables == 0
    assert m.total_columns == 0
    assert m.latest_hash is None
    assert m.drift_detected is False


def test_collect_metrics_single_snapshot(snap_dir: Path) -> None:
    schema = {"users": ["id", "email"], "orders": ["id", "total"]}
    capture_snapshot(schema, env="prod", snapshot_dir=snap_dir)

    m = collect_metrics(snap_dir, env="prod")
    assert m.total_snapshots == 1
    assert m.total_tables == 2
    assert m.total_columns == 4
    assert m.latest_hash is not None
    assert m.drift_detected is False


def test_collect_metrics_detects_drift(snap_dir: Path) -> None:
    schema1 = {"users": ["id", "email"]}
    schema2 = {"users": ["id", "email"], "orders": ["id"]}
    capture_snapshot(schema1, env="prod", snapshot_dir=snap_dir)
    capture_snapshot(schema2, env="prod", snapshot_dir=snap_dir)

    m = collect_metrics(snap_dir, env="prod")
    assert m.drift_detected is True
    assert m.added_tables == 1
    assert m.removed_tables == 0


def test_collect_metrics_no_drift_when_identical(snap_dir: Path) -> None:
    schema = {"users": ["id", "email"]}
    capture_snapshot(schema, env="prod", snapshot_dir=snap_dir)
    capture_snapshot(schema, env="prod", snapshot_dir=snap_dir)

    m = collect_metrics(snap_dir, env="prod")
    assert m.drift_detected is False


def test_render_metrics_json_valid(snap_dir: Path) -> None:
    m = SnapshotMetrics(env="staging", total_snapshots=3, total_tables=5, total_columns=12)
    raw = render_metrics_json(m)
    data = json.loads(raw)
    assert data["env"] == "staging"
    assert data["total_tables"] == 5


def test_render_metrics_text_contains_env() -> None:
    m = SnapshotMetrics(env="prod", total_snapshots=1, total_tables=2, total_columns=6)
    text = render_metrics_text(m)
    assert "prod" in text
    assert "2" in text


def test_render_metrics_text_shows_drift() -> None:
    m = SnapshotMetrics(
        env="prod", total_snapshots=2, total_tables=3, total_columns=8,
        drift_detected=True, added_tables=1, removed_tables=0, modified_tables=2,
    )
    text = render_metrics_text(m)
    assert "YES" in text
    assert "Modified" in text


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"env": "prod", "snapshot_dir": "snapshots", "format": "text"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_metrics_missing_dir(tmp_path: Path) -> None:
    args = _make_args(snapshot_dir=str(tmp_path / "no_such_dir"))
    assert cmd_metrics(args) == 1


def test_cmd_metrics_returns_zero(snap_dir: Path) -> None:
    capture_snapshot({"t": ["id"]}, env="prod", snapshot_dir=snap_dir)
    args = _make_args(snapshot_dir=str(snap_dir))
    assert cmd_metrics(args) == 0


def test_cmd_metrics_json_format(snap_dir: Path, capsys: pytest.CaptureFixture) -> None:
    capture_snapshot({"t": ["id"]}, env="prod", snapshot_dir=snap_dir)
    args = _make_args(snapshot_dir=str(snap_dir), format="json")
    cmd_metrics(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "env" in data


def test_add_metrics_subparsers_registers_command() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_metrics_subparsers(sub)
    args = parser.parse_args(["metrics", "prod"])
    assert args.env == "prod"
    assert hasattr(args, "func")
