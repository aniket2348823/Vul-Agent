from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.orchestrator import HiveOrchestrator

# Initialize Router
router = APIRouter()
brain = get_cortex_engine()

class MutationRequest(BaseModel):
    url: str
    method: str
    headers: Dict[str, str] = {}
    body: Optional[Any] = {} 
    velocity: Optional[int] = 50
    # New Config Fields matching Frontend
    interception_filters: Optional[List[str]] = [] 
    logic_vectors: Optional[List[Dict[str, Any]]] = []

@router.post("/mutate")
async def generate_mutations(payload: MutationRequest):
    """
    Trigger AI Payload suggestions manually.
    """
    base_request = {
        "url": payload.url,
        "method": payload.method,
        "body": payload.body
    }
    variants = brain.synthesize_payloads(base_request)
    return {"status": "success", "variants": variants}

@router.post("/autonomous/engage")
async def engage_autonomous(payload: MutationRequest, background_tasks: BackgroundTasks):
    """
    Full Auto Mode: Bootstraps the Hive Mind.
    """
    scan_id = "HIVE-" + payload.url.replace("https://", "").replace("http://", "")[:10]
    
    # Pass full payload to the Hive Orchestrator
    background_tasks.add_task(HiveOrchestrator.bootstrap_hive, payload.model_dump(), scan_id)
    
    return {
        "status": "launched", 
        "message": "Hive Mind Swarm Activated",
        "scan_id": scan_id 
    }

@router.get("/status")
async def get_ai_status():
    """
    Returns AI Core health, LLM metrics, and fallback state.
    """
    # Defensive access to telemetry
    telemetry = brain._telemetry if hasattr(brain, "_telemetry") else {}
    
    return {
        "core_status": {
            "gi5": "online" if getattr(brain, "_gi5_available", False) else "error",
            "ollama": "standby",
            "openrouter": "active"
        },
        "llm_calls": telemetry.get("llm_calls", 0),
        "circuit_breaker_trips": telemetry.get("circuit_breaker_trips", 0),
        "circuit_breaker_tripped": telemetry.get("circuit_breaker_trips", 0) > 0,
        "agent_capabilities": ["singularity", "recon", "attack", "defense"],
        "fallback": "OpenRouter" if getattr(brain, "_gi5_available", False) else "GI5_only"
    }
