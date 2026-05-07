"""CLI sub-commands for the audit log."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from schemasnap.audit import load_audit, filter_audit


def add_audit_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser("audit", help="View the schema audit log")
    sub = parser.add_subparsers(dest="audit_cmd")

    ls = sub.add_parser("list", help="List audit log entries")
    ls.add_argument("--dir", default="snapshots", help="Snapshot directory")
    ls.add_argument("--event", default=None, help="Filter by event type")
    ls.add_argument("--env", default=None, help="Filter by environment")
    ls.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")


def cmd_audit(args: argparse.Namespace) -> int:
    if args.audit_cmd == "list":
        return _cmd_audit_list(args)
    print(f"Unknown audit sub-command: {args.audit_cmd}", file=sys.stderr)
    return 1


def _cmd_audit_list(args: argparse.Namespace) -> int:
    entries = load_audit(args.dir)
    entries = filter_audit(entries, event=getattr(args, "event", None),
                           environment=getattr(args, "env", None))

    if not entries:
        print("No audit entries found.")
        return 0

    if getattr(args, "as_json", False):
        print(json.dumps([asdict(e) for e in entries], indent=2))
    else:
        for e in entries:
            detail_str = ", ".join(f"{k}={v}" for k, v in e.details.items())
            print(f"[{e.timestamp}] {e.event:<16} env={e.environment}  {detail_str}")
    return 0
