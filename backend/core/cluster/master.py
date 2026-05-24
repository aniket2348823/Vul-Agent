"""
XYTHERION COMMAND MATRIX (MASTER NODE)
Role: Central task coordination and worker management for the distributed cluster.
Extracted from orchestrator.py for clean architecture.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from backend.core.database import db_manager
from backend.core.graph_engine import GraphEngine
from backend.core.task_manager import TaskManager

logger = logging.getLogger("MasterNode")


class MasterNode:
    """XYTHERION COMMAND MATRIX (MASTER NODE)"""

    def __init__(self, redis_url: str, supabase_url: str, supabase_key: str):
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        from supabase import create_client, Client
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.attack_graph = GraphEngine()
        self._task_manager = TaskManager("MasterNode")

    async def start(self):
        self.active = True
        await self._discover_swarm()
        self._task_manager.create_task(self.monitor_workers(), name="worker_monitor")
        while self.active:
            try:
                task_data = await self.redis_client.brpop("pending_tasks", timeout=5)
                if task_data:
                    task = json.loads(task_data[1])
                    await self.distribute_tasks([task])
            except Exception:
                await asyncio.sleep(1)

    async def _discover_swarm(self):
        try:
            raw_workers = await self.redis_client.hgetall("workers")
            for worker_id, data in raw_workers.items():
                self.workers[worker_id] = json.loads(data)
        except Exception:
            pass

    async def register_worker(self, worker_id: str, specialty: str, capabilities: List[str]):
        worker_info = {
            "id": worker_id, "specialty": specialty, "capabilities": capabilities,
            "status": "active", "last_heartbeat": datetime.now().isoformat(), "current_tasks": []
        }
        self.workers[worker_id] = worker_info
        await self.redis_client.hset("workers", worker_id, json.dumps(worker_info))

    def select_optimal_worker(self, task: Dict) -> Optional[str]:
        required_type = task.get("worker_requirements", {}).get("type", "hybrid")
        eligible_workers = [
            wid for wid, w in self.workers.items()
            if (w["specialty"] in [required_type, "hybrid"]) and w["status"] == "active"
        ]
        if not eligible_workers:
            return None
        return min(eligible_workers, key=lambda w: len(self.workers[w].get("current_tasks", [])))

    async def distribute_tasks(self, tasks: List[Dict]):
        for task in tasks:
            worker_id = self.select_optimal_worker(task)
            if worker_id:
                await self.redis_client.lpush(f"worker_queue:{worker_id}", json.dumps(task))
                self.workers[worker_id].setdefault("current_tasks", []).append(task["task_id"])
                try:
                    await db_manager.initialize()
                    await db_manager.supabase.table("distributed_tasks").insert({
                        "scan_id": task.get("scan_id", "GLOBAL"),
                        "task_id": task["task_id"],
                        "worker_id": worker_id,
                        "status": "RUNNING",
                        "locked_by": worker_id,
                        "lock_time": datetime.now().isoformat()
                    }).execute()
                except Exception:
                    pass

    async def monitor_workers(self):
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            for wid, w in list(self.workers.items()):
                if now - datetime.fromisoformat(w["last_heartbeat"]) > timedelta(minutes=3):
                    w["status"] = "inactive"
                    await self.reassign_worker_tasks(wid)

    async def reassign_worker_tasks(self, failed_worker_id: str):
        worker = self.workers.get(failed_worker_id)
        if not worker:
            return
        for tid in worker.get("current_tasks", []):
            await self.redis_client.lpush("pending_tasks", json.dumps({"task_id": tid, "retry": True}))
        worker["current_tasks"] = []
