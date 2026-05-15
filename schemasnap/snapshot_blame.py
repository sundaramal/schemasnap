"""Blame: for each table/column, find the snapshot where it first appeared."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .snapshot import load_snapshot, list_snapshots


@dataclass
class BlameEntry:
    table: str
    column: Optional[str]  # None means the blame is for the table itself
    first_seen_file: str
    first_seen_env: str
    first_seen_hash: str


@dataclass
class BlameReport:
    entries: List[BlameEntry] = field(default_factory=list)

    def for_table(self, table: str) -> List[BlameEntry]:
        return [e for e in self.entries if e.table == table]

    def summary(self) -> str:
        lines = []
        for e in self.entries:
            target = f"{e.table}.{e.column}" if e.column else e.table
            lines.append(
                f"{target:40s}  first seen in {e.first_seen_file} ({e.first_seen_env})"
            )
        return "\n".join(lines)


def compute_blame(snapshot_dir: str, env: Optional[str] = None) -> BlameReport:
    """Walk snapshots in chronological order and record first-appearance."""
    files = list_snapshots(snapshot_dir)
    if env:
        files = [f for f in files if Path(f).name.startswith(f"{env}_")]
    # Sort by filename (which embeds a timestamp) for chronological order.
    files = sorted(files, key=lambda p: Path(p).name)

    seen_tables: Dict[str, BlameEntry] = {}
    seen_columns: Dict[str, BlameEntry] = {}  # key: "table.column"

    entries: List[BlameEntry] = []

    for filepath in files:
        snap = load_snapshot(filepath)
        snap_env = snap.get("environment", "unknown")
        snap_hash = snap.get("schema_hash", "")
        snap_file = Path(filepath).name
        schema: Dict = snap.get("schema", {})

        for table, columns in schema.items():
            if table not in seen_tables:
                entry = BlameEntry(
                    table=table,
                    column=None,
                    first_seen_file=snap_file,
                    first_seen_env=snap_env,
                    first_seen_hash=snap_hash,
                )
                seen_tables[table] = entry
                entries.append(entry)

            for col_name in (columns if isinstance(columns, list) else columns.keys()):
                key = f"{table}.{col_name}"
                if key not in seen_columns:
                    col_entry = BlameEntry(
                        table=table,
                        column=col_name,
                        first_seen_file=snap_file,
                        first_seen_env=snap_env,
                        first_seen_hash=snap_hash,
                    )
                    seen_columns[key] = col_entry
                    entries.append(col_entry)

    return BlameReport(entries=entries)
