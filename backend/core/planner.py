import asyncio
import logging
from enum import Enum
from typing import Dict, Any
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ModuleConfig, AgentID, TaskPriority, TaskTarget
from backend.core.config import settings
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.skill_library import skill_library
from backend.core.unified_knowledge_graph import unified_knowledge_graph

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
        self.cortex = get_cortex_engine()
        self.active_missions = {} # {target_url: mission_data}
        self.job_to_target = {}   # {job_id: target_url}

    async def setup(self):
        # 1. Listen for new targets
        self.bus.subscribe(EventType.TARGET_ACQUIRED, self.handle_new_target)
        # 2. Listen for findings to pivot strategy
        self.bus.subscribe(EventType.VULN_CANDIDATE, self.handle_candidate)
        # 3. Listen for job completions to trigger logical next steps
        self.bus.subscribe(EventType.JOB_COMPLETED, self.handle_job_completion)

    def _pre_plan(self, target_url: str) -> Dict[str, Any]:
        """Query the SkillLibrary and unified knowledge graph before planning.

        Architecture §6.7 / §29.1: the planner consumes learned skills and graph
        evidence up front so plans are informed by prior outcomes, not formed in
        a vacuum. Failures here are non-fatal (planning proceeds without recs)."""
        recs: Dict[str, Any] = {"skills": [], "graph_predictions": [], "chains": []}
        try:
            recs["skills"] = skill_library.get_recommendations(target_url=target_url, limit=10)
        except Exception as exc:
            logger.debug(f"[{self.name}] skill recommendations unavailable: {exc}")
        try:
            recs["graph_predictions"] = unified_knowledge_graph.predict_next("TARGET_ACQUIRED", target_url)
            recs["chains"] = unified_knowledge_graph.find_chains(max_depth=3)[:5]
        except Exception as exc:
            logger.debug(f"[{self.name}] graph pre-plan unavailable: {exc}")
        if recs["skills"] or recs["graph_predictions"]:
            logger.info(f"[{self.name}] pre-plan for {target_url}: "
                        f"{len(recs['skills'])} skills, {len(recs['graph_predictions'])} graph predictions")
        return recs

    async def handle_new_target(self, event: HiveEvent):
        """
        Phase 1: RECONNAISSANCE
        Triggered when a new URL enters the scope.
        """
        target_url = event.payload.get("url")
        if not target_url or target_url in self.active_missions:
             return

        print(f"[{self.name}] [MISSION] Target '{target_url}' acquired. Starting Phase 1: RECON.")

        # Pre-planning: consume learned skills + graph evidence BEFORE planning
        # (Architecture §29.1 priority 13, §6.7 — query skills/graph up front,
        # not only when stuck).
        recommendations = self._pre_plan(target_url)

        self.active_missions[target_url] = {
            "scan_id": event.scan_id,
            "state": MissionState.RECON,
            "findings": [],
            "history": [],
            "recommendations": recommendations,
        }

        # Dispatch Alpha for intelligent mapping
        recon_job = JobPacket(
            priority=TaskPriority.NORMAL,
            target=TaskTarget(url=target_url),
            config=ModuleConfig(
                module_id="alpha_v6_recon",
                agent_id=AgentID.ALPHA,
                params={
                    "scan_mode": event.payload.get("scan_mode")
                    or event.payload.get("mode")
                    or getattr(settings, "ALPHA_DEFAULT_MODE", "STANDARD"),
                    "skill_recommendations": recommendations.get("skills", []),
                },
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
