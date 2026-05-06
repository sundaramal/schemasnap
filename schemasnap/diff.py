"""Schema diff utilities for comparing two snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaDiff:
    """Represents the differences between two schema snapshots."""

    env: str
    old_hash: str
    new_hash: str
    added_tables: list[str] = field(default_factory=list)
    removed_tables: list[str] = field(default_factory=list)
    modified_tables: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.added_tables or self.removed_tables or self.modified_tables)

    def summary(self) -> str:
        if not self.has_changes:
            return f"[{self.env}] No schema changes detected."
        lines = [f"[{self.env}] Schema changes detected ({self.old_hash[:8]} -> {self.new_hash[:8]}):"]
        for table in self.added_tables:
            lines.append(f"  + Table added:   {table}")
        for table in self.removed_tables:
            lines.append(f"  - Table removed: {table}")
        for table, changes in self.modified_tables.items():
            added_cols = changes.get("added_columns", [])
            removed_cols = changes.get("removed_columns", [])
            for col in added_cols:
                lines.append(f"  ~ {table}: column added   '{col}'")
            for col in removed_cols:
                lines.append(f"  ~ {table}: column removed '{col}'")
        return "\n".join(lines)


def diff_snapshots(old: dict[str, Any], new: dict[str, Any], env: str = "unknown") -> SchemaDiff:
    """Compute the diff between two snapshot dictionaries."""
    old_schema = old.get("schema", {})
    new_schema = new.get("schema", {})
    old_hash = old.get("hash", "")
    new_hash = new.get("hash", "")

    old_tables = set(old_schema.keys())
    new_tables = set(new_schema.keys())

    added_tables = sorted(new_tables - old_tables)
    removed_tables = sorted(old_tables - new_tables)

    modified_tables: dict[str, dict[str, Any]] = {}
    for table in old_tables & new_tables:
        old_cols = set(old_schema[table].get("columns", []))
        new_cols = set(new_schema[table].get("columns", []))
        added_cols = sorted(new_cols - old_cols)
        removed_cols = sorted(old_cols - new_cols)
        if added_cols or removed_cols:
            modified_tables[table] = {
                "added_columns": added_cols,
                "removed_columns": removed_cols,
            }

    return SchemaDiff(
        env=env,
        old_hash=old_hash,
        new_hash=new_hash,
        added_tables=added_tables,
        removed_tables=removed_tables,
        modified_tables=modified_tables,
    )
