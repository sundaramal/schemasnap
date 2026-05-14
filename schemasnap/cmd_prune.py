"""CLI subcommand: prune snapshots based on retention or count limits."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schemasnap.retention import RetentionPolicy, apply_retention
from schemasnap.audit_hooks import audit_capture  # reuse append_audit pattern
from schemasnap.audit import append_audit


def add_prune_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "prune",
        help="Remove snapshots that exceed retention limits.",
    )
    p.add_argument("--snapshot-dir", default="snapshots", help="Directory holding snapshots.")
    p.add_argument("--env", default=None, help="Restrict pruning to a specific environment.")
    p.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        metavar="DAYS",
        help="Delete snapshots older than DAYS days.",
    )
    p.add_argument(
        "--max-count",
        type=int,
        default=None,
        metavar="N",
        help="Keep only the N most recent snapshots per environment.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print files that would be removed without deleting them.",
    )
    p.add_argument("--audit-dir", default=None, help="Directory for audit log (optional).")
    p.set_defaults(func=cmd_prune)


def cmd_prune(args: argparse.Namespace) -> int:
    snap_dir = Path(args.snapshot_dir)
    if not snap_dir.is_dir():
        print(f"[prune] snapshot directory not found: {snap_dir}", file=sys.stderr)
        return 1

    if args.max_age_days is None and args.max_count is None:
        print("[prune] specify at least one of --max-age-days or --max-count.", file=sys.stderr)
        return 1

    policy = RetentionPolicy(
        max_age_days=args.max_age_days,
        max_count=args.max_count,
        env=args.env,
    )

    removed = apply_retention(snap_dir, policy, dry_run=args.dry_run)

    label = "[dry-run] would remove" if args.dry_run else "removed"
    for path in removed:
        print(f"[prune] {label}: {path.name}")

    print(f"[prune] total {label}: {len(removed)} snapshot(s).")

    if not args.dry_run and args.audit_dir:
        audit_dir = Path(args.audit_dir)
        audit_dir.mkdir(parents=True, exist_ok=True)
        append_audit(
            audit_dir,
            action="prune",
            detail={
                "removed": [p.name for p in removed],
                "policy": {"max_age_days": args.max_age_days, "max_count": args.max_count, "env": args.env},
            },
        )

    return 0
