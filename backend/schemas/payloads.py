from pydantic import BaseModel, StrictInt
from typing import Dict, Optional, Any

class ReconPayload(BaseModel):
    url: str
    method: str
    headers: Dict[str, str]
    body: Optional[Any] = None
    timestamp: float

class TargetConfig(BaseModel):
    url: str
    method: str
    headers: Dict[str, str] = {}
    body: Optional[str] = ""

class AttackConfig(BaseModel):
    concurrency: StrictInt = 50
    strategy: str = "LAST_BYTE_SYNC"

class AttackPayload(BaseModel):
    target_url: str 
    method: str
    headers: Dict[str, str] = {}
    body: Optional[str] = ""
    velocity: StrictInt = 50 # Legacy mapping
    concurrency: StrictInt = 50 # New Performance Control
    rps: StrictInt = 100 # New Performance Control (Requests Per Second)
    modules: list[str] = []
    filters: list[str] = []
    duration: Optional[StrictInt] = 600  # Default 10 mins

