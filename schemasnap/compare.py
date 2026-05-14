"""compare.py — high-level environment comparison.

Compares two schema snapshots (by environment name or explicit file path)
and returns a CompareResult that bundles the SchemaDiff together with a
pre-rendered report string.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from schemasnap.diff import diff_snapshots, has_changes, SchemaDiff
from schemasnap.report import render_text_report, render_json_report
from schemasnap.snapshot import load_snapshot, latest_snapshot


@dataclass
class CompareResult:
    env_a: str
    env_b: str
    diff: SchemaDiff
    report: str
    has_changes: bool = field(init=False)

    def __post_init__(self) -> None:
        self.has_changes = has_changes(self.diff)


def compare_environments(
    snapshot_dir: str,
    env_a: str,
    env_b: str,
    snapshot_file_a: Optional[str] = None,
    snapshot_file_b: Optional[str] = None,
) -> CompareResult:
    """Load two snapshots and return a CompareResult.

    If *snapshot_file_a* / *snapshot_file_b* are provided they are used
    directly; otherwise the latest snapshot for each environment is used.
    """
    file_a = snapshot_file_a or latest_snapshot(snapshot_dir, env_a)
    file_b = snapshot_file_b or latest_snapshot(snapshot_dir, env_b)

    schema_a = load_snapshot(file_a)["schema"]
    schema_b = load_snapshot(file_b)["schema"]

    diff = diff_snapshots(schema_a, schema_b)
    return CompareResult(
        env_a=env_a,
        env_b=env_b,
        diff=diff,
        report=render_text_report(env_a, env_b, diff),
    )


def compare_and_report(
    snapshot_dir: str,
    env_a: str,
    env_b: str,
    fmt: str = "text",
    snapshot_file_a: Optional[str] = None,
    snapshot_file_b: Optional[str] = None,
) -> CompareResult:
    """Like compare_environments but renders the report in the requested format."""
    file_a = snapshot_file_a or latest_snapshot(snapshot_dir, env_a)
    file_b = snapshot_file_b or latest_snapshot(snapshot_dir, env_b)

    schema_a = load_snapshot(file_a)["schema"]
    schema_b = load_snapshot(file_b)["schema"]

    diff = diff_snapshots(schema_a, schema_b)

    if fmt == "json":
        report = render_json_report(env_a, env_b, diff)
    else:
        report = render_text_report(env_a, env_b, diff)

    return CompareResult(
        env_a=env_a,
        env_b=env_b,
        diff=diff,
        report=report,
    )
