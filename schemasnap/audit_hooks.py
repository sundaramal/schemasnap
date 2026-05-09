"""Audit hooks wired into capture, compare, baseline, tag, and rollback actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import append_audit
from .compare import CompareResult
from .rollback import RollbackResult


def audit_capture(snap_dir: Path, env: str, snapshot_file: str) -> None:
    """Record a snapshot capture event in the audit log."""
    append_audit(
        snap_dir,
        action="capture",
        env=env,
        detail={"snapshot_file": snapshot_file},
    )


def audit_compare(snap_dir: Path, result: CompareResult) -> None:
    """Record a compare event in the audit log."""
    append_audit(
        snap_dir,
        action="compare",
        env=f"{result.env_a}..{result.env_b}",
        detail={
            "has_changes": result.diff.has_changes(),
            "added": list(result.diff.added_tables),
            "removed": list(result.diff.removed_tables),
            "modified": list(result.diff.modified_tables.keys()),
        },
    )


def audit_baseline_set(snap_dir: Path, env: str, snapshot_file: str) -> None:
    """Record a baseline-set event in the audit log."""
    append_audit(
        snap_dir,
        action="baseline_set",
        env=env,
        detail={"snapshot_file": snapshot_file},
    )


def audit_tag_set(snap_dir: Path, env: str, tag_name: str, snapshot_file: str) -> None:
    """Record a tag-set event in the audit log."""
    append_audit(
        snap_dir,
        action="tag_set",
        env=env,
        detail={"tag": tag_name, "snapshot_file": snapshot_file},
    )


def audit_rollback(snap_dir: Path, env: str, result: RollbackResult) -> None:
    """Record a rollback event in the audit log."""
    append_audit(
        snap_dir,
        action="rollback",
        env=env,
        detail={
            "success": result.success,
            "source_file": result.source_file,
            "dest_file": result.dest_file,
            "message": result.message,
        },
    )
