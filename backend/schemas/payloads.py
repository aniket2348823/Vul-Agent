from pydantic import BaseModel
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
    concurrency: int = 50
    strategy: str = "LAST_BYTE_SYNC"

class AttackPayload(BaseModel):
    target_url: str 
    method: str
    headers: Dict[str, str]
    body: Optional[str] = ""
    velocity: int = 50 # Legacy mapping
    concurrency: int = 50 # New Performance Control
    rps: int = 100 # New Performance Control (Requests Per Second)
    modules: list[str] = []
    filters: list[str] = []
    duration: Optional[int] = 600  # Default 10 mins

