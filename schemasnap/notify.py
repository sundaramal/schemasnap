"""Notification backends for schema drift alerts."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional

from schemasnap.compare import CompareResult


@dataclass
class NotifyConfig:
    """Configuration for notification channels."""

    slack_webhook_url: Optional[str] = None
    email_recipients: list[str] = field(default_factory=list)
    custom_handlers: list[Callable[[CompareResult], None]] = field(default_factory=list)


def _build_slack_payload(result: CompareResult) -> dict:
    added = len(result.diff.added_tables)
    removed = len(result.diff.removed_tables)
    modified = len(result.diff.modified_tables)
    color = "#ff0000" if result.diff.has_changes() else "#36a64f"
    text = (
        f"*Schema drift detected* between `{result.env_a}` and `{result.env_b}`\n"
        f"> Added tables: {added}  |  Removed: {removed}  |  Modified: {modified}"
    )
    return {
        "attachments": [
            {"color": color, "text": text, "mrkdwn_in": ["text"]}
        ]
    }


def send_slack_notification(webhook_url: str, result: CompareResult) -> None:
    """POST a drift summary to a Slack incoming webhook."""
    payload = json.dumps(_build_slack_payload(result)).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(f"Slack webhook returned HTTP {resp.status}")


def dispatch_notifications(config: NotifyConfig, result: CompareResult) -> None:
    """Send all configured notifications for a CompareResult."""
    if config.slack_webhook_url and result.diff.has_changes():
        send_slack_notification(config.slack_webhook_url, result)

    for handler in config.custom_handlers:
        handler(result)
