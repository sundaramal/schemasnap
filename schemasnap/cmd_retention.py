"""CLI sub-commands for retention policy management."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from schemasnap.retention import RetentionPolicy, apply_retention, evaluate_retention


def add_retention_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("retention", help="Manage snapshot retention policies")
    sub = p.add_subparsers(dest="retention_cmd", required=True)

    # --- check ---
    chk = sub.add_parser("check", help="List snapshots that would be pruned")
    _add_common_args(chk)
    chk.add_argument("--dry-run", action="store_true", default=True,
                     help="Only list; do not delete (default: True)")
    chk.set_defaults(func=cmd_retention_check)

    # --- apply ---
    apl = sub.add_parser("apply", help="Delete snapshots that violate the policy")
    _add_common_args(apl)
    apl.add_argument("--yes", action="store_true", help="Confirm deletion")
    apl.set_defaults(func=cmd_retention_apply)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--snapshot-dir", default="snapshots",
                        help="Directory containing snapshots")
    parser.add_argument("--max-age-days", type=int, default=None,
                        help="Delete snapshots older than N days")
    parser.add_argument("--max-count", type=int, default=None,
                        help="Keep at most N snapshots")
    parser.add_argument("--env", nargs="*", default=[],
                        help="Restrict to these environment names")
    parser.add_argument("--json", dest="output_json", action="store_true",
                        help="Output results as JSON")


def _build_policy(args: argparse.Namespace) -> RetentionPolicy:
    return RetentionPolicy(
        max_age_days=args.max_age_days,
        max_count=args.max_count,
        env_filter=args.env or [],
    )


def cmd_retention_check(args: argparse.Namespace) -> int:
    policy = _build_policy(args)
    victims = evaluate_retention(args.snapshot_dir, policy)
    if args.output_json:
        print(json.dumps({"would_delete": victims}))
    else:
        if victims:
            print(f"Snapshots that would be pruned ({len(victims)}):")
            for v in victims:
                print(f"  {v}")
        else:
            print("No snapshots would be pruned.")
    return 0


def cmd_retention_apply(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Pass --yes to confirm deletion.", file=sys.stderr)
        return 1
    policy = _build_policy(args)
    deleted = apply_retention(args.snapshot_dir, policy, dry_run=False)
    if args.output_json:
        print(json.dumps({"deleted": deleted}))
    else:
        if deleted:
            print(f"Deleted {len(deleted)} snapshot(s):")
            for d in deleted:
                print(f"  {d}")
        else:
            print("Nothing to delete.")
    return 0
