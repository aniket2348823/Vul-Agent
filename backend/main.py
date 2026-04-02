import asyncio
import argparse
import signal
import sys
import uuid
import os
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Vul Agent Core Imports
from backend.core.config import settings, ConfigManager
from backend.core.orchestrator import HiveOrchestrator, MasterNode, WorkerNode
from backend.api.socket_manager import manager
from backend.core.state import stats_db_manager
from backend.api.endpoints import recon, attack, reports, dashboard, ai
from backend.api import defense

# FIX: Windows charmap encoding crash
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*50)
    print("VUL AGENT: UNIFIED LIFECYCLE START")
    print("="*50)
    
    # Pillar Initiation (GSD, Ralph, TestSprite)
    print("[PILLAR] Activating Governance Frameworks...")
    
    await manager.broadcast({
        "type": "LIFECYCLE_EVENT",
        "payload": {"state": "ACTIVE", "mode": "Unified"}
    })
    
    try:
        yield
    finally:
        print("[LIFECYCLE] Shutting down background tasks...")
        await manager.stop_tasks()
        print("[LIFECYCLE] Shutdown complete.")

app = FastAPI(title="Vulagent Scanner", lifespan=lifespan)

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
app.include_router(defense.router, prefix="/api/defense", tags=["Defense"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])

@app.websocket("/stream")
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket, client_type: str = Query("ui")):
    await manager.connect(websocket, client_type)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- INTEGRATED CLUSTER ORCHESTRATOR ---

class DistributedAttackCluster:
    """Orchestrates the lifecycle of the distributed cluster components."""
    def __init__(self, mode: str):
        self.mode = mode
        self.config = ConfigManager()
        self.running = False
        self.master_node: Optional[MasterNode] = None
        self.worker_node: Optional[WorkerNode] = None
        
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (ValueError, NotImplementedError):
            pass
    
    def _signal_handler(self, signum, frame):
        print(f"🛑 Received signal {signum}, initiating clean cluster extraction...")
        self.running = False
    
    async def start_master(self):
        try:
            self.master_node = MasterNode(
                self.config.redis.url,
                self.config.supabase.url,
                self.config.supabase.key
            )
            self.running = True
            print("📡 VUL AGENT: Master Node Activated.")
            await self.master_node.start()
        except Exception as e:
            print(f"❌ Master start error: {e}")
            raise
    
    async def start_worker(self, worker_id: Optional[str] = None):
        try:
            worker_id = worker_id or self.config.worker.worker_id or f"worker-{uuid.uuid4().hex[:6]}"
            self.worker_node = WorkerNode(
                worker_id,
                self.config.worker.specialty,
                self.config.redis.url,
                self.config.supabase.url,
                self.config.supabase.key
            )
            self.running = True
            print(f"🦾 VUL AGENT: Worker Node Activated ({worker_id})")
            await self.worker_node.start()
        except Exception as e:
            print(f"❌ Worker start error: {e}")
            raise

    async def start_cluster(self, num_workers: int = 5):
        master_task = asyncio.create_task(self.start_master())
        await asyncio.sleep(2)
        worker_tasks = []
        for i in range(num_workers):
            wid = f"worker-{i+1}-{uuid.uuid4().hex[:4]}"
            worker_tasks.append(asyncio.create_task(self.start_worker(wid)))
            await asyncio.sleep(0.5)
        print(f"🔗 Cluster Handshake: 1 Master + {num_workers} Workers Linked.")
        await asyncio.gather(master_task, *worker_tasks)

# --- EXECUTION KERNEL ---

async def vulagent_serve(args):
    if args.mode == "serve":
        print(f"🚀 Launching Vul Agent API Gateway on {args.host}:{args.port}")
        config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        cluster = DistributedAttackCluster(args.mode)
        try:
            if args.mode == "master":
                await cluster.start_master()
            elif args.mode == "worker":
                await cluster.start_worker(args.worker_id)
            elif args.mode == "cluster":
                await cluster.start_cluster(args.num_workers)
        except Exception as e:
            print(f"🚨 Cluster Hard Crash: {e}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vul Agent: Unified Entry Point")
    parser.add_argument("--mode", choices=["serve", "master", "worker", "cluster"], default="serve", help="Execution mode.")
    parser.add_argument("--host", default="127.0.0.1", help="API Host.")
    parser.add_argument("--port", type=int, default=8000, help="API Port.")
    parser.add_argument("--num-workers", type=int, default=3, help="Cluster worker count.")
    parser.add_argument("--worker-id", help="Override worker ID.")
    
    args = parser.parse_args()
    try:
        asyncio.run(vulagent_serve(args))
    except KeyboardInterrupt:
        print("\n[VUL AGENT] Service shutdown by user.")
