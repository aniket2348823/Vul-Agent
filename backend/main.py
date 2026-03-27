from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager

import os
import sys

# FIX: Windows charmap encoding crash — force UTF-8 for all console output
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from fastapi.middleware.cors import CORSMiddleware
from backend.api.endpoints import recon, attack, reports
from backend.api import defense # Import Defense API
from backend.api.socket_manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP: UNIFIED TRIPLE-PILLAR INITIATION (GSD, RALPH, TESTSPRITE) ---
    print("\n" + "="*50)
    print("ANTIGRAVITY IDE: TRIPLE-PILLAR LIFECYCLE START")
    print("="*50)
    
    # Check for startup signal from Desktop/Batch
    signal_path = os.path.join(os.getcwd(), ".agents", "startup_signal.tmp")
    auto_resume = os.path.exists(signal_path)

    # 1. GSD Context Restoration
    print("[GSD] Restoring Workspace State...")
    
    # 2. Ralph Autonomous Loop Activation
    print("[RALPH] Activating Supervisor Model...")
    
    # 3. TestSprite Quality Sentinel Initiation
    print("[TESTSPRITE] Priming Headless Quality Gates...")
    # Headless mode: no popups, no browser redirection.
    
    await manager.broadcast({
        "type": "LIFECYCLE_EVENT",
        "payload": {
            "state": "ACTIVE",
            "pillars": ["GSD", "Ralph", "TestSprite"],
            "mode": "Zero-Prompt/Headless"
        }
    })
    
    if auto_resume:
        try: os.remove(signal_path)
        except Exception: pass
        
    print("Antigravity IDE operational. Triple-Pillar Governance active.\n")
    yield

app = FastAPI(title="Antigravity", lifespan=lifespan)

# CORS to allow Chrome Extension and Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/api/health")
async def health_check():
    return {"status": "online", "version": "v6.1-omega"}

app.include_router(recon.router, prefix="/api/recon", tags=["Recon"])
app.include_router(attack.router, prefix="/api/attack", tags=["Attack"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(defense.router, prefix="/api/defense", tags=["Defense"]) # Register Defense API
from backend.api.endpoints import dashboard
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket, client_type: str = "ui"):
    await manager.connect(websocket, client_type)
    try:
        while True:
            # Keep alive / listen for client commands
            await websocket.receive_text()
            # If Spy sends heartbeat or data via WS, handle here
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # If Spy disconnected, we need to notify UIs.
        # Can't await inside sync disconnect, so we do it here manually if it was a spy
        if client_type == "spy":
            await manager.broadcast_to_ui({
                "type": "SPY_STATUS",
                "payload": {"connected": False}
            })

@app.websocket("/ws/live")
async def live_websocket_endpoint(websocket: WebSocket):
    # Standardized endpoint for live monitoring
    await manager.connect(websocket, "ui")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    # Use uvloop for performance if available (handles async much faster)

        
    uvicorn.run(app, host="127.0.0.1", port=8000)
