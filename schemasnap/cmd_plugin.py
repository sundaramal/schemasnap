"""CLI sub-commands for inspecting the schemasnap plugin registry."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from schemasnap.plugin import get_registry, load_plugins_from_list


def add_plugin_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("plugin", help="Inspect or load schemasnap plugins")
    sub = p.add_subparsers(dest="plugin_cmd", required=True)

    # list
    lp = sub.add_parser("list", help="List registered plugins")
    lp.add_argument("--load", nargs="*", metavar="MODULE",
                    help="Dotted module paths to load before listing")
    lp.set_defaults(func=cmd_plugin_list)

    # load
    lo = sub.add_parser("load", help="Load plugins and confirm registration")
    lo.add_argument("modules", nargs="+", metavar="MODULE",
                    help="Dotted module paths to load")
    lo.set_defaults(func=cmd_plugin_load)


def cmd_plugin_list(args: argparse.Namespace) -> int:
    load_plugins_from_list(getattr(args, "load", None))
    registry = get_registry()
    output = {
        "capture_backends": list(registry.capture_backends.keys()),
        "alert_handlers": [
            getattr(fn, "__name__", repr(fn)) for fn in registry.alert_handlers
        ],
    }
    print(json.dumps(output, indent=2))
    return 0


def cmd_plugin_load(args: argparse.Namespace) -> int:
    try:
        load_plugins_from_list(args.modules)
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    registry = get_registry()
    print(f"Loaded. Capture backends: {list(registry.capture_backends.keys())}")
    print(f"Alert handlers: {len(registry.alert_handlers)}")
    return 0
