"""Tests for schemasnap.filter module."""

import pytest

from schemasnap.filter import FilterConfig, apply_filter, filter_columns, filter_tables


SAMPLE_SCHEMA = {
    "users": {"id": "integer", "email": "varchar", "password_hash": "varchar"},
    "orders": {"id": "integer", "user_id": "integer", "total": "numeric"},
    "audit_logs": {"id": "integer", "action": "text", "created_at": "timestamp"},
}


def test_filter_tables_include_pattern():
    cfg = FilterConfig(include_tables=["user*"])
    result = filter_tables(SAMPLE_SCHEMA, cfg)
    assert "users" in result
    assert "orders" not in result
    assert "audit_logs" not in result


def test_filter_tables_exclude_pattern():
    cfg = FilterConfig(exclude_tables=["audit_*"])
    result = filter_tables(SAMPLE_SCHEMA, cfg)
    assert "users" in result
    assert "orders" in result
    assert "audit_logs" not in result


def test_filter_tables_include_and_exclude():
    cfg = FilterConfig(include_tables=["*s"], exclude_tables=["audit_*"])
    result = filter_tables(SAMPLE_SCHEMA, cfg)
    assert "users" in result
    assert "orders" in result
    assert "audit_logs" not in result


def test_filter_tables_no_patterns_returns_all():
    cfg = FilterConfig()
    result = filter_tables(SAMPLE_SCHEMA, cfg)
    assert set(result.keys()) == set(SAMPLE_SCHEMA.keys())


def test_filter_columns_exclude_sensitive():
    columns = {"id": "integer", "email": "varchar", "password_hash": "varchar"}
    cfg = FilterConfig(exclude_columns=["password*"])
    result = filter_columns(columns, cfg)
    assert "id" in result
    assert "email" in result
    assert "password_hash" not in result


def test_filter_columns_include_pattern():
    columns = {"id": "integer", "created_at": "timestamp", "updated_at": "timestamp"}
    cfg = FilterConfig(include_columns=["*_at"])
    result = filter_columns(columns, cfg)
    assert "created_at" in result
    assert "updated_at" in result
    assert "id" not in result


def test_apply_filter_returns_snapshot_unchanged_when_no_config():
    snapshot = {"env": "prod", "schema": SAMPLE_SCHEMA}
    result = apply_filter(snapshot, config=None)
    assert result is snapshot


def test_apply_filter_returns_snapshot_unchanged_when_empty_config():
    snapshot = {"env": "prod", "schema": SAMPLE_SCHEMA}
    result = apply_filter(snapshot, config=FilterConfig())
    assert result is snapshot


def test_apply_filter_filters_schema_section():
    snapshot = {"env": "prod", "schema": SAMPLE_SCHEMA}
    cfg = FilterConfig(exclude_tables=["audit_*"])
    result = apply_filter(snapshot, config=cfg)
    assert "audit_logs" not in result["schema"]
    assert "users" in result["schema"]
    assert result["env"] == "prod"  # non-schema keys preserved


def test_apply_filter_does_not_mutate_original():
    schema = dict(SAMPLE_SCHEMA)
    snapshot = {"env": "staging", "schema": schema}
    cfg = FilterConfig(exclude_tables=["orders"])
    apply_filter(snapshot, config=cfg)
    assert "orders" in snapshot["schema"]  # original untouched
