#!/usr/bin/env python3
"""
PinchTab SMCP Plugin

Exposes PinchTab's HTTP API as MCP tools for use with SMCP (sanctumos/smcp).
All operations (navigate, snapshot, action, text, screenshot, etc.) are available.
Supports both single-bridge (base_url = instance) and orchestrator (base_url + instance_id).

Copyright (c) 2026 actuallyrizzn. PinchTab (c) pinchtab.
"""

import argparse
import json
import sys
import traceback
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PLUGIN_VERSION = "0.1.0"
DEBUG_TRACEBACKS = False


def _error_response(error: str, error_type: str, include_traceback: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "status": "error",
        "error": error,
        "error_type": error_type,
    }
    if include_traceback and DEBUG_TRACEBACKS:
        out["traceback"] = traceback.format_exc()
    return out


def _canonical_option_name(action: argparse.Action) -> str:
    for opt in action.option_strings:
        if opt.startswith("--"):
            return opt[2:].replace("_", "-")
    return action.dest.replace("_", "-")


def _arg_type_name(action: argparse.Action) -> str:
    if isinstance(action, argparse._StoreTrueAction):
        return "boolean"
    if getattr(action, "type", None) is int:
        return "integer"
    if getattr(action, "type", None) is float:
        return "number"
    return "string"


def _describe_action(action: argparse.Action) -> Optional[Dict[str, Any]]:
    if action.dest in ("help", "command") or getattr(action, "help", None) == argparse.SUPPRESS:
        return None
    default = None if action.default is argparse.SUPPRESS else action.default
    return {
        "name": _canonical_option_name(action),
        "type": _arg_type_name(action),
        "description": (action.help or "").strip(),
        "required": bool(getattr(action, "required", False)),
        "default": default,
    }


def _get_subparsers_action(parser: argparse.ArgumentParser) -> Optional[argparse._SubParsersAction]:
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            return a
    return None


def _api_request(
    base_url: str,
    method: str,
    path: str,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    query: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Perform HTTP request to PinchTab API. base_url has no trailing slash."""
    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urlencode({k: v for k, v in query.items() if v is not None})
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            return json.loads(err_body)
        except Exception:
            return _error_response(f"HTTP {e.code}: {e.reason}", "api_error")
    except URLError as e:
        return _error_response(f"Request failed: {e.reason}", "connection_error")
    except json.JSONDecodeError as e:
        return _error_response(f"Invalid JSON: {e}", "parse_error")


def _instance_path(base_url: str, instance_id: Optional[str]) -> str:
    """Prefix for instance-scoped paths. If instance_id set, base is orchestrator."""
    if instance_id:
        return f"/instances/{instance_id}"
    return ""


# --- Commands ---

def cmd_health(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    path = _instance_path(base_url, args.get("instance-id")) + "/health"
    out = _api_request(base_url, "GET", path or "/health", token=token, timeout=10)
    if "status" in out and out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_instances(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    out = _api_request(base_url, "GET", "/instances", token=token)
    if isinstance(out, list):
        return {"status": "success", "instances": out}
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_instance_start(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    body = {}
    if args.get("profile-id"):
        body["profileId"] = args["profile-id"]
    if args.get("mode"):
        body["mode"] = args["mode"]
    if args.get("port") is not None:
        body["port"] = str(args["port"])
    out = _api_request(base_url, "POST", "/instances/start", token=token, body=body if body else None)
    if out.get("status") == "error":
        return out
    return {"status": "success", "instance": out}


def cmd_instance_stop(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    iid = args.get("instance-id")
    if not iid:
        return _error_response("instance-id is required", "validation_error")
    out = _api_request(base_url, "POST", f"/instances/{iid}/stop", token=token)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_tabs(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/tabs" if prefix else "/tabs"
    out = _api_request(base_url, "GET", path, token=token)
    if isinstance(out, list):
        return {"status": "success", "tabs": out}
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_navigate(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    url = args.get("url")
    if not url:
        return _error_response("url is required", "validation_error")
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/navigate" if prefix else "/navigate"
    body = {
        "url": url,
        "timeout": args.get("timeout"),
        "blockImages": args.get("block-images"),
        "newTab": args.get("new-tab"),
    }
    body = {k: v for k, v in body.items() if v is not None}
    out = _api_request(base_url, "POST", path, token=token, body=body)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_snapshot(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/snapshot" if prefix else "/snapshot"
    query = {
        "tabId": args.get("tab-id"),
        "filter": args.get("filter"),
        "format": args.get("format"),
        "selector": args.get("selector"),
        "maxTokens": args.get("max-tokens"),
        "diff": "true" if args.get("diff") else None,
        "depth": args.get("depth"),
        "noAnimations": "true" if args.get("no-animations") else None,
    }
    query = {k: v for k, v in query.items() if v is not None}
    out = _api_request(base_url, "GET", path, token=token, query=query)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_action(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    kind = args.get("kind")
    if not kind:
        return _error_response("kind is required (click, type, press, focus, fill, hover, select, scroll)", "validation_error")
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/action" if prefix else "/action"
    body = {"kind": kind}
    if args.get("ref"):
        body["ref"] = args["ref"]
    if args.get("key"):
        body["key"] = args["key"]
    if args.get("text") is not None:
        body["text"] = args["text"]
    if args.get("value") is not None:
        body["value"] = args["value"]
    if args.get("selector"):
        body["selector"] = args["selector"]
    if args.get("scroll-y") is not None:
        body["scrollY"] = args["scroll-y"]
    if args.get("wait-nav"):
        body["waitNav"] = True
    out = _api_request(base_url, "POST", path, token=token, body=body)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_actions(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    actions_list = args.get("actions")
    if not actions_list:
        return _error_response("actions (JSON array) is required", "validation_error")
    if isinstance(actions_list, str):
        try:
            actions_list = json.loads(actions_list)
        except json.JSONDecodeError:
            return _error_response("actions must be a JSON array", "validation_error")
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/actions" if prefix else "/actions"
    body = {"actions": actions_list, "stopOnError": args.get("stop-on-error", False)}
    if args.get("tab-id"):
        body["tabId"] = args["tab-id"]
    out = _api_request(base_url, "POST", path, token=token, body=body)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_text(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/text" if prefix else "/text"
    query = {"tabId": args.get("tab-id"), "mode": args.get("mode")}
    query = {k: v for k, v in query.items() if v is not None}
    out = _api_request(base_url, "GET", path, token=token, query=query)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_screenshot(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/screenshot" if prefix else "/screenshot"
    query = {"tabId": args.get("tab-id"), "raw": "true" if args.get("raw") else None, "quality": args.get("quality")}
    query = {k: v for k, v in query.items() if v is not None}
    out = _api_request(base_url, "GET", path, token=token, query=query)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_pdf(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    tab_id = args.get("tab-id")
    if not tab_id:
        return _error_response("tab-id is required for PDF export", "validation_error")
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/tabs/{tab_id}/pdf" if prefix else f"/tabs/{tab_id}/pdf"
    query = {
        "raw": "true" if args.get("raw") else None,
        "landscape": "true" if args.get("landscape") else None,
        "scale": args.get("scale"),
    }
    query = {k: v for k, v in query.items() if v is not None}
    out = _api_request(base_url, "GET", path, token=token, query=query)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_evaluate(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    expr = args.get("expression")
    if not expr:
        return _error_response("expression is required", "validation_error")
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/evaluate" if prefix else "/evaluate"
    out = _api_request(base_url, "POST", path, token=token, body={"expression": expr})
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_cookies_get(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/cookies" if prefix else "/cookies"
    out = _api_request(base_url, "GET", path, token=token)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def cmd_stealth_status(args: Dict[str, Any], base_url: str, token: Optional[str]) -> Dict[str, Any]:
    prefix = _instance_path(base_url, args.get("instance-id"))
    path = f"{prefix}/stealth/status" if prefix else "/stealth/status"
    out = _api_request(base_url, "GET", path, token=token)
    if out.get("status") == "error":
        return out
    return {"status": "success", "data": out}


def get_plugin_description(parser: argparse.ArgumentParser) -> Dict[str, Any]:
    commands: List[Dict[str, Any]] = []
    sub = _get_subparsers_action(parser)
    if sub:
        for cmd_name, cmd_parser in sub.choices.items():
            params = []
            for a in cmd_parser._actions:
                d = _describe_action(a)
                if d:
                    params.append(d)
            commands.append({
                "name": cmd_name,
                "description": (cmd_parser.description or "").strip(),
                "parameters": params,
            })
    return {
        "plugin": {
            "name": "pinchtab",
            "version": PLUGIN_VERSION,
            "description": "Browser control for AI agents via PinchTab HTTP API. Navigate, snapshot, action (click/type/press), text, screenshot, PDF, evaluate, instances, tabs.",
        },
        "commands": commands,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PinchTab SMCP plugin — browser control via HTTP API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--describe", action="store_true", help="Output plugin description JSON")
    parser.add_argument("--debug", action="store_true", help="Include tracebacks in errors")
    parser.add_argument("--base-url", dest="base_url", default="http://localhost:9867", help="PinchTab base URL (orchestrator or instance)")
    parser.add_argument("--token", help="Bearer token (BRIDGE_TOKEN)")
    parser.add_argument("--instance-id", dest="instance_id", help="Instance ID when using orchestrator")
    sub = parser.add_subparsers(dest="command", help="Commands")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--base-url", dest="base_url", default="http://localhost:9867")
        p.add_argument("--token")
        p.add_argument("--instance-id", dest="instance_id")

    # health
    p_health = sub.add_parser("health", help="Health check")
    add_common(p_health)

    # instances
    p_inst = sub.add_parser("instances", help="List instances (orchestrator)")
    add_common(p_inst)

    # instance-start
    p_start = sub.add_parser("instance-start", help="Start an instance")
    add_common(p_start)
    p_start.add_argument("--profile-id", dest="profile_id")
    p_start.add_argument("--mode", choices=["headless", "headed"])
    p_start.add_argument("--port", type=int)

    # instance-stop (instance-id from add_common; required at runtime in handler)
    p_stop = sub.add_parser("instance-stop", help="Stop an instance (requires --instance-id)")
    add_common(p_stop)

    # tabs
    p_tabs = sub.add_parser("tabs", help="List tabs")
    add_common(p_tabs)

    # navigate
    p_nav = sub.add_parser("navigate", help="Navigate to URL")
    add_common(p_nav)
    p_nav.add_argument("--url", required=True)
    p_nav.add_argument("--timeout", type=int)
    p_nav.add_argument("--block-images", dest="block_images", action="store_true")
    p_nav.add_argument("--new-tab", dest="new_tab", action="store_true")

    # snapshot
    p_snap = sub.add_parser("snapshot", help="Get accessibility tree snapshot")
    add_common(p_snap)
    p_snap.add_argument("--tab-id", dest="tab_id")
    p_snap.add_argument("--filter", choices=["interactive", "all"])
    p_snap.add_argument("--format", choices=["json", "text", "compact", "yaml"])
    p_snap.add_argument("--selector")
    p_snap.add_argument("--max-tokens", dest="max_tokens", type=int)
    p_snap.add_argument("--diff", action="store_true")
    p_snap.add_argument("--depth", type=int)
    p_snap.add_argument("--no-animations", dest="no_animations", action="store_true")

    # action
    p_act = sub.add_parser("action", help="Single action: click, type, press, focus, fill, hover, select, scroll")
    add_common(p_act)
    p_act.add_argument("--kind", required=True, choices=["click", "type", "press", "focus", "fill", "hover", "select", "scroll"])
    p_act.add_argument("--ref")
    p_act.add_argument("--key")
    p_act.add_argument("--text")
    p_act.add_argument("--value")
    p_act.add_argument("--selector")
    p_act.add_argument("--scroll-y", dest="scroll_y", type=int)
    p_act.add_argument("--wait-nav", dest="wait_nav", action="store_true")

    # actions (batch)
    p_acts = sub.add_parser("actions", help="Batch actions (JSON array)")
    add_common(p_acts)
    p_acts.add_argument("--actions", required=True, help="JSON array of action objects")
    p_acts.add_argument("--tab-id", dest="tab_id")
    p_acts.add_argument("--stop-on-error", dest="stop_on_error", action="store_true")

    # text
    p_text = sub.add_parser("text", help="Extract page text")
    add_common(p_text)
    p_text.add_argument("--tab-id", dest="tab_id")
    p_text.add_argument("--mode", choices=["readability", "raw"])

    # screenshot
    p_ss = sub.add_parser("screenshot", help="Take screenshot")
    add_common(p_ss)
    p_ss.add_argument("--tab-id", dest="tab_id")
    p_ss.add_argument("--raw", action="store_true")
    p_ss.add_argument("--quality", type=int)

    # pdf
    p_pdf = sub.add_parser("pdf", help="Export tab to PDF")
    add_common(p_pdf)
    p_pdf.add_argument("--tab-id", dest="tab_id", required=True)
    p_pdf.add_argument("--raw", action="store_true")
    p_pdf.add_argument("--landscape", action="store_true")
    p_pdf.add_argument("--scale", type=float)

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Run JavaScript in page")
    add_common(p_eval)
    p_eval.add_argument("--expression", required=True)

    # cookies
    p_cook = sub.add_parser("cookies-get", help="Get cookies")
    add_common(p_cook)

    # stealth-status
    p_stealth = sub.add_parser("stealth-status", help="Stealth/fingerprint status")
    add_common(p_stealth)

    return parser


def main() -> None:
    global DEBUG_TRACEBACKS
    parser = build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 0:
            raise
        err = _error_response("Invalid arguments", "argument_error", include_traceback=False)
        print(json.dumps(err, indent=2), file=sys.stderr)
        print(json.dumps(err, indent=2))
        sys.exit(e.code if isinstance(e.code, int) else 2)

    DEBUG_TRACEBACKS = bool(getattr(args, "debug", False))
    if args.describe:
        print(json.dumps(get_plugin_description(parser), indent=2))
        sys.exit(0)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    base_url = getattr(args, "base_url", "http://localhost:9867") or "http://localhost:9867"
    token = getattr(args, "token", None)
    args_dict: Dict[str, Any] = {}
    for k, v in vars(args).items():
        if k in ("command", "describe", "debug"):
            continue
        if v is None:
            continue
        key = k.replace("_", "-")
        args_dict[key] = v

    commands = {
        "health": cmd_health,
        "instances": cmd_instances,
        "instance-start": cmd_instance_start,
        "instance-stop": cmd_instance_stop,
        "tabs": cmd_tabs,
        "navigate": cmd_navigate,
        "snapshot": cmd_snapshot,
        "action": cmd_action,
        "actions": cmd_actions,
        "text": cmd_text,
        "screenshot": cmd_screenshot,
        "pdf": cmd_pdf,
        "evaluate": cmd_evaluate,
        "cookies-get": cmd_cookies_get,
        "stealth-status": cmd_stealth_status,
    }
    fn = commands.get(args.command)
    if not fn:
        result = _error_response(f"Unknown command: {args.command}", "argument_error", include_traceback=False)
    else:
        try:
            result = fn(args_dict, base_url, token)
        except Exception as e:
            result = _error_response(str(e), "unknown_error")
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
