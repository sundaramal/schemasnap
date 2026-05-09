"""CLI subcommands for snapshot annotations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from schemasnap.annotation import (
    AnnotationEntry,
    delete_annotation,
    get_annotations_for,
    load_annotations,
    save_annotation,
)


def add_annotation_subparsers(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("annotation", help="Manage snapshot annotations")
    sub = p.add_subparsers(dest="annotation_cmd", required=True)

    add_p = sub.add_parser("add", help="Add a note to a snapshot")
    add_p.add_argument("snapshot_file", help="Snapshot filename (basename)")
    add_p.add_argument("note", help="Annotation text")
    add_p.add_argument("--env", default="", help="Environment label")
    add_p.add_argument("--author", default="unknown", help="Author name")
    add_p.add_argument("--dir", dest="snapshot_dir", default="snapshots")

    show_p = sub.add_parser("show", help="Show annotations for a snapshot")
    show_p.add_argument("snapshot_file", help="Snapshot filename (basename)")
    show_p.add_argument("--dir", dest="snapshot_dir", default="snapshots")
    show_p.add_argument("--json", dest="as_json", action="store_true")

    list_p = sub.add_parser("list", help="List all annotations")
    list_p.add_argument("--dir", dest="snapshot_dir", default="snapshots")
    list_p.add_argument("--json", dest="as_json", action="store_true")

    del_p = sub.add_parser("delete", help="Delete an annotation")
    del_p.add_argument("snapshot_file")
    del_p.add_argument("--author", required=True)
    del_p.add_argument("--timestamp", required=True)
    del_p.add_argument("--dir", dest="snapshot_dir", default="snapshots")


def cmd_annotation_add(args: argparse.Namespace) -> int:
    ts = datetime.now(timezone.utc).isoformat()
    entry = AnnotationEntry(
        snapshot_file=args.snapshot_file,
        env=args.env,
        note=args.note,
        author=args.author,
        timestamp=ts,
    )
    save_annotation(args.snapshot_dir, entry)
    print(f"Annotation added at {ts}")
    return 0


def cmd_annotation_show(args: argparse.Namespace) -> int:
    entries = get_annotations_for(args.snapshot_dir, args.snapshot_file)
    if args.as_json:
        print(json.dumps([e.__dict__ for e in entries], indent=2))
    else:
        if not entries:
            print("No annotations found.")
        for e in entries:
            print(f"[{e.timestamp}] {e.author}: {e.note}")
    return 0


def cmd_annotation_list(args: argparse.Namespace) -> int:
    entries = load_annotations(args.snapshot_dir)
    if args.as_json:
        print(json.dumps([e.__dict__ for e in entries], indent=2))
    else:
        for e in entries:
            print(f"{e.snapshot_file} [{e.timestamp}] {e.author}: {e.note}")
    return 0


def cmd_annotation_delete(args: argparse.Namespace) -> int:
    removed = delete_annotation(
        args.snapshot_dir, args.snapshot_file, args.author, args.timestamp
    )
    print(f"Removed {removed} annotation(s).")
    return 0
