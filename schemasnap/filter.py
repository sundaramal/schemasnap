"""Filter snapshots by table name patterns or column criteria."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FilterConfig:
    """Configuration for snapshot filtering."""

    include_tables: List[str] = field(default_factory=list)  # glob patterns
    exclude_tables: List[str] = field(default_factory=list)  # glob patterns
    include_columns: List[str] = field(default_factory=list)  # glob patterns
    exclude_columns: List[str] = field(default_factory=list)  # glob patterns


def _matches_any(name: str, patterns: List[str]) -> bool:
    """Return True if *name* matches at least one glob pattern."""
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def filter_tables(schema: Dict, config: FilterConfig) -> Dict:
    """Return a copy of *schema* with tables filtered according to *config*.

    The schema dict maps table names to their column definitions.
    """
    result: Dict = {}
    for table_name, columns in schema.items():
        if config.include_tables and not _matches_any(table_name, config.include_tables):
            continue
        if config.exclude_tables and _matches_any(table_name, config.exclude_tables):
            continue
        filtered_columns = filter_columns(columns, config)
        result[table_name] = filtered_columns
    return result


def filter_columns(columns: Dict, config: FilterConfig) -> Dict:
    """Return a copy of *columns* filtered by include/exclude column patterns."""
    result: Dict = {}
    for col_name, col_def in columns.items():
        if config.include_columns and not _matches_any(col_name, config.include_columns):
            continue
        if config.exclude_columns and _matches_any(col_name, config.exclude_columns):
            continue
        result[col_name] = col_def
    return result


def apply_filter(snapshot: Dict, config: Optional[FilterConfig] = None) -> Dict:
    """Apply *config* to the schema section of a snapshot dict.

    Returns a new snapshot dict with the filtered schema.
    If *config* is None or has no patterns, returns the snapshot unchanged.
    """
    if config is None:
        return snapshot

    has_any_filter = (
        config.include_tables
        or config.exclude_tables
        or config.include_columns
        or config.exclude_columns
    )
    if not has_any_filter:
        return snapshot

    filtered_snapshot = dict(snapshot)
    filtered_snapshot["schema"] = filter_tables(snapshot.get("schema", {}), config)
    return filtered_snapshot
