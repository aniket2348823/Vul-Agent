#!/usr/bin/env python3
import asyncio
import argparse
import signal
import sys
import uuid
import logging
from typing import Optional
from backend.core.config import ConfigManager
from backend.core.master import MasterNode
from backend.core.worker import WorkerNode
from backend.core.task_queue import TaskQueue
from backend.core.graph_ai import GraphIntelligence

# XYTHERION CLUSTER ORCHESTRATOR
# Role: Standardized bootstrap and lifecycle management for the distributed attack cluster.

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Xytherion.Main")

class DistributedAttackCluster:
    """Orchestrates the lifecycle of the distributed cluster components."""
    def __init__(self, mode: str):
        self.mode = mode
        self.config = ConfigManager()
        self.running = False
        self.master_node: Optional[MasterNode] = None
        self.worker_node: Optional[WorkerNode] = None
        
        # Signal Handlers (SIGINT/SIGTERM)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Signal intercept for clean extraction."""
        logger.info(f"🛑 Received signal {signum}, initiating clean cluster extraction...")
        self.running = False
    
    async def start_master(self):
        """Standardized Master bootstrap."""
        try:
            self.master_node = MasterNode(
                self.config.redis.url,
                self.config.supabase.url,
                self.config.supabase.key
            )
            self.running = True
            logger.info("📡 Xytherion Master Node Activated.")
            await self.master_node.start()
        except Exception as e:
            logger.error(f"❌ Master start error: {e}")
            raise
    
    async def start_worker(self, worker_id: Optional[str] = None):
        """Standardized Worker bootstrap."""
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
            logger.info(f"🦾 Xytherion Worker Node Activated ({worker_id})")
            await self.worker_node.start()
        except Exception as e:
            logger.error(f"❌ Worker start error: {e}")
            raise

    async def start_cluster(self, num_workers: int = 5):
        """Local cluster orchestration for dev testing."""
        master_task = asyncio.create_task(self.start_master())
        await asyncio.sleep(2) # Bootstrap delay
        
        worker_tasks = []
        for i in range(num_workers):
            wid = f"worker-{i+1}-{uuid.uuid4().hex[:4]}"
            worker_tasks.append(asyncio.create_task(self.start_worker(wid)))
            await asyncio.sleep(0.5)
        
        logger.info(f"🔗 Cluster Handshake: 1 Master + {num_workers} Workers Linked.")
        await asyncio.gather(master_task, *worker_tasks)

async def main():
    parser = argparse.ArgumentParser(description="Xytherion Distributed Attack Cluster Orchestrator")
    parser.add_argument("--mode", choices=["master", "worker", "cluster"], required=True, help="Run mode for this instance.")
    parser.add_argument("--num-workers", type=int, default=3, help="Worker count for local cluster mode.")
    parser.add_argument("--worker-id", help="Override worker ID.")
    
    args = parser.parse_args()
    cluster = DistributedAttackCluster(args.mode)
    
    try:
        if args.mode == "master":
            await cluster.start_master()
        elif args.mode == "worker":
            await cluster.start_worker(args.worker_id)
        elif args.mode == "cluster":
            await cluster.start_cluster(args.num_workers)
    except Exception as e:
        logger.critical(f"🚨 Cluster Hard Crash: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
