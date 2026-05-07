"""CLI subcommands for managing snapshot tags."""

from __future__ import annotations

import argparse
import sys

from schemasnap.snapshot import latest_snapshot
from schemasnap.tag import TagEntry, get_tag, list_tags, remove_tag, save_tag


def add_tag_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    tag_parser = subparsers.add_parser("tag", help="Manage snapshot tags")
    tag_sub = tag_parser.add_subparsers(dest="tag_cmd")

    # tag set
    p_set = tag_sub.add_parser("set", help="Assign a tag to a snapshot")
    p_set.add_argument("--env", required=True, help="Environment name")
    p_set.add_argument("--tag", required=True, help="Tag label")
    p_set.add_argument("--file", default=None, help="Snapshot file (defaults to latest)")
    p_set.add_argument("--note", default="", help="Optional note")
    p_set.add_argument("--dir", dest="snapshot_dir", default="snapshots")

    # tag show
    p_show = tag_sub.add_parser("show", help="Show snapshot for a tag")
    p_show.add_argument("--tag", required=True)
    p_show.add_argument("--dir", dest="snapshot_dir", default="snapshots")

    # tag list
    p_list = tag_sub.add_parser("list", help="List all tags")
    p_list.add_argument("--env", default=None)
    p_list.add_argument("--dir", dest="snapshot_dir", default="snapshots")

    # tag remove
    p_rm = tag_sub.add_parser("remove", help="Remove a tag")
    p_rm.add_argument("--tag", required=True)
    p_rm.add_argument("--dir", dest="snapshot_dir", default="snapshots")


def cmd_tag_set(args: argparse.Namespace) -> int:
    snapshot_file = args.file
    if snapshot_file is None:
        snapshot_file = latest_snapshot(args.snapshot_dir, args.env)
    if snapshot_file is None:
        print(f"No snapshot found for env '{args.env}'", file=sys.stderr)
        return 1
    entry = TagEntry(
        snapshot_file=snapshot_file,
        tag=args.tag,
        env=args.env,
        note=args.note,
    )
    save_tag(args.snapshot_dir, entry)
    print(f"Tagged '{snapshot_file}' as '{args.tag}'")
    return 0


def cmd_tag_show(args: argparse.Namespace) -> int:
    entry = get_tag(args.snapshot_dir, args.tag)
    if entry is None:
        print(f"Tag '{args.tag}' not found", file=sys.stderr)
        return 1
    print(f"tag:   {entry.tag}")
    print(f"env:   {entry.env}")
    print(f"file:  {entry.snapshot_file}")
    if entry.note:
        print(f"note:  {entry.note}")
    return 0


def cmd_tag_list(args: argparse.Namespace) -> int:
    tags = list_tags(args.snapshot_dir, env=args.env)
    if not tags:
        print("No tags found.")
        return 0
    for t in tags:
        note_part = f"  # {t.note}" if t.note else ""
        print(f"{t.tag:<20} [{t.env}]  {t.snapshot_file}{note_part}")
    return 0


def cmd_tag_remove(args: argparse.Namespace) -> int:
    removed = remove_tag(args.snapshot_dir, args.tag)
    if not removed:
        print(f"Tag '{args.tag}' not found", file=sys.stderr)
        return 1
    print(f"Removed tag '{args.tag}'")
    return 0
