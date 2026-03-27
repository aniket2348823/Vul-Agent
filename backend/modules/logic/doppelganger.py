import difflib
from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, Vulnerability, TaskTarget
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine

cortex = CortexEngine()

class Doppelganger(BaseArsenalModule):
    """
    MODULE: DOPPELGANGER
    Logic: Insecure Direct Object Reference (IDOR).
    Cyber-Organism Protocol: Cosine Similarity Diffing.
    """
    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        target = packet.target
        user_a_token = target.headers.get("Authorization")
        if not user_a_token:
            return []
            
        # Simulated User B Token
        user_b_token = "Bearer MOCK_USER_B_TOKEN"
        headers_b = target.headers.copy()
        headers_b["Authorization"] = user_b_token
        
        return [
            target, # Baseline Target (User A)
            TaskTarget(url=target.url, method=target.method, headers=headers_b, payload=target.payload) # Attack Target (User B)
        ]

    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        if len(interactions) < 2: return []
        
        baseline_target, baseline_text = interactions[0]
        attack_target, attack_text = interactions[1]
        
        vulns = []
        if isinstance(attack_text, str) and isinstance(baseline_text, str):
            ratio = difflib.SequenceMatcher(None, baseline_text, attack_text).ratio()
            if ratio > 0.95:
                idor_analysis = await cortex.classify_idor_response(attack_text, ratio)
                sensitivity = idor_analysis.get("sensitivity", "HIGH")
                data_types = idor_analysis.get("data_types", [])
                
                vulns.append(Vulnerability(
                    name="IDOR (Broken Access Control)",
                    severity="CRITICAL" if sensitivity in ["CRITICAL", "HIGH"] else "HIGH",
                    description=f"User B access confirmed. Similarity: {ratio*100:.2f}%. Sensitivity: {sensitivity}. Data: {data_types}",
                    evidence=f"Diff Ratio: {ratio}, AI Sensitivity: {sensitivity}",
                    remediation="Implement strict object-level authorization matching session ID to resource owner."
                ))
        return vulns
