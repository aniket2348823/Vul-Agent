# FILE: backend/agents/chi.py
# IDENTITY: AGENT CHI (THE INSPECTOR)
# MISSION: Active Event Interception & Dark Pattern Blocking.

import asyncio
import json
import redis
import re
from typing import Dict, List, Any, Pattern
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, Vulnerability, TaskPriority
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.ai.gi5 import brain
from backend.core.config import ConfigManager
from backend.core.keyring_intelligence import KeyringIntelligence


class AgentChi(BaseAgent):
    """
    AGENT CHI (THE INSPECTOR): The Kinetic Interceptor.
    Visual Logic: The Greek letter Chi (X) represents a "Block" or "Cross-out".
    Core Function: Active Event Interception & Dark Pattern Blocking.
    """

    def __init__(self, bus):
        super().__init__("agent_chi", bus) # AgentID.CHI
        self.name = "agent_chi"
        
        # CORTEX AI (Local Ollama)
        try:
            self.ai = get_cortex_engine()
        except Exception as e:
            from backend.core.hive import logger
            logger.debug(f"[{self.name}] AI Engine initialization deferred: {e}")
            self.ai = None


        
        # Knowledge Base: Deceptive Semantics
        self.safe_intent_keywords = ["cancel", "back", "close", "no", "decline"]
        self.risky_action_keywords = ["pay", "subscribe", "buy", "order", "confirm", "submit"]
        
        self.homoglyph_map = {
            "g00gle.com": "google.com",
            "linked1n.com": "linkedin.com",
            "paypa1.com": "paypal.com"
        }
        
        # 1. Distributed Payload Auditor (Cluster Mode)
        self.redis_client: Optional[redis.Redis] = None
        self.config = ConfigManager()
        self.blacklist: List[Pattern] = [
            re.compile(r"rm\s+-rf\s+/?", re.I),
            re.compile(r"DROP\s+DATABASE\s+", re.I),
            re.compile(r"mkfs\..*", re.I),
            re.compile(r":\(\)\{ :\|:& \};:", re.I)
        ]
        
        # 3. Dynamic Token Harvester
        self.keyring = KeyringIntelligence()


    async def setup(self):
        # Local Event Subscriptions
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)
        
        # 2. Redis Bridge (Distributed Safety - Fixed Async)
        redis_url = getattr(self.config.redis, "url", None)
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
                # Active payload auditing loop
                asyncio.create_task(self._audit_cluster_payloads())
            except Exception as e:
                print(f"[{self.name}] Safety Matrix failure: {e}")



    async def handle_job(self, event: HiveEvent):
        """
        Process incoming Intercepted Event (Click/Request).
        """
        payload = event.payload
        try:
            packet = JobPacket(**payload)
        except Exception as e:
            return

        # Am I the target?
        if packet.config.agent_id != AgentID.CHI:
            return

        # print(f"[{self.name}] Chi Active. Intercepting Kinetic Event...")
        
        # [NEW] Token Extraction Pipeline
        event_data = packet.target.payload or {}
        self._extract_and_store_tokens(event_data, packet.target.url)

        verdict = await self.judge_intent(event_data, packet.target.url)
        
        # If BLOCK verdict, publish VULN_CONFIRMED (which triggers Dashboard Alert)
        if verdict["action"] == "BLOCK":
             print(f"[{self.name}]  EVENT BLOCKED: {verdict['reason']}")
             
             await self.bus.publish(HiveEvent(
                type=EventType.VULN_CONFIRMED,
                source=self.name,
                payload={
                    "type": "DARK_PATTERN_BLOCK",
                    "url": packet.target.url,
                    "severity": "Critical",
                    "data": verdict,
                    "description": f"Chi Blocked: {verdict['reason']}"
                }
             ))
        
        # Return Verdict to Extension (via ResultPacket)
        # The Defense API will need to poll or wait for this result to release the browser pause.
        # For V1, we just log it, but in full implementation, this result goes back to API response.
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_COMPLETED,
            source=self.name,
            payload={
                "job_id": packet.id,
                "status": "SUCCESS" if verdict["action"] == "ALLOW" else "BLOCKED",
                "data": verdict
            }
        ))


    def _extract_and_store_tokens(self, data: Dict[str, Any], url: str):
        """Scans the payload/headers for potential tokens and logs them."""
        import json
        payload_str = json.dumps(data)
        
        # Quick regex scan for JWTs and Bearer tokens
        import re
        jwt_matches = re.finditer(r'(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)', payload_str)
        for m in jwt_matches:
            self.keyring.process_and_store(m.group(1), url, "auto-harvest")
            
        bearer_matches = re.finditer(r'(Bearer [A-Za-z0-9_-]{20,})', payload_str)
        for m in bearer_matches:
            self.keyring.process_and_store(m.group(1), url, "auto-harvest")

    async def judge_intent(self, data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Decides whether to ALLOW or BLOCK the event.
        """
        button_text = data.get("innerText", "").lower()
        target_action = data.get("action", "").lower() # e.g., URL or Form Action
        event_type = data.get("type", "click")
        
        # 1. GI5 OMEGA: Advanced Typosquatting & Forensics
        if url:
             from urllib.parse import urlparse
             domain = urlparse(url).netloc or url
             is_phish, root, dist = brain._detect_typosquatting(domain)
             if is_phish:
                  return {
                      "action": "BLOCK", 
                      "reason": f"GI5 OMEGA: Phishing Domain Detect (Mimics '{root}', Distance: {dist})",
                      "risk_score": 95
                  }

        # 1.1 Legacy Homoglyph Check (Safety Fallback)
        for fake, real in self.homoglyph_map.items():
            if fake in url:
                return {"action": "BLOCK", "reason": f"Phishing Domain Detected ({fake})"}

        # 2. Semantic Mismatch (Roach Motel)
        # If button says "Cancel" but action is "Pay/Submit"
        is_safe_label = any(w in button_text for w in self.safe_intent_keywords)
        is_risky_action = any(w in target_action for w in self.risky_action_keywords) or (data.get("method", "GET") == "POST")
        
        if is_safe_label and is_risky_action:
             return {
                 "action": "BLOCK", 
                 "reason": f"Deceptive UI: '{button_text}' triggers '{target_action}'",
                 "risk_score": 95
             }

        # 3. Aggressive Upgrade Upsell (Clickjacking stub)
        if data.get("is_overlay", False):
             return {"action": "BLOCK", "reason": "Clickjacking Overlay Detected"}

        # --- CONCRETE DARK PATTERN DETECTORS (Phase 3 Definition) ---

        # 4. Timing Side Channel Detection
        # >200ms delta between baseline and attack response = potential blind injection
        latency = data.get("latency", 0)
        baseline_latency = data.get("baseline_latency", 100)
        if latency and baseline_latency:
            try:
                delta = abs(float(latency) - float(baseline_latency))
                if delta > 200:
                    return {
                        "action": "BLOCK",
                        "reason": f"Timing Side Channel: {delta:.0f}ms delta (blind injection signature)",
                        "risk_score": min(95, 50 + int(delta / 10))
                    }
            except (ValueError, TypeError):
                pass

        # 5. Size Oracle Detection
        # >20% response size change = potential data leak
        response_size = data.get("response_size", 0)
        baseline_size = data.get("baseline_size", 0)
        if response_size and baseline_size:
            try:
                size_delta = abs(float(response_size) - float(baseline_size)) / max(float(baseline_size), 1)
                if size_delta > 0.20:
                    return {
                        "action": "BLOCK",
                        "reason": f"Size Oracle: {size_delta:.0%} response deviation (data leak indicator)",
                        "risk_score": min(95, 50 + int(size_delta * 100))
                    }
            except (ValueError, TypeError):
                pass

        # 6. Masked Error Detection
        # 200 OK but body contains error indicators = hidden server failure
        status_code = data.get("status", 0)
        response_body = str(data.get("response_body", data.get("body", ""))).lower()
        if status_code == 200 and response_body:
            masked_signals = ["undefined", "null", "nan", "internal server error",
                              "stack trace", "exception", "segfault", "core dump",
                              "syntax error", "fatal error", "access denied"]
            for signal in masked_signals:
                if signal in response_body:
                    return {
                        "action": "BLOCK",
                        "reason": f"Masked Error: 200 OK but body contains '{signal}' (hidden failure)",
                        "risk_score": 70
                    }

        # 7. Hidden Field Detection
        # Fields appearing only in attack responses that weren't in baseline
        baseline_fields = set(data.get("baseline_fields", []))
        attack_fields = set(data.get("response_fields", []))
        if baseline_fields and attack_fields:
            new_fields = attack_fields - baseline_fields
            sensitive_keywords = ["admin", "token", "secret", "password", "key", "ssn", "credit"]
            leaked_fields = [f for f in new_fields if any(kw in f.lower() for kw in sensitive_keywords)]
            if leaked_fields:
                return {
                    "action": "BLOCK",
                    "reason": f"Hidden Field Leak: {', '.join(leaked_fields[:3])} exposed in attack response",
                    "risk_score": 90
                }

        # --- END CONCRETE DETECTORS ---

        # 8. CORTEX AI: Semantic Intent Analysis (catches novel dark patterns)
        if self.ai and self.ai.enabled and button_text:
            try:
                ai_verdict = await self.ai.judge_user_intent(button_text, target_action or url, url)
                if ai_verdict.get("action") == "BLOCK":
                    return {
                        "action": "BLOCK",
                        "reason": f"AI-Detected: {ai_verdict.get('reason', 'Deceptive intent')}",
                        "risk_score": ai_verdict.get("risk_score", 80)
                    }
            except Exception:pass  # Don't let AI failure block legitimate clicks

        return {"action": "ALLOW", "reason": "Intent verified"}

    async def execute_task(self, packet):
        """
        Synchronous execution for Defense API.
        Returns a ResultPacket with intent verdict.
        """
        from backend.core.protocol import ResultPacket, Vulnerability
        
        event_data = packet.target.payload or {}
        verdict = await self.judge_intent(event_data, packet.target.url)
        
        vulnerabilities = []
        status = "SAFE"
        
        if verdict["action"] == "BLOCK":
            status = "THREAT_BLOCKED"
            vulnerabilities.append(Vulnerability(
                name="DARK_PATTERN_BLOCK",
                severity="Critical",
                description=f"Chi Blocked: {verdict['reason']}",
                evidence=f"Button: {event_data.get('innerText', 'Unknown')}",
                remediation="Fix the deceptive UI element."
            ))
            
            # Also broadcast to EventBus for Dashboard
            await self.bus.publish(HiveEvent(
                type=EventType.VULN_CONFIRMED,
                source=self.name,
                payload={
                    "type": "DARK_PATTERN_BLOCK",
                    "url": packet.target.url,
                    "severity": "Critical",
                    "data": verdict,
                    "description": vulnerabilities[0].description
                }
            ))
        
        return ResultPacket(
            job_id=packet.id if hasattr(packet, 'id') else "unknown",
            source_agent=self.name,
            status=status,
            vulnerabilities=vulnerabilities,
            execution_time_ms=0,
            data=verdict
        )

    # --- AGENT IOTA: DISTRIBUTED AUDITOR UPGRADE ---

    async def _audit_cluster_payloads(self):
        """Intercepts and scrutinizes global swarm jobs before execution (V6-ASYNC)."""
        if not self.redis_client: return
        while self.active:
            try:
                # Use await to avoid blocking the event loop
                job_data = await self.redis_client.brpop("xytherion_audit_queue", timeout=5)
                if job_data:

                    event_dict = json.loads(job_data[1])
                    job_id = event_dict.get("id")
                    job_payload = event_dict.get("payload", {})
                    
                    # SEMANTIC AUDIT
                    is_safe, reason = await self._audit_logic(job_payload)
                    
                    if is_safe:
                        # Release to execution pool (Async)
                        await self.redis_client.lpush("pending_tasks", json.dumps(job_payload))
                    else:

                        print(f"[{self.name}] 🚨 IOTA BLOCK: {reason}")
                        await self._report_safety_violation(job_payload, reason)
                        
                        # V6-HARDENED: SIGNAL FAILURE TO HIVE
                        # Ensures the UI doesn't hang in 'PENDING'
                        await self.bus.publish(HiveEvent(
                            type=EventType.JOB_COMPLETED,
                            source=self.name,
                            payload={"job_id": job_id, "status": "BLOCKED", "reason": reason}
                        ))
            except Exception as e:
                logger.error(f"Inspector Audit Loop Error: {e}")
                await asyncio.sleep(1)

    async def _audit_logic(self, payload: Dict) -> tuple[bool, str]:
        """Deep pattern and semantic scrutiny for safety violations."""
        raw_payload = payload.get("payload", {})
        payload_str = json.dumps(raw_payload)
        
        # 1. HEURISTIC BLACKLIST
        for pattern in self.blacklist:
            if pattern.search(payload_str):
                return False, f"Blacklisted pattern detected: {pattern.pattern}"

        # 2. SEMANTIC AI SCRUTINY (V6-HARDENED)
        # Catches novel or obfuscated (Base64/Hex) destructive intents
        if self.ai and self.ai.enabled:
            # We use the 'judge_user_intent' heuristic for payload safety analysis
            verdict = await self.ai.judge_user_intent(
                "Execute Payload", 
                payload_str, 
                payload.get("target", {}).get("url", "")
            )
            if verdict.get("action") == "BLOCK":
                return False, f"AI Semantic Guardrail: {verdict.get('reason')}"
                
        return True, "Safe"

    async def _report_safety_violation(self, payload: Dict, reason: str):

        """Persists violation to common safety logs."""
        if not self.redis_client: return
        violation = {
            "type": "IOTA_VIOLATION",
            "task_id": payload.get("task_id", "???"),
            "timestamp": asyncio.get_event_loop().time()
        }
        self.redis_client.lpush("xytherion_safety_logs", json.dumps(violation))

