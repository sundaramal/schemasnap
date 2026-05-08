"""Search snapshots by table name, column name, or schema properties."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from schemasnap.snapshot import load_snapshot, list_snapshots


@dataclass
class SearchResult:
    snapshot_file: str
    env: str
    table: str
    column: Optional[str] = None
    match_type: str = "table"  # "table" | "column"


@dataclass
class SearchConfig:
    snapshot_dir: str
    env: Optional[str] = None
    table_pattern: Optional[str] = None
    column_pattern: Optional[str] = None
    latest_only: bool = True


def _env_from_filename(filename: str) -> str:
    """Extract environment name from snapshot filename."""
    stem = Path(filename).stem  # e.g. "prod_2024-01-01T00-00-00_abc123"
    return stem.split("_")[0]


def _snapshots_to_search(config: SearchConfig) -> List[str]:
    """Return list of snapshot file paths to search."""
    all_snaps = list_snapshots(config.snapshot_dir)
    if not all_snaps:
        return []

    if config.env:
        all_snaps = [
            s for s in all_snaps if _env_from_filename(Path(s).name) == config.env
        ]

    if not config.latest_only:
        return all_snaps

    # Keep only the most recent snapshot per environment
    latest: dict[str, str] = {}
    for snap in sorted(all_snaps):
        env = _env_from_filename(Path(snap).name)
        latest[env] = snap
    return list(latest.values())


def search_snapshots(config: SearchConfig) -> List[SearchResult]:
    """Search snapshots according to config, returning matched results."""
    results: List[SearchResult] = []
    snaps = _snapshots_to_search(config)

    table_re = re.compile(config.table_pattern, re.IGNORECASE) if config.table_pattern else None
    column_re = re.compile(config.column_pattern, re.IGNORECASE) if config.column_pattern else None

    for snap_path in snaps:
        data = load_snapshot(snap_path)
        schema = data.get("schema", {})
        env = _env_from_filename(Path(snap_path).name)

        for table_name, table_def in schema.items():
            table_matches = table_re is None or table_re.search(table_name)

            if column_re is None:
                if table_matches:
                    results.append(SearchResult(
                        snapshot_file=snap_path,
                        env=env,
                        table=table_name,
                        match_type="table",
                    ))
            else:
                columns = table_def.get("columns", {})
                for col_name in columns:
                    if (table_matches or table_re is None) and column_re.search(col_name):
                        results.append(SearchResult(
                            snapshot_file=snap_path,
                            env=env,
                            table=table_name,
                            column=col_name,
                            match_type="column",
                        ))

    return results
