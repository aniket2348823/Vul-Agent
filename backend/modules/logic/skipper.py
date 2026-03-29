import aiohttp
from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, ResultPacket, Vulnerability, AgentID, TaskTarget
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

cortex = get_cortex_engine()

class TheSkipper(BaseArsenalModule):
    """
    MODULE: THE SKIPPER
    Logic: Workflow Bypass (State Machine Violation).
    Cyber-Organism Protocol: Step Jumping & Referer Spoofing.
    """
    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        target = packet.target
        
        # HYBRID AI: Infer the full workflow chain
        workflow_steps = await cortex.infer_workflow_chain(target.url)
        success_url = target.url
        if workflow_steps:
            from urllib.parse import urljoin
            success_url = urljoin(target.url, workflow_steps[-1])
            
        targets = []
        # 1. Step Jumping (Direct Access)
        targets.append(TaskTarget(url=success_url, method="GET", headers=target.headers, payload=target.payload))
        
        # 2. Header Spoofing (Referer)
        headers_spoof = target.headers.copy()
        headers_spoof["Referer"] = target.url.replace("success", "payment") # Mock previous step
        targets.append(TaskTarget(url=success_url, method="GET", headers=headers_spoof, payload=target.payload))
        
        return targets

    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        vulns = []
        
        for idx, (target, text) in enumerate(interactions):
            if not isinstance(text, str): continue
            
            # Since we lost HTTP status codes in pure evaluation, we look for success strings
            is_success = "success" in text.lower() or "welcome" in text.lower() or "confirmed" in text.lower()
            
            if is_success:
                if idx == 0:
                    vulns.append(Vulnerability(
                        name="Workflow Bypass (Direct Access)", 
                        severity="HIGH", 
                        description="Accessed final step directly.",
                        evidence="Direct Access Successful",
                        remediation="Enforce state machine checks at each workflow step."
                    ))
                elif idx == 1:
                    vulns.append(Vulnerability(
                        name="Workflow Bypass (Referer Spoofing)", 
                        severity="CRITICAL", 
                        description="Accessed final step by spoofing Referer header.",
                        evidence=f"Referer: {target.headers.get('Referer', '')}",
                        remediation="Do not rely on Referer headers for authorization."
                    ))
        return vulns
