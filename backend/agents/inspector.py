# FILE: backend/agents/inspector.py
# IDENTITY: AGENT IOTA (THE INSPECTOR)
# MISSION: Active Event Interception & Dark Pattern Blocking.

import asyncio
from typing import Dict, List, Any
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, Vulnerability, TaskPriority
from backend.ai.cortex import CortexEngine

class AgentIota(BaseAgent):
    """
    AGENT IOTA (THE INSPECTOR): The Kinetic Interceptor.
    Visual Logic: The Greek letter Chi (X) represents a "Block" or "Cross-out".
    Core Function: Active Event Interception & Dark Pattern Blocking.
    """

    def __init__(self, bus):
        super().__init__("agent_iota", bus) # AgentID.IOTA
        self.name = "agent_iota"
        
        # CORTEX AI (Local Ollama)
        try:
            self.ai = CortexEngine()
        except Exception:self.ai = None
        
        # Knowledge Base: Deceptive Semantics
        self.safe_intent_keywords = ["cancel", "back", "close", "no", "decline"]
        self.risky_action_keywords = ["pay", "subscribe", "buy", "order", "confirm", "submit"]
        
        self.homoglyph_map = {
            "g00gle.com": "google.com",
            "linked1n.com": "linkedin.com",
            "paypa1.com": "paypal.com"
        }

    async def setup(self):
        # Subscribe to new jobs (from Defense API)
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)

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
        if packet.config.agent_id != AgentID.IOTA:
            return

        # print(f"[{self.name}] Inspector Active. Intercepting Kinetic Event...")
        
        event_data = packet.target.payload or {}
        verdict = await self.judge_intent(event_data, packet.target.url)
        
        # If BLOCK verdict, publish VULN_CONFIRMED (which triggers Dashboard Alert)
        if verdict["action"] == "BLOCK":
             print(f"[{self.name}] âŒ EVENT BLOCKED: {verdict['reason']}")
             
             await self.bus.publish(HiveEvent(
                type=EventType.VULN_CONFIRMED,
                source=self.name,
                payload={
                    "type": "DARK_PATTERN_BLOCK",
                    "url": packet.target.url,
                    "severity": "Critical",
                    "data": verdict,
                    "description": f"Inspector Blocked: {verdict['reason']}"
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

    async def judge_intent(self, data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Decides whether to ALLOW or BLOCK the event.
        """
        button_text = data.get("innerText", "").lower()
        target_action = data.get("action", "").lower() # e.g., URL or Form Action
        event_type = data.get("type", "click")
        
        # 1. Homoglyph Check
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

        # 4. CORTEX AI: Semantic Intent Analysis (catches novel dark patterns)
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
                description=f"Inspector Blocked: {verdict['reason']}",
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
