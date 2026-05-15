"""Apply a patch (diff) to a snapshot to produce a new snapshot."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .diff import SchemaDiff


@dataclass
class PatchResult:
    success: bool
    patched_schema: Dict[str, Any] = field(default_factory=dict)
    applied: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    message: str = ""


def apply_patch(
    base_snapshot: Dict[str, Any],
    diff: SchemaDiff,
    *,
    allow_missing: bool = False,
) -> PatchResult:
    """Return a new snapshot dict with *diff* applied to *base_snapshot*.

    Parameters
    ----------
    base_snapshot:
        Parsed snapshot dict (as returned by ``load_snapshot``).
    diff:
        A :class:`~schemasnap.diff.SchemaDiff` describing the changes to apply.
    allow_missing:
        When *True*, removals that target a table not present in the base are
        silently skipped instead of causing a failure.
    """
    schema: Dict[str, Any] = copy.deepcopy(base_snapshot.get("schema", {}))
    applied: List[str] = []
    skipped: List[str] = []

    # Remove tables
    for table in diff.removed_tables:
        if table in schema:
            del schema[table]
            applied.append(f"remove:{table}")
        elif allow_missing:
            skipped.append(f"remove:{table}")
        else:
            return PatchResult(
                success=False,
                message=f"Cannot remove table '{table}': not present in base snapshot.",
            )

    # Add tables
    for table, columns in diff.added_tables.items():
        schema[table] = copy.deepcopy(columns)
        applied.append(f"add:{table}")

    # Modify tables
    for table, changes in diff.modified_tables.items():
        if table not in schema:
            if allow_missing:
                skipped.append(f"modify:{table}")
                continue
            return PatchResult(
                success=False,
                message=f"Cannot modify table '{table}': not present in base snapshot.",
            )
        for col, col_def in changes.get("added_columns", {}).items():
            schema[table][col] = copy.deepcopy(col_def)
        for col in changes.get("removed_columns", []):
            schema[table].pop(col, None)
        for col, col_def in changes.get("modified_columns", {}).items():
            schema[table][col] = copy.deepcopy(col_def)
        applied.append(f"modify:{table}")

    patched = {**base_snapshot, "schema": schema}
    return PatchResult(success=True, patched_schema=patched, applied=applied, skipped=skipped)
