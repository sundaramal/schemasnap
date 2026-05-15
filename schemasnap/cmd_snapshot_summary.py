"""CLI sub-command: snapshot-summary — show a concise overview of a snapshot file."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schemasnap.snapshot_summary import (
    compute_summary,
    render_summary_json,
    render_summary_text,
)


def add_snapshot_summary_subparsers(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "snapshot-summary",
        help="Print a concise overview of a snapshot file.",
    )
    p.add_argument("snapshot", help="Path to the snapshot JSON file.")
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_snapshot_summary)


def cmd_snapshot_summary(args: argparse.Namespace) -> int:
    path = Path(args.snapshot)
    if not path.exists():
        print(f"Error: snapshot file not found: {path}", file=sys.stderr)
        return 1

    try:
        summary = compute_summary(path)
    except Exception as exc:  # noqa: BLE001
        print(f"Error reading snapshot: {exc}", file=sys.stderr)
        return 1

    if args.fmt == "json":
        print(render_summary_json(summary))
    else:
        print(render_summary_text(summary))

    return 0
