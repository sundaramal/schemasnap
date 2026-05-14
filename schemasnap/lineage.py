"""Snapshot lineage tracking — records parent→child relationships between snapshots."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LineageEntry:
    child_hash: str
    parent_hash: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


def _lineage_path(snap_dir: Path) -> Path:
    return snap_dir / ".lineage.jsonl"


def load_lineage(snap_dir: Path) -> list[LineageEntry]:
    """Load all recorded lineage entries from *snap_dir*."""
    path = _lineage_path(snap_dir)
    if not path.exists():
        return []
    entries: list[LineageEntry] = []
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        entries.append(
            LineageEntry(
                child_hash=obj["child_hash"],
                parent_hash=obj.get("parent_hash"),
                metadata=obj.get("metadata", {}),
            )
        )
    return entries


def record_lineage(
    snap_dir: Path,
    *,
    child_hash: str,
    parent_hash: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LineageEntry:
    """Append a lineage entry mapping *child_hash* to *parent_hash*."""
    snap_dir.mkdir(parents=True, exist_ok=True)
    entry = LineageEntry(
        child_hash=child_hash,
        parent_hash=parent_hash,
        metadata=metadata or {},
    )
    path = _lineage_path(snap_dir)
    with path.open("a") as fh:
        fh.write(
            json.dumps(
                {
                    "child_hash": entry.child_hash,
                    "parent_hash": entry.parent_hash,
                    "metadata": entry.metadata,
                }
            )
            + "\n"
        )
    return entry


def get_parent(entries: list[LineageEntry], child_hash: str) -> LineageEntry | None:
    """Return the lineage entry whose *child_hash* matches, or *None*."""
    for e in reversed(entries):  # latest write wins
        if e.child_hash == child_hash:
            return e
    return None


def get_children(entries: list[LineageEntry], parent_hash: str) -> list[LineageEntry]:
    """Return all lineage entries whose *parent_hash* matches."""
    return [e for e in entries if e.parent_hash == parent_hash]
