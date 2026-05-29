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
        """Confirm a race condition by counting concurrent CLEAN successes
        (Architecture §9.3): a success marker AND no denial/error marker. A
        single success is not a race; we require > 1 simultaneous clean success."""
        from backend.modules.evidence import logic_confirm

        vulns = []
        clean_successes = 0
        for _target, text in interactions:
            if not isinstance(text, str):
                continue
            ev = logic_confirm(text, positive_markers=["success", "redeem", "confirm", "applied"])
            if ev.verified:
                clean_successes += 1

        # The race signal is multiple clean concurrent successes where the logic
        # should have allowed only one.
        if clean_successes > 1:
            vulns.append(Vulnerability(
                name="Race Condition (Concurrency Exploitation)",
                severity="HIGH",
                description=f"Executed {len(interactions)} parallel requests; "
                            f"{clean_successes} succeeded simultaneously without denial.",
                evidence=f"Clean concurrent successes: {clean_successes}/{len(interactions)}",
                remediation="Implement strict database locks, atomic operations, or mutexes."
            ))
        return vulns
