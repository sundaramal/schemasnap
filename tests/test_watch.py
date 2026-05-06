"""Tests for schemasnap.watch — schema drift watcher."""

import os
import pytest

from schemasnap.watch import WatchConfig, watch_schema, default_drift_handler
from schemasnap.snapshot import capture_snapshot


SCHEMA_V1 = {
    "users": {"id": "integer", "name": "varchar"},
}

SCHEMA_V2 = {
    "users": {"id": "integer", "name": "varchar", "email": "varchar"},
}


@pytest.fixture()
def tmp_watch_dir(tmp_path):
    return str(tmp_path / "snapshots")


def test_watch_no_drift_returns_zero(tmp_watch_dir, monkeypatch):
    """When schema is unchanged, drift count should be 0."""
    monkeypatch.setattr("schemasnap.watch.time.sleep", lambda _: None)

    config = WatchConfig(
        snapshot_dir=tmp_watch_dir,
        env="staging",
        interval_seconds=0,
        max_iterations=1,
    )
    drift_count = watch_schema(SCHEMA_V1, config)
    assert drift_count == 0


def test_watch_detects_drift(tmp_watch_dir, monkeypatch):
    """Drift is detected when the schema changes between iterations."""
    schemas = iter([SCHEMA_V1, SCHEMA_V2])
    sleep_calls = []

    monkeypatch.setattr("schemasnap.watch.time.sleep", lambda s: sleep_calls.append(s))

    # Patch capture_snapshot so each call uses the next schema version
    original_capture = capture_snapshot

    def fake_capture(schema, env, snapshot_dir):
        return original_capture(next(schemas, SCHEMA_V2), env, snapshot_dir)

    monkeypatch.setattr("schemasnap.watch.capture_snapshot", fake_capture)

    collected_reports = []
    config = WatchConfig(
        snapshot_dir=tmp_watch_dir,
        env="staging",
        interval_seconds=0,
        max_iterations=1,
        on_drift=collected_reports.append,
    )
    drift_count = watch_schema(SCHEMA_V1, config)

    assert drift_count == 1
    assert len(collected_reports) == 1
    assert "staging" in collected_reports[0]


def test_watch_calls_extra_alert_handlers(tmp_watch_dir, monkeypatch):
    """All registered alert_handlers are called on drift."""
    schemas = iter([SCHEMA_V1, SCHEMA_V2])
    monkeypatch.setattr("schemasnap.watch.time.sleep", lambda _: None)

    original_capture = capture_snapshot

    def fake_capture(schema, env, snapshot_dir):
        return original_capture(next(schemas, SCHEMA_V2), env, snapshot_dir)

    monkeypatch.setattr("schemasnap.watch.capture_snapshot", fake_capture)

    primary_calls, secondary_calls = [], []
    config = WatchConfig(
        snapshot_dir=tmp_watch_dir,
        env="prod",
        interval_seconds=0,
        max_iterations=1,
        on_drift=primary_calls.append,
        alert_handlers=[secondary_calls.append],
    )
    watch_schema(SCHEMA_V1, config)

    assert len(primary_calls) == 1
    assert len(secondary_calls) == 1


def test_default_drift_handler_logs_warning(caplog):
    """default_drift_handler emits a WARNING log entry."""
    import logging

    with caplog.at_level(logging.WARNING, logger="schemasnap.watch"):
        default_drift_handler("DRIFT REPORT")

    assert any("drift" in r.message.lower() for r in caplog.records)
