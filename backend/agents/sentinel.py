# FILE: backend/agents/sentinel.py
# IDENTITY: AGENT THETA (THE SENTINEL)
# MISSION: Passive DOM Analysis & Prompt Injection Defense.

import re
import asyncio
from typing import Dict, List, Any
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, Vulnerability, TaskPriority
from backend.ai.cortex import CortexEngine

class AgentTheta(BaseAgent):
    """
    AGENT THETA (THE SENTINEL): The Optical Truth Engine.
    Visual Logic: A prism splits light to reveal what is hidden.
    Core Function: Passive DOM Analysis & Prompt Injection Defense.
    """

    def __init__(self, bus):
        super().__init__("agent_theta", bus) # AgentID.THETA
        self.name = "agent_theta"
        
        # CORTEX AI Engine (Local Ollama)
        try:
            self.ai = CortexEngine()
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
            r"debug mode"
        ]

    async def setup(self):
        # Subscribe to new jobs (specifically from Defense API)
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)

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
        if packet.config.agent_id != AgentID.THETA:
            return

        # print(f"[{self.name}] Sentinel Active. Analyzing DOM Snapshot...")
        
        dom_content = packet.target.payload or {}
        analysis_result = await self.analyze_dom(dom_content)
        
        # If threat detected, publish VULN_CONFIRMED for EACH type
        if analysis_result["risk_score"] > 50:
             detected_types = []
             if "Injection" in analysis_result['threat_type']: detected_types.append("PROMPT_INJECTION")
             if "Invisible" in analysis_result['threat_type']: detected_types.append("HIDDEN_TEXT")
             
             for t_type in detected_types:
                 print(f"[{self.name}] ðŸ‘ï¸ THREAT DETECTED: {t_type}")
                 # Broadcast for Dashboard & Visual Alert
                 await self.bus.publish(HiveEvent(
                    type=EventType.VULN_CONFIRMED,
                    source=self.name,
                    payload={
                        "type": t_type,
                        "url": packet.target.url,
                        "severity": "High" if analysis_result["risk_score"] > 80 else "Medium",
                        "data": analysis_result,
                        "description": f"Sentinel detected {t_type.replace('_', ' ').title()}"
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
                    description=f"Sentinel detected {t_type.replace('_', ' ').title()}",
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
                        "description": f"Sentinel detected {t_type.replace('_', ' ').title()}"
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
