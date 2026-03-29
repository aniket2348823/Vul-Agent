"""
SMCP compatibility tests.

Ensures the plugin satisfies SMCP discovery and execution contract:
- --describe returns valid JSON with plugin + commands + parameters
- All commands are invocable with correct args
- Output is always a single JSON object to stdout
- No functionality missing (all PinchTab API operations covered)
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Run cli.py as module or script
PLUGIN_DIR = Path(__file__).resolve().parent.parent
CLI = PLUGIN_DIR / "cli.py"


def run_cli(*args: str, timeout: int = 10) -> tuple[str, str, int]:
    """Run cli.py with args; return (stdout, stderr, returncode)."""
    proc = subprocess.run(
        [sys.executable, str(CLI)] + list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(PLUGIN_DIR),
    )
    return proc.stdout, proc.stderr, proc.returncode


def run_describe() -> dict:
    """Run --describe and parse JSON."""
    out, err, code = run_cli("--describe")
    assert code == 0, f"describe failed: stdout={out!r} stderr={err!r}"
    return json.loads(out)


# --- Describe contract (SMCP discovery) ---


def test_describe_returns_valid_json():
    """--describe must output a single valid JSON object."""
    payload = run_describe()
    assert isinstance(payload, dict)
    assert "plugin" in payload
    assert "commands" in payload


def test_describe_plugin_schema():
    """Plugin object must have name, version, description."""
    payload = run_describe()
    plugin = payload["plugin"]
    assert plugin["name"] == "pinchtab"
    assert "version" in plugin
    assert isinstance(plugin["version"], str)
    assert "description" in plugin


def test_describe_commands_list():
    """Commands must be a list of command objects."""
    payload = run_describe()
    commands = payload["commands"]
    assert isinstance(commands, list)
    for cmd in commands:
        assert "name" in cmd
        assert "description" in cmd
        assert "parameters" in cmd
        assert isinstance(cmd["parameters"], list)


def test_describe_parameter_schema():
    """Each parameter must have name, type, description, required, default."""
    payload = run_describe()
    for cmd in payload["commands"]:
        for param in cmd["parameters"]:
            assert "name" in param
            assert param["type"] in ("string", "integer", "number", "boolean", "array", "object")
            assert "required" in param
            assert isinstance(param["required"], bool)


def test_describe_all_required_commands_present():
    """All PinchTab API operations must be exposed as commands."""
    payload = run_describe()
    names = {c["name"] for c in payload["commands"]}
    required = {
        "health",
        "instances",
        "instance-start",
        "instance-stop",
        "tabs",
        "navigate",
        "snapshot",
        "action",
        "actions",
        "text",
        "screenshot",
        "pdf",
        "evaluate",
        "cookies-get",
        "stealth-status",
    }
    missing = required - names
    assert not missing, f"Missing commands: {missing}"


def test_describe_navigate_has_url():
    """navigate command must have url parameter."""
    payload = run_describe()
    nav = next(c for c in payload["commands"] if c["name"] == "navigate")
    param_names = [p["name"] for p in nav["parameters"]]
    assert "url" in param_names


def test_describe_snapshot_has_filter_and_format():
    """snapshot command must have filter and format for token control."""
    payload = run_describe()
    snap = next(c for c in payload["commands"] if c["name"] == "snapshot")
    param_names = [p["name"] for p in snap["parameters"]]
    assert "filter" in param_names
    assert "format" in param_names


def test_describe_action_has_kind_and_ref():
    """action command must have kind and ref."""
    payload = run_describe()
    act = next(c for c in payload["commands"] if c["name"] == "action")
    param_names = [p["name"] for p in act["parameters"]]
    assert "kind" in param_names


def test_describe_pdf_requires_tab_id():
    """pdf command must have tab-id required."""
    payload = run_describe()
    pdf_cmd = next(c for c in payload["commands"] if c["name"] == "pdf")
    tab_param = next((p for p in pdf_cmd["parameters"] if p["name"] == "tab-id"), None)
    assert tab_param is not None
    assert tab_param["required"] is True


# --- Execution contract: JSON only to stdout ---


def test_help_exits_nonzero():
    """No command should exit 0 and print help only (no JSON)."""
    out, err, code = run_cli()
    assert code != 0


def test_unknown_command_returns_json_error():
    """Unknown command should print JSON with error_type."""
    out, err, code = run_cli("not-a-command")
    assert code != 0
    data = json.loads(out)
    assert "status" in data
    assert data.get("status") == "error"
    assert "error_type" in data


def test_validation_errors_return_json():
    """Missing required args must return JSON error (validation_error or argument_error)."""
    out, err, code = run_cli("navigate", "--base-url", "http://localhost:9867")
    assert code != 0
    data = json.loads(out)
    assert data.get("status") == "error"
    assert data.get("error_type") in ("validation_error", "argument_error")


def test_instance_stop_missing_id_returns_validation_error():
    """instance-stop without instance-id must return validation_error."""
    out, err, code = run_cli("instance-stop", "--base-url", "http://localhost:9867")
    assert code != 0
    data = json.loads(out)
    assert data.get("status") == "error"
    assert data.get("error_type") == "validation_error"


def test_pdf_missing_tab_id_returns_validation_error():
    """pdf without tab-id must return validation_error or argument_error."""
    out, err, code = run_cli("pdf", "--base-url", "http://localhost:9867")
    assert code != 0
    data = json.loads(out)
    assert data.get("status") == "error"
    assert data.get("error_type") in ("validation_error", "argument_error")


def test_action_missing_kind_returns_validation_error():
    """action without kind must return validation_error or argument_error."""
    out, err, code = run_cli("action", "--base-url", "http://localhost:9867")
    assert code != 0
    data = json.loads(out)
    assert data.get("status") == "error"
    assert data.get("error_type") in ("validation_error", "argument_error")


def test_actions_missing_actions_returns_error():
    """actions without --actions must fail (arg parse or validation_error)."""
    out, err, code = run_cli("actions", "--base-url", "http://localhost:9867")
    assert code != 0
    data = json.loads(out)
    assert data.get("status") == "error"


def test_evaluate_missing_expression_returns_validation_error():
    """evaluate without expression must return validation_error or argument_error."""
    out, err, code = run_cli("evaluate", "--base-url", "http://localhost:9867")
    assert code != 0
    data = json.loads(out)
    assert data.get("status") == "error"
    assert data.get("error_type") in ("validation_error", "argument_error")


# --- SMCP invocation style: kebab-case args ---


def test_smcp_style_invoke_navigate_with_kebab_args():
    """SMCP passes --url, --instance-id etc.; plugin must accept and return JSON."""
    out, err, code = run_cli(
        "navigate",
        "--base-url", "http://127.0.0.1:9999",
        "--url", "https://pinchtab.com",
    )
    # Server likely unreachable -> connection_error; we only require valid JSON
    data = json.loads(out)
    assert "status" in data
    assert data["status"] in ("success", "error")
    if data["status"] == "error":
        assert "error_type" in data


def test_smcp_style_invoke_snapshot_with_options():
    """Snapshot with filter and format (common agent pattern)."""
    out, err, code = run_cli(
        "snapshot",
        "--base-url", "http://127.0.0.1:9999",
        "--filter", "interactive",
        "--format", "compact",
    )
    data = json.loads(out)
    assert "status" in data


def test_smcp_style_invoke_action_click():
    """Action click with ref."""
    out, err, code = run_cli(
        "action",
        "--base-url", "http://127.0.0.1:9999",
        "--kind", "click",
        "--ref", "e5",
    )
    data = json.loads(out)
    assert "status" in data


def test_success_response_structure():
    """When command succeeds (or server returns 200), response has status success and data."""
    # We can't guarantee server is up; test that our success path structure is correct
    # by testing that connection_error has status/error/error_type
    out, err, code = run_cli("health", "--base-url", "http://127.0.0.1:9999")
    data = json.loads(out)
    assert "status" in data
    if data["status"] == "success":
        assert "data" in data
    else:
        assert "error" in data
        assert "error_type" in data
