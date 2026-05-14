"""CLI subcommand: similarity — compare structural similarity between two snapshots."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.similarity import compute_similarity, summary
from schemasnap.snapshot import load_snapshot


def add_similarity_subparsers(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = sub.add_parser(
        "similarity",
        help="Compute structural similarity score between two snapshot files.",
    )
    p.add_argument("snapshot_a", help="Path to the first snapshot file.")
    p.add_argument("snapshot_b", help="Path to the second snapshot file.")
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
        metavar="SCORE",
        help="Exit with code 1 if overall similarity is below this value (0.0-1.0).",
    )
    p.set_defaults(func=cmd_similarity)


def cmd_similarity(args: argparse.Namespace) -> int:
    path_a = Path(args.snapshot_a)
    path_b = Path(args.snapshot_b)

    for p in (path_a, path_b):
        if not p.exists():
            print(f"error: snapshot not found: {p}", file=sys.stderr)
            return 1

    snap_a = load_snapshot(path_a)
    snap_b = load_snapshot(path_b)

    report = compute_similarity(snap_a, snap_b)

    if args.fmt == "json":
        data = {
            "env_a": snap_a.get("environment", str(path_a)),
            "env_b": snap_b.get("environment", str(path_b)),
            "overall_score": report.overall_score,
            "table_scores": report.table_scores,
            "summary": summary(report),
        }
        print(json.dumps(data, indent=2))
    else:
        env_a = snap_a.get("environment", str(path_a))
        env_b = snap_b.get("environment", str(path_b))
        print(f"Similarity: {env_a}  vs  {env_b}")
        print(f"  Overall score : {report.overall_score:.4f}")
        print(f"  {summary(report)}")
        if report.table_scores:
            print("  Per-table scores:")
            for tbl, score in sorted(report.table_scores.items()):
                print(f"    {tbl:<40} {score:.4f}")

    if args.threshold is not None and report.overall_score < args.threshold:
        print(
            f"\nSimilarity {report.overall_score:.4f} is below threshold {args.threshold:.4f}.",
            file=sys.stderr,
        )
        return 1

    return 0
