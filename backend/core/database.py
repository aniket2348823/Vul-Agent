import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
import redis.asyncio as aioredis
from backend.core.config import settings

logger = logging.getLogger("ELITE-DB")

class EliteDBManager:
    """
    The Single Source of Truth Manager for the Vulagent Scanner.
    Coordinates distributed state across Supabase (Persistence) and Redis (Hot Cache/Locking).
    """
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.redis_url = settings.REDIS_URL
        
        self.supabase: Optional[Client] = None
        self.redis: Optional[aioredis.Redis] = None
        self._initialized = False

    async def initialize(self):
        """Lazy initialization of cloud/cache connections."""
        if self._initialized:
            return

        try:
            # 1. Supabase Initialization
            if self.supabase_url and self.supabase_key:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("ELITE-DB: Supabase Connection Active ✓")
            
            # 2. Redis Initialization
            if self.redis_url:
                self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
                logger.info("ELITE-DB: Redis Distributed Cache Active ✓")
            
            self._initialized = True
        except Exception as e:
            logger.error(f"ELITE-DB Initialization Failed: {e}")

    # --- 1. VULNERABILITY MANAGEMENT (Intelligence) ---

    async def report_vulnerability(self, scan_id: str, endpoint: str, vuln_type: str, severity: str, evidence: Dict[str, Any], validated_by: str) -> Optional[str]:
        """
        Reports a verified vulnerability with strict deduplication.
        Uses a hash-based hot-cache in Redis before performing the Supabase UPSERT.
        """
        if not self.supabase: return None
        
        # 1. Generate Deduplication Signature
        signature = f"vuln:{scan_id}:{endpoint}:{vuln_type}"
        
        # 2. Check Redis Hot-Cache (O(1))
        if self.redis:
            if await self.redis.get(signature):
                return "CACHED"

        # 3. Suppress duplicates in Supabase (O(log n)) using ON CONFLICT logic
        data = {
            "scan_id": scan_id,
            "endpoint": endpoint,
            "vuln_type": vuln_type,
            "severity": severity,
            "evidence": evidence,
            "validated_by": validated_by,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Perform upsert based on the unique constraint (scan_id, endpoint, vuln_type)
            result = self.supabase.table("vulnerabilities").upsert(data, on_conflict="scan_id,endpoint,vuln_type").execute()
            
            if result.data:
                vuln_id = result.data[0]["id"]
                # Update Hot-Cache for 1 hour to prevent redundant writes
                if self.redis:
                    await self.redis.set(signature, vuln_id, ex=3600)
                return vuln_id
        except Exception as e:
            logger.error(f"Failed to report vulnerability to Supabase: {e}")
        
        return None

    # --- 2. DISTRIBUTED TASK MANAGEMENT (Coordination) ---

    async def acquire_task_lock(self, task_id: str, worker_id: str) -> bool:
        """
        Attempts to acquire a distributed lock for a task.
        Implementation: Redis SETNX (Atomic) + Supabase Status Update.
        """
        lock_key = f"lock:task:{task_id}"
        
        # 1. Atomic Redis Lock (expires in 10 minutes case worker crashes)
        if self.redis:
            locked = await self.redis.set(lock_key, worker_id, nx=True, ex=600)
            if not locked:
                return False

        # 2. Sync State to Supabase
        try:
            data = {
                "status": "RUNNING",
                "locked_by": worker_id,
                "lock_time": datetime.utcnow().isoformat()
            }
            result = self.supabase.table("distributed_tasks").update(data).eq("id", task_id).eq("status", "PENDING").execute()
            
            if not result.data:
                # Task was already claimed or moved state
                if self.redis: await self.redis.delete(lock_key)
                return False
            
            return True
        except Exception as e:
            logger.error(f"Supabase task lock failed: {e}")
            if self.redis: await self.redis.delete(lock_key)
            return False

    async def complete_task(self, task_id: str, status: str = "COMPLETED"):
        """Releases the lock and updates task status."""
        lock_key = f"lock:task:{task_id}"
        if self.redis:
            await self.redis.delete(lock_key)
        
        try:
            self.supabase.table("distributed_tasks").update({
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", task_id).execute()
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")

    # --- 3. BATCH OPERATIONS (Optimization) ---

    async def create_tasks_batch(self, tasks: List[Dict[str, Any]]):
        """Inserts multiple tasks in a single Supabase request."""
        if not self.supabase or not tasks: return
        try:
            self.supabase.table("distributed_tasks").insert(tasks).execute()
        except Exception as e:
            logger.error(f"Batch task creation failed: {e}")

    # --- 4. EXPLOIT & REMEDIATION ( Intelligence ) ---

    async def log_exploit_result(self, vuln_id: str, result: Dict[str, Any]):
        """Logs the final evidence of a successful exploit."""
        if not self.supabase: return
        try:
            self.supabase.table("exploit_results").insert({
                "vuln_id": vuln_id,
                "payload": result.get("payload", "N/A"),
                "worker_id": result.get("worker_id", "local"),
                "status": result.get("status", "EXPLOITED"),
                "response_dump": result.get("response", ""),
                "execution_time_ms": result.get("time_ms", 0)
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log exploit result: {e}")

# Global Instance
db_manager = EliteDBManager()
