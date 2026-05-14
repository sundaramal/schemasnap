"""CLI command: render a snapshot lineage as a DOT/Mermaid graph."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.lineage import load_lineage


def add_lineage_graph_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "lineage-graph",
        help="Render snapshot lineage as a graph (dot or mermaid).",
    )
    p.add_argument("--dir", required=True, help="Snapshot directory.")
    p.add_argument(
        "--fmt",
        choices=["dot", "mermaid", "json"],
        default="mermaid",
        help="Output format (default: mermaid).",
    )
    p.add_argument("--env", default=None, help="Filter to a specific environment.")
    p.set_defaults(func=cmd_lineage_graph)


def _build_edges(entries: list) -> list[tuple[str, str]]:
    """Return (parent_hash, child_hash) pairs from lineage entries."""
    edges = []
    for entry in entries:
        if entry.parent_hash:
            edges.append((entry.parent_hash[:8], entry.snapshot_hash[:8]))
    return edges


def _render_dot(edges: list[tuple[str, str]], nodes: list[str]) -> str:
    lines = ["digraph lineage {"]
    for node in nodes:
        lines.append(f'    "{node}";')
    for parent, child in edges:
        lines.append(f'    "{parent}" -> "{child}";')
    lines.append("}")
    return "\n".join(lines)


def _render_mermaid(edges: list[tuple[str, str]], nodes: list[str]) -> str:
    lines = ["graph TD"]
    seen: set[str] = set()
    for node in nodes:
        if node not in seen:
            lines.append(f"    {node}[{node}]")
            seen.add(node)
    for parent, child in edges:
        lines.append(f"    {parent} --> {child}")
    return "\n".join(lines)


def cmd_lineage_graph(args: argparse.Namespace) -> int:
    snap_dir = Path(args.dir)
    if not snap_dir.is_dir():
        print(f"error: directory not found: {snap_dir}", file=sys.stderr)
        return 1

    entries = load_lineage(snap_dir)
    if args.env:
        entries = [e for e in entries if e.environment == args.env]

    edges = _build_edges(entries)
    nodes = list(
        dict.fromkeys(
            h for entry in entries for h in [entry.snapshot_hash[:8]]
        )
    )

    if args.fmt == "dot":
        print(_render_dot(edges, nodes))
    elif args.fmt == "mermaid":
        print(_render_mermaid(edges, nodes))
    else:  # json
        print(json.dumps({"nodes": nodes, "edges": [{"parent": p, "child": c} for p, c in edges]}, indent=2))

    return 0
