import shutil
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import redis
from supabase import create_client, Client
import logging
from playwright.async_api import async_playwright
from backend.core.arsenal.striker_module import StrikerModule
from backend.core.arsenal.tactician_module import TacticianModule
from backend.core.hive import DistributedEventBus, HiveEvent, EventType
from backend.core.protocol import AgentID, JobPacket, ResultPacket, TaskTarget


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Xytherion.Worker")


class PinchTabInstance:
    """
    PINCHTAB BROWSER INSTANCE
    Role: Isolated browser execution for complex DOM fuzzing and IDOR detection.
    """
    def __init__(self, worker_id: str, port: int):
        self.worker_id = worker_id
        self.port = port
        self.profile_path = f"/tmp/pinchtab_profiles/{worker_id}"
        self.browser = None
        self.context = None
        self.page = None
        
        # Ensure workspace isolate folder exists
        os.makedirs(self.profile_path, exist_ok=True)
    
    async def start(self):
        """Activates the isolated Playwright instance."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    f"--user-data-dir={self.profile_path}",
                    f"--remote-debugging-port={self.port}",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            logger.info(f"🌐 PinchTab Instance Online (Worker: {self.worker_id}, Port: {self.port})")
        except Exception as e:
            logger.error(f"❌ PinchTab failed to initialize: {e}")

    async def execute_flow(self, flow_config: Dict) -> Dict:
        """Executes a multi-stage semantic browser attack flow (Phase 3: REFINE -> ACT)."""
        results = {"steps": [], "findings": []}
        try:
            for step in flow_config.get("actions_mapped", []):
                # Only execute explicitly defined, DOM-validated actions (No Hallucination)
                step_result = await self._execute_semantic_step(step, flow_config.get("target_url"))
                if step_result:
                    results["steps"].append(step_result)
                 
                # Active Safety Inspection (Level 1)
                if step_result and step_result.get("success"):
                     vulnerabilities = await self._check_vulnerabilities(step_result)
                     results["findings"].extend(vulnerabilities)
            
            # Post-Action State Extraction (Verify Tokens)
            results["post_state"] = await self._extract_state()
                     
        except Exception as e:
            logger.error(f"⚠️ Semantic Flow execution interrupted: {e}")
            results["error"] = str(e)
        return results

    async def _execute_semantic_step(self, step: Dict, target_url: str) -> Optional[Dict]:
        """Executes a single semantic action (Navigate, Click, Fill) originating from reality."""
        result = {"action": step["type"], "target": step["target"], "success": False}
        try:
            target_str = str(step["target"])
            if step["type"] == "input":
                # Ensure the input actually exists before interacting
                selector = f"input[name='{target_str}'], input[id='{target_str}'], *[placeholder*='{target_str}' i]"
                if await self.page.locator(selector).count() > 0:
                     await self.page.fill(selector, "xytherion_fuzz_payload")
                     result["success"] = True
            elif step["type"] == "click":
                # Ensure the button actually exists
                selector = f"button:text-matches('(?i){target_str}'), input[type='submit'][value*='(?i){target_str}']"
                if await self.page.locator(selector).count() > 0:
                     await self.page.click(selector)
                     result["success"] = True
            elif step["action"] == "navigate": # Direct nav from legacy jobs
                response = await self.page.goto(step.get("url", target_url))
                result["url"] = self.page.url
                result["response_status"] = response.status if response else 0
                result["success"] = True
        except Exception as e:
            result["error"] = str(e)
            
        return result

    async def _extract_state(self) -> Dict:
        """Isolated Token & Cookie extraction per tab."""
        state = {"cookies": [], "tokens": {}}
        try:
            state["cookies"] = await self.context.cookies()
            local_storage = await self.page.evaluate("() => JSON.stringify(window.localStorage)")
            session_storage = await self.page.evaluate("() => JSON.stringify(window.sessionStorage)")
            import json
            state["tokens"]["local"] = json.loads(local_storage)
            state["tokens"]["session"] = json.loads(session_storage)
        except Exception:
            pass
        return state


    async def _check_vulnerabilities(self, step_result: Dict) -> List[Dict]:
        """Deep DOM/Network vulnerability detection logic."""
        vulns = []
        content = await self.page.content()
        # Level 1: Heuristic Scrutiny
        if "<script>alert(1)</script>" in content or "gi5_trigger" in content:
            vulns.append({"type": "xss", "severity": "HIGH", "desc": "Reflected Payload detected in DOM rendering."})
        return vulns

    async def stop(self):
        """Clean shutdown of browser resources and profile removal."""
        logger.info(f"🛑 Stopping PinchTab Instance {self.worker_id}...")
        try:
            if self.browser: await self.browser.close()
            if hasattr(self, 'playwright'): await self.playwright.stop()
            
            # AUTOMATIC PROFILE REMOVAL (V6-HARDENED)
            if os.path.exists(self.profile_path):
                shutil.rmtree(self.profile_path, ignore_errors=True)
                logger.debug(f"🧹 Cleaned up profile: {self.profile_path}")
        except Exception as e:
            logger.debug(f"PinchTab cleanup FAIL: {e}")


class WorkerNode:
    """
    XYTHERION EXECUTION NODE (WORKER NODE)
    Role: Local orchestration and execution of attack tasks.
    """
    def __init__(self, worker_id: str, specialty: str, redis_url: str, supabase_url: str, supabase_key: str):
        self.id = worker_id
        self.specialty = specialty
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.pinchtab = PinchTabInstance(worker_id, 9867 + hash(worker_id) % 1000)
        
        # 1. Distributed Nervous System Bridge (Async)
        self.bus = DistributedEventBus(redis_url)

        
        # 2. Arsenal Loading
        self.striker = StrikerModule(bus=self.bus)
        self.tactician = TacticianModule()
        
        self.running = False


    async def start(self):
        """Enters the execution loop with signal management."""
        logger.info(f"🦾 Worker Node {self.id} (Specialty: {self.specialty}) Starting...")
        self.running = True
        
        # 1. Setup Signal Handlers for Orchestrator/CLI safety
        loop = asyncio.get_event_loop()
        for s in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(s, lambda: asyncio.create_task(self.shutdown()))
            except (NotImplementedError, ValueError):
                pass # Fallback for Windows
        
        # 2. Start Subsystems
        await self.bus.start()
        if self.specialty in ["browser", "hybrid"]:
            await self.pinchtab.start()
        
        asyncio.create_task(self.send_heartbeat())
        
        # 3. Main Loop (V6-ASYNC POLLING + RESOURCE GUARD)
        try:
            import psutil
            while self.running:
                # 3.1 Resource Guard (Level 2 Safety)
                mem_percent = psutil.virtual_memory().percent
                if mem_percent > 85.0:
                    logger.warning(f"⚠️ High Memory Usage ({mem_percent}%). Throttling execution to prevent OOM.")
                    await asyncio.sleep(5)
                    continue
                
                queue_key = f"worker_queue:{self.id}"
                # Use await to prevent event loop blockage
                task_data = await self.redis_client.brpop(queue_key, timeout=5)

                if task_data:
                    task = json.loads(task_data[1])
                    asyncio.create_task(self.execute_task(task))

        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Atomic extraction from the swarm."""
        if not self.running: return
        self.running = False
        logger.info(f"🛑 Worker {self.id} SHUTTING DOWN...")
        
        # 1. Cleanup Browser Isolation
        await self.pinchtab.stop()
        
        # 2. Close Distributed Bridge (Async)
        try:
            # Mark offline in Registry
            await self.redis_client.hdel("workers", self.id)
            await self.redis_client.close()
        except Exception as e:
            logger.debug(f"Worker extraction cleanup error: {e}")


        
        logger.info(f"✨ Worker {self.id} Cleanly Extracted.")

    async def send_heartbeat(self):

        """Reports health to the Master Command Matrix."""
        while self.running:
            try:
                heartbeat = {
                    "id": self.id,
                    "last_heartbeat": datetime.now().isoformat(),
                    "status": "active"
                }
                await self.redis_client.hset("workers", self.id, json.dumps(heartbeat))
                await asyncio.sleep(30)

            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

    async def execute_task(self, task: Dict):
        """Orchestrates specific execution modules based on task type or agent_id."""
        task_id = task.get("task_id", str(uuid.uuid4()))
        agent_id = task.get("config", {}).get("agent_id")
        
        logger.info(f"🎯 Node {self.id} Executing Task {task_id} (Agent: {agent_id})")
        
        try:
            # Lifecycle: START
            await self.update_task_status(task_id, "RUNNING")
            
            result = {}
            # 1. Map to Arsenal
            if agent_id == AgentID.BETA or task["type"] == "api_fuzz":
                result = await self.execute_api_fuzz(task)
            elif agent_id == AgentID.SIGMA:
                result = await self.execute_generative_fuzz(task)
            elif task["type"] == "browser_flow":
                result = await self.execute_browser_flow(task)
            else:
                logger.warning(f"⚠️ Unhandled agent_id {agent_id} on worker {self.id}")
                result = {"error": "unsupported_agent"}
            
            # Lifecycle: COMPLETED
            await self.store_result(task_id, result)
            await self.update_task_status(task_id, "COMPLETED")
            
            # 2. Global Sync (Reporting finding back to Master)
            await self.bus.publish(HiveEvent(
                type=EventType.JOB_COMPLETED,
                source=f"worker:{self.id}",
                payload={"job_id": task_id, "result": result, "status": "SUCCESS"}
            ))
            
        except Exception as e:
            logger.error(f"Task Failure: {e}")
            await self.update_task_status(task_id, "FAILED")

    async def execute_api_fuzz(self, task: Dict) -> Dict:
        """Executes HTTP multi-vector assault via Striker module."""
        target_url = task.get("target", {}).get("url")
        payloads = task.get("config", {}).get("params", {}).get("payloads", [])
        
        if not payloads:
            # Generate default polyglots if none provided
            payloads = ["' OR 1=1--", "<script>alert(1)</script>", "{{7*7}}"]
            
        results = await self.striker.execute_assault(target_url, payloads)
        return {"status": "success", "execution_results": results}

    async def execute_generative_fuzz(self, task: Dict) -> Dict:
        """Executes weaponsmithing via Tactician module."""
        target_url = task.get("target", {}).get("url")
        vectors = await self.tactician.generate_vectors(target_url)
        return {"status": "success", "generated_payloads": vectors}


    async def execute_browser_flow(self, task: Dict) -> Dict:
        """Browser Flow Module Placeholder."""
        return await self.pinchtab.execute_flow(task.get("payload", {}))

    async def update_task_status(self, task_id: str, status: str):
        """Syncs task progress to Supabase."""
        try:
            self.supabase.table("task_assignments").update({
                "status": status,
                "updated_at": datetime.now().isoformat()
            }).eq("task_id", task_id).execute()
        except Exception as e:
            logger.debug(f"Status sync failed: {e}")

    async def store_result(self, task_id: str, result: Dict):
        """Stores final execution outcome."""
        try:
            self.supabase.table("attack_results").insert({
                "task_id": task_id,
                "worker_id": self.id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.debug(f"Result storage failed: {e}")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    worker_id = os.getenv("WORKER_ID", f"worker-{uuid.uuid4().hex[:6]}")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    worker = WorkerNode(worker_id, "hybrid", redis_url, supabase_url, supabase_key)
    asyncio.run(worker.start())
