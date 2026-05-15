"""Snapshot health checks — evaluate a snapshot directory for common issues."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from schemasnap.snapshot import load_snapshot, list_snapshots


@dataclass
class HealthIssue:
    level: str  # "warn" | "error"
    code: str
    message: str
    snapshot: str = ""


@dataclass
class HealthReport:
    issues: List[HealthIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    def summary(self) -> str:
        errors = sum(1 for i in self.issues if i.level == "error")
        warns = sum(1 for i in self.issues if i.level == "warn")
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {errors} error(s), {warns} warning(s)"


def _check_empty_schema(snapshots: list, snap_dir: Path) -> List[HealthIssue]:
    issues = []
    for fname in snapshots:
        data = load_snapshot(snap_dir / fname)
        if not data.get("schema"):
            issues.append(HealthIssue(
                level="warn",
                code="EMPTY_SCHEMA",
                message="Snapshot contains no tables.",
                snapshot=fname,
            ))
    return issues


def _check_missing_metadata(snapshots: list, snap_dir: Path) -> List[HealthIssue]:
    issues = []
    required = {"environment", "captured_at", "schema_hash"}
    for fname in snapshots:
        data = load_snapshot(snap_dir / fname)
        missing = required - set(data.keys())
        if missing:
            issues.append(HealthIssue(
                level="error",
                code="MISSING_METADATA",
                message=f"Missing required fields: {', '.join(sorted(missing))}",
                snapshot=fname,
            ))
    return issues


def _check_duplicate_hashes(snapshots: list, snap_dir: Path) -> List[HealthIssue]:
    seen: dict = {}
    issues = []
    for fname in snapshots:
        data = load_snapshot(snap_dir / fname)
        h = data.get("schema_hash", "")
        if h and h in seen:
            issues.append(HealthIssue(
                level="warn",
                code="DUPLICATE_HASH",
                message=f"Same schema hash as '{seen[h]}'.",
                snapshot=fname,
            ))
        else:
            seen[h] = fname
    return issues


def run_health_checks(snap_dir: Path) -> HealthReport:
    report = HealthReport()
    snapshots = list_snapshots(snap_dir)
    if not snapshots:
        return report
    for checker in (_check_missing_metadata, _check_empty_schema, _check_duplicate_hashes):
        report.issues.extend(checker(snapshots, snap_dir))
    return report


def render_health_text(report: HealthReport) -> str:
    lines = [report.summary()]
    for issue in report.issues:
        tag = issue.snapshot or "<global>"
        lines.append(f"  [{issue.level.upper()}] {issue.code} — {tag}: {issue.message}")
    return "\n".join(lines)


def render_health_json(report: HealthReport) -> str:
    return json.dumps({
        "passed": report.passed,
        "summary": report.summary(),
        "issues": [
            {"level": i.level, "code": i.code, "snapshot": i.snapshot, "message": i.message}
            for i in report.issues
        ],
    }, indent=2)
