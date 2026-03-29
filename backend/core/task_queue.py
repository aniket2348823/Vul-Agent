import asyncio
import json
import redis
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Xytherion.TaskQueue")

class TaskQueue:
    """
    REDIS-BACKED PRIORITY QUEUE SYSTEM
    Role: Resilient task distribution and state tracking.
    """
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
        self.queues = {
            "high": "tasks:high",
            "medium": "tasks:medium", 
            "low": "tasks:low",
            "failed": "tasks:failed"
        }
    
    async def enqueue(self, task: Dict, priority: str = "medium") -> bool:
        """Enqueues a task with the specified priority tier."""
        try:
            task["queued_at"] = datetime.now().isoformat()
            task["status"] = "QUEUED"
            
            queue_key = self.queues.get(priority, self.queues["medium"])
            # Atomic PUSH
            self.redis_client.lpush(queue_key, json.dumps(task))
            
            # Indexing for visibility
            self.redis_client.hset("task_index", task["task_id"], 
                                 json.dumps({"queue": queue_key, "priority": priority}))
            
            logger.info(f"📤 Task {task['task_id']} enqueued ({priority})")
            return True
        except Exception as e:
            logger.error(f"❌ Enqueue FAIL: {e}")
            return False

    async def dequeue(self, worker_id: str) -> Optional[Dict]:
        """Atomic POP based on priority sequence."""
        try:
            for priority in ["high", "medium", "low"]:
                queue_key = self.queues[priority]
                task_data = self.redis_client.rpop(queue_key) # Atomic grab
                
                if task_data:
                    task = json.loads(task_data)
                    task["assigned_to"] = worker_id
                    task["assigned_at"] = datetime.now().isoformat()
                    task["status"] = "ASSIGNED"
                    
                    # Update tracking index
                    self.redis_client.hset("task_index", task["task_id"], json.dumps(task))
                    logger.info(f"📥 Task {task['task_id']} dequeued for node {worker_id}")
                    return task
            return None
        except Exception as e:
            logger.error(f"❌ Dequeue FAIL: {e}")
            return None

    async def acquire_lock(self, task_id: str, lifetime: int = 300) -> bool:
        """Distributed lock via SET NX (Exclusive) to prevent double-execution."""
        lock_key = f"lock:task:{task_id}"
        # Set with expiration (PX) and if not exist (NX)
        result = self.redis_client.set(lock_key, "LOCKED", ex=lifetime, nx=True)
        return result is not None

    async def release_lock(self, task_id: str):
        """Releases the distributed lock."""
        self.redis_client.delete(f"lock:task:{task_id}")

    async def mark_failed(self, task_id: str, error: str):
        """Moves job to the DLQ (Dead Letter Queue) for review."""
        try:
            task_info = self.redis_client.hget("task_index", task_id)
            if task_info:
                task = json.loads(task_info)
                task["error"] = error
                task["failed_at"] = datetime.now().isoformat()
                
                self.redis_client.lpush(self.queues["failed"], json.dumps(task))
                self.redis_client.hdel("task_index", task_id)
                logger.error(f"🚨 Task {task_id} FAILED: {error}")
        except Exception as e:
            logger.debug(f"Failed status update failed: {e}")

if __name__ == "__main__":
    # Smoke Test
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    tq = TaskQueue(redis_url)
    asyncio.run(tq.enqueue({"task_id": "TEST_001", "type": "heartbeat"}, priority="high"))
    print("Test Task Pushed.")
