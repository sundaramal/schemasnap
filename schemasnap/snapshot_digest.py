"""Compute a human-readable digest summary for one or more snapshots."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from schemasnap.snapshot import load_snapshot


@dataclass
class DigestEntry:
    env: str
    snapshot_file: str
    table_count: int
    column_count: int
    short_hash: str
    top_tables: List[str] = field(default_factory=list)


def _short_hash(schema: dict) -> str:
    """Return a short (8-char) deterministic hash of the schema dict."""
    raw = str(sorted(schema.items())).encode()
    return hashlib.sha256(raw).hexdigest()[:8]


def _top_tables(schema: dict, n: int = 5) -> List[str]:
    """Return up to *n* table names sorted by descending column count."""
    ranked = sorted(schema.keys(), key=lambda t: len(schema[t]), reverse=True)
    return ranked[:n]


def compute_digest(snapshot_path: Path) -> DigestEntry:
    """Load a snapshot file and return a DigestEntry for it."""
    data = load_snapshot(snapshot_path)
    schema: Dict[str, dict] = data.get("schema", {})
    column_count = sum(len(cols) for cols in schema.values())
    return DigestEntry(
        env=data.get("environment", "unknown"),
        snapshot_file=snapshot_path.name,
        table_count=len(schema),
        column_count=column_count,
        short_hash=_short_hash(schema),
        top_tables=_top_tables(schema),
    )


def render_digest_text(entry: DigestEntry) -> str:
    lines = [
        f"Snapshot : {entry.snapshot_file}",
        f"Env      : {entry.env}",
        f"Hash     : {entry.short_hash}",
        f"Tables   : {entry.table_count}",
        f"Columns  : {entry.column_count}",
    ]
    if entry.top_tables:
        lines.append("Top tables (by column count):")
        for t in entry.top_tables:
            lines.append(f"  - {t}")
    return "\n".join(lines)


def render_digest_json(entry: DigestEntry) -> str:
    import json
    return json.dumps(
        {
            "env": entry.env,
            "snapshot_file": entry.snapshot_file,
            "table_count": entry.table_count,
            "column_count": entry.column_count,
            "short_hash": entry.short_hash,
            "top_tables": entry.top_tables,
        },
        indent=2,
    )
