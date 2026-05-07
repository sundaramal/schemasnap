"""Audit log for schema snapshot events (captures, diffs, baseline changes)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

AUDIT_FILENAME = "audit.jsonl"


@dataclass
class AuditEntry:
    timestamp: str
    event: str          # e.g. "capture", "compare", "baseline_set", "tag_set"
    environment: str
    details: dict

    @classmethod
    def now(cls, event: str, environment: str, details: dict) -> "AuditEntry":
        ts = datetime.now(timezone.utc).isoformat()
        return cls(timestamp=ts, event=event, environment=environment, details=details)


def _audit_path(snapshot_dir: str) -> Path:
    return Path(snapshot_dir) / AUDIT_FILENAME


def append_audit(snapshot_dir: str, entry: AuditEntry) -> None:
    """Append a single audit entry to the JSONL audit log."""
    path = _audit_path(snapshot_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(entry)) + "\n")


def load_audit(snapshot_dir: str) -> List[AuditEntry]:
    """Load all audit entries from the log; returns [] if file absent."""
    path = _audit_path(snapshot_dir)
    if not path.exists():
        return []
    entries: List[AuditEntry] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                data = json.loads(line)
                entries.append(AuditEntry(**data))
    return entries


def filter_audit(
    entries: List[AuditEntry],
    event: Optional[str] = None,
    environment: Optional[str] = None,
) -> List[AuditEntry]:
    """Filter audit entries by event type and/or environment."""
    result = entries
    if event:
        result = [e for e in result if e.event == event]
    if environment:
        result = [e for e in result if e.environment == environment]
    return result
