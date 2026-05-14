"""CLI sub-command: compare-report

Captures two snapshots (or loads existing ones) and writes a formatted
diff report to stdout or a file.  Thin glue between compare.py, report.py
and the argument parser.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schemasnap.compare import compare_and_report
from schemasnap.report import write_report


def add_compare_report_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "compare-report",
        help="Diff two snapshots and write a formatted report.",
    )
    p.add_argument("snapshot_a", help="Path to the baseline snapshot file.")
    p.add_argument("snapshot_b", help="Path to the target snapshot file.")
    p.add_argument(
        "--format",
        dest="fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Write report to this file instead of stdout.",
    )
    p.add_argument(
        "--env-a",
        default="env_a",
        help="Label for snapshot A environment (default: env_a).",
    )
    p.add_argument(
        "--env-b",
        default="env_b",
        help="Label for snapshot B environment (default: env_b).",
    )
    p.set_defaults(func=cmd_compare_report)


def cmd_compare_report(args: argparse.Namespace) -> int:
    path_a = Path(args.snapshot_a)
    path_b = Path(args.snapshot_b)

    if not path_a.exists():
        print(f"[error] snapshot_a not found: {path_a}", file=sys.stderr)
        return 1
    if not path_b.exists():
        print(f"[error] snapshot_b not found: {path_b}", file=sys.stderr)
        return 1

    result = compare_and_report(
        snapshot_dir=str(path_a.parent),
        env_a=args.env_a,
        env_b=args.env_b,
        snapshot_file_a=str(path_a),
        snapshot_file_b=str(path_b),
        fmt=args.fmt,
    )

    report_text = result.report

    if args.output:
        write_report(report_text, args.output)
        print(f"Report written to {args.output}")
    else:
        print(report_text)

    return 1 if result.has_changes else 0
