"""CLI sub-command: schemasnap metrics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schemasnap.metrics import collect_metrics, render_metrics_json, render_metrics_text


def add_metrics_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "metrics",
        help="Show snapshot metrics for an environment",
    )
    p.add_argument("env", help="Environment name (e.g. production)")
    p.add_argument(
        "--snapshot-dir",
        default="snapshots",
        help="Directory where snapshots are stored (default: snapshots)",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    p.set_defaults(func=cmd_metrics)


def cmd_metrics(args: argparse.Namespace) -> int:
    snapshot_dir = Path(args.snapshot_dir)
    if not snapshot_dir.is_dir():
        print(f"error: snapshot directory not found: {snapshot_dir}", file=sys.stderr)
        return 1

    metrics = collect_metrics(snapshot_dir, env=args.env)

    if args.format == "json":
        print(render_metrics_json(metrics))
    else:
        print(render_metrics_text(metrics))

    return 0
