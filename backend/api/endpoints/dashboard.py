from fastapi import APIRouter
import random
import json
import os
import pyotp
import qrcode
import io
import base64
from typing import List, Dict
from pydantic import BaseModel
from backend.core.state import stats_db_manager

router = APIRouter()

# --- PERSISTENCE HELPERS ---
CONFIG_FILE = "user_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"secret": None, "enabled": False}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:return {"secret": None, "enabled": False}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

# --- IN-MEMORY SESSION STATE ---
# In a real app, use a proper session manager (e.g., redis, secure cookie)
# For this local tool, a simple global variable works for the single active user session.
# We reset this to False on server restart, forcing re-login if 2FA is enabled.
session_state = {
    "authenticated": False
}

# --- DATA MODELS ---

class SettingsUpdate(BaseModel):
    pass 

class Verify2FA(BaseModel):
    token: str

class LoginRequest(BaseModel):
    token: str

# --- ENDPOINTS ---

@router.get("/stats")
async def get_dashboard_stats():
    # Only allow stats if authenticated (or if 2FA is disabled)
    config = load_config()
    if config["enabled"] and not session_state["authenticated"]:
         return {"error": "Unauthorized", "metrics": {}, "graph_data": [], "recent_activity": []}

    recent = []
    historical_threats = []
    
    stats = stats_db_manager.get_stats()
    scans = stats.get("scans", [])
    
    for s in scans:
        # Logic for 'recent' summaries
        recent.append({
            "text": f"Scan {s['status']}: {s['name']}",
            "time": s["timestamp"],
            "type": "info" if s["status"] == "Completed" else "critical"
        })
        # Logic for pre-populating threat_feed
        for r in s.get("results", []):
            payload = r.get("payload", {})
            historical_threats.append({
                "timestamp": str(r.get("timestamp", "")).split()[-1][:8] if " " in str(r.get("timestamp", "")) else "History",
                "agent": r.get("source", "agent_prism"),
                "threat_type": payload.get("type", "VULNERABILITY"),
                "url": payload.get("url", s.get("name", "Unknown")),
                "severity": payload.get("severity", "MEDIUM").upper(),
                "risk_score": payload.get("data", {}).get("risk_score", 50)
            })

    return {
        "metrics": {
            "total_scans": len(scans),
            "active_scans": sum(1 for s in scans if s["status"] == "Running"),
            "vulnerabilities": stats.get("vulnerabilities", 0),
            "critical": stats.get("critical", 0)
        },
        "graph_data": stats.get("history", []),
        "recent_activity": recent[:5],
        "historical_threats": historical_threats[:60]
    }

@router.get("/scans")
async def get_scan_list():
    config = load_config()
    if config["enabled"] and not session_state["authenticated"]:
        return []
    return stats_db_manager.get_stats().get("scans", [])

@router.post("/settings")
async def update_settings(settings: SettingsUpdate):
    return {"status": "success", "message": "Settings updated."}

@router.get("/settings")
async def get_settings():
    config = load_config()
    return {
        "2fa_enabled": config["enabled"]
    }

# --- 2FA MANAGEMENT ---

@router.post("/settings/2fa/generate")
async def generate_2fa():
    secret = pyotp.random_base32()
    # We DON'T save to config yet, only when verified. 
    # But we need to store it temporarily for the verify step.
    # For simplicity, we'll save it to config but with enabled=False
    config = load_config()
    config["secret"] = secret
    config["enabled"] = False 
    save_config(config)
    
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name="Agent Omega", issuer_name="Antigravity")
    
    img = qrcode.make(provisioning_uri)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{img_str}"
    }

@router.post("/settings/2fa/verify")
async def verify_2fa(payload: Verify2FA):
    config = load_config()
    if not config["secret"]:
        return {"status": "error", "message": "No secret generated."}
        
    totp = pyotp.TOTP(config["secret"])
    if totp.verify(payload.token):
        config["enabled"] = True
        save_config(config)
        session_state["authenticated"] = True # Auto-login on setup
        return {"status": "success", "message": "2FA Enabled Successfully."}
    else:
        return {"status": "error", "message": "Invalid Token."}

# --- AUTHENTICATION FLOW ---

@router.get("/auth/status")
async def auth_status():
    config = load_config()
    return {
        "2fa_required": config["enabled"],
        "authenticated": session_state["authenticated"]
    }

@router.post("/auth/login")
async def login(payload: LoginRequest):
    config = load_config()
    if not config["enabled"]:
        return {"status": "success", "message": "No 2FA needed."}
        
    totp = pyotp.TOTP(config["secret"])
    if totp.verify(payload.token):
        session_state["authenticated"] = True
        return {"status": "success", "message": "Authenticated."}
    else:
        # Prevent brute force (simple delay could be added here)
        return {"status": "error", "message": "Invalid 2FA Code."}

@router.post("/auth/logout")
async def logout():
    session_state["authenticated"] = False
    return {"status": "success"}

@router.post("/reset")
async def reset_dashboard():
    from backend.core.state import stats_db_manager
    stats_db_manager.wipe_scans()
    return {"status": "success", "message": "All historical scans have been wiped."}
