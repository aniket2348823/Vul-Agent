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
    headers: Dict[str, str] = {}
    body: Optional[str] = ""
    velocity: int = 50
    concurrency: int = 50
    rps: int = 100
    modules: list[str] = []
    filters: list[str] = []
    duration: Optional[int] = 600


