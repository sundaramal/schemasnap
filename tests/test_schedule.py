"""Tests for schemasnap.schedule."""

import os
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from schemasnap.schedule import ScheduleConfig, prune_old_snapshots, run_schedule


@pytest.fixture
def tmp_dir(tmp_path):
    return str(tmp_path)


def _write_snapshot(directory, env, filename, mtime_offset_days=0):
    """Write a fake snapshot file, optionally back-dating its mtime."""
    env_dir = Path(directory) / env
    env_dir.mkdir(parents=True, exist_ok=True)
    snap = env_dir / filename
    snap.write_text(json.dumps({"tables": {}}))
    if mtime_offset_days:
        old_time = time.time() - mtime_offset_days * 86400
        os.utime(str(snap), (old_time, old_time))
    return str(snap)


def test_prune_removes_old_snapshots(tmp_dir):
    old = _write_snapshot(tmp_dir, "prod", "snap_old.json", mtime_offset_days=40)
    recent = _write_snapshot(tmp_dir, "prod", "snap_recent.json", mtime_offset_days=1)
    pruned = prune_old_snapshots(tmp_dir, "prod", retention_days=30)
    assert pruned == 1
    assert not os.path.exists(old)
    assert os.path.exists(recent)


def test_prune_keeps_all_when_within_retention(tmp_dir):
    _write_snapshot(tmp_dir, "staging", "snap_a.json", mtime_offset_days=5)
    _write_snapshot(tmp_dir, "staging", "snap_b.json", mtime_offset_days=10)
    pruned = prune_old_snapshots(tmp_dir, "staging", retention_days=30)
    assert pruned == 0


def test_prune_returns_zero_when_no_snapshots(tmp_dir):
    pruned = prune_old_snapshots(tmp_dir, "empty_env", retention_days=7)
    assert pruned == 0


def test_run_schedule_calls_capture(tmp_dir):
    config = ScheduleConfig(
        db_url="sqlite:///:memory:",
        env="dev",
        snapshot_dir=tmp_dir,
        interval_seconds=0,
        max_runs=2,
    )
    with patch("schemasnap.schedule.capture_snapshot", return_value="/fake/snap.json") as mock_cap, \
         patch("schemasnap.schedule.prune_old_snapshots", return_value=0):
        run_schedule(config)
    assert mock_cap.call_count == 2
    mock_cap.assert_called_with("sqlite:///:memory:", "dev", tmp_dir)


def test_run_schedule_calls_on_tick(tmp_dir):
    ticks = []
    config = ScheduleConfig(
        db_url="sqlite:///:memory:",
        env="dev",
        snapshot_dir=tmp_dir,
        interval_seconds=0,
        max_runs=3,
        on_tick=lambda path, run: ticks.append((path, run)),
    )
    with patch("schemasnap.schedule.capture_snapshot", return_value="/snap.json"), \
         patch("schemasnap.schedule.prune_old_snapshots", return_value=0):
        run_schedule(config)
    assert len(ticks) == 3
    assert ticks[0] == ("/snap.json", 1)
    assert ticks[2] == ("/snap.json", 3)


def test_run_schedule_continues_on_error(tmp_dir):
    config = ScheduleConfig(
        db_url="sqlite:///:memory:",
        env="dev",
        snapshot_dir=tmp_dir,
        interval_seconds=0,
        max_runs=3,
    )
    with patch("schemasnap.schedule.capture_snapshot", side_effect=RuntimeError("db down")), \
         patch("schemasnap.schedule.prune_old_snapshots", return_value=0):
        # Should not raise
        run_schedule(config)


def test_run_schedule_invokes_watch_when_configured(tmp_dir):
    from schemasnap.watch import WatchConfig
    wc = WatchConfig(alert_handlers=[])
    config = ScheduleConfig(
        db_url="sqlite:///:memory:",
        env="dev",
        snapshot_dir=tmp_dir,
        interval_seconds=0,
        max_runs=1,
        watch_config=wc,
    )
    with patch("schemasnap.schedule.capture_snapshot", return_value="/snap.json"), \
         patch("schemasnap.schedule.watch_schema", return_value=0) as mock_watch, \
         patch("schemasnap.schedule.prune_old_snapshots", return_value=0):
        run_schedule(config)
    mock_watch.assert_called_once_with("sqlite:///:memory:", "dev", tmp_dir, wc)
