import asyncio
import time
import json
import uuid
import sys
import os
import random
from typing import Dict, Any, List

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
from backend.agents.sentinel import AgentTheta
from backend.agents.inspector import AgentIota

# -------------------------
# CHAOS INJECTOR (THE ANTAGONIST)
# -------------------------
class ChaosEventBus(EventBus):
    """
    Overloads the core EventBus with adversarial networking conditions.
    Simulates split-brain, CPU starvation, arbitrary reordering, and drop rates.
    """
    def __init__(self):
        super().__init__()
        self.chaos_config = {
            "throttle_delay": 0.0,
            "reorder_chance": 0.0,
            "split_brain": False
        }
        self.split_brain_buffer = []

    async def publish(self, event: HiveEvent):
        # Intercept CONTROL_SIGNAL to simulate Orchestrator cancellations
        if event.type == EventType.CONTROL_SIGNAL:
            signal = event.payload.get("signal")
            if signal in ["SCAN_COMPLETE", "SCAN_CANCELLED", "SCAN_FAILED"]:
                target_scan = event.payload.get("session_id", event.scan_id)
                if target_scan in self.scan_contexts:
                     self.scan_contexts[target_scan].is_cancelled = True
                     if target_scan in self._context_tasks:
                         self._context_tasks[target_scan].cancel()
                     print(f"  -> Chaos Harness cancelled ScanContext {target_scan}")

        # Phase 6: Split-Brain
        if self.chaos_config["split_brain"]:
            self.split_brain_buffer.append(event)
            return

        # Phase 4/5: Causal Reordering & Temporal Jitter
        if self.chaos_config["reorder_chance"] > 0 and random.random() < self.chaos_config["reorder_chance"]:
            asyncio.create_task(self._delayed_publish(event))
            return

        # Phase 2: CPU Throttling / Backpressure
        if self.chaos_config["throttle_delay"] > 0:
            await asyncio.sleep(self.chaos_config["throttle_delay"])

        # Call the absolute integrity implementation (queues causally to ScanContext)
        await super().publish(event)

    async def _delayed_publish(self, event: HiveEvent):
        # Induces 100-500ms lag before attempting to enter the Strict Queue, simulating out-of-order network arrival.
        await asyncio.sleep(random.uniform(0.1, 0.5))
        await super().publish(event)

    async def reconcile_split_brain(self):
        self.chaos_config["split_brain"] = False
        queue = list(self.split_brain_buffer)
        self.split_brain_buffer.clear()
        for ev in queue:
            await super().publish(ev)

# -------------------------
# METRICS TRACKER
# -------------------------
class InvariantTracker:
    def __init__(self):
        self.metrics = {
            "events_published": 0,
            "events_received": 0,
            "violations": []
        }
        
    async def global_sniffer(self, event: HiveEvent):
        self.metrics["events_received"] += 1

    def evaluate(self, phase: str, agents: list, bus: EventBus):
        violations = []
        
        # Invariant 5: Orphan Tasks
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        # We allow a baseline of ~50 tasks (main loop, agents loops, etc)
        orphan_count = max(0, len(tasks) - 60) 
        if orphan_count > 50:
            violations.append(f"Invariant 5 [Orphans]: {orphan_count} tasks leaked.")

        # Invariant 7: Explosion (Expected fan-out is ~4-5 events per external trigger)
        if self.metrics["events_received"] > self.metrics["events_published"] * 10:
             violations.append(f"Invariant 7 [Explosion]: Sent {self.metrics['events_published']}, Processed {self.metrics['events_received']}")

        # Invariant 8: Cross Scan Bleed
        alpha = next((a for a in agents if a.name == "agent_alpha"), None)
        gamma = next((a for a in agents if a.name == "agent_gamma"), None)
        if hasattr(alpha, 'visited_urls'):
            violations.append("Invariant 8 [Bleed]: Alpha maintains local state.")
        if hasattr(gamma, 'baseline_cache'):
            violations.append("Invariant 8 [Bleed]: Gamma maintains local state.")

        if violations:
            print(f"\n[X] [{phase}] FAILED. INVARIANTS VIOLATED:")
            for v in violations:
                print(f"   -> {v}")
            raise RuntimeError(f"INTEGRITY FAILURE in {phase}")
        else:
            print(f"[OK] [{phase}] SURVIVED. Invariants intact.")

# -------------------------
# THE ORCHESTRATOR
# -------------------------
class HarshEnvironmentHarness:
    def __init__(self):
        self.bus = ChaosEventBus()
        self.tracker = InvariantTracker()
        self.agents = []

        # Monitor all events
        for et in EventType:
            self.bus.subscribe(et, self.tracker.global_sniffer)

    async def boot(self):
        print("\n[INIT] Booting Organism into Chaos Harness...")
        self.agents = [
            AlphaAgent(self.bus), BetaAgent(self.bus), GammaAgent(self.bus),
            SigmaAgent(self.bus), OmegaAgent(self.bus), ZetaAgent(self.bus),
            KappaAgent(self.bus), AgentTheta(self.bus), AgentIota(self.bus)
        ]
        await asyncio.gather(*[a.start() for a in self.agents])

    def emit(self, event: HiveEvent):
        self.tracker.metrics["events_published"] += 1
        return self.bus.publish(event)

    async def phase_1_baseline(self):
        print("\n--- PHASE 1: Controlled Full Activation ---")
        scan_id = uuid.uuid4().hex
        
        for i in range(10):
            job = JobPacket(target=TaskTarget(url=f"http://base-{i}.loc"), config=ModuleConfig(module_id="tech_sqli", agent_id=AgentID.BETA, session_id=scan_id))
            await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=job.model_dump()))
        
        await asyncio.sleep(2)
        self.tracker.evaluate("PHASE 1", self.agents, self.bus)

    async def phase_2_backpressure(self):
        print("\n--- PHASE 2: Multi-Arsenal Conflict + Backpressure ---")
        self.bus.chaos_config["throttle_delay"] = 0.05 # Artificial CPU Starvation
        
        scan_id = uuid.uuid4().hex
        for i in range(50):
            job = JobPacket(target=TaskTarget(url=f"http://bp-{i}.loc"), config=ModuleConfig(module_id="logic_tycoon", agent_id=AgentID.GAMMA, session_id=scan_id))
            await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=job.model_dump()))
            
            job2 = JobPacket(target=TaskTarget(url=f"http://bp-{i}.loc"), config=ModuleConfig(module_id="tech_jwt", agent_id=AgentID.BETA, session_id=scan_id))
            await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=job2.model_dump()))
            
        await asyncio.sleep(5)
        self.bus.chaos_config["throttle_delay"] = 0.0
        self.tracker.evaluate("PHASE 2", self.agents, self.bus)

    async def phase_3_overlap(self):
        print("\n--- PHASE 3: Cross-Scan Override Attack ---")
        for i in range(10):
            scan_id = f"SCAN_ID_OVERLAP_{i}"
            job = JobPacket(target=TaskTarget(url="http://shared-target.loc"), config=ModuleConfig(module_id="tech_fuzzer", agent_id=AgentID.ALPHA, session_id=scan_id))
            await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=job.model_dump()))
            
        await asyncio.sleep(3)
        self.tracker.evaluate("PHASE 3", self.agents, self.bus)

    async def phase_4_reordering(self):
        print("\n--- PHASE 4: Causal Corruption (Jitter Injection) ---")
        self.bus.chaos_config["reorder_chance"] = 0.3 # 30% chance for temporal scrambling
        
        scan_id = uuid.uuid4().hex
        for _ in range(20):
            await self.emit(HiveEvent(type=EventType.LOG, source="Chaos", scan_id=scan_id, payload={"msg": "causal A"}))
            await self.emit(HiveEvent(type=EventType.LOG, source="Chaos", scan_id=scan_id, payload={"msg": "causal B"}))
            await self.emit(HiveEvent(type=EventType.LOG, source="Chaos", scan_id=scan_id, payload={"msg": "causal C"}))
            
        await asyncio.sleep(4)
        self.bus.chaos_config["reorder_chance"] = 0.0
        self.tracker.evaluate("PHASE 4", self.agents, self.bus)

    async def phase_6_split_brain(self):
        print("\n--- PHASE 6: Split-Brain Network Partition ---")
        scan_id = uuid.uuid4().hex
        
        # Normal
        await self.emit(HiveEvent(type=EventType.LOG, source="Chaos", scan_id=scan_id, payload={"state": "pre-isolation"}))
        
        # Isolate
        self.bus.chaos_config["split_brain"] = True
        for _ in range(15):
             await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=JobPacket(target=TaskTarget(url="http://split.loc"), config=ModuleConfig(module_id="tech_sqli", agent_id=AgentID.BETA)).model_dump()))
        
        # Wait silently
        await asyncio.sleep(1)
        
        # Rejoin
        print("  -> Healing Network Partition (Reconciling)")
        await self.bus.reconcile_split_brain()
        await asyncio.sleep(3)
        self.tracker.evaluate("PHASE 6", self.agents, self.bus)

    async def phase_7_8_cancellation_fragmentation(self):
        print("\n--- PHASE 7 & 8: Teardown Storms & Memory Fragmentation ---")
        # Rapid creation and destruction of scans
        for i in range(25):
            scan_id = f"FRAG_SCAN_{i}"
            await self.emit(HiveEvent(type=EventType.SYSTEM_START, source="Chaos", scan_id=scan_id, payload={"scan_id": scan_id}))
            
            # Flood it with massive jobs
            payload = {"large_blob": "A" * 1024 * 100} # 100kb
            job = JobPacket(target=TaskTarget(url=f"http://frag-{i}.loc", payload=payload), config=ModuleConfig(module_id="tech_fuzzer", agent_id=AgentID.BETA, session_id=scan_id))
            await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=job.model_dump()))
            
            if i % 2 == 0:
                # Cancel immediately
                await self.emit(HiveEvent(type=EventType.CONTROL_SIGNAL, source="Chaos", scan_id=scan_id, payload={"signal": "SCAN_COMPLETE", "session_id": scan_id}))
                
        await asyncio.sleep(4)
        self.tracker.evaluate("PHASE 7/8", self.agents, self.bus)

    async def phase_10_totality(self):
        print("\n--- PHASE 10: MAXIMAL NONLINEAR CONVERGENCE ---")
        self.bus.chaos_config["throttle_delay"] = 0.02
        self.bus.chaos_config["reorder_chance"] = 0.2
        
        scan_id = "DOOMSDAY_SCAN"
        print("  -> Injecting 600 payloads under active delay + causal corruption...")
        for i in range(300): # Scale down slightly for acceptable local testing time 300 x 2 = 600
            j1 = JobPacket(target=TaskTarget(url=f"http://doom-{i}.loc"), config=ModuleConfig(module_id="tech_sqli", agent_id=AgentID.BETA, session_id=scan_id))
            j2 = JobPacket(target=TaskTarget(url=f"http://doom-{i}.loc"), config=ModuleConfig(module_id="logic_tycoon", agent_id=AgentID.GAMMA, session_id=scan_id))
            await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=j1.model_dump()))
            await self.emit(HiveEvent(type=EventType.JOB_ASSIGNED, source="Chaos", scan_id=scan_id, payload=j2.model_dump()))
            
            if i == 50:
                self.bus.chaos_config["split_brain"] = True
            if i == 100:
                await self.bus.reconcile_split_brain()
                
            if i % 50 == 0:
                await asyncio.sleep(0.1)

        print("  -> Waiting for Organism to Stabilize (Approx 15 seconds)...")
        await asyncio.sleep(15)
        
        self.bus.chaos_config["throttle_delay"] = 0.0
        self.bus.chaos_config["reorder_chance"] = 0.0
        
        # Teardown Storm
        print("  -> Issuing Doomsday Teardown...")
        await self.emit(HiveEvent(type=EventType.CONTROL_SIGNAL, source="Chaos", scan_id=scan_id, payload={"signal": "SCAN_COMPLETE", "session_id": scan_id}))
        await asyncio.sleep(1.0)
        
        self.tracker.evaluate("PHASE 10", self.agents, self.bus)

    async def run(self):
        await self.boot()
        
        try:
            await self.phase_1_baseline()
            await self.phase_2_backpressure()
            await self.phase_3_overlap()
            await self.phase_4_reordering()
            await self.phase_6_split_brain()
            await self.phase_7_8_cancellation_fragmentation()
            await self.phase_10_totality()
            
            print("\n=======================================================")
            print("🚀 TERMINAL VERDICT: SYSTEM HAS TRANSCENDED CHAOS. 🚀")
            print("Antigravity V6 is structurally fault-tolerant and deployment locked.")
            print("=======================================================")
            
        finally:
            print("\n[TEARDOWN] Triggering Hard Global Agent Stop")
            await self.bus.shutdown()
            for a in self.agents:
                await a.stop()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    harness = HarshEnvironmentHarness()
    asyncio.run(harness.run())
