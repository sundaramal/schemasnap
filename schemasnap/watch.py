"""Periodic schema-watch loop with pluggable drift handlers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from schemasnap.compare import compare_environments
from schemasnap.diff import SchemaDiff
from schemasnap.notify import NotifyConfig, dispatch_notifications
from schemasnap.snapshot import capture_snapshot


@dataclass
class WatchConfig:
    """Settings that drive the watch loop."""

    snapshot_dir: str
    environments: list[str]
    capture_schema: Callable[[str], dict]  # env -> raw schema dict
    interval_seconds: float = 60.0
    max_iterations: Optional[int] = None  # None = run forever
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    extra_drift_handlers: list[Callable[[SchemaDiff, str, str], None]] = field(
        default_factory=list
    )


def default_drift_handler(diff: SchemaDiff, env_a: str, env_b: str) -> None:
    """Print a human-readable drift summary to stdout."""
    print(
        f"[schemasnap] Drift detected between '{env_a}' and '{env_b}': "
        f"+{len(diff.added_tables)} tables, "
        f"-{len(diff.removed_tables)} tables, "
        f"~{len(diff.modified_tables)} modified."
    )


def watch_schema(config: WatchConfig) -> int:
    """Run the watch loop; returns total drift events observed."""
    drift_count = 0
    iteration = 0

    while True:
        # Capture a fresh snapshot for every tracked environment.
        for env in config.environments:
            schema = config.capture_schema(env)
            capture_snapshot(schema, env, config.snapshot_dir)

        # Compare consecutive environment pairs.
        envs = config.environments
        for i in range(len(envs) - 1):
            env_a, env_b = envs[i], envs[i + 1]
            result = compare_environments(
                env_a, env_b, config.snapshot_dir, config.snapshot_dir
            )
            if result.diff.has_changes():
                drift_count += 1
                default_drift_handler(result.diff, env_a, env_b)
                for handler in config.extra_drift_handlers:
                    handler(result.diff, env_a, env_b)
                dispatch_notifications(config.notify, result)

        iteration += 1
        if config.max_iterations is not None and iteration >= config.max_iterations:
            break

        time.sleep(config.interval_seconds)

    return drift_count
