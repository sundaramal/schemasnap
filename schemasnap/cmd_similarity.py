"""CLI subcommand: schemasnap similarity <env_a> <env_b>."""
from __future__ import annotations

import argparse
import json
import sys

from schemasnap.similarity import compute_similarity
from schemasnap.snapshot import latest_snapshot, load_snapshot


def add_similarity_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "similarity",
        help="Compute a similarity score between two environment snapshots.",
    )
    p.add_argument("env_a", help="First environment name.")
    p.add_argument("env_b", help="Second environment name.")
    p.add_argument(
        "--snapshot-dir",
        default="snapshots",
        help="Directory containing snapshot files (default: snapshots).",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="SCORE",
        help="Exit with code 1 if overall similarity is below this value (0.0-1.0).",
    )
    p.set_defaults(func=cmd_similarity)


def cmd_similarity(args: argparse.Namespace) -> int:
    snap_a = latest_snapshot(args.snapshot_dir, args.env_a)
    snap_b = latest_snapshot(args.snapshot_dir, args.env_b)

    if snap_a is None:
        print(f"[error] No snapshot found for environment '{args.env_a}'.", file=sys.stderr)
        return 1
    if snap_b is None:
        print(f"[error] No snapshot found for environment '{args.env_b}'.", file=sys.stderr)
        return 1

    data_a = load_snapshot(snap_a)
    data_b = load_snapshot(snap_b)

    report = compute_similarity(data_a, data_b, env_a=args.env_a, env_b=args.env_b)

    if args.format == "json":
        out = {
            "env_a": report.env_a,
            "env_b": report.env_b,
            "overall_score": report.overall_score,
            "table_scores": report.table_scores,
            "only_in_env_a": sorted(report.only_in_a),
            "only_in_env_b": sorted(report.only_in_b),
        }
        print(json.dumps(out, indent=2))
    else:
        print(report.summary())

    if args.threshold is not None and report.overall_score < args.threshold:
        print(
            f"[warn] Similarity {report.overall_score:.2%} is below threshold {args.threshold:.2%}.",
            file=sys.stderr,
        )
        return 1

    return 0
