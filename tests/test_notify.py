"""Tests for schemasnap.notify."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from schemasnap.compare import CompareResult
from schemasnap.diff import SchemaDiff
from schemasnap.notify import (
    NotifyConfig,
    _build_slack_payload,
    dispatch_notifications,
    send_slack_notification,
)


def _make_result(added=None, removed=None, modified=None) -> CompareResult:
    diff = SchemaDiff(
        added_tables=added or [],
        removed_tables=removed or [],
        modified_tables=modified or {},
    )
    return CompareResult(env_a="prod", env_b="staging", diff=diff)


def test_build_slack_payload_contains_env_names():
    result = _make_result(added=["users"])
    payload = _build_slack_payload(result)
    text = payload["attachments"][0]["text"]
    assert "prod" in text
    assert "staging" in text


def test_build_slack_payload_counts_changes():
    result = _make_result(added=["a", "b"], removed=["c"], modified={"d": {}})
    payload = _build_slack_payload(result)
    text = payload["attachments"][0]["text"]
    assert "Added tables: 2" in text
    assert "Removed: 1" in text
    assert "Modified: 1" in text


def test_build_slack_payload_red_on_drift():
    result = _make_result(added=["users"])
    payload = _build_slack_payload(result)
    assert payload["attachments"][0]["color"] == "#ff0000"


def test_build_slack_payload_green_on_no_drift():
    result = _make_result()
    payload = _build_slack_payload(result)
    assert payload["attachments"][0]["color"] == "#36a64f"


def test_send_slack_notification_posts_json():
    result = _make_result(added=["orders"])
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        send_slack_notification("https://hooks.slack.com/test", result)
        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "attachments" in body


def test_dispatch_notifications_skips_slack_when_no_changes():
    config = NotifyConfig(slack_webhook_url="https://hooks.slack.com/test")
    result = _make_result()  # no drift
    with patch("schemasnap.notify.send_slack_notification") as mock_slack:
        dispatch_notifications(config, result)
        mock_slack.assert_not_called()


def test_dispatch_notifications_sends_slack_on_drift():
    config = NotifyConfig(slack_webhook_url="https://hooks.slack.com/test")
    result = _make_result(added=["logs"])
    with patch("schemasnap.notify.send_slack_notification") as mock_slack:
        dispatch_notifications(config, result)
        mock_slack.assert_called_once_with(config.slack_webhook_url, result)


def test_dispatch_notifications_calls_custom_handlers():
    calls = []
    config = NotifyConfig(custom_handlers=[lambda r: calls.append(r)])
    result = _make_result()
    dispatch_notifications(config, result)
    assert calls == [result]


def test_dispatch_notifications_multiple_custom_handlers():
    calls: list[str] = []
    config = NotifyConfig(
        custom_handlers=[
            lambda r: calls.append("h1"),
            lambda r: calls.append("h2"),
        ]
    )
    dispatch_notifications(config, _make_result())
    assert calls == ["h1", "h2"]
