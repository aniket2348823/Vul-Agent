"""
Scans API (Architecture §22)
================================================================================
The §22 primary scan API surface, added additively (existing /api/attack/fire,
/api/recon, etc. are unchanged — Architecture §13.4 frontend-contract rule).

Endpoints (Architecture §22):
  POST   /api/scans                       create a scan
  GET    /api/scans                       list scans
  GET    /api/scans/{scan_id}             scan detail
  POST   /api/scans/{scan_id}/pause       pause
  POST   /api/scans/{scan_id}/resume      resume
  POST   /api/scans/{scan_id}/cancel      cancel
  GET    /api/scans/{scan_id}/events      event transcript
  GET    /api/scans/{scan_id}/findings    findings
  GET    /api/scans/{scan_id}/graph       knowledge-graph stats/snapshot
  GET    /api/scans/{scan_id}/report      report file/links
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.core.state import stats_db_manager

router = APIRouter()


class CreateScanRequest(BaseModel):
    target_url: str
    mode: str = "STANDARD"
    modules: list[str] = Field(default_factory=list)
    scan_id: str | None = None


@router.post("")
@router.post("/")
async def create_scan(req: CreateScanRequest, background_tasks: BackgroundTasks):
    """Create + launch a scan (Architecture §22 POST /api/scans)."""
    from backend.core.orchestrator import HiveOrchestrator

    scan_id = req.scan_id or f"HIVE-V5-{uuid.uuid4().hex[:10]}"
    target_config = {"url": req.target_url, "mode": req.mode, "modules": req.modules}
    scan_record = {
        "id": scan_id, "scan_id": scan_id, "target_url": req.target_url,
        "scope": req.target_url, "status": "Initializing", "modules": req.modules,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "results": [], "events": [],
    }
    await stats_db_manager.register_scan(scan_record)

    async def _run():
        try:
            await HiveOrchestrator.bootstrap_hive(target_config, scan_id)
        except Exception as exc:  # pragma: no cover - background
            stats_db_manager.update_scan_status(scan_id, "Failed")
            import logging
            logging.getLogger("api.scans").error("scan %s failed: %s", scan_id, exc)

    background_tasks.add_task(_run)
    return JSONResponse(status_code=202, content={"scan_id": scan_id, "status": "accepted"})


@router.get("")
@router.get("/")
async def list_scans():
    stats = stats_db_manager.get_stats()
    scans = stats.get("scans", [])
    return {"scans": [{"id": s.get("id"), "target": s.get("target_url") or s.get("scope"),
                       "status": s.get("status"), "report_ready": s.get("report_ready", False)}
                      for s in scans], "count": len(scans)}


@router.get("/{scan_id}")
async def get_scan(scan_id: str):
    scan = stats_db_manager.get_scan_state(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Unknown scan_id")
    return scan


def _signal(scan_id: str, signal: str) -> dict:
    """Publish a CONTROL_SIGNAL to the scan's context if the hive is live."""
    delivered = False
    try:
        from backend.core.orchestrator import HiveOrchestrator
        import asyncio
        from backend.core.hive import EventType, HiveEvent
        # Find any active agent's bus to publish the control signal.
        agents = getattr(HiveOrchestrator, "active_agents", {}) or {}
        bus = None
        for a in agents.values():
            bus = getattr(a, "bus", None)
            if bus is not None:
                break
        if bus is not None:
            asyncio.create_task(bus.publish(HiveEvent(
                type=EventType.CONTROL_SIGNAL, source="api.scans", scan_id=scan_id,
                payload={"signal": signal})))
            delivered = True
    except Exception:
        delivered = False
    return {"scan_id": scan_id, "signal": signal, "delivered": delivered}


@router.post("/{scan_id}/pause")
async def pause_scan(scan_id: str):
    stats_db_manager.update_scan_status(scan_id, "Paused")
    return _signal(scan_id, "THROTTLE")


@router.post("/{scan_id}/resume")
async def resume_scan(scan_id: str):
    stats_db_manager.update_scan_status(scan_id, "Running")
    return _signal(scan_id, "RESUME")


@router.post("/{scan_id}/cancel")
async def cancel_scan(scan_id: str):
    stats_db_manager.update_scan_status(scan_id, "Cancelled")
    return _signal(scan_id, "ABORT")


@router.get("/{scan_id}/events")
async def scan_events(scan_id: str, limit: int = 500):
    scan = stats_db_manager.get_scan_state(scan_id) or {}
    events = scan.get("events", [])
    return {"scan_id": scan_id, "events": events[-limit:], "count": len(events)}


@router.get("/{scan_id}/findings")
async def scan_findings(scan_id: str):
    scan = stats_db_manager.get_scan_state(scan_id) or {}
    findings = scan.get("results") or scan.get("findings") or []
    return {"scan_id": scan_id, "findings": findings, "count": len(findings)}


@router.get("/{scan_id}/graph")
async def scan_graph(scan_id: str):
    """Knowledge-graph stats for the scan (Architecture §12, §22)."""
    try:
        from backend.core.unified_knowledge_graph import unified_knowledge_graph
        return unified_knowledge_graph.stats()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/{scan_id}/report")
async def scan_report(scan_id: str):
    """Return generated report links for the scan (Architecture §18, §22)."""
    import os
    from backend.core.config import settings
    reports_dir = settings.REPORTS_DIR
    pdf = f"Scan_Report_{scan_id}.pdf"
    findings_dir = os.path.join(reports_dir, scan_id)
    outputs = {}
    if os.path.exists(os.path.join(reports_dir, pdf)):
        outputs["pdf"] = f"/api/reports/download/{pdf}"
    if os.path.isdir(findings_dir):
        for f in os.listdir(findings_dir):
            outputs[f.rsplit(".", 1)[-1]] = os.path.join(findings_dir, f)
    return {"scan_id": scan_id, "reports": outputs,
            "export_endpoint": f"/api/reports/findings/{scan_id}/export"}
