"""Compute a numeric drift score between two snapshots.

The score is a float in [0.0, 1.0] where 0.0 means identical schemas
and 1.0 means completely disjoint schemas.  It is derived from the
Jaccard *distance* (1 - Jaccard similarity) across three dimensions:
  - table presence
  - column presence (qualified as table.column)
  - column type agreement
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class DriftScore:
    table_distance: float
    column_distance: float
    type_distance: float
    overall: float
    details: Dict[str, Any] = field(default_factory=dict)


def _jaccard_distance(set_a: set, set_b: set) -> float:
    """Return 1 - Jaccard similarity; 0.0 when both sets are empty."""
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    intersection = set_a & set_b
    return 1.0 - len(intersection) / len(union)


def _qualified_columns(schema: Dict[str, Any]) -> set:
    """Return a set of 'table.column' strings for all tables in *schema*."""
    result: set = set()
    for table, cols in schema.items():
        for col in cols:
            result.add(f"{table}.{col}")
    return result


def _type_pairs(schema: Dict[str, Any]) -> Dict[str, str]:
    """Return a mapping of 'table.column' -> type string."""
    pairs: Dict[str, str] = {}
    for table, cols in schema.items():
        for col, col_type in cols.items():
            pairs[f"{table}.{col}"] = col_type
    return pairs


def compute_drift_score(
    schema_a: Dict[str, Any],
    schema_b: Dict[str, Any],
    *,
    weight_tables: float = 0.3,
    weight_columns: float = 0.5,
    weight_types: float = 0.2,
) -> DriftScore:
    """Compute a weighted drift score between two schema dicts.

    Each schema is expected to be ``{table_name: {column_name: type_str}}``.
    """
    tables_a = set(schema_a)
    tables_b = set(schema_b)
    table_dist = _jaccard_distance(tables_a, tables_b)

    cols_a = _qualified_columns(schema_a)
    cols_b = _qualified_columns(schema_b)
    col_dist = _jaccard_distance(cols_a, cols_b)

    types_a = _type_pairs(schema_a)
    types_b = _type_pairs(schema_b)
    common_cols = set(types_a) & set(types_b)
    if common_cols:
        mismatched = sum(1 for c in common_cols if types_a[c] != types_b[c])
        type_dist = mismatched / len(common_cols)
    else:
        type_dist = 0.0

    overall = (
        weight_tables * table_dist
        + weight_columns * col_dist
        + weight_types * type_dist
    )

    return DriftScore(
        table_distance=round(table_dist, 4),
        column_distance=round(col_dist, 4),
        type_distance=round(type_dist, 4),
        overall=round(overall, 4),
        details={
            "tables_only_in_a": sorted(tables_a - tables_b),
            "tables_only_in_b": sorted(tables_b - tables_a),
            "common_tables": len(tables_a & tables_b),
        },
    )
