import asyncio
import json
import uuid
import os
import shutil
import signal
import psutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import redis
from supabase import create_client, Client
import logging
from playwright.async_api import async_playwright

from backend.core.hive import EventBus, DistributedEventBus, EventType, HiveEvent
from backend.core.protocol import ModuleConfig, AgentID, TaskPriority, TaskTarget
from backend.core.state import stats_db_manager
from backend.core.config import settings
from backend.api.socket_manager import manager
from backend.core.graph_engine import GraphEngine

# --- INTEGRATED CLUSTER COMPONENTS ---

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
        os.makedirs(self.profile_path, exist_ok=True)
    
    async def start(self):
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
            print(f"🌐 PinchTab Instance Online (Worker: {self.worker_id}, Port: {self.port})")
        except Exception as e:
            print(f"❌ PinchTab failed to initialize: {e}")

    async def execute_flow(self, flow_config: Dict) -> Dict:
        results = {"steps": [], "findings": []}
        try:
            for step in flow_config.get("actions_mapped", []):
                step_result = await self._execute_semantic_step(step, flow_config.get("target_url"))
                if step_result:
                    results["steps"].append(step_result)
                 
                if step_result and step_result.get("success"):
                     vulnerabilities = await self._check_vulnerabilities(step_result)
                     results["findings"].extend(vulnerabilities)
            results["post_state"] = await self._extract_state()
        except Exception as e:
            results["error"] = str(e)
        return results

    async def _execute_semantic_step(self, step: Dict, target_url: str) -> Optional[Dict]:
        result = {"action": step["type"], "target": step["target"], "success": False}
        try:
            target_str = str(step["target"])
            if step["type"] == "input":
                selector = f"input[name='{target_str}'], input[id='{target_str}'], *[placeholder*='{target_str}' i]"
                if await self.page.locator(selector).count() > 0:
                     await self.page.fill(selector, "xytherion_fuzz_payload")
                     result["success"] = True
            elif step["type"] == "click":
                selector = f"button:text-matches('(?i){target_str}'), input[type='submit'][value*='(?i){target_str}']"
                if await self.page.locator(selector).count() > 0:
                     await self.page.click(selector)
                     result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        return result

    async def _extract_state(self) -> Dict:
        state = {"cookies": [], "tokens": {}}
        try:
            state["cookies"] = await self.context.cookies()
            local_storage = await self.page.evaluate("() => JSON.stringify(window.localStorage)")
            session_storage = await self.page.evaluate("() => JSON.stringify(window.sessionStorage)")
            state["tokens"]["local"] = json.loads(local_storage)
            state["tokens"]["session"] = json.loads(session_storage)
        except Exception: pass
        return state

    async def _check_vulnerabilities(self, step_result: Dict) -> List[Dict]:
        vulns = []
        content = await self.page.content()
        if "<script>alert(1)</script>" in content:
            vulns.append({"type": "xss", "severity": "HIGH", "desc": "Reflected Payload detected."})
        return vulns

    async def stop(self):
        try:
            if self.browser: await self.browser.close()
            if hasattr(self, 'playwright'): await self.playwright.stop()
            if os.path.exists(self.profile_path):
                shutil.rmtree(self.profile_path, ignore_errors=True)
        except Exception: pass

class MasterNode:
    """XYTHERION COMMAND MATRIX (MASTER NODE)"""
    def __init__(self, redis_url: str, supabase_url: str, supabase_key: str):
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.attack_graph = GraphEngine()

    async def start(self):
        self.active = True
        await self._discover_swarm()
        asyncio.create_task(self.monitor_workers())
        while self.active:
            try:
                task_data = await self.redis_client.brpop("pending_tasks", timeout=5)
                if task_data:
                    task = json.loads(task_data[1])
                    await self.distribute_tasks([task])
            except Exception: await asyncio.sleep(1)

    async def _discover_swarm(self):
        try:
            raw_workers = await self.redis_client.hgetall("workers")
            for worker_id, data in raw_workers.items():
                self.workers[worker_id] = json.loads(data)
        except Exception: pass

    async def register_worker(self, worker_id: str, specialty: str, capabilities: List[str]):
        worker_info = {
            "id": worker_id, "specialty": specialty, "capabilities": capabilities,
            "status": "active", "last_heartbeat": datetime.now().isoformat(), "current_tasks": []
        }
        self.workers[worker_id] = worker_info
        await self.redis_client.hset("workers", worker_id, json.dumps(worker_info))

    def select_optimal_worker(self, task: Dict) -> Optional[str]:
        required_type = task.get("worker_requirements", {}).get("type", "hybrid")
        eligible_workers = [wid for wid, w in self.workers.items() if (w["specialty"] in [required_type, "hybrid"]) and w["status"] == "active"]
        if not eligible_workers: return None
        return min(eligible_workers, key=lambda w: len(self.workers[w].get("current_tasks", [])))

    async def distribute_tasks(self, tasks: List[Dict]):
        for task in tasks:
            worker_id = self.select_optimal_worker(task)
            if worker_id:
                await self.redis_client.lpush(f"worker_queue:{worker_id}", json.dumps(task))
                self.workers[worker_id].setdefault("current_tasks", []).append(task["task_id"])
                try:
                    self.supabase.table("task_assignments").insert({"task_id": task["task_id"], "worker_id": worker_id, "assigned_at": datetime.now().isoformat()}).execute()
                except Exception: pass

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
        if not worker: return
        for tid in worker.get("current_tasks", []):
            await self.redis_client.lpush("pending_tasks", json.dumps({"task_id": tid, "retry": True}))
        worker["current_tasks"] = []

class WorkerNode:
    """XYTHERION EXECUTION NODE (WORKER NODE)"""
    def __init__(self, worker_id: str, specialty: str, redis_url: str, supabase_url: str, supabase_key: str):
        self.id = worker_id
        self.specialty = specialty
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.pinchtab = PinchTabInstance(worker_id, 9867 + hash(worker_id) % 1000)
        self.bus = DistributedEventBus(redis_url)
        self.running = False

    async def start(self):
        self.running = True
        await self.bus.start()
        if self.specialty in ["browser", "hybrid"]: await self.pinchtab.start()
        asyncio.create_task(self.send_heartbeat())
        try:
            while self.running:
                if psutil.virtual_memory().percent > 85.0:
                    await asyncio.sleep(5)
                    continue
                task_data = await self.redis_client.brpop(f"worker_queue:{self.id}", timeout=5)
                if task_data:
                    task = json.loads(task_data[1])
                    asyncio.create_task(self.execute_task(task))
        except asyncio.CancelledError: pass
        finally: await self.shutdown()

    async def shutdown(self):
        if not self.running: return
        self.running = False
        await self.pinchtab.stop()
        try:
            await self.redis_client.hdel("workers", self.id)
            await self.redis_client.close()
        except Exception: pass

    async def send_heartbeat(self):
        while self.running:
            try:
                heartbeat = {"id": self.id, "last_heartbeat": datetime.now().isoformat(), "status": "active"}
                await self.redis_client.hset("workers", self.id, json.dumps(heartbeat))
                await asyncio.sleep(30)
            except Exception: pass

    async def execute_task(self, task: Dict):
        tid = task.get("task_id", str(uuid.uuid4()))
        try:
            await self.update_task_status(tid, "RUNNING")
            await self.update_task_status(tid, "COMPLETED")
            await self.bus.publish(HiveEvent(type=EventType.JOB_COMPLETED, source=f"worker:{self.id}", payload={"job_id": tid, "status": "SUCCESS"}))
        except Exception:
            await self.update_task_status(tid, "FAILED")

    async def update_task_status(self, tid: str, status: str):
        try: self.supabase.table("task_assignments").update({"status": status, "updated_at": datetime.now().isoformat()}).eq("task_id", tid).execute()
        except Exception: pass

# Import Agents
from backend.agents.alpha import AlphaAgent
from backend.agents.beta import BetaAgent
from backend.agents.gamma import GammaAgent
from backend.agents.omega import OmegaAgent
from backend.agents.zeta import ZetaAgent
from backend.agents.sigma import SigmaAgent
from backend.agents.kappa import KappaAgent 

# Xytherion Distributed Architecture (Logic Integrated Locally)
# Legacy imports removed to prevent shadowing

# Unified Safety Agents (Prism & Chi)
from backend.agents.prism import AgentPrism # Agent Theta (The Sentinel)
from backend.agents.chi import AgentChi # Agent Iota (The Inspector)
from backend.agents.delta import AgentDelta # Agent Delta (Hybrid DOM Controller)


# recorder removed - unused import cleanup V6
from backend.core.reporting import ReportGenerator # The Voice
# Hybrid AI Engine for campaign strategy
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.planner import MissionPlanner

logger = logging.getLogger("HiveOrchestrator")
ai_cortex = get_cortex_engine()

class HiveOrchestrator:
    # Global Registry for API Access (Nervous System)
    active_agents = {}
    _orphaned_tasks = set()

    @staticmethod
    async def bootstrap_hive(target_config, scan_id=None):
        """
        Initializes the Antigravity V5 Singularity.
        """
        start_time = datetime.now()
        if not scan_id:
             scan_id = f"HIVE-V5-{int(start_time.timestamp())}"

        # 0. Register Scan (Idempotent Check)
        # Check if already registered by attack.py
        existing = next((s for s in stats_db_manager.get_stats()["scans"] if s["id"] == scan_id), None)
        if not existing:
            scan_record = {
                "id": scan_id,
                "status": "Initializing",
                "name": target_config['url'],
                "scope": target_config['url'],
                "modules": ["Singularity V5"],
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": []
            }
            # V6: Internal Persistence & State
            self.state_db = stats_db_manager
            
            # [NEW] Redundant assignment removed in favor of proper settings-based initiation below
            # [FATAL BUG FIX: V6-OMEGA] register_scan is an async def and MUST be awaited
            try:
                await stats_db_manager.register_scan(scan_record)
            except Exception:
                pass # DB might be locked
        else:
             # Just update status if needed
             for s in stats_db_manager.get_stats()["scans"]:
                 if s["id"] == scan_id:
                     s["status"] = "Running"
                     break
             stats_db_manager._save()
            
        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Initializing"}})

        # 1. Create Nervous System (Distributed Switch)
        redis_url = getattr(settings, "REDIS_URL", None)
        if redis_url:
            bus = DistributedEventBus(redis_url)
            await bus.start()
            logger.info("🕸️ Xytherion Distributed Singularity Initialized.")
            
            # --- START DISTRIBUTED COMMAND LAYER ---
            # Automatically start Master for this scan
            master = MasterNode(redis_url, settings.SUPABASE_URL, settings.SUPABASE_KEY)
            asyncio.create_task(master.start())
            
            # Start Worker for dynamic execution
            worker_id = f"local-hive-{uuid.uuid4().hex[:4]}"
            worker = WorkerNode(worker_id, "hybrid", redis_url, settings.SUPABASE_URL, settings.SUPABASE_KEY)
            asyncio.create_task(worker.start())
            
            # The Unified Agents (Prism/Chi) handle individual guardian duties
            # they are already in the core_agents list and started below.
            logger.info("🛡️ Xytherion Command Matrix Activated (Master + Local Worker). Safety Guardians Unified.")
            
            # V6-HARDENED: Start Cluster Telemetry Loop
            asyncio.create_task(HiveOrchestrator._cluster_telemetry_loop(redis_url, scan_id))
            # ----------------------------------------

        else:
            bus = EventBus()
            logger.info("🛡️ Local Singularity Initialized (Standalone).")



        
        # --- REPORTING LINK ---
        scan_events = []
        async def event_listener(event: HiveEvent):
            scan_events.append(event.model_dump())
            
            # REAL-TIME DASHBOARD SYNC
            if event.type == EventType.VULN_CONFIRMED:
                # Update global stats immediately
                real_payload = event.payload
                if 'payload' in real_payload and isinstance(real_payload['payload'], dict):
                     pass

                severity = real_payload.get('severity', 'High')
                # Passing normalized signature data to StateManager for robust deduplication
                sig_data = {
                    "url": str(real_payload.get('url', '')).strip().lower(),
                    "type": str(real_payload.get('type', '')).upper(),
                    "data": str(real_payload.get('data', real_payload.get('payload', '')))
                }
                await stats_db_manager.record_finding(scan_id, severity, sig_data)
                
                # Broadcast authoritative stats to UI
                current_stats = stats_db_manager.get_stats()
                await manager.broadcast({
                    "type": "VULN_UPDATE", 
                    "payload": {
                        "metrics": {
                            "vulnerabilities": current_stats["vulnerabilities"],
                            "critical": current_stats["critical"],
                            "active_scans": current_stats["active_scans"], 
                            "total_scans": current_stats["total_scans"]
                        },
                        "graph_data": current_stats["history"]
                    }
                })

                # V6: Persist Threat Metrics (Async Fix)
                threat_type = real_payload.get("type", "Unknown Threat")
                risk_score = real_payload.get("data", {}).get("risk_score", 0)
                await stats_db_manager.record_threat(threat_type, risk_score)


                # Broadcast LIVE THREAT LOG (New Feature)
                await manager.broadcast({
                    "type": "LIVE_THREAT_LOG",
                    "payload": {
                        "agent": event.source,
                        "threat_type": threat_type,
                        "url": real_payload.get("url", "Unknown Source"),
                        "severity": severity,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "risk_score": risk_score
                    }
                })
                
            elif event.type == EventType.VULN_CANDIDATE:
                real_payload = event.payload
                threat_type = real_payload.get("tag", "Anomaly Target")
                await manager.broadcast({
                    "type": "LIVE_THREAT_LOG",
                    "payload": {
                        "agent": event.source,
                        "threat_type": f"[RECON] {threat_type}",
                        "url": real_payload.get("url", "Unknown Source"),
                        "severity": "INFO",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "risk_score": 0
                    }
                })

            elif event.type == EventType.LIVE_ATTACK:
                # Compute a dynamic severity based on keywords in the action/arsenal
                action_str = (event.payload.get("action", "") + event.payload.get("arsenal", "")).lower()
                if any(k in action_str for k in ["inject", "sqli", "xss", "bypass", "exploit", "crack"]):
                    attack_severity = "HIGH"
                    attack_risk = 75
                elif any(k in action_str for k in ["fuzz", "mutation", "brute", "payload"]):
                    attack_severity = "MEDIUM"
                    attack_risk = 50
                else:
                    attack_severity = "LOW"
                    attack_risk = 25

                await manager.broadcast({
                    "type": "LIVE_ATTACK_FEED",
                    "payload": {
                        "agent": event.source,
                        "url": event.payload.get("url", "N/A"),
                        "arsenal": event.payload.get("arsenal", "General"),
                        "action": event.payload.get("action", "Processing"),
                        "payload": event.payload.get("payload", "N/A"),
                        "severity": attack_severity,
                        "risk_score": attack_risk,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })

            elif event.type == EventType.RECON_PACKET:
                await manager.broadcast({
                    "type": "RECON_PACKET",
                    "payload": {
                        "url": event.payload.get("url", "Unknown"),
                        "severity": event.payload.get("severity", "INFO"),
                        "risk_score": event.payload.get("risk_score", 10),
                        "source": event.source,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })

            elif event.type == EventType.JOB_ASSIGNED:
                # Broadcast job dispatch as a visual event for the dashboard
                target_data = event.payload.get("target", {})
                config_data = event.payload.get("config", {})
                job_url = target_data.get("url", "System Process") if isinstance(target_data, dict) else "System Process"
                job_module = config_data.get("module_id", "Unknown") if isinstance(config_data, dict) else "Unknown"
                await manager.broadcast({
                    "type": "JOB_ASSIGNED",
                    "payload": {
                        "source": event.source,
                        "url": job_url,
                        "module": job_module,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })

        # Subscribe Recorder to Everything for maximum fidelity
        for etype in EventType:
            bus.subscribe(etype, event_listener)
        # ----------------------

        # 2. Spawn Agents (Singularity V5)
        # All agents now inherit from Hive BaseAgent and take `bus`
        scout = AlphaAgent(bus)
        breaker = BetaAgent(bus)
        analyst = GammaAgent(bus)
        strategist = OmegaAgent(bus)
        governor = ZetaAgent(bus)
        
        # AWAKENING: The Smith and The Librarian
        sigma = SigmaAgent(bus)
        kappa = KappaAgent(bus) 
        
        # AWAKENING: The Sentinel and The Inspector (Purple Team Expansion)
        sentinel = AgentPrism(bus)
        inspector = AgentChi(bus) 
        
        # AWAKENING: The Hybrid Controller (Browser DOM Wrapper)
        delta = AgentDelta(bus)
        
        # AWAKENING: The Mission Planner (V6 Strategic Heart)
        planner = MissionPlanner(bus)

        # 4. Wake Up the Hive
        # DATA WIRING: Pass Mission Profile
        mission_profile = {
            "modules": target_config.get("modules", []),
            "filters": target_config.get("filters", []),
            "scope": target_config.get("url", "")
        }
        
        # MODULE-BASED AGENT ROUTING
        # Core agents always run — these provide essential cross-cutting services
        # Alpha: Recon, Kappa: Memory, Planner: Strategy, Prism: Defense, Chi: Defense
        # Gamma: Forensic Audit, Omega: Campaign Strategy, Zeta: Governance/Throttle, Delta: DOM Interceptor
        core_agents = [scout, kappa, planner, sentinel, inspector, analyst, strategist, governor, delta]
        
        # Offensive agents mapped to modules (Beta + Sigma are attack-specific)
        module_agent_map = {
            "The Tycoon": [breaker, sigma],
            "The Escalator": [breaker, sigma],
            "The Skipper": [breaker, sigma],
            "Doppelganger (IDOR)": [breaker, sigma],
            "Chronomancer": [breaker, sigma],
            "SQL Injection Probe": [breaker, sigma],
            "JWT Token Cracker": [breaker, sigma],
            "API Fuzzer (REST)": [breaker, sigma],
            "Auth Bypass Tester": [breaker, sigma],
        }
        
        selected_modules = target_config.get("modules", [])
        
        if selected_modules:
            # Build unique set of agents from selected modules
            offensive_agents_set = set()
            for mod in selected_modules:
                for agent in module_agent_map.get(mod, []):
                    offensive_agents_set.add(agent)
            agents = core_agents + list(offensive_agents_set)
        else:
            # No modules selected = run everything (backward compatibility)
            agents = [scout, breaker, analyst, strategist, governor, sigma, kappa, sentinel, inspector, planner]
        
        for agent in agents:
            agent.mission_config = mission_profile # Inject Config
            await agent.start()
            
        # Register in Global State (Dual Keying for String and Enum access)
        HiveOrchestrator.active_agents["agent_prism"] = sentinel
        HiveOrchestrator.active_agents[AgentID.PRISM] = sentinel
        
        HiveOrchestrator.active_agents["agent_chi"] = inspector
        HiveOrchestrator.active_agents[AgentID.CHI] = inspector
        
        HiveOrchestrator.active_agents["agent_omega"] = strategist
        HiveOrchestrator.active_agents[AgentID.OMEGA] = strategist
        
        HiveOrchestrator.active_agents["agent_alpha"] = scout
        HiveOrchestrator.active_agents[AgentID.ALPHA] = scout
        
        HiveOrchestrator.active_agents["agent_beta"] = breaker
        HiveOrchestrator.active_agents[AgentID.BETA] = breaker
        
        HiveOrchestrator.active_agents["agent_gamma"] = analyst
        HiveOrchestrator.active_agents[AgentID.GAMMA] = analyst
        
        HiveOrchestrator.active_agents["agent_zeta"] = governor
        HiveOrchestrator.active_agents[AgentID.ZETA] = governor
        
        HiveOrchestrator.active_agents["agent_sigma"] = sigma
        HiveOrchestrator.active_agents[AgentID.SIGMA] = sigma
        
        HiveOrchestrator.active_agents["agent_kappa"] = kappa
        HiveOrchestrator.active_agents[AgentID.KAPPA] = kappa
        
        HiveOrchestrator.active_agents["agent_delta"] = delta
        HiveOrchestrator.active_agents[AgentID.DELTA] = delta
        
        HiveOrchestrator.active_agents["PLANNER"] = planner
        
        # HYBRID AI: Log campaign strategy
        strategy_name = "Dynamic Multi-Core Heuristics"
        logger.info(f"AI Campaign Strategy: {strategy_name}")
            
        await manager.broadcast({"type": "GI5_LOG", "payload": f"SINGULARITY V6 ONLINE. AI Strategy: {strategy_name}."})
        # CRITICAL FIX: Include target_url in SCAN_UPDATE so Dashboard can filter
        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Running", "target_url": target_config['url']}})

        # 5. Seed the Mission — PUBLISH WITH SCAN_ID FOR CONTEXT ISOLATION
        await bus.publish(HiveEvent(
            type=EventType.TARGET_ACQUIRED,
            source="Orchestrator",
            scan_id=scan_id,
            payload={"url": target_config['url'], "tech_stack": ["Unknown"]} 
        ))
        
        # [V6 REAL-TIME FIX] Dispatch selected modules concurrently!
        module_mapper = {
            "The Tycoon": "logic_tycoon",
            "The Escalator": "logic_escalator",
            "The Skipper": "logic_skipper",
            "Doppelganger (IDOR)": "logic_doppelganger",
            "Chronomancer": "logic_chronomancer",
            "SQL Injection Probe": "tech_sqli",
            "JWT Token Cracker": "tech_jwt",
            "API Fuzzer (REST)": "tech_fuzzer",
            "Auth Bypass Tester": "tech_auth_bypass",
            "Hybrid DOM Extraction": "delta_pinch_extract"
        }
        
        # Bug Fix #5: Core Module Fallback Breakage
        if not selected_modules:
            selected_modules = list(module_mapper.keys())
        
        for ui_module_name in selected_modules:
            internal_id = module_mapper.get(ui_module_name)
            if not internal_id: continue
            
            packet = JobPacket(
                priority=TaskPriority.HIGH,
                target=TaskTarget(url=target_config['url']),
                config=ModuleConfig(
                    module_id=internal_id,
                    agent_id=AgentID.SIGMA,
                    params={
                        "concurrency": target_config.get("concurrency", 50),
                        "rps": target_config.get("rps", 100)
                    }
                )
            )

            
            await bus.publish(HiveEvent(
                type=EventType.JOB_ASSIGNED,
                source="Orchestrator",
                scan_id=scan_id,
                payload=packet.model_dump()
            ))

        # [V6 REAL-TIME FIX] Always force an AI Generative Assault payload to feed BetaAgent
        ai_packet = JobPacket(
            priority=TaskPriority.NORMAL,
            target=TaskTarget(url=target_config['url']),
            config=ModuleConfig(
                module_id="sigma_generative_blast",
                agent_id=AgentID.SIGMA,
                params={
                    "concurrency": target_config.get("concurrency", 50),
                    "rps": target_config.get("rps", 100)
                }
            )
        )

        await bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="Orchestrator",
            scan_id=scan_id,
            payload=ai_packet.model_dump()
        ))

        # [V6 REAL-TIME FIX] Also dispatch a direct Beta assault job to ensure real-time attacks
        beta_assault_packet = JobPacket(
            priority=TaskPriority.HIGH,
            target=TaskTarget(url=target_config['url']),
            config=ModuleConfig(
                module_id="beta_direct_assault",
                agent_id=AgentID.BETA,
                aggression=8
            )
        )
        await bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="Orchestrator",
            scan_id=scan_id,
            payload=beta_assault_packet.model_dump()
        ))

        await manager.broadcast({"type": "GI5_LOG", "payload": "HYPER-MIND ONLINE. Parallel Overdrive Active."})

        # 6. Run Duration (Custom duration from config or default)
        duration_val = target_config.get('duration')
        scan_duration = int(duration_val) if duration_val is not None else settings.SCAN_TIMEOUT
        scan_duration = max(scan_duration, 1) # Ensure at least 1s
        try:
            await asyncio.sleep(scan_duration)
        except asyncio.CancelledError:
            pass
        finally:
            await manager.broadcast({"type": "GI5_LOG", "payload": "Hyper-Mind: Mission Complete. Shutting down."})
            for agent in agents:
                try:
                    await asyncio.wait_for(agent.stop(), timeout=5.0)
                except Exception as e:
                    logger.error(f"Failed to stop agent {agent.name}: {e}")
            
            # --- V6 GRACE PERIOD ---
            await asyncio.sleep(1.0)
            
            # --- SHUTDOWN CORTEX ENSURING SOCKET RELEASE ---
            await ai_cortex.shutdown()
            
            # --- AWAIT CAPTURED ORPHAN TASKS ---
            if HiveOrchestrator._orphaned_tasks:
                await asyncio.gather(*HiveOrchestrator._orphaned_tasks, return_exceptions=True)
                HiveOrchestrator._orphaned_tasks.clear()
            
            # --- SCAN ISOLATION: UNSUBSCRIBE LISTENERS ---
            for etype in EventType:
                bus.unsubscribe(etype, event_listener)
            
            # Clear registry
            HiveOrchestrator.active_agents.clear()
            print(f"[Orchestrator] Scan {scan_id} Cleaned Up. Listeners detached.")
            
            # --- GENERATE GOD MODE REPORT ---
            try:
                items_found = [e for e in scan_events if e.get('type') in (EventType.VULN_CONFIRMED, "VULN_CONFIRMED")]
                stats_db_manager.complete_scan(scan_id, items_found, scan_duration)
                await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Finalizing"}})
            except Exception as e:
                logger.error(f"Failed to record complete_scan (Finalizing): {e}")

            # --- FINAL MEMORY PURGE (Hard-Zero Gap Fix) ---
            try:
                await self.bus.evict_scan_context(scan_id)
            except Exception: pass

            try:
                async def generate_and_mark_ready():
                    try:
                        report_gen = ReportGenerator()
                        print(f"[Orchestrator] Starting AI report generation for scan {scan_id}...")
                        
                        end_time = datetime.now()
                        requested_concurrency = target_config.get('velocity', len(agents))
                        
                        # Get REAL AI telemetry from CortexEngine
                        cortex_telemetry = ai_cortex.get_telemetry()
                        real_ai_calls = cortex_telemetry.get("llm_calls", 0)
                        real_avg_latency = cortex_telemetry.get("avg_llm_latency", 0.0)
                        real_cb_trips = cortex_telemetry.get("circuit_breaker_trips", 0)
                        
                        total_attack_events = sum(1 for e in scan_events if e.get('type') in (EventType.LIVE_ATTACK, "LIVE_ATTACK"))
                        avg_request_latency = round((scan_duration / max(total_attack_events, 1)) * 1000, 1)
                        
                        telemetry = {
                            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "duration": f"{scan_duration}s",
                            "total_requests": len(scan_events),
                            "avg_latency_ms": avg_request_latency,
                            "peak_concurrency": requested_concurrency,
                            "ai_calls": real_ai_calls,
                            "llm_avg_latency": f"{real_avg_latency:.1f}" if real_avg_latency else "N/A",
                            "circuit_breaker_activations": real_cb_trips,
                        }
                        
                        await asyncio.wait_for(
                            report_gen.generate_report(scan_id, scan_events, target_config['url'], telemetry=telemetry, manager=manager),
                            timeout=900.0
                        )
                        
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                        
                        stats_db_manager.flush_immediate()
                        print(f"[Orchestrator] AI Report for {scan_id} is now READY and SYNCED with UI.")
                    except asyncio.TimeoutError:
                        print(f"[Orchestrator] Report generation TIMED OUT for {scan_id}. Forcing ready.")
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                                
                        stats_db_manager.flush_immediate()
                    except Exception as ge:
                        print(f"[Orchestrator] Background Report Async Task Error: {ge}")
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                                
                        stats_db_manager.flush_immediate()
                        import traceback
                        traceback.print_exc()

                task = asyncio.create_task(generate_and_mark_ready())
                HiveOrchestrator._orphaned_tasks.add(task)
                task.add_done_callback(HiveOrchestrator._orphaned_tasks.discard)
                
                await manager.broadcast({"type": "GI5_LOG", "payload": f"FORENSIC REPORT GENERATION INITIATED FOR {scan_id}"})
            except Exception as e:
                logger.error(f"Report Background Gen Trigger Failed: {e}")

            await manager.broadcast({"type": "GI5_LOG", "payload": f"SCAN FINISHED. AI FINALIZING FORENSIC DATA FOR {scan_id}..."})

    @staticmethod
    async def _cluster_telemetry_loop(redis_url: str, scan_id: str):
        """Syncs distributed cluster metrics to the UI Dashboard."""
        import redis
        import json
        try:
            r = redis.from_url(redis_url)
            while True:
                # 1. Gather Metrics
                worker_data = r.hgetall("workers")
                worker_count = len(worker_data)
                queue_depth = r.llen("pending_tasks")
                audit_depth = r.llen("xytherion_audit_queue")
                
                # 2. Broadcast to UI
                await manager.broadcast({
                    "type": "CLUSTER_TELEMETRY",
                    "payload": {
                        "scan_id": scan_id,
                        "workers_active": worker_count,
                        "queue_depth": queue_depth,
                        "audit_depth": audit_depth,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })
                
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:

            pass
        except Exception as e:
            logger.debug(f"Cluster Telemetry loop failure: {e}")

