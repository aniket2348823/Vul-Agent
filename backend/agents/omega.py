import asyncio
import random
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskPriority, ModuleConfig, TaskTarget
from backend.ai.cortex import CortexEngine

class OmegaAgent(BaseAgent):
    """
    AGENT OMEGA: THE STRATEGIST
    Advanced Capabilities:
    1. Nash Equilibrium Strategy (Randomized mixed strategies)
    2. Dynamic Campaign Chaining
    """
    def __init__(self, bus):
        super().__init__("agent_omega", bus)
        # CORTEX AI Strategist (Local Ollama)
        try:
            self.ai = CortexEngine()
        except Exception:self.ai = None

    async def setup(self):
        # Listen for TARGET_ACQUIRED to start campaigns
        self.bus.subscribe(EventType.TARGET_ACQUIRED, self.handle_target)

    async def handle_target(self, event: HiveEvent):
        """
        Triggered when the system identifies a new target.
        """
        payload = event.payload
        target_url = payload.get("url")
        if target_url:
            await self.initiate_campaign(target_url)

    async def initiate_campaign(self, target_url: str):
        # 1. STRATEGY GENERATION (AI-Powered + Context)
        hypotheses = [
            "Changing user_id may expose another user's data",
            "Negative price may bypass payment validation",
            "JWT algorithm change may bypass verification",
            "Auth bypass -> IDOR -> Data Extraction"
        ]
        
        # Try AI strategy selection first
        strategy = None
        if self.ai and self.ai.enabled:
            try:
                strategy = await self.ai.select_attack_strategy(target_url)
                print(f"[{self.name}]: [CORTEX AI] Strategy selected: {strategy}")
            except Exception as e:
                print(f"[{self.name}]: CORTEX strategy failed: {e}")
        
        if not strategy or strategy not in ["E_COMMERCE_BLITZ", "BLITZKRIEG", "LOW_AND_SLOW"]:
            strategy = "MULTI_STEP_EXPLOIT"
            
        selected_hypothesis = random.choice(hypotheses)
        
        # Broadcast to Dashboard: Campaign started
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            payload={"url": target_url, "arsenal": "Campaign Strategy", "action": f"Strategy: {strategy}", "payload": selected_hypothesis[:50]}
        ))
            
        await self.bus.publish(HiveEvent(
            type=EventType.LOG,
            source=self.name,
            payload={"message": f"ðŸ‘‘ OMEGA: Initiating Campaign '{target_url}' | Strategy: {strategy} | Hypothesis: {selected_hypothesis}"}
        ))

        # 2. CAMPAIGN CHAINING
        target = TaskTarget(url=target_url)

        if strategy == "E_COMMERCE_BLITZ":
            # Specialized Packet for Tycoon (Financial)
            tycoon_packet = JobPacket(
                priority=TaskPriority.HIGH,
                target=target,
                config=ModuleConfig(
                    module_id="logic_tycoon", 
                    agent_id=AgentID.GAMMA,
                    aggression=8,
                    ai_mode=True
                )
            )
            await self.dispatch_job(tycoon_packet)
            
        else:
            # Multi-Step Exploit Flow (Research-Grade Pipeline)
            
            # Step 1: Payload Generation (Agent Sigma) - Qwen 2.5 Coder
            sigma_packet = JobPacket(
                priority=TaskPriority.CRITICAL,
                target=target,
                config=ModuleConfig(
                    module_id="sigma_forge",
                    agent_id=AgentID.SIGMA,
                    aggression=10,
                    ai_mode=True,
                    params={"attack_hypothesis": selected_hypothesis}
                )
            )
            await self.dispatch_job(sigma_packet)
            
            # Step 2: Offensive Execution & Mutation (Agent Beta)
            beta_packet = JobPacket(
                priority=TaskPriority.HIGH,
                target=target,
                config=ModuleConfig(
                    module_id="beta_execution", 
                    agent_id=AgentID.BETA,
                    aggression=8,
                    ai_mode=True
                )
            )
            await self.dispatch_job(beta_packet)
            
            # Step 3: Analytical Reasoning (Gamma) is handled via event propagation
            # once Beta executes and captures HTTP responses.
            
    async def dispatch_job(self, packet: JobPacket):
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source=self.name,
            payload=packet.model_dump()
        ))

    def _generate_mixed_strategy(self):
        strategies = ["BLITZKRIEG", "LOW_AND_SLOW", "DECEPTION"]
        return random.choices(strategies, weights=[0.2, 0.5, 0.3], k=1)[0]
