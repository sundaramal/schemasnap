"""Property-style tests ensuring render functions never raise on edge-case schemas."""
from __future__ import annotations

from schemasnap.export import render_csv, render_markdown, render_html, snapshot_to_rows


EMPTY_SCHEMA: dict = {}
SINGLE_TABLE = {"accounts": {"id": "serial"}}
SPECIAL_CHARS = {"my-table": {"col<1>": "varchar(255) default '<none>'"}}


def test_render_csv_empty_schema():
    out = render_csv(EMPTY_SCHEMA)
    assert "table,column,definition" in out
    # Only header, no data rows
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) == 1


def test_render_markdown_empty_schema():
    out = render_markdown(EMPTY_SCHEMA, title="Empty")
    assert "# Empty" in out


def test_render_html_empty_schema():
    out = render_html(EMPTY_SCHEMA, title="Empty")
    assert "<html>" in out
    assert "Empty" in out


def test_snapshot_to_rows_empty():
    assert snapshot_to_rows(EMPTY_SCHEMA) == []


def test_snapshot_to_rows_single_table():
    rows = snapshot_to_rows(SINGLE_TABLE)
    assert len(rows) == 1
    assert rows[0] == {"table": "accounts", "column": "id", "definition": "serial"}


def test_render_csv_special_chars_does_not_raise():
    out = render_csv(SPECIAL_CHARS)
    assert "my-table" in out


def test_render_markdown_special_chars_does_not_raise():
    out = render_markdown(SPECIAL_CHARS)
    assert "my-table" in out


def test_render_html_special_chars_does_not_raise():
    out = render_html(SPECIAL_CHARS)
    assert "my-table" in out


def test_render_csv_row_count_matches_columns():
    schema = {
        "t1": {"a": "int", "b": "text"},
        "t2": {"x": "float"},
    }
    rows = snapshot_to_rows(schema)
    assert len(rows) == 3
    out = render_csv(schema)
    data_lines = [l for l in out.splitlines() if l.strip()][1:]  # skip header
    assert len(data_lines) == 3


def test_render_markdown_table_order_is_sorted():
    schema = {"zebra": {"z": "int"}, "alpha": {"a": "int"}}
    out = render_markdown(schema)
    pos_alpha = out.index("## alpha")
    pos_zebra = out.index("## zebra")
    assert pos_alpha < pos_zebra


def test_render_html_contains_all_tables():
    schema = {"t1": {"c": "int"}, "t2": {"d": "text"}, "t3": {"e": "bool"}}
    out = render_html(schema)
    for t in ["t1", "t2", "t3"]:
        assert f"<h2>{t}</h2>" in out
