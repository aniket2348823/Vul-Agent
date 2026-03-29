from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, Vulnerability, TaskTarget
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

cortex = get_cortex_engine()

class TheEscalator(BaseArsenalModule):
    """
    MODULE: THE ESCALATOR
    Logic: Privilege Escalation (Mass Assignment).
    Cyber-Organism Protocol: Dictionary Merging & JSON Patching.
    """
    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        target = packet.target
        # Default payloads for dictionary merging
        payloads = [
            {"is_admin": True},
            {"role": "admin"},
            {"groups": ["root", "admin"]},
            {"permissions": "ALL"}
        ]
        
        # HYBRID AI: Add AI-guessed privilege parameters
        ai_params = await cortex.guess_privilege_params(target.url, target.payload)
        for p in ai_params:
            if isinstance(p, dict) and p not in payloads:
                payloads.append(p)
                
        targets = []
        for vector in payloads:
            merged_payload = target.payload.copy() if target.payload else {}
            merged_payload.update(vector)
            targets.append(TaskTarget(url=target.url, method="POST", headers=target.headers, payload=merged_payload))
            targets.append(TaskTarget(url=target.url, method="PATCH", headers=target.headers, payload=merged_payload))
            
        return targets
        
    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        vulns = []
        for target, text in interactions:
            if not isinstance(text, str): continue
            
            if "admin" in text.lower():
                meth = target.method
                severity = "CRITICAL" if meth == "PATCH" else "HIGH"
                vulns.append(Vulnerability(
                    name=f"Mass Assignment ({meth})", 
                    severity=severity, 
                    description=f"Accepted {target.payload} via {meth}",
                    evidence=f"Response contained 'admin' for payload {target.payload}",
                    remediation="Use explicit DTOs and block arbitrary model bindings."
                ))
        return vulns
