from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
# Import your orchestrator instance class to access static registry
from backend.core.orchestrator import HiveOrchestrator
from backend.core.protocol import JobPacket, TaskTarget, ModuleConfig, AgentID
from backend.api.socket_manager import manager # UI Broadcast
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

router = APIRouter()
cortex = get_cortex_engine()

class ThreatPayload(BaseModel):
    agent_id: str  # "agent_prism" or "agent_chi"
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
        from backend.core.hive import DistributedEventBus, EventBus
        # Use an ephemeral bus for independent analysis
        try:
            # We attempt to use the distributed bus first for shared state
            ephemeral_bus = DistributedEventBus("redis://localhost:6379")
        except Exception:
            # V6 OMEGA HARDENING: Fall back to local bus if Redis is offline
            ephemeral_bus = EventBus()
            
        if payload.agent_id == "agent_prism":
            from backend.agents.prism import AgentPrism
            agent = AgentPrism(ephemeral_bus)
        elif payload.agent_id == "agent_chi":
            from backend.agents.chi import AgentChi
            agent = AgentChi(ephemeral_bus)
        else:
            return {
                "verdict": "IDLE",
                "reason": "Antigravity Hive is in Standby Mode",
                "risk_score": 0
            }

    # 2. Create a Job Packet for the Agent
    # We wrap the extension data into a format the Agent understands (JobPacket)
    # Mapping "agent_prism" -> AgentID.PRISM
    agent_enum = AgentID.PRISM if payload.agent_id == "agent_prism" else AgentID.CHI
    
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
    
    # 3. Execute the Agent Logic (Prism or Chi)
    # We call execute_task directly to get result immediately (synchronous wait for async func)
    result = await agent.execute_task(packet)
    
    # 4. Return Verdict to Extension (BLOCK or ALLOW)
    reason = None
    if result.vulnerabilities:
        reason = result.vulnerabilities[0].description
    
    # HYBRID AI: Dynamic risk scoring instead of hardcoded 95/10
    if result.vulnerabilities:
        # V6 REFINEMENT: Fix TypeError and handle integer return value
        risk_score = await cortex.assess_contextual_risk(
            threat_type=reason or "UI_ANOMALY", 
            target_url=payload.url, 
            context=payload.content
        )
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
