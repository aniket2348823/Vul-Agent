"""
Vigilagent Terminal Engine (Architecture §8, §29.13)
================================================================================
The governed bridge between agents and real CLI tools. It is the single audited
path for recon/tool execution.

Responsibilities (Architecture §8):
  - Execute local commands where safe.
  - Execute Docker-isolated commands by default for Linux-native toolchains.
  - Support timeouts and no-output watchdogs.
  - Capture stdout, stderr, exit code, duration, hash, truncation status.
  - Enforce command allowlists (argv-only, no shell strings).
  - Enforce scope extraction from command arguments.
  - Require approval for risky or state-changing actions.
  - Store command artifacts under scan-specific directories.

Execution pipeline (Architecture §8):
  request -> tool registry -> budget consume -> command guard -> scope policy
          -> approval gate -> terminal engine -> docker/local backend
          -> output watchdog -> parser -> evidence store -> graph -> events

This engine is RECON/TOOL execution only. It is NOT a generic exploitation
shell: only registered, allowlisted binaries run, and every argv passes the
guardrail validator that rejects shell metacharacters.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from backend.core.iteration_budget import IterationBudget
from backend.core.queue import LanePriority, ProcessRunner, command_lane
from backend.core.sandbox import DockerSandbox
from backend.core.scope import ScopePolicy, ScopeViolation, scope_guard
from backend.core.stdout_watchdog import watch_output
from backend.tools.recon.guardrails import validate_command

logger = logging.getLogger("vigilagent.terminal")

_DEFAULT_OUTPUT_CAP = 10 * 1024 * 1024  # 10 MB (config/tools.yaml output_cap_bytes)
_STDERR_TAIL = 16 * 1024


class TerminalBackend(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"


@dataclass
class TerminalResult:
    """Structured result of a single governed command execution (§8)."""

    tool: str
    argv: list[str]
    backend: str
    exit_code: int | None
    output_path: str
    stdout: str = ""
    stderr_tail: str = ""
    timed_out: bool = False
    blocked: bool = False
    block_reason: str = ""
    duration_ms: int = 0
    sha256: str = ""
    output_bytes: int = 0
    scan_id: str = ""
    agent: str = ""
    parser_hint: str = "lines"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        if self.blocked:
            return "blocked"
        if self.timed_out:
            return "timeout"
        if self.exit_code == 0:
            return "finished"
        return "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "argv": self.argv,
            "backend": self.backend,
            "exit_code": self.exit_code,
            "status": self.status,
            "output_path": self.output_path,
            "stderr_tail": self.stderr_tail,
            "timed_out": self.timed_out,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "duration_ms": self.duration_ms,
            "sha256": self.sha256,
            "output_bytes": self.output_bytes,
            "scan_id": self.scan_id,
            "agent": self.agent,
            "parser_hint": self.parser_hint,
            "metadata": self.metadata,
        }


def _docker_available() -> bool:
    return shutil.which("docker") is not None


class TerminalEngine:
    """Single governed execution path for recon/tool CLI commands."""

    def __init__(
        self,
        scope: ScopePolicy | None = None,
        *,
        prefer_docker: bool = True,
        docker_image: str | None = None,
        output_cap_bytes: int = _DEFAULT_OUTPUT_CAP,
    ) -> None:
        self.scope = scope or scope_guard
        self.prefer_docker = prefer_docker
        self.output_cap_bytes = output_cap_bytes
        self._sandbox = DockerSandbox(image=docker_image) if docker_image else DockerSandbox()
        self._docker_ok = _docker_available()
        self.telemetry = {
            "runs": 0,
            "blocked": 0,
            "timeouts": 0,
            "failures": 0,
            "docker_runs": 0,
            "local_runs": 0,
        }

    # ── Backend selection (Architecture §7 rule 3) ───────────────────────────

    def choose_backend(self, prefer_docker: bool | None = None) -> TerminalBackend:
        want_docker = self.prefer_docker if prefer_docker is None else prefer_docker
        if want_docker and self._docker_ok:
            return TerminalBackend.DOCKER
        return TerminalBackend.LOCAL

    @staticmethod
    def _extract_target(argv: Sequence[str]) -> str | None:
        """Find a host/URL inside an argv array for scope validation."""
        for arg in argv:
            a = str(arg)
            if a.startswith(("http://", "https://")):
                return a
            # bare domain heuristic: contains a dot, no slash, no leading dash
            if "." in a and "/" not in a and not a.startswith("-") and " " not in a:
                # Skip obvious file paths / flags-with-values
                if not a.lower().endswith((".txt", ".json", ".jsonl", ".xml", ".kite", ".py", ".csv")):
                    parsed = urlparse(f"//{a}", scheme="")
                    if parsed.hostname:
                        return a
        return None

    # ── Execution ─────────────────────────────────────────────────────────────

    async def run(
        self,
        argv: Sequence[str],
        *,
        scan_id: str = "GLOBAL",
        agent: str = "terminal",
        output_path: str | Path | None = None,
        timeout_seconds: int = 180,
        budget: IterationBudget | None = None,
        parser_hint: str = "lines",
        priority: LanePriority = LanePriority.NORMAL,
        stdin: str | None = None,
        cwd: str | Path | None = None,
        prefer_docker: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TerminalResult:
        argv = [str(part) for part in argv]
        tool = os.path.basename(argv[0]) if argv else "unknown"
        out_path = str(output_path) if output_path else ""
        meta = metadata or {}

        def _blocked(reason: str) -> TerminalResult:
            self.telemetry["blocked"] += 1
            logger.warning("[TERMINAL] BLOCKED %s: %s", tool, reason)
            return TerminalResult(
                tool=tool, argv=argv, backend="none", exit_code=-1,
                output_path=out_path, blocked=True, block_reason=reason,
                scan_id=scan_id, agent=agent, parser_hint=parser_hint, metadata=meta,
            )

        # 1. Budget (Architecture §8 pipeline step 1)
        if budget is not None and not budget.consume(1):
            return _blocked("budget_exhausted")

        # 2. Command guardrail — argv-only, no shell strings (Property §29.14.6)
        guard = validate_command(argv)
        if not guard.allowed:
            if budget is not None:
                budget.refund(1)
            return _blocked(f"guardrail:{guard.reason}")

        # 3. Scope extraction from arguments (Architecture §8)
        target = self._extract_target(argv)
        if target:
            try:
                self.scope.assert_allowed(target, action="recon")
            except ScopeViolation as exc:
                if budget is not None:
                    budget.refund(1)
                return _blocked(f"scope:{exc}")

        # 4. Backend selection
        backend = self.choose_backend(prefer_docker)

        # 5. Prepare artifact directory
        if out_path:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        self.telemetry["runs"] += 1
        started = time.time()

        try:
            if backend is TerminalBackend.DOCKER:
                result = await self._run_docker(argv, scan_id, timeout_seconds)
            else:
                result = await self._run_local(
                    argv, stdin=stdin, cwd=cwd, timeout_seconds=timeout_seconds, priority=priority
                )
        except Exception as exc:  # pragma: no cover - defensive
            self.telemetry["failures"] += 1
            logger.error("[TERMINAL] %s execution error: %s", tool, exc)
            return TerminalResult(
                tool=tool, argv=argv, backend=backend.value, exit_code=1,
                output_path=out_path, stderr_tail=str(exc)[-_STDERR_TAIL:],
                duration_ms=int((time.time() - started) * 1000),
                scan_id=scan_id, agent=agent, parser_hint=parser_hint, metadata=meta,
            )

        stdout, stderr, exit_code, timed_out = result
        duration_ms = int((time.time() - started) * 1000)

        # 6. Output watchdog / cap + persist artifact
        watched = await watch_output(stdout, max_bytes=self.output_cap_bytes)
        sha256 = hashlib.sha256(watched.content.encode("utf-8", errors="replace")).hexdigest()
        out_bytes = len(watched.content.encode("utf-8", errors="replace"))
        if out_path:
            try:
                Path(out_path).write_text(watched.content, encoding="utf-8", errors="replace")
            except Exception as exc:
                logger.warning("[TERMINAL] could not write artifact %s: %s", out_path, exc)

        if timed_out:
            self.telemetry["timeouts"] += 1
        elif exit_code not in (0, None):
            self.telemetry["failures"] += 1

        if backend is TerminalBackend.DOCKER:
            self.telemetry["docker_runs"] += 1
        else:
            self.telemetry["local_runs"] += 1

        return TerminalResult(
            tool=tool, argv=argv, backend=backend.value, exit_code=exit_code,
            output_path=out_path, stdout=watched.content,
            stderr_tail=stderr[-_STDERR_TAIL:], timed_out=timed_out,
            duration_ms=duration_ms, sha256=sha256, output_bytes=out_bytes,
            scan_id=scan_id, agent=agent, parser_hint=parser_hint,
            metadata={**meta, "truncated": watched.truncated},
        )

    async def _run_local(
        self,
        argv: list[str],
        *,
        stdin: str | None,
        cwd: str | Path | None,
        timeout_seconds: int,
        priority: LanePriority,
    ) -> tuple[str, str, int | None, bool]:
        # Resolve binary from PATH first, then tool root (Architecture §7 rule 2).
        async with command_lane.slot(priority):
            proc = await ProcessRunner.run_exec(
                argv,
                stdin=stdin,
                cwd=cwd,
                no_output_timeout_ms=min(timeout_seconds * 1000, 30_000),
                max_runtime_ms=timeout_seconds * 1000,
            )
        return proc.stdout, proc.stderr, proc.exit_code, proc.timed_out

    async def _run_docker(
        self,
        argv: list[str],
        scan_id: str,
        timeout_seconds: int,
    ) -> tuple[str, str, int | None, bool]:
        # DockerSandbox runs a single shell-quoted command inside an isolated
        # container. We pass the argv joined safely; the sandbox enforces
        # resource limits and network policy.
        from backend.core.sandbox import quote_command

        command = quote_command(argv)
        sandbox_res = await self._sandbox.run(command, engagement_id=scan_id, timeout=timeout_seconds)
        timed_out = sandbox_res.exit_code == 124
        return sandbox_res.stdout, sandbox_res.stderr, sandbox_res.exit_code, timed_out

    def get_telemetry(self) -> dict[str, Any]:
        return {**self.telemetry, "docker_available": self._docker_ok, "prefer_docker": self.prefer_docker}


# Global governed terminal engine, bound to the active scope guard.
def _build_default_engine() -> TerminalEngine:
    try:
        from backend.core.config import settings
        prefer_docker = bool(getattr(settings, "TERMINAL_PREFER_DOCKER", True))
        image = getattr(settings, "SANDBOX_IMAGE", None)
    except Exception:
        prefer_docker, image = True, None
    return TerminalEngine(scope=scope_guard, prefer_docker=prefer_docker, docker_image=image)


terminal_engine = _build_default_engine()


def register_terminal_tool() -> None:
    """Register terminal execution as a governed tool (Architecture §8, §24).

    The handler runs only allowlisted recon binaries (argv arrays) through the
    governed pipeline: guardrails -> scope -> backend -> watchdog. It is NOT a
    generic exploitation shell.
    """
    try:
        from backend.core.tool_registry import ToolDefinition, tool_registry
        from backend.core.tool_types import ToolType
    except Exception:  # pragma: no cover - registry optional at import time
        return

    if tool_registry.exists("terminal"):
        return

    async def _handler(argv, scan_id: str = "GLOBAL", agent: str = "terminal",
                       timeout_seconds: int = 180, **kwargs):
        result = await terminal_engine.run(
            argv, scan_id=scan_id, agent=agent, timeout_seconds=timeout_seconds, **kwargs
        )
        return result.to_dict()

    tool_registry.register(ToolDefinition(
        name="terminal",
        description=(
            "Execute an allowlisted recon CLI tool as an argv array through the "
            "governed Terminal Engine (scope-checked, sandboxed, audited). "
            "Recon only — not an exploitation shell."
        ),
        parameters={
            "type": "object",
            "properties": {
                "argv": {"type": "array", "items": {"type": "string"},
                          "description": "Command as an argv array (no shell strings)."},
                "scan_id": {"type": "string"},
                "agent": {"type": "string"},
                "timeout_seconds": {"type": "integer"},
            },
            "required": ["argv"],
        },
        handler=_handler,
        tool_type=ToolType.ENVIRONMENT,
        requires_approval=False,
        mutates_state=False,
        store_result=True,
    ))


# Register on import so the tool is discoverable by agents.
register_terminal_tool()
