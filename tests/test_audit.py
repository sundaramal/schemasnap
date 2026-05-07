"""Tests for schemasnap.audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.audit import (
    AuditEntry,
    append_audit,
    load_audit,
    filter_audit,
    AUDIT_FILENAME,
)


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_append_and_load_roundtrip(tmp_dir):
    entry = AuditEntry.now("capture", "production", {"hash": "abc123"})
    append_audit(str(tmp_dir), entry)
    loaded = load_audit(str(tmp_dir))
    assert len(loaded) == 1
    assert loaded[0].event == "capture"
    assert loaded[0].environment == "production"
    assert loaded[0].details["hash"] == "abc123"


def test_load_audit_empty_when_no_file(tmp_dir):
    result = load_audit(str(tmp_dir))
    assert result == []


def test_append_multiple_entries(tmp_dir):
    for i in range(3):
        append_audit(str(tmp_dir), AuditEntry.now("compare", f"env{i}", {"changes": i}))
    loaded = load_audit(str(tmp_dir))
    assert len(loaded) == 3


def test_audit_file_is_jsonl(tmp_dir):
    append_audit(str(tmp_dir), AuditEntry.now("tag_set", "staging", {"tag": "v1"}))
    lines = (tmp_dir / AUDIT_FILENAME).read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert "timestamp" in data
    assert data["event"] == "tag_set"


def test_filter_by_event(tmp_dir):
    append_audit(str(tmp_dir), AuditEntry.now("capture", "prod", {}))
    append_audit(str(tmp_dir), AuditEntry.now("compare", "prod", {}))
    entries = load_audit(str(tmp_dir))
    filtered = filter_audit(entries, event="capture")
    assert len(filtered) == 1
    assert filtered[0].event == "capture"


def test_filter_by_environment(tmp_dir):
    append_audit(str(tmp_dir), AuditEntry.now("capture", "prod", {}))
    append_audit(str(tmp_dir), AuditEntry.now("capture", "staging", {}))
    entries = load_audit(str(tmp_dir))
    filtered = filter_audit(entries, environment="staging")
    assert len(filtered) == 1
    assert filtered[0].environment == "staging"


def test_filter_by_event_and_environment(tmp_dir):
    append_audit(str(tmp_dir), AuditEntry.now("capture", "prod", {}))
    append_audit(str(tmp_dir), AuditEntry.now("compare", "prod", {}))
    append_audit(str(tmp_dir), AuditEntry.now("capture", "staging", {}))
    entries = load_audit(str(tmp_dir))
    filtered = filter_audit(entries, event="capture", environment="prod")
    assert len(filtered) == 1


def test_entry_timestamp_is_utc_iso(tmp_dir):
    entry = AuditEntry.now("baseline_set", "dev", {})
    assert entry.timestamp.endswith("+00:00") or entry.timestamp.endswith("Z") or "T" in entry.timestamp
