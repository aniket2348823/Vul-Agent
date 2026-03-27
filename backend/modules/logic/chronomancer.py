from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, Vulnerability, TaskTarget

class Chronomancer(BaseArsenalModule):
    """
    MODULE: CHRONOMANCER
    Logic: Race Conditions (Concurrency Exploitation).
    Cyber-Organism Protocol: Gate Synchronization (Single Packet Flood).
    """
    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        # Cyber-Organism Protocol: 20 Parallel Connections (Single Packet Flood via gather)
        return [packet.target] * 20

    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        vulns = []
        
        # Analysis: Did we get multiple successes?
        # Since we lost HTTP status codes, we assume success if response contains "success" or "redeem"
        success_count = sum(1 for _, text in interactions if isinstance(text, str) and ("success" in text.lower() or "redeem" in text.lower() or "confirm" in text.lower()))
        
        # If target logic was "Redeem Coupon", and we got 20 successes...
        if success_count > 1:
            vulns.append(Vulnerability(
                name="Race Condition (Concurrency Exploitation)",
                severity="HIGH",
                description=f"Executed 20 parallel requests. {success_count} succeeded simultaneously.",
                evidence=f"Success Rate: {success_count}/20",
                remediation="Implement strict database locks, atomic operations, or mutexes."
            ))

        return vulns
