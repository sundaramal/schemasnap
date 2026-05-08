"""Snapshot lineage: track parent-child relationships between snapshots."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class LineageEntry:
    snapshot_file: str
    parent_file: Optional[str]
    env: str
    schema_hash: str
    timestamp: str


def _lineage_path(snapshot_dir: str) -> Path:
    return Path(snapshot_dir) / ".lineage.jsonl"


def load_lineage(snapshot_dir: str) -> List[LineageEntry]:
    """Load all lineage entries from the lineage journal."""
    path = _lineage_path(snapshot_dir)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            data = json.loads(line)
            entries.append(LineageEntry(**data))
    return entries


def record_lineage(snapshot_dir: str, entry: LineageEntry) -> None:
    """Append a lineage entry to the journal."""
    path = _lineage_path(snapshot_dir)
    with path.open("a") as fh:
        fh.write(json.dumps(asdict(entry)) + "\n")


def get_parent(snapshot_dir: str, snapshot_file: str) -> Optional[LineageEntry]:
    """Return the lineage entry whose snapshot_file matches, or None."""
    for entry in load_lineage(snapshot_dir):
        if entry.snapshot_file == snapshot_file:
            return entry
    return None


def lineage_chain(snapshot_dir: str, snapshot_file: str) -> List[LineageEntry]:
    """Return the ancestry chain starting from snapshot_file back to the root."""
    index = {e.snapshot_file: e for e in load_lineage(snapshot_dir)}
    chain: List[LineageEntry] = []
    current = snapshot_file
    visited = set()
    while current and current not in visited:
        entry = index.get(current)
        if entry is None:
            break
        chain.append(entry)
        visited.add(current)
        current = entry.parent_file  # type: ignore[assignment]
    return chain
