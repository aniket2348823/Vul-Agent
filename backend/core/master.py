import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import redis
from supabase import create_client, Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Xytherion.Master")

class MasterNode:
    """
    XYTHERION COMMAND MATRIX (MASTER NODE)
    Role: Central coordination of the distributed attack cluster.
    """
    def __init__(self, redis_url: str, supabase_url: str, supabase_key: str):
        # 1. Connection Matrix (Async)
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        self.supabase: Client = create_client(supabase_url, supabase_key)

        
        # 2. Registries
        self.workers: Dict[str, Dict[str, Any]] = {}
        
        # 3. Decision Engine
        from backend.core.graph_engine import GraphEngine
        self.attack_graph = GraphEngine() # Inherit from project standard

    async def start(self):
        """Start the master node lifecycle."""
        logger.info("📡 Xytherion Master Node Starting...")
        self.active = True
        
        # 0. Swarm Discovery (V6-HARDENED)
        # Pull existing workers from Redis to ensure state continuity after restart
        await self._discover_swarm()
        
        # Start background health monitoring
        asyncio.create_task(self.monitor_workers())

        
        # Main reactive orchestration loop
        while self.active:
            try:
                # 1. REACTIVE BLOCKING POP (V6-REALTIME ASYNC)
                task_data = await self.redis_client.brpop("pending_tasks", timeout=5)
                if task_data:
                    task = json.loads(task_data[1])
                    await self.distribute_tasks([task])
            except Exception as e:
                logger.error(f"Master Reactive Loop Failure: {e}")

                await asyncio.sleep(1)


    async def shutdown(self):
        """Graceful release of cluster resources."""
        self.active = False
        logger.info("🛑 Xytherion Master Node Shutting Down...")
        try:
            # 1. Clear Local Worker Registrations on global redis (Async Fix)
            for worker_id in list(self.workers.keys()):
                await self.redis_client.hdel("workers", worker_id)
            
            # 2. Close Clients
            await self.redis_client.close()
        except Exception as e:
            logger.debug(f"Shutdown Cleanup Error: {e}")

    async def _discover_swarm(self):
        """Initial Swarm Discovery: Sync local state with Redis registry on startup."""
        try:
            raw_workers = await self.redis_client.hgetall("workers")
            for worker_id, data in raw_workers.items():
                worker_info = json.loads(data)
                self.workers[worker_id] = worker_info
            logger.info(f"🧬 Swarm Discovery Complete: {len(self.workers)} nodes recovered from registry.")
        except Exception as e:
            logger.error(f"Swarm Discovery Failed: {e}")



    async def register_worker(self, worker_id: str, specialty: str, capabilities: List[str]):
        """Register a new worker node from the swarm."""
        worker_info = {
            "id": worker_id,
            "specialty": specialty,
            "capabilities": capabilities,
            "status": "active",
            "last_heartbeat": datetime.now().isoformat(),
            "current_tasks": []
        }
        self.workers[worker_id] = worker_info
        # Persist status to Redis for cluster discovery (Async Fix)
        await self.redis_client.hset("workers", worker_id, json.dumps(worker_info))
        logger.info(f"🤝 Worker {worker_id} registered with specialty: {specialty}")


    async def generate_tasks(self, target_config: Dict) -> List[Dict]:
        """Generate attack tasks based on target fingerprinting."""
        tasks = []
        
        # API fuzzing tasks
        if "api_endpoints" in target_config:
            for endpoint in target_config["api_endpoints"]:
                tasks.append({
                    "task_id": str(uuid.uuid4()),
                    "type": "api_fuzz",
                    "target": endpoint,
                    "priority": 7,
                    "payload": {"methods": ["GET", "POST", "PUT", "DELETE"]},
                    "worker_requirements": {"type": "api"}
                })
        
        # Browser flow tasks
        if "browser_flows" in target_config:
            for flow in target_config["browser_flows"]:
                tasks.append({
                    "task_id": str(uuid.uuid4()),
                    "type": "browser_flow",
                    "target": flow,
                    "priority": 8,
                    "payload": {"depth": 3},
                    "worker_requirements": {"type": "browser"}
                })
        
        return tasks

    def select_optimal_worker(self, task: Dict) -> Optional[str]:
        """Heuristic selection of the best worker for a given task."""
        required_type = task.get("worker_requirements", {}).get("type", "hybrid")
        
        # Filter workers by capability and status
        eligible_workers = [
            worker_id for worker_id, worker in self.workers.items()
            if (worker["specialty"] == required_type or worker["specialty"] == "hybrid") 
            and worker["status"] == "active"
        ]
        
        if not eligible_workers:
            return None
        
        # Load balancing: Select worker with least current tasks
        best_worker = min(eligible_workers, 
                         key=lambda w: len(self.workers[w].get("current_tasks", [])))
        return best_worker

    async def distribute_tasks(self, tasks: List[Dict]):
        """Distribute tasks to optimal nodes via Redis Pub/Sub."""
        for task in tasks:
            worker_id = self.select_optimal_worker(task)
            if worker_id:
                # Dispatch to worker-specific queue (Async Fix)
                queue_key = f"worker_queue:{worker_id}"
                await self.redis_client.lpush(queue_key, json.dumps(task))

                
                # Update local state
                if "current_tasks" not in self.workers[worker_id]:
                    self.workers[worker_id]["current_tasks"] = []
                self.workers[worker_id]["current_tasks"].append(task["task_id"])
                
                # Sync assignment to Supabase
                try:
                    self.supabase.table("task_assignments").insert({
                        "task_id": task["task_id"],
                        "worker_id": worker_id,
                        "assigned_at": datetime.now().isoformat()
                    }).execute()
                except Exception as e:
                    logger.debug(f"Assignment sync failed (Supabase offline?): {e}")
                
                logger.info(f"🎯 Task {task['task_id']} assigned to node {worker_id}")
            else:
                logger.warning(f"⚠️ No suitable worker found for task {task['task_id']}")

    async def monitor_workers(self):
        """Health check loop for the distributed swarm."""
        while True:
            await asyncio.sleep(60) 
            current_time = datetime.now()
            for worker_id, worker in list(self.workers.items()):
                last_heartbeat = datetime.fromisoformat(worker["last_heartbeat"])
                
                # Time out nodes if dead for > 3 mins
                if current_time - last_heartbeat > timedelta(minutes=3):
                    worker["status"] = "inactive"
                    logger.error(f"💀 Worker {worker_id} TIMED OUT. Initiating task reassignment.")
                    await self.reassign_worker_tasks(worker_id)

    async def reassign_worker_tasks(self, failed_worker_id: str):
        """Recovery logic for failed nodes."""
        worker = self.workers.get(failed_worker_id)
        if not worker: return
        
        for task_id in worker.get("current_tasks", []):
            # Mark as failed and requeue in the global pending pool (Async Fix)
            await self.redis_client.lpush("pending_tasks", json.dumps({"task_id": task_id, "retry": True}))

        
        worker["current_tasks"] = []

if __name__ == "__main__":
    # Local Development Entry
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if supabase_url:
        master = MasterNode(redis_url, supabase_url, supabase_key)
        asyncio.run(master.start())
