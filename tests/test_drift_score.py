"""Tests for schemasnap.drift_score."""
import pytest
from schemasnap.drift_score import (
    DriftScore,
    _jaccard_distance,
    _qualified_columns,
    _type_pairs,
    compute_drift_score,
)


# ---------------------------------------------------------------------------
# _jaccard_distance
# ---------------------------------------------------------------------------

def test_jaccard_distance_identical_sets():
    assert _jaccard_distance({1, 2, 3}, {1, 2, 3}) == 0.0


def test_jaccard_distance_disjoint_sets():
    assert _jaccard_distance({1, 2}, {3, 4}) == 1.0


def test_jaccard_distance_partial_overlap():
    dist = _jaccard_distance({1, 2, 3}, {2, 3, 4})
    # intersection=2, union=4 -> similarity=0.5 -> distance=0.5
    assert abs(dist - 0.5) < 1e-9


def test_jaccard_distance_both_empty():
    assert _jaccard_distance(set(), set()) == 0.0


# ---------------------------------------------------------------------------
# _qualified_columns
# ---------------------------------------------------------------------------

def test_qualified_columns_basic():
    schema = {"users": {"id": "int", "name": "text"}}
    result = _qualified_columns(schema)
    assert result == {"users.id", "users.name"}


def test_qualified_columns_multiple_tables():
    schema = {
        "orders": {"id": "int"},
        "items": {"sku": "text"},
    }
    result = _qualified_columns(schema)
    assert "orders.id" in result
    assert "items.sku" in result


# ---------------------------------------------------------------------------
# compute_drift_score – identical schemas
# ---------------------------------------------------------------------------

def test_drift_score_identical_schemas_is_zero():
    schema = {"users": {"id": "int", "email": "text"}}
    score = compute_drift_score(schema, schema)
    assert score.overall == 0.0
    assert score.table_distance == 0.0
    assert score.column_distance == 0.0
    assert score.type_distance == 0.0


def test_drift_score_both_empty_is_zero():
    score = compute_drift_score({}, {})
    assert score.overall == 0.0


# ---------------------------------------------------------------------------
# compute_drift_score – added / removed tables
# ---------------------------------------------------------------------------

def test_drift_score_added_table_increases_score():
    a = {"users": {"id": "int"}}
    b = {"users": {"id": "int"}, "orders": {"id": "int"}}
    score = compute_drift_score(a, b)
    assert score.overall > 0.0
    assert "orders" in score.details["tables_only_in_b"]


def test_drift_score_removed_table_increases_score():
    a = {"users": {"id": "int"}, "logs": {"ts": "timestamp"}}
    b = {"users": {"id": "int"}}
    score = compute_drift_score(a, b)
    assert score.overall > 0.0
    assert "logs" in score.details["tables_only_in_a"]


# ---------------------------------------------------------------------------
# compute_drift_score – type mismatch
# ---------------------------------------------------------------------------

def test_drift_score_type_mismatch_increases_type_distance():
    a = {"users": {"id": "int"}}
    b = {"users": {"id": "bigint"}}
    score = compute_drift_score(a, b)
    assert score.type_distance == 1.0
    assert score.overall > 0.0


def test_drift_score_partial_type_mismatch():
    a = {"t": {"a": "int", "b": "text"}}
    b = {"t": {"a": "bigint", "b": "text"}}  # only 'a' changed
    score = compute_drift_score(a, b)
    assert score.type_distance == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# DriftScore is a dataclass with details
# ---------------------------------------------------------------------------

def test_drift_score_details_common_tables():
    schema = {"users": {"id": "int"}}
    score = compute_drift_score(schema, schema)
    assert score.details["common_tables"] == 1
    assert score.details["tables_only_in_a"] == []
    assert score.details["tables_only_in_b"] == []
