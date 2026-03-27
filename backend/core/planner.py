import asyncio
import logging
from enum import Enum
from typing import Dict, Any
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ModuleConfig, AgentID, TaskPriority, TaskTarget
from backend.ai.cortex import CortexEngine

logger = logging.getLogger("MissionPlanner")

class MissionState(str, Enum):
    RECON = "RECON"
    ASSESSMENT = "ASSESSMENT"
    EXPLOITATION = "EXPLOITATION"
    COMPLETED = "COMPLETED"

class MissionPlanner(BaseAgent):
    """
    AGENT OMEGA-PLANNER: THE STRATEGIST
    Role: Hierarchical Mission Planning & Autonomous Chaining.
    
    V6 Innovation: Instead of simple event reaction, the Planner generates
    structured 3-step offensive chains for every targets.
    """
    def __init__(self, bus):
        super().__init__("agent_planner", bus)
        self.cortex = CortexEngine()
        self.active_missions = {} # {target_url: mission_data}
        self.job_to_target = {}   # {job_id: target_url}

    async def setup(self):
        # 1. Listen for new targets
        self.bus.subscribe(EventType.TARGET_ACQUIRED, self.handle_new_target)
        # 2. Listen for findings to pivot strategy
        self.bus.subscribe(EventType.VULN_CANDIDATE, self.handle_candidate)
        # 3. Listen for job completions to trigger logical next steps
        self.bus.subscribe(EventType.JOB_COMPLETED, self.handle_job_completion)

    async def handle_new_target(self, event: HiveEvent):
        """
        Phase 1: RECONNAISSANCE
        Triggered when a new URL enters the scope.
        """
        target_url = event.payload.get("url")
        if not target_url or target_url in self.active_missions:
             return

        print(f"[{self.name}] [MISSION] Target '{target_url}' acquired. Starting Phase 1: RECON.")
        
        self.active_missions[target_url] = {
            "scan_id": event.scan_id,
            "state": MissionState.RECON,
            "findings": [],
            "history": []
        }

        # Dispatch Alpha for intelligent mapping
        recon_job = JobPacket(
            priority=TaskPriority.NORMAL,
            target=TaskTarget(url=target_url),
            config=ModuleConfig(
                module_id="api_mapping",
                agent_id=AgentID.ALPHA
            )
        )
        
        self.job_to_target[recon_job.id] = target_url
        
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source=self.name,
            scan_id=event.scan_id,
            payload=recon_job.model_dump()
        ))

    async def handle_candidate(self, event: HiveEvent):
        """
        Phase 2: ASSESSMENT
        Triggered when Alpha finds an interesting endpoint.
        """
        target_url = event.payload.get("url")
        if target_url not in self.active_missions:
            return

        mission = self.active_missions[target_url]
        if mission["state"] == MissionState.RECON:
            print(f"[{self.name}] [MISSION] '{target_url}' - Recon confirmed potential. Pivoting to Phase 2: ASSESSMENT.")
            mission["state"] = MissionState.ASSESSMENT
            
            # Dispatch Gamma for forensic audit
            assess_job = JobPacket(
                priority=TaskPriority.HIGH,
                target=TaskTarget(url=target_url),
                config=ModuleConfig(
                    module_id="vulnerability_audit",
                    agent_id=AgentID.GAMMA
                )
            )
            
            self.job_to_target[assess_job.id] = target_url
            
            await self.bus.publish(HiveEvent(
                type=EventType.JOB_ASSIGNED,
                source=self.name,
                scan_id=mission["scan_id"],
                payload=assess_job.model_dump()
            ))

    async def handle_job_completion(self, event: HiveEvent):
        """
        Phase 3: EXPLOITATION
        Triggered when Gamma confirms a vulnerability.
        """
        payload = event.payload
        job_id = payload.get("job_id")
        target_url = self.job_to_target.get(job_id)
        
        if not target_url or target_url not in self.active_missions:
            return

        mission = self.active_missions[target_url]

        if payload.get("status") == "VULN_FOUND":
            vulns = payload.get("vulnerabilities", [])
            for vuln in vulns:
                if mission["state"] == MissionState.ASSESSMENT:
                    print(f"[{self.name}] [MISSION] '{target_url}' - Vuln Vetted ({vuln.get('type')}). Launching Phase 3: EXPLOITATION.")
                    mission["state"] = MissionState.EXPLOITATION
                    
                    # Dispatch Beta for active breach
                    exploit_job = JobPacket(
                        priority=TaskPriority.CRITICAL,
                        target=TaskTarget(url=target_url),
                        config=ModuleConfig(
                            module_id="exploit_delivery",
                            agent_id=AgentID.BETA,
                            params={"vuln_type": vuln.get("type"), "evidence": vuln.get("evidence")}
                        )
                    )
                    
                    self.job_to_target[exploit_job.id] = target_url

                    await self.bus.publish(HiveEvent(
                        type=EventType.JOB_ASSIGNED,
                        source=self.name,
                        scan_id=mission["scan_id"],
                        payload=exploit_job.model_dump()
                    ))
        
        elif mission["state"] == MissionState.EXPLOITATION:
             # Mission Over
             print(f"[{self.name}] [MISSION] '{target_url}' - Mission Successfully Completed.")
             mission["state"] = MissionState.COMPLETED

    async def lifecycle(self):
        """Monitor mission timeouts and cleanup."""
        while self.active:
            await asyncio.sleep(60)
            # Periodic cleanup of completed or stale missions could go here
