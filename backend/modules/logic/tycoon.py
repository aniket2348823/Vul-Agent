import aiohttp
import time
from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, ResultPacket, Vulnerability, AgentID, TaskTarget
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

cortex = get_cortex_engine()

class TheTycoon(BaseArsenalModule):
    """
    MODULE: THE TYCOON
    Category: Logic Assassin (Financial)
    Advanced Capabilities:
    1. Negative Quantity Injection (Integer Overflow)
    2. Floating Point Rounding (0.1 + 0.2 != 0.3)
    3. Currency Arbitrage
    """
    def __init__(self):
        super().__init__()
        self.name = "The Tycoon"

    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        target = packet.target
        targets = []
        
        # HYBRID AI: Generate financial attack vectors
        ai_vectors = await cortex.generate_financial_vectors(target.url, target.payload)
        
        # VECTOR 1: Standard + AI-generated financial attacks
        test_values = [(-1, "Negative Quantity"), (2147483648, "Integer Overflow")]
        for vec in ai_vectors:
            if isinstance(vec, dict) and "value" in vec:
                test_values.append((vec["value"], vec.get("attack", "AI_Generated")))
        
        for qty, attack_name in test_values:
            payload_qty = target.payload.copy() if target.payload else {}
            payload_qty["quantity"] = qty
            targets.append(TaskTarget(
                url=target.url, method="POST", headers=target.headers, payload=payload_qty
            ))

        # VECTOR 2: FLOATING POINT ROUNDING
        payload_float = target.payload.copy() if target.payload else {}
        payload_float["price"] = 0.00001
        payload_float["amount"] = 1000
        targets.append(TaskTarget(
            url=target.url, method="POST", headers=target.headers, payload=payload_float
        ))
        
        return targets

    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        vulns = []
        for target, text in interactions:
            if isinstance(text, str) and ("success" in text.lower() or "order confirmed" in text.lower()):
                if target.payload and "quantity" in target.payload:
                    qty = target.payload.get("quantity")
                    vulns.append(Vulnerability(
                        name="Financial Logic Flaw (Qty)",
                        severity="CRITICAL",
                        description=f"Server accepted quantity {qty}, potentially refunding or overflowing.",
                        evidence=str(target.payload),
                        remediation="Perform strict validation on quantity and ensure it is > 0."
                    ))
                elif target.payload and "price" in target.payload:
                    vulns.append(Vulnerability(
                        name="Precision Rounding Bypass",
                        severity="HIGH",
                        description="Server accepted sub-atomic currency values.",
                        evidence=str(target.payload),
                        remediation="Validate decimal precision matches currency constraints."
                    ))
        return vulns
