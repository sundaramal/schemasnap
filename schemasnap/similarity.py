"""Compute schema similarity scores between two snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class SimilarityReport:
    env_a: str
    env_b: str
    overall_score: float  # 0.0 (completely different) .. 1.0 (identical)
    table_scores: Dict[str, float] = field(default_factory=dict)
    only_in_a: Set[str] = field(default_factory=set)
    only_in_b: Set[str] = field(default_factory=set)

    def summary(self) -> str:
        lines = [
            f"Similarity: {self.env_a} vs {self.env_b}",
            f"  Overall score : {self.overall_score:.2%}",
            f"  Only in {self.env_a}: {sorted(self.only_in_a) or 'none'}",
            f"  Only in {self.env_b}: {sorted(self.only_in_b) or 'none'}",
        ]
        for table, score in sorted(self.table_scores.items()):
            lines.append(f"  {table}: {score:.2%}")
        return "\n".join(lines)


def _column_set(table_schema: dict) -> Set[str]:
    """Return a set of 'name:type' strings for quick comparison."""
    columns = table_schema.get("columns", {})
    if isinstance(columns, dict):
        return {f"{k}:{v}" for k, v in columns.items()}
    if isinstance(columns, list):
        return {f"{c.get('name', '')}:{c.get('type', '')}" for c in columns}
    return set()


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union)


def compute_similarity(snapshot_a: dict, snapshot_b: dict,
                       env_a: str = "env_a", env_b: str = "env_b") -> SimilarityReport:
    """Compute a SimilarityReport between two snapshot dicts."""
    schema_a: dict = snapshot_a.get("schema", {})
    schema_b: dict = snapshot_b.get("schema", {})

    tables_a: Set[str] = set(schema_a.keys())
    tables_b: Set[str] = set(schema_b.keys())
    all_tables = tables_a | tables_b

    only_in_a = tables_a - tables_b
    only_in_b = tables_b - tables_a
    common = tables_a & tables_b

    table_scores: Dict[str, float] = {}
    for table in common:
        cols_a = _column_set(schema_a[table])
        cols_b = _column_set(schema_b[table])
        table_scores[table] = _jaccard(cols_a, cols_b)

    if not all_tables:
        overall = 1.0
    else:
        present_score = len(common) / len(all_tables)
        column_score = (sum(table_scores.values()) / len(common)) if common else 0.0
        overall = (present_score + column_score) / 2.0

    return SimilarityReport(
        env_a=env_a,
        env_b=env_b,
        overall_score=overall,
        table_scores=table_scores,
        only_in_a=only_in_a,
        only_in_b=only_in_b,
    )
