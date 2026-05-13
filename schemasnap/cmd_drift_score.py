"""CLI sub-command: drift-score — compute and display drift scores between two snapshots."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.drift_score import compute_drift_score
from schemasnap.snapshot import load_snapshot


def add_drift_score_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "drift-score",
        help="Compute a numeric drift score between two snapshot files.",
    )
    p.add_argument("primary", help="Path to the primary (baseline) snapshot file.")
    p.add_argument("secondary", help="Path to the secondary (current) snapshot file.")
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="fmt",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Exit with code 1 if overall score exceeds this threshold (0.0–1.0).",
    )
    p.set_defaults(func=cmd_drift_score)


def cmd_drift_score(args: argparse.Namespace) -> int:
    primary_path = Path(args.primary)
    secondary_path = Path(args.secondary)

    if not primary_path.exists():
        print(f"[error] primary snapshot not found: {primary_path}", file=sys.stderr)
        return 1
    if not secondary_path.exists():
        print(f"[error] secondary snapshot not found: {secondary_path}", file=sys.stderr)
        return 1

    primary = load_snapshot(primary_path)
    secondary = load_snapshot(secondary_path)

    score = compute_drift_score(
        primary.get("schema", {}),
        secondary.get("schema", {}),
    )

    if args.fmt == "json":
        payload = {
            "primary": str(primary_path),
            "secondary": str(secondary_path),
            "overall": score.overall,
            "table_score": score.table_score,
            "column_score": score.column_score,
            "type_score": score.type_score,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Drift score: {score.overall:.4f}")
        print(f"  table  distance : {score.table_score:.4f}")
        print(f"  column distance : {score.column_score:.4f}")
        print(f"  type   distance : {score.type_score:.4f}")

    if args.threshold is not None and score.overall > args.threshold:
        print(
            f"[warn] drift score {score.overall:.4f} exceeds threshold {args.threshold:.4f}",
            file=sys.stderr,
        )
        return 1

    return 0
