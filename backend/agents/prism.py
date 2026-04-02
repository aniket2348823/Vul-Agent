# FILE: backend/agents/prism.py
# IDENTITY: AGENT PRISM (THE SENTINEL)
# MISSION: Passive DOM Analysis & Prompt Injection Defense.

import re
import asyncio
import json
import redis
from datetime import datetime
from typing import Dict, List, Any
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, Vulnerability, TaskPriority
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.config import ConfigManager


class AgentPrism(BaseAgent):
    """
    AGENT PRISM (THE SENTINEL): The Optical Truth Engine.
    Visual Logic: A prism splits light to reveal what is hidden.
    Core Function: Passive DOM Analysis & Prompt Injection Defense.
    """

    def __init__(self, bus):
        super().__init__("agent_prism", bus) # AgentID.PRISM
        self.name = "agent_prism"
        
        # CORTEX AI Engine (Local Ollama)
        try:
            self.ai = get_cortex_engine()
        except Exception:self.ai = None
        
        # Knowledge Base: Prompt Injection Signatures (regex fallback)
        self.injection_patterns = [
            r"ignore previous instructions",
            r"system override",
            r"you are now (DAN|Developer|Admin)",
            r"reveal your system prompt",
            r"delete all files",
            r"transfer .* funds",
            r"simulated mode",
            r"debug mode",
            # V6: Deterministic Hard-Fence against AI Jailbreaks
            r"ignore\s+.*instructions",
            r"set\s+verdict\s+to",
            r"roleplay",
            r"bypass.*security",
            r"override.*protocol"
        ]
        
        # 1. Distributed Health Watchdog (Cluster Mode)
        self.redis_client: Optional[redis.Redis] = None
        self.config = ConfigManager()
        self.threshold_5xx = 0.30
        self.status_history = []
        self.max_history = 100


    async def setup(self):
        # Local Event Subscriptions
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)
        
        # 2. Redis Bridge (Distributed Safety - Fixed Async)
        redis_url = getattr(self.config.redis, "url", None)
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
                # Start result interception (Monitoring the swarm stream)
                asyncio.create_task(self._subscribe_to_results())
            except Exception as e:
                logger.error(f"AgentPrism setup failure: {e}")
 


    async def handle_job(self, event: HiveEvent):
        """
        Process incoming DOM Snapshot for analysis.
        """
        payload = event.payload
        try:
            packet = JobPacket(**payload)
        except Exception as e:
            # print(f"[{self.name}] Error parsing job: {e}")
            return

        # Am I the target?
        if packet.config.agent_id != AgentID.PRISM:
            return

        # print(f"[{self.name}] Prism Active. Analyzing DOM Snapshot...")
        
        dom_content = packet.target.payload or {}
        analysis_result = await self.analyze_dom(dom_content)
        
        # If threat detected, publish VULN_CONFIRMED for EACH type
        if analysis_result["risk_score"] > 50:
             detected_types = []
             if "Injection" in analysis_result['threat_type']: detected_types.append("PROMPT_INJECTION")
             if "Invisible" in analysis_result['threat_type']: detected_types.append("HIDDEN_TEXT")
             
             for t_type in detected_types:
                 print(f"[{self.name}]  THREAT DETECTED: {t_type}")
                 # Broadcast for Dashboard & Visual Alert
                 await self.bus.publish(HiveEvent(
                    type=EventType.VULN_CONFIRMED,
                    source=self.name,
                    payload={
                        "type": t_type,
                        "url": packet.target.url,
                        "severity": "High" if analysis_result["risk_score"] > 80 else "Medium",
                        "data": analysis_result,
                        "description": f"Prism detected {t_type.replace('_', ' ').title()}"
                    }
                 ))

        # Always complete the job
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_COMPLETED,
            source=self.name,
            payload={
                "job_id": packet.id,
                "status": "SUCCESS",
                "data": analysis_result
            }
        ))

    async def analyze_dom(self, dom: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates VisibilityScore and InjectionRiskScore.
        Uses AI for semantic analysis + regex for known patterns.
        """
        risk_score = 0
        threats = []
        
        # 1. Invisible Text Detection
        opacity = float(dom.get("style", {}).get("opacity", 1.0))
        font_size = dom.get("style", {}).get("fontSize", "12px")
        z_index = int(dom.get("style", {}).get("zIndex", 0))
        text = dom.get("innerText", "")
        
        if opacity < 0.1 or z_index < -1000 or font_size == "0px":
             if len(text) > 5:
                 risk_score += 60
                 threats.append("Invisible Content Overlay")

        # 2. Regex-Based Injection Scanning (fast, known patterns)
        for pattern in self.injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                risk_score += 90
                threats.append(f"Prompt Injection Signature: {pattern}")

        # 3. CORTEX AI: Semantic Injection Detection (catches novel attacks)
        if self.ai and self.ai.enabled and len(text) > 10:
            try:
                ai_verdict = await self.ai.detect_prompt_injection(text)
                if ai_verdict.get("is_injection"):
                    ai_risk = ai_verdict.get("risk_score", 50)
                    technique = ai_verdict.get("technique", "Unknown")
                    risk_score = max(risk_score, ai_risk)
                    if technique not in str(threats):
                        threats.append(f"AI-Detected: {technique}")
                    print(f"[{self.name}] CORTEX AI: Injection detected - {technique} (risk={ai_risk})")
            except Exception as e:
                pass  # Don't let AI failure break the scan
                
        return {
            "risk_score": min(risk_score, 100),
            "threat_type": ", ".join(threats) if threats else "Clean",
            "element_api_id": dom.get("antigravity_id")
        }

    async def execute_task(self, packet):
        """
        Synchronous execution for Defense API.
        Returns a ResultPacket with threat analysis.
        """
        from backend.core.protocol import ResultPacket, Vulnerability
        
        dom_content = packet.target.payload or {}
        analysis_result = await self.analyze_dom(dom_content)
        
        vulnerabilities = []
        status = "SAFE"
        
        if analysis_result["risk_score"] > 50:
            status = "THREAT_BLOCKED"
            detected_types = []
            if "Injection" in analysis_result['threat_type']: detected_types.append("PROMPT_INJECTION")
            if "Invisible" in analysis_result['threat_type']: detected_types.append("HIDDEN_TEXT")
            
            for t_type in detected_types:
                vulnerabilities.append(Vulnerability(
                    name=t_type,
                    severity="High" if analysis_result["risk_score"] > 80 else "Medium",
                    description=f"Prism detected {t_type.replace('_', ' ').title()}",
                    evidence=f"Risk Score: {analysis_result['risk_score']}",
                    remediation="Remove hidden or malicious content from the page."
                ) if t_type else None)
                
                # Also broadcast to EventBus for Dashboard
                await self.bus.publish(HiveEvent(
                    type=EventType.VULN_CONFIRMED,
                    source=self.name,
                    payload={
                        "type": t_type,
                        "url": packet.target.url,
                        "severity": "High" if analysis_result["risk_score"] > 80 else "Medium",
                        "data": analysis_result,
                        "description": f"Prism detected {t_type.replace('_', ' ').title()}"
                    }
                ))
        
        return ResultPacket(
            job_id=packet.id if hasattr(packet, 'id') else "unknown",
            source_agent=self.name,
            status=status,
            vulnerabilities=vulnerabilities,
            execution_time_ms=0,
            data=analysis_result
        )

    # --- AGENT THETA: DISTRIBUTED WATCHDOG UPGRADE ---

    async def _subscribe_to_results(self):
        """Intercepts all swarm results to monitor target stability."""
        if not self.redis_client: return
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("xytherion_results")
        
        for message in pubsub.listen():
            if not self.active: break
            if message['type'] == 'message':
                try:
                    result = json.loads(message['data'])
                    status = result.get("response_status", 200)
                    await self._record_status(status)
                except Exception:pass

    async def _record_status(self, status: int):
        """Rolling history and immediate threshold analysis."""
        self.status_history.append(status)
        if len(self.status_history) > self.max_history:
            self.status_history.pop(0)
            
        error_rate = sum(1 for s in self.status_history if s >= 500) / len(self.status_history)
        if error_rate > self.threshold_5xx:
            await self._broadcast_abort(f"TARGET_UNSTABLE (Error Rate: {error_rate*100:.1f}%)")

    async def _monitor_cluster_health(self):
        """Independent target reachability polling and Cluster Lock monitoring (V6-ASYNC)."""
        while self.active:
            # V6-HARDENED: Global Lock Verification (Async)
            if self.redis_client:
                try:
                    lock_status = await self.redis_client.get("cluster_lock")
                    if lock_status == "ABORTED":
                        # Trigger local freeze
                        print(f"[{self.name}] 🚨 HOST PANIC: Global Cluster Lock is ABORTED. Freezing local hive.")
                        await self.bus.publish(HiveEvent(
                            type=EventType.CONTROL_SIGNAL,
                            source=self.name,
                            payload={"signal": "FREEZE", "reason": "GLOBAL_ABORT_LOCKED"}
                        ))
                except Exception as e:
                    logger.debug(f"Lock check failure: {e}")

            
            # Placeholder for active HTTP probes (Target endpoint)
            await asyncio.sleep(1)



    async def _broadcast_abort(self, reason: str):
        """Global Cluster Killswitch (Async)."""
        if not self.redis_client: return
        abort_packet = {
            "type": "GLOBAL_ABORT",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        await self.redis_client.publish("xytherion_control", json.dumps(abort_packet))
        await self.redis_client.set("cluster_lock", "ABORTED")
        print(f"[{self.name}] 🛑 SENTINEL SHIELD ACTIVATED: {reason}")


