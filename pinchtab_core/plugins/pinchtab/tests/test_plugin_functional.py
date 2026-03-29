"""
Functional tests for plugin command handlers.

Uses mocks so no real PinchTab server is required. Ensures each command
builds correct request and handles response.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

# Import after path fix in conftest
import cli  # noqa: E402


@pytest.fixture
def base_url():
    return "http://localhost:9867"


@pytest.fixture
def token():
    return None


def test_health_success(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {"ok": True}
        result = cli.cmd_health({}, base_url, token)
    assert result["status"] == "success"
    assert "data" in result
    m.assert_called_once()
    call_args = m.call_args
    assert call_args[0][2] == "/health"  # path without instance prefix


def test_health_with_instance_id(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {}
        cli.cmd_health({"instance-id": "inst_abc"}, base_url, token)
    m.assert_called_once()
    assert "/instances/inst_abc/health" in m.call_args[0][2]


def test_navigate_requires_url(base_url, token):
    result = cli.cmd_navigate({}, base_url, token)
    assert result["status"] == "error"
    assert result["error_type"] == "validation_error"


def test_navigate_success(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {}
        result = cli.cmd_navigate({"url": "https://pinchtab.com"}, base_url, token)
    assert result["status"] == "success"
    m.assert_called_once()
    body = m.call_args[1]["body"]
    assert body["url"] == "https://pinchtab.com"


def test_navigate_with_options(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {}
        cli.cmd_navigate({
            "url": "https://pinchtab.com",
            "block-images": True,
            "new-tab": True,
            "timeout": 60,
        }, base_url, token)
    body = m.call_args[1]["body"]
    assert body["blockImages"] is True
    assert body["newTab"] is True
    assert body["timeout"] == 60


def test_snapshot_query_params(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {"nodes": []}
        cli.cmd_snapshot({
            "filter": "interactive",
            "format": "compact",
            "max-tokens": 2000,
        }, base_url, token)
    m.assert_called_once()
    query = m.call_args[1]["query"]
    assert query.get("filter") == "interactive"
    assert query.get("format") == "compact"
    assert query.get("maxTokens") == 2000


def test_action_click(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {}
        result = cli.cmd_action({
            "kind": "click",
            "ref": "e5",
        }, base_url, token)
    assert result["status"] == "success"
    body = m.call_args[1]["body"]
    assert body["kind"] == "click"
    assert body["ref"] == "e5"


def test_action_type(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {}
        cli.cmd_action({"kind": "type", "ref": "e3", "text": "hello"}, base_url, token)
    body = m.call_args[1]["body"]
    assert body["kind"] == "type"
    assert body["text"] == "hello"


def test_action_requires_kind(base_url, token):
    result = cli.cmd_action({"ref": "e5"}, base_url, token)
    assert result["status"] == "error"
    assert result["error_type"] == "validation_error"


def test_instance_stop_requires_instance_id(base_url, token):
    result = cli.cmd_instance_stop({}, base_url, token)
    assert result["status"] == "error"
    assert "instance-id" in result["error"].lower()


def test_instance_stop_success(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {"id": "inst_xyz", "status": "stopped"}
        result = cli.cmd_instance_stop({"instance-id": "inst_xyz"}, base_url, token)
    assert result["status"] == "success"
    m.assert_called_once()
    assert m.call_args[0][2] == "/instances/inst_xyz/stop"


def test_pdf_requires_tab_id(base_url, token):
    result = cli.cmd_pdf({}, base_url, token)
    assert result["status"] == "error"
    assert result["error_type"] == "validation_error"


def test_pdf_success(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {"data": "base64..."}
        result = cli.cmd_pdf({"tab-id": "tab_abc", "instance-id": "inst_1"}, base_url, token)
    assert result["status"] == "success"
    assert m.call_args[0][2] == "/instances/inst_1/tabs/tab_abc/pdf"


def test_instances_list(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = [{"id": "inst_1", "port": "9868"}]
        result = cli.cmd_instances({}, base_url, token)
    assert result["status"] == "success"
    assert "instances" in result
    assert len(result["instances"]) == 1


def test_instance_start_body(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {"id": "inst_new", "status": "starting"}
        cli.cmd_instance_start({
            "profile-id": "prof_123",
            "mode": "headed",
            "port": 9999,
        }, base_url, token)
    body = m.call_args[1]["body"]
    assert body["profileId"] == "prof_123"
    assert body["mode"] == "headed"
    assert body["port"] == "9999"


def test_evaluate_requires_expression(base_url, token):
    result = cli.cmd_evaluate({}, base_url, token)
    assert result["status"] == "error"
    assert result["error_type"] == "validation_error"


def test_evaluate_success(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {"result": "Page title"}
        result = cli.cmd_evaluate({"expression": "document.title"}, base_url, token)
    assert result["status"] == "success"
    body = m.call_args[1]["body"]
    assert body["expression"] == "document.title"


def test_api_error_propagated(base_url, token):
    with patch("cli._api_request") as m:
        m.return_value = {"status": "error", "error": "Connection refused", "error_type": "connection_error"}
        result = cli.cmd_health({}, base_url, token)
    assert result["status"] == "error"
    assert result["error_type"] == "connection_error"
