from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.approval import approval_store
from backend.core.unified_knowledge_graph import knowledge_graph
from backend.core.telemetry import telemetry
from backend.core.tool_executor import tool_executor
from backend.core.tool_registry import tool_registry

router = APIRouter(prefix="/runtime", tags=["runtime"])


class ToolRunRequest(BaseModel):
    tool_name: str
    args: dict = Field(default_factory=dict)
    scan_id: str = "GLOBAL"
    agent: str = "api"
    approval_id: str | None = None


@router.get("/tools")
async def list_tools():
    return {"tools": tool_registry.schemas()}


@router.post("/tools/run")
async def run_tool(payload: ToolRunRequest):
    result = await tool_executor.execute(
        payload.tool_name,
        payload.args,
        scan_id=payload.scan_id,
        agent=payload.agent,
        approval_id=payload.approval_id,
    )
    return result.__dict__


@router.get("/approvals")
async def list_approvals(scan_id: str | None = None):
    return {"approvals": [ticket.__dict__ for ticket in approval_store.pending(scan_id)]}


@router.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str):
    try:
        return approval_store.approve(approval_id).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown approval id")


@router.post("/approvals/{approval_id}/deny")
async def deny(approval_id: str):
    try:
        return approval_store.deny(approval_id).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown approval id")


@router.get("/graph")
async def graph_stats():
    return knowledge_graph.stats()


@router.get("/telemetry")
async def recent_telemetry(limit: int = 100):
    return {"spans": telemetry.recent(limit)}


@router.get("/self-improvement")
async def self_improvement_audit(limit: int = 50):
    """Auditable agent-evolution changes + routing weights (Architecture §13.4, §15.1)."""
    from backend.core.self_improvement_engine import self_improvement_engine
    return {
        "stats": self_improvement_engine.stats(),
        "audit": self_improvement_engine.get_audit(limit=limit),
        "profiles": {a: p.to_dict() for a, p in self_improvement_engine.profiles.items()},
    }


@router.get("/scope")
async def scope_status():
    """Current engagement scope + authorization state (Architecture §9, §10)."""
    from backend.core.scope import scope_guard
    return scope_guard.to_dict()


@router.get("/terminal")
async def terminal_status():
    """Governed Terminal Engine telemetry (Architecture §8)."""
    from backend.core.terminal_engine import terminal_engine
    return terminal_engine.get_telemetry()


@router.get("/recovery")
async def recovery_status():
    """Recovery engine metrics: healing + error recovery (Architecture §14)."""
    from backend.core.recovery_engine import recovery_engine
    return recovery_engine.get_metrics()
