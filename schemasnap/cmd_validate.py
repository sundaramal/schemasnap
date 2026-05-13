"""CLI sub-command: schemasnap validate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from schemasnap.snapshot import latest_snapshot
from schemasnap.validate import (
    ValidationReport,
    load_rules,
    validate_snapshot_file,
)


def add_validate_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "validate",
        help="Validate a snapshot against a rules file",
    )
    p.add_argument("--rules", required=True, help="Path to JSON rules file")
    p.add_argument("--snapshot", default=None, help="Snapshot file to validate (default: latest)")
    p.add_argument("--env", default="production", help="Environment name (used to find latest snapshot)")
    p.add_argument("--snapshot-dir", default="snapshots", help="Directory containing snapshots")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.set_defaults(func=cmd_validate)


def cmd_validate(args: argparse.Namespace) -> int:
    # Resolve snapshot file
    snap_file = args.snapshot
    if snap_file is None:
        snap_file = latest_snapshot(args.snapshot_dir, args.env)
        if snap_file is None:
            print(f"No snapshots found for env '{args.env}' in {args.snapshot_dir}",
                  file=sys.stderr)
            return 1

    if not Path(snap_file).exists():
        print(f"Snapshot file not found: {snap_file}", file=sys.stderr)
        return 1

    rules_path = args.rules
    if not Path(rules_path).exists():
        print(f"Rules file not found: {rules_path}", file=sys.stderr)
        return 1

    rules = load_rules(rules_path)
    report: ValidationReport = validate_snapshot_file(snap_file, rules)

    if args.format == "json":
        out = {
            "snapshot_file": report.snapshot_file,
            "passed": report.passed,
            "violations": [
                {"table": v.table, "rule_index": v.rule_index, "message": v.message}
                for v in report.violations
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print(report.summary())

    return 0 if report.passed else 2
