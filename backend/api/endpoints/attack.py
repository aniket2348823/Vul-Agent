from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.schemas.payloads import AttackPayload
from backend.core.orchestrator import HiveOrchestrator
from backend.api.socket_manager import manager
from datetime import datetime
from urllib.parse import urlparse
import uuid
import re
from backend.core.state import stats_db

router = APIRouter()

# --- INPUT VALIDATION: URL ALLOWLIST ---
ALLOWED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "test-env.local",
    "host.docker.internal",
}
ALLOWED_PRIVATE_RANGES = [
    re.compile(r"^10\."),           # 10.x.x.x
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[01])\."),  # 172.16-31.x.x
    re.compile(r"^192\.168\."),     # 192.168.x.x
]
BLOCKED_PATTERNS = [
    re.compile(r"169\.254\.169\.254"),  # AWS metadata
    re.compile(r"metadata\.google\.internal"),  # GCP metadata
    re.compile(r"^file://", re.I),
    re.compile(r"^ftp://", re.I),
]

def validate_target_url(url: str) -> tuple[bool, str]:
    """Validates the target URL against the allowlist. Returns (is_valid, reason)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Malformed URL"

    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid scheme '{parsed.scheme}'. Only HTTP/HTTPS allowed."

    hostname = parsed.hostname or ""
    
    # Check blocked patterns first
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(url):
            return False, f"Target URL matches blocked pattern: {pattern.pattern}"

    # Allow explicitly whitelisted hosts
    if hostname in ALLOWED_HOSTS:
        return True, "OK"

    # Allow private IP ranges
    for pattern in ALLOWED_PRIVATE_RANGES:
        if pattern.match(hostname):
            return True, "OK"

    # Allow any hostname with a port (likely a local service)
    if parsed.port and parsed.port != 80 and parsed.port != 443:
        return True, "OK"

    # Reject everything else (public domains)
    return False, f"Target '{hostname}' is not in the allowed scope. Add it to ALLOWED_HOSTS or use a private IP."


@router.post("/fire")
async def fire_attack(payload: AttackPayload, background_tasks: BackgroundTasks):
    """
    Triggers the Antigravity V5 Singularity Swarm.
    Replaces legacy Gatekeeper Engine.
    """
    # INPUT VALIDATION: Reject out-of-scope targets
    is_valid, reason = validate_target_url(payload.target_url)
    if not is_valid:
        raise HTTPException(status_code=422, detail=f"Target URL rejected: {reason}")

    scan_id = str(uuid.uuid4())
    
    import json
    parsed_body = {}
    if payload.body:
        try:
            parsed_body = json.loads(payload.body)
        except Exception:
            parsed_body = payload.body # Fallback if not JSON string

    target_config = {
        "url": payload.target_url,
        "method": payload.method,
        "headers": payload.headers,
        "payload": parsed_body,
        "velocity": payload.velocity,
        "concurrency": payload.concurrency, # Performance Bound
        "rps": payload.rps, # Requests Per Second Bound
        "modules": payload.modules,
        "filters": payload.filters,
        "duration": payload.duration
    }

    # 1.5 ATOMIC LOCKING (Prevent Race Conditions - TC020)
    from backend.core.database import db_manager
    await db_manager.initialize()
    if db_manager.redis:
        lock_key = f"scan_lock:{payload.target_url}"
        locked = await db_manager.redis.set(lock_key, "LOCKED", nx=True, ex=10) # 10s cooldown
        if not locked:
            raise HTTPException(status_code=429, detail="A scan for this target is already initializing.")
    elif not hasattr(db_manager, "_local_locks"):
        db_manager._local_locks = set()
    elif payload.target_url in db_manager._local_locks:
        raise HTTPException(status_code=429, detail="A scan for this target is already initializing.")
    else:
        db_manager._local_locks.add(payload.target_url)


    # We do a minimal placeholder here to ensure immediate UI feedback
    # 2. Initial DB Registration (Sync)
    # Use Manager to ensure persistence to disk immediately
    from backend.core.state import stats_db_manager
    start_time = datetime.now()
    scan_record = {
        "id": scan_id,
        "status": "Initializing",
        "name": target_config['url'],
        "scope": target_config['url'],
        "modules": target_config['modules'] if target_config['modules'] else ["Singularity V5"],
        "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": []
    }
    # [FATAL BUG FIX: V6-OMEGA] register_scan is an async def and MUST be awaited
    await stats_db_manager.register_scan(scan_record)
    
    # 3. Launch The Hive (Background Task)
    # The Orchestrator manages the entire lifecycle (Agents, EventBus, Reporting)
    background_tasks.add_task(HiveOrchestrator.bootstrap_hive, target_config, scan_id)
    
    # 4. Immediate Response
    return {
        "status": "Swarm Online",
        "scan_id": scan_id,
        "message": "The Singularity has been unleashed. Monitor the 'Live Graph' for real-time telemetry."
    }


# --- PROBLEM 13 FIX: Attack Replay Mechanism ---

@router.post("/replay/{vuln_id}")
async def replay_attack(vuln_id: str, background_tasks: BackgroundTasks):
    """
    Re-run a specific attack against a confirmed vulnerability to verify if a fix was applied.
    Avoids re-running the entire scan.
    """
    import asyncio
    import time

    from backend.core.state import stats_db_manager

    vuln = await stats_db_manager.find_vulnerability(vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail=f"Vulnerability '{vuln_id}' not found in any scan.")

    replay_config = {
        "url": vuln.get("url", ""),
        "method": vuln.get("method", "GET"),
        "headers": vuln.get("headers", {}),
        "payload": vuln.get("payload", ""),
        "modules": [vuln.get("attack_type", vuln.get("type", ""))],
        "velocity": 5,
        "concurrency": 1,
        "rps": 10,
        "filters": [],
        "duration": 60
    }

    replay_scan_id = f"replay_{vuln_id[:8]}_{int(time.time())}"

    # Register the replay scan
    start_time = datetime.now()
    replay_record = {
        "id": replay_scan_id,
        "status": "Initializing",
        "name": f"REPLAY: {vuln.get('type', 'Unknown')} @ {vuln.get('url', 'Unknown')}",
        "scope": replay_config["url"],
        "modules": replay_config["modules"],
        "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [],
        "replay_of": vuln_id
    }
    await stats_db_manager.register_scan(replay_record)

    # Launch replay in background
    background_tasks.add_task(HiveOrchestrator.bootstrap_hive, replay_config, replay_scan_id)

    return {
        "status": "Replay initiated",
        "replay_scan_id": replay_scan_id,
        "original_vuln_id": vuln_id,
        "target": replay_config["url"],
        "module": replay_config["modules"]
    }
