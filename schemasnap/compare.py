"""Compare snapshots across environments and produce structured results."""

from dataclasses import dataclass
from typing import Optional

from schemasnap.snapshot import load_snapshot, latest_snapshot
from schemasnap.diff import diff_snapshots, SchemaDiff, has_changes
from schemasnap.report import render_text_report, render_json_report, write_report


@dataclass
class CompareResult:
    source_env: str
    target_env: str
    source_snapshot_path: str
    target_snapshot_path: str
    diff: SchemaDiff
    has_changes: bool


def compare_environments(
    source_env: str,
    target_env: str,
    snapshot_dir: str = "snapshots",
    source_snapshot: Optional[str] = None,
    target_snapshot: Optional[str] = None,
) -> CompareResult:
    """Compare schemas between two environments using their latest (or specified) snapshots."""
    source_path = source_snapshot or latest_snapshot(snapshot_dir, source_env)
    target_path = target_snapshot or latest_snapshot(snapshot_dir, target_env)

    if source_path is None:
        raise FileNotFoundError(f"No snapshot found for environment: {source_env}")
    if target_path is None:
        raise FileNotFoundError(f"No snapshot found for environment: {target_env}")

    source_schema = load_snapshot(source_path)
    target_schema = load_snapshot(target_path)

    diff = diff_snapshots(source_schema, target_schema)

    return CompareResult(
        source_env=source_env,
        target_env=target_env,
        source_snapshot_path=source_path,
        target_snapshot_path=target_path,
        diff=diff,
        has_changes=has_changes(diff),
    )


def compare_and_report(
    source_env: str,
    target_env: str,
    snapshot_dir: str = "snapshots",
    output_format: str = "text",
    output_path: Optional[str] = None,
) -> CompareResult:
    """Compare environments and optionally write a report to disk."""
    result = compare_environments(source_env, target_env, snapshot_dir)

    if output_format == "json":
        report_content = render_json_report(result.diff, source_env, target_env)
    else:
        report_content = render_text_report(result.diff, source_env, target_env)

    if output_path:
        write_report(report_content, output_path)

    return result
