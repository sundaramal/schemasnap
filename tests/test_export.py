"""Tests for schemasnap.export and schemasnap.cmd_export."""
from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from schemasnap.export import (
    snapshot_to_rows,
    render_csv,
    render_markdown,
    render_html,
    export_snapshot,
)


SAMPLE_SCHEMA = {
    "users": {"id": "integer primary key", "email": "text not null"},
    "orders": {"id": "integer primary key", "total": "numeric"},
}


@pytest.fixture()
def snapshot_file(tmp_path: Path) -> Path:
    data = {"env": "prod", "schema": SAMPLE_SCHEMA, "hash": "abc123"}
    p = tmp_path / "snap_prod_abc123.json"
    p.write_text(json.dumps(data))
    return p


def test_snapshot_to_rows_flattens_correctly():
    rows = snapshot_to_rows(SAMPLE_SCHEMA)
    assert any(r["table"] == "users" and r["column"] == "email" for r in rows)
    assert any(r["table"] == "orders" and r["column"] == "total" for r in rows)


def test_render_csv_has_header():
    csv_text = render_csv(SAMPLE_SCHEMA)
    assert csv_text.startswith("table,column,definition")


def test_render_csv_contains_all_columns():
    csv_text = render_csv(SAMPLE_SCHEMA)
    assert "users" in csv_text
    assert "email" in csv_text
    assert "orders" in csv_text


def test_render_markdown_contains_table_headings():
    md = render_markdown(SAMPLE_SCHEMA, title="Test")
    assert "## users" in md
    assert "## orders" in md


def test_render_markdown_contains_column_names():
    md = render_markdown(SAMPLE_SCHEMA)
    assert "`id`" in md
    assert "`email`" in md


def test_render_html_is_valid_structure():
    html = render_html(SAMPLE_SCHEMA, title="My Schema")
    assert "<html>" in html
    assert "<h2>users</h2>" in html
    assert "<code>email</code>" in html
    assert "</html>" in html


def test_export_snapshot_csv(snapshot_file: Path):
    content = export_snapshot(snapshot_file, fmt="csv")
    assert "table,column,definition" in content
    assert "users" in content


def test_export_snapshot_markdown(snapshot_file: Path):
    content = export_snapshot(snapshot_file, fmt="markdown")
    assert "## users" in content


def test_export_snapshot_html(snapshot_file: Path):
    content = export_snapshot(snapshot_file, fmt="html")
    assert "<html>" in content


def test_export_snapshot_writes_file(snapshot_file: Path, tmp_path: Path):
    out = tmp_path / "out.md"
    export_snapshot(snapshot_file, fmt="markdown", output=out)
    assert out.exists()
    assert "## users" in out.read_text()


def test_export_snapshot_invalid_format(snapshot_file: Path):
    with pytest.raises(ValueError, match="Unsupported format"):
        export_snapshot(snapshot_file, fmt="xml")


# ---------- cmd_export tests ----------

def _make_args(**kwargs):
    defaults = {
        "env": "prod",
        "snapshot_dir": "snapshots",
        "file": None,
        "fmt": "markdown",
        "output": None,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def test_cmd_export_no_snapshot_returns_1(tmp_path: Path):
    from schemasnap.cmd_export import cmd_export
    args = _make_args(env="ghost", snapshot_dir=str(tmp_path))
    assert cmd_export(args) == 1


def test_cmd_export_uses_latest(snapshot_file: Path, tmp_path: Path, capsys):
    from schemasnap.cmd_export import cmd_export
    # snapshot_file is already in tmp_path
    args = _make_args(env="prod", snapshot_dir=str(snapshot_file.parent))
    rc = cmd_export(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "users" in captured.out


def test_cmd_export_explicit_file(snapshot_file: Path, capsys):
    from schemasnap.cmd_export import cmd_export
    args = _make_args(env="prod", snapshot_dir=str(snapshot_file.parent), file=str(snapshot_file))
    rc = cmd_export(args)
    assert rc == 0
