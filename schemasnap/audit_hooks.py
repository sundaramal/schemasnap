"""Convenience hooks that integrate audit logging into existing operations."""

from __future__ import annotations

from typing import Optional

from schemasnap.audit import AuditEntry, append_audit
from schemasnap.compare import CompareResult


def audit_capture(
    snapshot_dir: str,
    environment: str,
    snapshot_file: str,
    schema_hash: str,
) -> None:
    """Record a snapshot capture event in the audit log."""
    entry = AuditEntry.now(
        event="capture",
        environment=environment,
        details={"file": snapshot_file, "hash": schema_hash},
    )
    append_audit(snapshot_dir, entry)


def audit_compare(
    snapshot_dir: str,
    result: CompareResult,
) -> None:
    """Record a compare/diff event in the audit log."""
    diff = result.diff
    details = {
        "env_a": result.env_a,
        "env_b": result.env_b,
        "has_changes": diff.has_changes() if diff else False,
        "added_tables": len(diff.added_tables) if diff else 0,
        "removed_tables": len(diff.removed_tables) if diff else 0,
        "modified_tables": len(diff.modified_tables) if diff else 0,
    }
    entry = AuditEntry.now(
        event="compare",
        environment=f"{result.env_a}:{result.env_b}",
        details=details,
    )
    append_audit(snapshot_dir, entry)


def audit_baseline_set(
    snapshot_dir: str,
    environment: str,
    snapshot_file: str,
    schema_hash: str,
) -> None:
    """Record a baseline-set event in the audit log."""
    entry = AuditEntry.now(
        event="baseline_set",
        environment=environment,
        details={"file": snapshot_file, "hash": schema_hash},
    )
    append_audit(snapshot_dir, entry)


def audit_tag_set(
    snapshot_dir: str,
    environment: str,
    tag: str,
    snapshot_file: str,
) -> None:
    """Record a tag-set event in the audit log."""
    entry = AuditEntry.now(
        event="tag_set",
        environment=environment,
        details={"tag": tag, "file": snapshot_file},
    )
    append_audit(snapshot_dir, entry)
