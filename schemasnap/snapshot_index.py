"""Build and query an in-memory index of all snapshots in a directory."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from schemasnap.snapshot import list_snapshots, load_snapshot


@dataclass
class IndexEntry:
    path: Path
    env: str
    schema_hash: str
    table_count: int
    tables: List[str]


@dataclass
class SnapshotIndex:
    entries: List[IndexEntry] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    def by_env(self, env: str) -> List[IndexEntry]:
        """Return all entries for *env*, sorted by filename (oldest first)."""
        return sorted(
            [e for e in self.entries if e.env == env],
            key=lambda e: e.path.name,
        )

    def by_hash(self, schema_hash: str) -> Optional[IndexEntry]:
        """Return the first entry whose hash starts with *schema_hash*."""
        for e in self.entries:
            if e.schema_hash.startswith(schema_hash):
                return e
        return None

    def envs(self) -> List[str]:
        """Sorted list of unique environment names present in the index."""
        return sorted({e.env for e in self.entries})

    def to_dict(self) -> Dict:
        return {
            "environments": self.envs(),
            "total_snapshots": len(self.entries),
            "entries": [
                {
                    "path": str(e.path),
                    "env": e.env,
                    "schema_hash": e.schema_hash,
                    "table_count": e.table_count,
                    "tables": e.tables,
                }
                for e in self.entries
            ],
        }


def build_index(snapshot_dir: str | Path) -> SnapshotIndex:
    """Scan *snapshot_dir* and return a populated :class:`SnapshotIndex`."""
    snapshot_dir = Path(snapshot_dir)
    entries: List[IndexEntry] = []
    for path in list_snapshots(snapshot_dir):
        try:
            snap = load_snapshot(path)
        except (json.JSONDecodeError, KeyError, OSError):
            continue
        schema = snap.get("schema", {})
        entries.append(
            IndexEntry(
                path=path,
                env=snap.get("environment", "unknown"),
                schema_hash=snap.get("schema_hash", ""),
                table_count=len(schema),
                tables=sorted(schema.keys()),
            )
        )
    return SnapshotIndex(entries=entries)
