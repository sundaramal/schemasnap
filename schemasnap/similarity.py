"""Structural similarity scoring between two schema snapshots.

Uses Jaccard similarity on column sets to produce per-table and overall scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SimilarityReport:
    """Holds per-table and aggregate similarity scores."""

    overall_score: float
    table_scores: Dict[str, float] = field(default_factory=dict)


def summary(report: SimilarityReport) -> str:
    """Return a one-line human-readable summary."""
    n = len(report.table_scores)
    if n == 0:
        return "No tables to compare."
    perfect = sum(1 for s in report.table_scores.values() if s == 1.0)
    return (
        f"{n} table(s) compared; {perfect} identical; "
        f"overall score {report.overall_score:.4f}."
    )


def _column_set(table_schema: object) -> frozenset:
    """Return a frozenset of 'column:type' strings for a table definition."""
    if isinstance(table_schema, dict):
        return frozenset(f"{col}:{typ}" for col, typ in table_schema.items())
    return frozenset()


def _jaccard(a: frozenset, b: frozenset) -> float:
    """Jaccard similarity between two sets; returns 1.0 when both are empty."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def compute_similarity(
    snapshot_a: dict,
    snapshot_b: dict,
) -> SimilarityReport:
    """Compute structural similarity between two loaded snapshot dicts.

    Parameters
    ----------
    snapshot_a, snapshot_b:
        Dicts as returned by ``load_snapshot``, expected to contain a
        ``"schema"`` key mapping table names to column-type dicts.

    Returns
    -------
    SimilarityReport
        Per-table Jaccard scores and a weighted overall score.
    """
    schema_a: dict = snapshot_a.get("schema", {})
    schema_b: dict = snapshot_b.get("schema", {})

    all_tables = set(schema_a) | set(schema_b)

    if not all_tables:
        return SimilarityReport(overall_score=1.0, table_scores={})

    table_scores: Dict[str, float] = {}
    for table in all_tables:
        cols_a = _column_set(schema_a.get(table, {}))
        cols_b = _column_set(schema_b.get(table, {}))
        table_scores[table] = _jaccard(cols_a, cols_b)

    overall = sum(table_scores.values()) / len(table_scores)
    return SimilarityReport(overall_score=overall, table_scores=table_scores)
