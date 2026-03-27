from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from backend.ai.cortex import CortexEngine
from backend.core.orchestrator import HiveOrchestrator

# Initialize Router
router = APIRouter()
brain = CortexEngine()

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
