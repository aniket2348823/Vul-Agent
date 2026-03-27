from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
# Import your orchestrator instance class to access static registry
from backend.core.orchestrator import HiveOrchestrator
from backend.core.protocol import JobPacket, TaskTarget, ModuleConfig, AgentID
from backend.api.socket_manager import manager # UI Broadcast
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine

router = APIRouter()
cortex = CortexEngine()

class ThreatPayload(BaseModel):
    agent_id: str  # "THETA" or "IOTA"
    content: Dict[str, Any]  # The DOM data or Text
    url: str
    session_id: Optional[str] = "anonymous-session" # V6: Session Persistence

@router.post("/analyze")
async def analyze_threat(payload: ThreatPayload):
    """
    The Single Entry Point for the Extension Defense Shield.
    """
    # 1. Lookup Agent
    agent = HiveOrchestrator.active_agents.get(payload.agent_id)
    
    if not agent:
        # Better to return IDLE to avoid extension error spam if backend is not currently scanning
        return {
            "verdict": "IDLE",
            "reason": "Antigravity Hive is in Standby Mode",
            "risk_score": 0
        }

    # 2. Create a Job Packet for the Agent
    # We wrap the extension data into a format the Agent understands (JobPacket)
    # Mapping "THETA" -> AgentID.THETA
    agent_enum = AgentID.THETA if payload.agent_id == "THETA" else AgentID.IOTA
    
    # 2.5 Quick Check / Routing (Optional Optimization)
    # In a real system, we might bypass the full Agent Queue for sync blocking,
    # but for this architecture, we push to Swarm.
    
    packet = JobPacket(
        target=TaskTarget(
            url=payload.url,
            payload=payload.content # Passing content here
        ),
        config=ModuleConfig(
            module_id="defense_scan",
            agent_id=agent_enum,
            aggression=1,
            ai_mode=False,
            session_id=payload.session_id # V6: Persist Session Context
        )
    )
    
    # 3. Execute the Agent Logic (Theta or Iota)
    # We call execute_task directly to get result immediately (synchronous wait for async func)
    result = await agent.execute_task(packet)
    
    # 4. Return Verdict to Extension (BLOCK or ALLOW)
    reason = None
    if result.vulnerabilities:
        reason = result.vulnerabilities[0].description
    
    # HYBRID AI: Dynamic risk scoring instead of hardcoded 95/10
    if result.vulnerabilities:
        context = f"{payload.url} {reason or ''}"
        risk_assessment = cortex.assess_contextual_risk(context)
        risk_score = risk_assessment.get("risk_score", 95)
    else:
        risk_score = 10

    verdict = "BLOCK" if result.status == "THREAT_BLOCKED" else "ALLOW"
    
    # BROADCAST TO UI (Real-time Feedback)
    await manager.broadcast({
        "type": "LIVE_THREAT_LOG",
        "source": payload.agent_id,
        "payload": {
            "timestamp": result.timestamp,
            "agent": payload.agent_id,
            "threat_type": reason or "UI_ANOMALY",
            "url": payload.url,
            "severity": "CRITICAL" if verdict == "BLOCK" else "LOW",
            "risk_score": risk_score,
            "verdict": verdict
        }
    })

    return {
        "verdict": verdict,
        "reason": reason,
        "risk_score": risk_score
    }
