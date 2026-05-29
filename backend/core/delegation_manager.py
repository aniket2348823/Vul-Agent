"""
Vigilagent Delegation Manager (Architecture §5.5, §5.1.2, §29.13)
================================================================================
The control plane that replaces the flat EventBus as the *agent coordination*
model. The EventBus remains for UI/telemetry/audit (Architecture §5.5).

Pattern (Hermes delegate_tool → §29.13):
  - A parent agent spawns an isolated child agent with:
      * a restricted tool allowlist,
      * its own IterationBudget (independent — cannot drain the parent §5),
      * an isolated context summary (no unrestricted global memory §5),
      * a structured result contract (ResultPacket / ChildResult).
  - When a MasterNode + Redis are available, the child task is enqueued onto the
    worker substrate (worker_queue:{id}) and the result awaited.
  - Otherwise delegation runs in-process.
  - Cancellation propagates to the child subtree.

Routing pattern (Architecture §5.1.2):
  Omega -> Master -> Worker pool -> Specialized agent/task -> Parsed result
        -> Master -> Omega/Graph
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

from backend.core.iteration_budget import IterationBudget, budget_config

logger = logging.getLogger("vigilagent.delegation")

ChildStatus = Literal["completed", "failed", "budget_exhausted", "cancelled", "timeout"]

# A child runner is any coroutine that takes a context dict + budget and returns
# a dict of findings/artifacts/summary. Specialized agents register builders.
ChildRunner = Callable[[dict, IterationBudget], Awaitable[dict]]


@dataclass
class ChildSpec:
    """Specification for a delegated child agent (Architecture §5)."""

    agent_class: str                       # e.g. "ReconChild", "AttackChild"
    objective: str
    tools: list[str] = field(default_factory=list)   # tool allowlist
    budget: int = 50
    context: dict = field(default_factory=dict)       # isolated parent summary
    phase: str = ""
    timeout_s: int = 600
    worker_specialty: str = "hybrid"       # recon|browser|api|network|validation|...

    def to_task(self, scan_id: str, task_id: str) -> dict:
        """Serialize to a worker task packet for the Master substrate."""
        return {
            "task_id": task_id,
            "scan_id": scan_id,
            "agent_class": self.agent_class,
            "objective": self.objective,
            "phase": self.phase,
            "worker_requirements": {"type": self.worker_specialty},
            "config": {
                "tools": self.tools,
                "budget": self.budget,
                "context": self.context,
            },
        }


@dataclass
class ChildResult:
    """Structured child-agent return object (Architecture §5, ResultPacket)."""

    child_id: str
    agent_class: str
    status: ChildStatus
    findings: list[dict] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    summary: str = ""
    budget_used: int = 0
    duration_ms: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "child_id": self.child_id,
            "agent_class": self.agent_class,
            "status": self.status,
            "findings": self.findings,
            "artifacts": self.artifacts,
            "summary": self.summary,
            "budget_used": self.budget_used,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class DelegationManager:
    """Spawns budgeted, isolated child agents and returns structured results."""

    # Registry of in-process child runners keyed by agent_class.
    _runners: dict[str, ChildRunner] = {}

    def __init__(self, bus: Any = None, master: Any = None, *, scan_id: str = "GLOBAL") -> None:
        self.bus = bus
        self.master = master
        self.scan_id = scan_id
        self._active: dict[str, asyncio.Task] = {}
        self.telemetry = {
            "spawned": 0,
            "completed": 0,
            "failed": 0,
            "timeouts": 0,
            "cancelled": 0,
            "budget_exhausted": 0,
        }

    # ── Runner registration (Architecture §5.1.2 worker specialties) ──────────

    @classmethod
    def register_runner(cls, agent_class: str, runner: ChildRunner) -> None:
        cls._runners[agent_class] = runner

    @classmethod
    def has_runner(cls, agent_class: str) -> bool:
        return agent_class in cls._runners

    # ── Spawning ──────────────────────────────────────────────────────────────

    async def spawn(self, spec: ChildSpec, parent_budget: IterationBudget | None = None) -> ChildResult:
        """Spawn a child agent. The child receives an INDEPENDENT budget so it can
        never drain the parent (Architecture §5 budget boundedness)."""
        child_id = f"{spec.agent_class}-{uuid.uuid4().hex[:8]}"
        if parent_budget is not None:
            child_budget = parent_budget.child(spec.budget, label=child_id)
        else:
            child_budget = IterationBudget(spec.budget, label=child_id)

        self.telemetry["spawned"] += 1
        started = time.time()

        # Prefer the distributed substrate when available (Architecture §5.1.2).
        use_worker = self.master is not None and getattr(self.master, "redis_client", None) is not None

        try:
            if use_worker:
                coro = self._run_on_worker(spec, child_id, child_budget)
            else:
                coro = self._run_in_process(spec, child_id, child_budget)

            task = asyncio.ensure_future(coro)
            self._active[child_id] = task
            result = await asyncio.wait_for(task, timeout=spec.timeout_s)
            result.duration_ms = int((time.time() - started) * 1000)
            self._tally(result.status)
            return result
        except asyncio.TimeoutError:
            await self._cancel_child(child_id)
            self.telemetry["timeouts"] += 1
            return ChildResult(child_id, spec.agent_class, "timeout",
                               summary=f"child exceeded timeout {spec.timeout_s}s",
                               duration_ms=int((time.time() - started) * 1000))
        except asyncio.CancelledError:
            await self._cancel_child(child_id)
            self.telemetry["cancelled"] += 1
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Delegation error for %s: %s", child_id, exc)
            self.telemetry["failed"] += 1
            return ChildResult(child_id, spec.agent_class, "failed", error=str(exc),
                               duration_ms=int((time.time() - started) * 1000))
        finally:
            self._active.pop(child_id, None)

    async def spawn_many(self, specs: list[ChildSpec],
                         parent_budget: IterationBudget | None = None) -> list[ChildResult]:
        """Spawn several children concurrently; ordered results (Architecture §29.3
        concurrent tool dispatch with ordered result collection)."""
        results = await asyncio.gather(
            *(self.spawn(spec, parent_budget) for spec in specs),
            return_exceptions=True,
        )
        normalized: list[ChildResult] = []
        for spec, res in zip(specs, results):
            if isinstance(res, ChildResult):
                normalized.append(res)
            else:
                normalized.append(ChildResult(
                    f"{spec.agent_class}-error", spec.agent_class, "failed", error=str(res)))
        return normalized

    # ── In-process execution ───────────────────────────────────────────────────

    async def _run_in_process(self, spec: ChildSpec, child_id: str,
                              budget: IterationBudget) -> ChildResult:
        runner = self._runners.get(spec.agent_class)
        if runner is None:
            return ChildResult(child_id, spec.agent_class, "failed",
                               error=f"no in-process runner registered for {spec.agent_class}")
        if budget.exhausted():
            self.telemetry["budget_exhausted"] += 1
            return ChildResult(child_id, spec.agent_class, "budget_exhausted",
                               summary="child budget exhausted before start")
        try:
            out = await runner(spec.context, budget) or {}
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return ChildResult(child_id, spec.agent_class, "failed", error=str(exc),
                               budget_used=budget.consumed)
        status: ChildStatus = "budget_exhausted" if budget.exhausted() and not out else "completed"
        return ChildResult(
            child_id=child_id,
            agent_class=spec.agent_class,
            status=status,
            findings=list(out.get("findings", [])),
            artifacts=list(out.get("artifacts", [])),
            summary=str(out.get("summary", "")),
            budget_used=budget.consumed,
        )

    # ── Distributed (worker) execution (Architecture §5.1.2) ─────────────────────

    async def _run_on_worker(self, spec: ChildSpec, child_id: str,
                             budget: IterationBudget) -> ChildResult:
        master = self.master
        task = spec.to_task(self.scan_id, child_id)
        result_key = f"delegation_result:{child_id}"
        try:
            await master.distribute_tasks([task])
        except Exception as exc:
            logger.warning("Worker distribute failed (%s); falling back in-process.", exc)
            return await self._run_in_process(spec, child_id, budget)

        # Await result key written by the worker (durable task lease §5.6).
        redis = master.redis_client
        deadline = time.time() + spec.timeout_s
        while time.time() < deadline:
            try:
                raw = await redis.get(result_key)
            except Exception:
                raw = None
            if raw:
                import json
                data = json.loads(raw)
                return ChildResult(
                    child_id=child_id,
                    agent_class=spec.agent_class,
                    status=data.get("status", "completed"),
                    findings=data.get("findings", []),
                    artifacts=data.get("artifacts", []),
                    summary=data.get("summary", ""),
                    budget_used=data.get("budget_used", 0),
                )
            await asyncio.sleep(1.0)
        return ChildResult(child_id, spec.agent_class, "timeout",
                           summary="worker result not received in time")

    # ── Cancellation (Architecture §5 interrupt propagation) ─────────────────────

    async def cancel_all(self) -> None:
        for child_id in list(self._active.keys()):
            await self._cancel_child(child_id)

    async def _cancel_child(self, child_id: str) -> None:
        task = self._active.get(child_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    def _tally(self, status: ChildStatus) -> None:
        if status == "completed":
            self.telemetry["completed"] += 1
        elif status == "failed":
            self.telemetry["failed"] += 1
        elif status == "budget_exhausted":
            self.telemetry["budget_exhausted"] += 1

    def get_telemetry(self) -> dict[str, Any]:
        return dict(self.telemetry)


def make_delegation_manager(bus: Any = None, master: Any = None,
                            scan_id: str = "GLOBAL") -> DelegationManager:
    return DelegationManager(bus=bus, master=master, scan_id=scan_id)
