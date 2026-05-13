"""Merge two snapshots into a unified schema view.

The merge resolves conflicts by preferring the 'primary' snapshot's
definition when the same table exists in both environments.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from schemasnap.snapshot import load_snapshot


@dataclass
class MergeResult:
    merged_schema: Dict[str, object]
    primary_env: str
    secondary_env: str
    tables_only_in_primary: List[str] = field(default_factory=list)
    tables_only_in_secondary: List[str] = field(default_factory=list)
    tables_conflicted: List[str] = field(default_factory=list)
    tables_identical: List[str] = field(default_factory=list)

    @property
    def conflict_count(self) -> int:
        return len(self.tables_conflicted)

    def summary(self) -> str:
        lines = [
            f"Merge: {self.primary_env} (primary) <- {self.secondary_env} (secondary)",
            f"  Tables only in primary   : {len(self.tables_only_in_primary)}",
            f"  Tables only in secondary : {len(self.tables_only_in_secondary)}",
            f"  Conflicted (primary wins): {len(self.tables_conflicted)}",
            f"  Identical                : {len(self.tables_identical)}",
        ]
        return "\n".join(lines)


def merge_schemas(
    primary: Dict[str, object],
    secondary: Dict[str, object],
    primary_env: str = "primary",
    secondary_env: str = "secondary",
) -> MergeResult:
    """Merge two schema dicts.  Primary wins on conflict."""
    merged: Dict[str, object] = {}
    only_primary: List[str] = []
    only_secondary: List[str] = []
    conflicted: List[str] = []
    identical: List[str] = []

    all_tables = set(primary.keys()) | set(secondary.keys())

    for table in sorted(all_tables):
        in_primary = table in primary
        in_secondary = table in secondary

        if in_primary and not in_secondary:
            merged[table] = copy.deepcopy(primary[table])
            only_primary.append(table)
        elif in_secondary and not in_primary:
            merged[table] = copy.deepcopy(secondary[table])
            only_secondary.append(table)
        else:
            # Both have the table — check for conflict
            if primary[table] == secondary[table]:
                merged[table] = copy.deepcopy(primary[table])
                identical.append(table)
            else:
                # Primary wins
                merged[table] = copy.deepcopy(primary[table])
                conflicted.append(table)

    return MergeResult(
        merged_schema=merged,
        primary_env=primary_env,
        secondary_env=secondary_env,
        tables_only_in_primary=only_primary,
        tables_only_in_secondary=only_secondary,
        tables_conflicted=conflicted,
        tables_identical=identical,
    )


def merge_snapshot_files(
    primary_file: str,
    secondary_file: str,
) -> MergeResult:
    """Load two snapshot files and merge them."""
    primary_snap = load_snapshot(primary_file)
    secondary_snap = load_snapshot(secondary_file)

    primary_env: str = primary_snap.get("environment", "primary")
    secondary_env: str = secondary_snap.get("environment", "secondary")
    primary_schema: Dict[str, object] = primary_snap.get("schema", {})
    secondary_schema: Dict[str, object] = secondary_snap.get("schema", {})

    return merge_schemas(primary_schema, secondary_schema, primary_env, secondary_env)
