from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class TaskPriority(str, Enum):
    CRITICAL = "CRITICAL" # Immediate execution, overrides locks
    HIGH = "HIGH"         # Active attacks (SQLi, Race Conditions)
    NORMAL = "NORMAL"     # Standard Recon
    LOW = "LOW"           # Background Logging/Archiving

class AgentStatus(str, Enum):
    IDLE = "IDLE"
    WORKING = "WORKING"
    THROTTLED = "THROTTLED"
    SLEEPING = "SLEEPING"

class AgentID(str, Enum):
    OMEGA = "agent_omega"
    ZETA = "agent_zeta"
    ALPHA = "agent_alpha"
    BETA = "agent_beta"
    GAMMA = "agent_gamma"
    SIGMA = "agent_sigma"
    KAPPA = "agent_kappa"
    PRISM = "agent_prism"
    CHI = "agent_chi"

# --- THE JOB PACKET (Input) ---
class ModuleConfig(BaseModel):
    module_id: str          # e.g., "logic_tycoon"
    agent_id: AgentID       # Who owns this? e.g., "agent_gamma"
    aggression: int = Field(5, ge=1, le=10)
    ai_mode: bool = True    # Use advanced AI features?
    session_id: Optional[str] = None # V6: Session Persistence
    params: Dict[str, Any] = Field(default_factory=dict)

class TaskTarget(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict[str, str] = {}
    payload: Optional[Dict[str, Any]] = None

class JobPacket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: TaskPriority = TaskPriority.NORMAL
    target: TaskTarget
    config: ModuleConfig
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# --- THE RESULT PACKET (Output) ---
class Vulnerability(BaseModel):
    name: str
    severity: str # HIGH, MED, LOW
    description: str
    evidence: str # The payload that worked
    remediation: Optional[str] = None # Fix suggestion

class ResultPacket(BaseModel):
    job_id: str
    source_agent: AgentID
    status: str       # SUCCESS, FAILURE, VULN_FOUND
    execution_time_ms: float
    data: Dict[str, Any] # Raw response data
    vulnerabilities: List[Vulnerability] = []
    next_step: Optional[str] = None # Hint for the next agent
    timestamp: datetime = Field(default_factory=datetime.utcnow) # V6: Temporal Tracking
