"""
XYTHERION EXECUTION NODE (WORKER NODE)
Role: Distributed task executor with browser automation, module dispatch, and heartbeat.
Extracted from orchestrator.py for clean architecture.
"""
import asyncio
import importlib
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any

import aiohttp
import psutil

from backend.core.hive import DistributedEventBus, EventType, HiveEvent
from backend.core.stdout_watchdog import watch_output
from backend.core.cluster.pinchtab import PinchTabInstance
from backend.core.task_manager import TaskManager

logger = logging.getLogger("WorkerNode")


class WorkerNode:
    """XYTHERION EXECUTION NODE (WORKER NODE)"""

    def __init__(self, worker_id: str, specialty: str, redis_url: str, supabase_url: str, supabase_key: str):
        self.id = worker_id
        self.specialty = specialty
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        from supabase import create_client, Client
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.pinchtab = PinchTabInstance(worker_id, 9867 + hash(worker_id) % 1000)
        self.bus = DistributedEventBus(redis_url)
        self.running = False
        self._task_manager = TaskManager("WorkerNode")

    async def start(self):
        self.running = True
        await self.bus.start()
        if self.specialty in ["browser", "hybrid"]:
            await self.pinchtab.start()
        self._task_manager.create_task(self.send_heartbeat(), name="heartbeat")
        try:
            while self.running:
                if psutil.virtual_memory().percent > 85.0:
                    await asyncio.sleep(5)
                    continue
                task_data = await self.redis_client.brpop(f"worker_queue:{self.id}", timeout=5)
                if task_data:
                    task = json.loads(task_data[1])
                    self._task_manager.create_task(
                        self.execute_task(task),
                        name=f"task_{task.get('task_id', 'unknown')}"
                    )
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    async def shutdown(self):
        if not self.running:
            return
        self.running = False
        await self._task_manager.cancel_all()
        await self.pinchtab.stop()
        try:
            await self.redis_client.hdel("workers", self.id)
            await self.redis_client.close()
        except Exception:
            pass

    async def send_heartbeat(self):
        while self.running:
            try:
                heartbeat = {"id": self.id, "last_heartbeat": datetime.now().isoformat(), "status": "active"}
                await self.redis_client.hset("workers", self.id, json.dumps(heartbeat))
                await asyncio.sleep(30)
            except Exception:
                pass

    async def execute_task(self, task: Dict):
        tid = task.get("task_id", str(uuid.uuid4()))
        scan_id = task.get("scan_id", "GLOBAL")
        module_id = task.get("config", {}).get("module_id")

        try:
            await self.update_task_status(tid, "RUNNING")

            if not module_id:
                raise ValueError("No module_id provided in task config")

            # Map internal module IDs to actual python paths
            module_map = {
                "logic_tycoon": ("backend.modules.logic.tycoon", "TheTycoon"),
                "logic_escalator": ("backend.modules.logic.escalator", "TheEscalator"),
                "logic_skipper": ("backend.modules.logic.skipper", "TheSkipper"),
                "logic_doppelganger": ("backend.modules.logic.doppelganger", "Doppelganger"),
                "logic_chronomancer": ("backend.modules.logic.chronomancer", "Chronomancer"),
                "tech_sqli": ("backend.modules.tech.sqli", "SQLInjectionProbe"),
                "tech_jwt": ("backend.modules.tech.jwt", "JWTTokenCracker"),
                "tech_fuzzer": ("backend.modules.tech.fuzzer", "APIFuzzer"),
                "tech_auth_bypass": ("backend.modules.tech.auth_bypass", "AuthBypassTester")
            }

            if module_id in module_map:
                path, class_name = module_map[module_id]
                module_pkg = importlib.import_module(path)
                module_class = getattr(module_pkg, class_name)
                instance = module_class()

                from backend.core.protocol import JobPacket
                packet = JobPacket(**task)

                # 1. Generate Payloads
                targets = await instance.generate_payloads(packet)

                # 2. Real-Time Execution
                interactions = []
                from backend.api.socket_manager import publish_request_event

                from backend.core.content_boundary import content_boundary
                from backend.core.proxy import network_interceptor

                async with aiohttp.ClientSession() as session:
                    for t in targets:
                        await publish_request_event({
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "method": t.method,
                            "endpoint": t.url,
                            "payload": str(t.payload)[:50],
                            "agent": self.id,
                            "result": "EXECUTING"
                        }, scan_id=scan_id)

                        start_time = datetime.now()
                        try:
                            response = await network_interceptor.fetch(
                                t.method, t.url, session=session, json=t.payload, headers=t.headers, timeout=10
                            )
                            text = content_boundary.wrap_http_response(
                                response.status, response.headers, response.body, response.url
                            )
                            watched = await watch_output(text)
                            text = watched.content
                            latency = response.elapsed_ms
                            interactions.append((t, text))

                            await publish_request_event({
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "method": t.method,
                                "endpoint": t.url,
                                "payload": str(t.payload)[:50],
                                "status": response.status,
                                "latency": latency,
                                "agent": self.id,
                                "result": "OK" if response.status < 400 else "ERROR"
                            }, scan_id=scan_id)
                        except Exception as e:
                            interactions.append((t, f"Error: {str(e)}"))

                # 3. Analyze Responses
                vulns = await instance.analyze_responses(interactions, packet)

                # 4. Report findings
                for v in vulns:
                    await self.bus.publish(HiveEvent(
                        type=EventType.VULN_CONFIRMED,
                        source=f"worker:{self.id}",
                        scan_id=scan_id,
                        payload=v.model_dump()
                    ))

            await self.update_task_status(tid, "COMPLETED")
            await self.bus.publish(HiveEvent(
                type=EventType.JOB_COMPLETED,
                source=f"worker:{self.id}",
                payload={"job_id": tid, "status": "SUCCESS"}
            ))

        except Exception as e:
            logger.error(f"Worker Task Error [{tid}]: {e}")
            await self.update_task_status(tid, "FAILED")

    async def update_task_status(self, tid: str, status: str):
        try:
            self.supabase.table("task_assignments").update(
                {"status": status, "updated_at": datetime.now().isoformat()}
            ).eq("task_id", tid).execute()
        except Exception:
            pass
