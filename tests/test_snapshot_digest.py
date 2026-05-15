"""Tests for schemasnap.snapshot_digest."""
import json
from pathlib import Path

import pytest

from schemasnap.snapshot_digest import (
    DigestEntry,
    _short_hash,
    _top_tables,
    compute_digest,
    render_digest_json,
    render_digest_text,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(path: Path, env: str, schema: dict) -> Path:
    import json
    snap = {"environment": env, "schema": schema}
    path.write_text(json.dumps(snap))
    return path


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


_SCHEMA = {
    "users": {"id": "int", "name": "text", "email": "text"},
    "orders": {"id": "int", "user_id": "int"},
    "products": {"id": "int", "sku": "text", "price": "numeric", "stock": "int"},
}


# ---------------------------------------------------------------------------
# _short_hash
# ---------------------------------------------------------------------------

def test_short_hash_is_eight_chars():
    h = _short_hash(_SCHEMA)
    assert len(h) == 8


def test_short_hash_deterministic():
    assert _short_hash(_SCHEMA) == _short_hash(_SCHEMA)


def test_short_hash_differs_on_change():
    modified = {**_SCHEMA, "new_table": {"id": "int"}}
    assert _short_hash(_SCHEMA) != _short_hash(modified)


# ---------------------------------------------------------------------------
# _top_tables
# ---------------------------------------------------------------------------

def test_top_tables_returns_sorted_by_column_count():
    top = _top_tables(_SCHEMA, n=2)
    # products has 4 cols, users has 3, orders has 2
    assert top[0] == "products"
    assert top[1] == "users"


def test_top_tables_respects_n():
    top = _top_tables(_SCHEMA, n=1)
    assert len(top) == 1


def test_top_tables_empty_schema():
    assert _top_tables({}) == []


# ---------------------------------------------------------------------------
# compute_digest
# ---------------------------------------------------------------------------

def test_compute_digest_returns_digest_entry(snap_dir: Path):
    f = _write_snapshot(snap_dir / "snap.json", "prod", _SCHEMA)
    entry = compute_digest(f)
    assert isinstance(entry, DigestEntry)


def test_compute_digest_correct_counts(snap_dir: Path):
    f = _write_snapshot(snap_dir / "snap.json", "staging", _SCHEMA)
    entry = compute_digest(f)
    assert entry.table_count == 3
    assert entry.column_count == 9  # 3 + 2 + 4
    assert entry.env == "staging"


def test_compute_digest_empty_schema(snap_dir: Path):
    f = _write_snapshot(snap_dir / "empty.json", "dev", {})
    entry = compute_digest(f)
    assert entry.table_count == 0
    assert entry.column_count == 0


# ---------------------------------------------------------------------------
# render_digest_text
# ---------------------------------------------------------------------------

def test_render_digest_text_contains_env(snap_dir: Path):
    f = _write_snapshot(snap_dir / "snap.json", "prod", _SCHEMA)
    entry = compute_digest(f)
    text = render_digest_text(entry)
    assert "prod" in text


def test_render_digest_text_contains_counts(snap_dir: Path):
    f = _write_snapshot(snap_dir / "snap.json", "prod", _SCHEMA)
    entry = compute_digest(f)
    text = render_digest_text(entry)
    assert "3" in text  # table count
    assert "9" in text  # column count


# ---------------------------------------------------------------------------
# render_digest_json
# ---------------------------------------------------------------------------

def test_render_digest_json_is_valid_json(snap_dir: Path):
    f = _write_snapshot(snap_dir / "snap.json", "prod", _SCHEMA)
    entry = compute_digest(f)
    parsed = json.loads(render_digest_json(entry))
    assert parsed["env"] == "prod"
    assert parsed["table_count"] == 3
    assert isinstance(parsed["top_tables"], list)
