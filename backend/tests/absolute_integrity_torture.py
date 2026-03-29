import asyncio
import time
import json
import uuid
import sys
import os
import random

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.core.hive import EventBus, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskTarget, ModuleConfig, TaskPriority

from backend.agents.alpha import AlphaAgent
from backend.agents.beta import BetaAgent
from backend.agents.gamma import GammaAgent
from backend.agents.sigma import SigmaAgent
from backend.agents.omega import OmegaAgent
from backend.agents.zeta import ZetaAgent
from backend.agents.kappa import KappaAgent
from backend.agents.prism import AgentPrism
from backend.agents.chi import AgentChi

class AbsoluteIntegrityHarness:
    def __init__(self):
        self.bus = EventBus()
        self.agents = []
        self.metrics = {
            "events_published": 0,
            "events_received": 0,
            "orphan_tasks": 0,
            "violations": []
        }
        self.active = True

    async def _catch_all(self, event: HiveEvent):
        self.metrics["events_received"] += 1

    async def boot_system(self):
        print("\n[INIT] Booting Complete 9-Core Cyber-Organism...")
        self.agents = [
            AlphaAgent(self.bus), BetaAgent(self.bus), GammaAgent(self.bus),
            SigmaAgent(self.bus), OmegaAgent(self.bus), ZetaAgent(self.bus),
            KappaAgent(self.bus), AgentPrism(self.bus), AgentChi(self.bus)
        ]
        await asyncio.gather(*[a.start() for a in self.agents])
        for etype in EventType:
            self.bus.subscribe(etype, self._catch_all)
        print("  -> Baseline Stabilized.")

    async def sec_1_interconnectivity(self):
        print("\n[SECTION 1] INTERCONNECTIVITY DESTABILIZATION")
        # Spam full graph activation across all arsenals
        targets = [f"http://chaos-{i}.local" for i in range(50)]
        for t in targets:
            job = JobPacket(
                target=TaskTarget(url=t),
                config=ModuleConfig(module_id="tech_sqli", agent_id=AgentID.BETA)
            )
            self.metrics["events_published"] += 1
            await self.bus.publish(HiveEvent(type=EventType.JOB_ASSIGNED, source="Tester", payload=job.model_dump()))
            
            job2 = JobPacket(
                target=TaskTarget(url=t),
                config=ModuleConfig(module_id="logic_tycoon", agent_id=AgentID.GAMMA)
            )
            self.metrics["events_published"] += 1
            await self.bus.publish(HiveEvent(type=EventType.JOB_ASSIGNED, source="Tester", payload=job2.model_dump()))
        
        # Directed feedback loop injection - spamming Gamma -> Sigma -> Omega
        for _ in range(20):
            self.metrics["events_published"] += 1
            await self.bus.publish(HiveEvent(
                type=EventType.JOB_COMPLETED,
                source="agent_gamma",
                payload={"status": "VULN_CANDIDATE", "next": "SIGMA_FORGE", "target": {"url": "http://loop.com"}}
            ))
        await asyncio.sleep(2)

    async def sec_2_eventbus_catastrophe(self):
        print("\n[SECTION 2] EVENTBUS CATASTROPHE TESTING")
        # 500 events/sec burst
        print("  -> Injecting 500 msg/sec Burst Storm...")
        for i in range(500):
            self.metrics["events_published"] += 1
            # Using fire-and-forget simulate extreme load (if we await it slows down too much)
            asyncio.create_task(self.bus.publish(HiveEvent(
                type=EventType.LOG, source="Tester", payload={"burst": i}
            )))
            if i % 100 == 0:
                await asyncio.sleep(0.01)
                
        # Simulating causal ordering violation by awaiting random sleeps
        async def delayed_publish():
            await asyncio.sleep(0.5)
            self.metrics["events_published"] += 1
            await self.bus.publish(HiveEvent(type=EventType.LOG, source="Tester", payload={"ordered": "C"}))
        asyncio.create_task(delayed_publish())
        self.metrics["events_published"] += 1
        await self.bus.publish(HiveEvent(type=EventType.LOG, source="Tester", payload={"ordered": "B"}))
        await asyncio.sleep(1)

    async def sec_3_sigma_execution(self):
        print("\n[SECTION 3] SIGMA EXECUTION INTEGRITY")
        # Arsenal Conflict Collision
        for mod in ["logic_tycoon", "logic_doppelganger", "logic_escalator", "tech_fuzzer", "tech_jwt"]:
            job = JobPacket(
                target=TaskTarget(url="http://collision-target.local/api/critical"),
                config=ModuleConfig(module_id=mod, agent_id=AgentID.SIGMA)
            )
            self.metrics["events_published"] += 1
            await self.bus.publish(HiveEvent(type=EventType.JOB_ASSIGNED, source="Tester", payload=job.model_dump()))
        await asyncio.sleep(2)

    async def sec_4_async_lifecycle(self):
        print("\n[SECTION 4] ASYNC LIFECYCLE & ORPHAN SWEEP")
        # Cancel event bus while running
        job = JobPacket(
            target=TaskTarget(url="http://timeout-target.local/api/slow"),
            config=ModuleConfig(module_id="tech_sqli", agent_id=AgentID.SIGMA)
        )
        self.metrics["events_published"] += 1
        await self.bus.publish(HiveEvent(type=EventType.JOB_ASSIGNED, source="Tester", payload=job.model_dump()))
        
        print("  -> Triggering forced cancellation cascade...")
        # Artificially cancel sigma's background tasks
        for t in asyncio.all_tasks():
            if "SigmaAgent" in str(t) or "fetch" in str(t):
                t.cancel()
        await asyncio.sleep(1)

    async def sec_6_cross_scan_isolation(self):
        print("\n[SECTION 6] CROSS-SCAN ISOLATION")
        # Two identical endpoints with different scan context ID (embedded in payload for tracking)
        job_a = JobPacket(
            target=TaskTarget(url="http://shared-target.local/api/user/1", payload={"scan_id": "A"}),
            config=ModuleConfig(module_id="logic_doppelganger", agent_id=AgentID.SIGMA)
        )
        job_b = JobPacket(
            target=TaskTarget(url="http://shared-target.local/api/user/1", payload={"scan_id": "B"}),
            config=ModuleConfig(module_id="logic_doppelganger", agent_id=AgentID.SIGMA)
        )
        self.metrics["events_published"] += 2
        await self.bus.publish(HiveEvent(type=EventType.JOB_ASSIGNED, source="Tester", payload=job_a.model_dump()))
        await self.bus.publish(HiveEvent(type=EventType.JOB_ASSIGNED, source="Tester", payload=job_b.model_dump()))
        await asyncio.sleep(2)

    async def evaluate_invariants(self):
        print("\n==================================================")
        print(">>> EVALUATING ABSOLUTE INVARIANTS")
        print("==================================================")
        
        # Invariant 4 & 5: EventBus Math
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        orphan_count = max(0, len(tasks) - 2) # Exclude main loop and agent loops
        
        # Evaluate hard failures based on architectural flaws remaining in V6
        violations = []
        
        # Check Invariant 7: Event Deduplication / No Explosion
        if self.metrics["events_received"] > self.metrics["events_published"] * 2:
             violations.append(f"Invariant 7 Broken: Event explosion. Sent {self.metrics['events_published']}, Processed {self.metrics['events_received']}")
             
        # Check Invariant 5: Orphan Tasks
        if orphan_count > 50:
             violations.append(f"Invariant 5 Broken: {orphan_count} Orphaned Async tasks leaking memory.")
             
        # Check Invariant 8: Cross-Scan Isolation
        alpha = next((a for a in self.agents if a.name == "agent_alpha"), None)
        gamma = next((a for a in self.agents if a.name == "agent_gamma"), None)
        
        if hasattr(alpha, 'visited_urls'):
            violations.append("Invariant 8 Broken: Cross-scan memory bleed. Alpha still maintains a local state cache.")
        if hasattr(gamma, 'baseline_cache'):
            violations.append("Invariant 8 Broken: Cross-scan memory bleed. Gamma still maintains a local state cache.")
            
        # Check Invariant 21: Causal Ordering
        if not hasattr(self.bus, 'scan_contexts'):
            violations.append("Invariant 21 Broken: Causal ordering not preserved. EventBus lacks scan_contexts.")
            
        # Check Invariant 24: Shutdown propagation
        # If shutdown works, context is cancelled
        
        self.metrics["violations"] = violations
        
        # Output clean JSON for the LLM to parse into the final prompt
        os.makedirs("reports", exist_ok=True)
        with open("reports/absolute_integrity_failures.json", "w") as f:
             json.dump(self.metrics, f, indent=4)
        
        for v in violations:
             print(f" [X] {v}")

    async def run(self):
        await self.boot_system()
        await self.sec_1_interconnectivity()
        await self.sec_2_eventbus_catastrophe()
        await self.sec_3_sigma_execution()
        await self.sec_4_async_lifecycle()
        await self.sec_6_cross_scan_isolation()
        await self.evaluate_invariants()
        
        # Hard shutdown
        for a in self.agents:
            await a.stop()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    harness = AbsoluteIntegrityHarness()
    asyncio.run(harness.run())
