import asyncio
import random
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskPriority, ModuleConfig, TaskTarget
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.graph_engine import graph_engine

class OmegaAgent(BaseAgent):
    """
    AGENT OMEGA: THE STRATEGIST
    Role: Campaign Intelligence & Attack Chain Orchestration.
    
    Advanced Capabilities:
    1. Nash Equilibrium Strategy (Randomized mixed strategies)
    2. Dynamic Campaign Chaining
    3. Graph-Driven Attack Prioritization (V6 Phase 2)
    4. Mid-Scan Strategy Adaptation
    5. Mission Planner Integration
    """
    def __init__(self, bus):
        super().__init__("agent_omega", bus)
        try:
            self.ai = get_cortex_engine()
        except Exception:
            self.ai = None

        # Campaign State
        self._active_campaigns = {}  # scan_id -> campaign state
        self._confirmed_vulns = []   # Accumulator for mid-scan adaptation
        self._job_results = {}       # job_id -> result tracking

    async def setup(self):
        self.bus.subscribe(EventType.TARGET_ACQUIRED, self.handle_target)
        self.bus.subscribe(EventType.VULN_CONFIRMED, self.handle_confirmed_vuln)
        self.bus.subscribe(EventType.JOB_COMPLETED, self.handle_job_completed)
        self.bus.subscribe(EventType.PATTERN_LEARNED, self.handle_pattern_learned)

    async def handle_pattern_learned(self, event: HiveEvent):
        """PROBLEM 6: Receive intelligence from Kappa and boost relevant attack priority."""
        pattern = event.payload.get("pattern", {})
        vuln_type = pattern.get("vuln_type", "")
        print(f"[{self.name}] [ADAPT] Received pattern intelligence: {vuln_type} (confidence: {pattern.get('confidence', 0):.2f})")
        # Boost priority of the attack type that just confirmed a hit
        for strategy_name, profile in self.STRATEGY_PROFILES.items():
            for module in profile.get("modules", []):
                if vuln_type.lower() in module.lower():
                    profile["aggression"] = min(10, profile.get("aggression", 5) + 2)
                    print(f"[{self.name}] [BOOST] Strategy '{strategy_name}' aggression boosted to {profile['aggression']}")

    # --- STRATEGY SELECTION ---

    STRATEGY_PROFILES = {
        "E_COMMERCE_BLITZ": {
            "description": "Financial logic attack chain targeting pricing, coupons, and cart manipulation",
            "modules": ["logic_tycoon", "logic_escalator", "logic_skipper"],
            "aggression": 8,
            "priority": TaskPriority.CRITICAL,
        },
        "BLITZKRIEG": {
            "description": "Maximum aggression, all modules fire simultaneously",
            "modules": ["tech_sqli", "tech_fuzzer", "tech_jwt", "tech_auth_bypass",
                        "logic_tycoon", "logic_doppelganger", "logic_skipper"],
            "aggression": 10,
            "priority": TaskPriority.CRITICAL,
        },
        "LOW_AND_SLOW": {
            "description": "Stealth-focused sequential probing to avoid WAF detection",
            "modules": ["tech_fuzzer", "logic_chronomancer", "logic_doppelganger"],
            "aggression": 3,
            "priority": TaskPriority.LOW,
        },
        "MULTI_STEP_EXPLOIT": {
            "description": "Research-grade multi-vector pipeline with AI payload generation",
            "modules": ["sigma_generative_blast", "beta_direct_assault"],
            "aggression": 7,
            "priority": TaskPriority.HIGH,
        },
        "GRAPH_DRIVEN": {
            "description": "Prioritizes modules based on historical attack graph intelligence",
            "modules": [],  # Dynamically populated from graph predictions
            "aggression": 6,
            "priority": TaskPriority.HIGH,
        }
    }

    def _select_strategy(self, target_url: str, ai_strategy: str = None) -> str:
        """Selects optimal strategy based on AI recommendation and graph intelligence."""
        
        # 1. If AI gave a valid recommendation, use it
        if ai_strategy and ai_strategy in self.STRATEGY_PROFILES:
            return ai_strategy

        # 2. Check graph intelligence for historical patterns
        predictions = graph_engine.predict_next("TARGET_ACQUIRED", target_url)
        if predictions and predictions[0].get("confidence", 0) > 40:
            return "GRAPH_DRIVEN"

        # 3. Nash Equilibrium mixed strategy (game-theoretic randomization)
        return self._generate_mixed_strategy()

    def _generate_mixed_strategy(self) -> str:
        strategies = ["BLITZKRIEG", "LOW_AND_SLOW", "MULTI_STEP_EXPLOIT", "E_COMMERCE_BLITZ"]
        weights = [0.15, 0.25, 0.40, 0.20]
        return random.choices(strategies, weights=weights, k=1)[0]

    def _build_graph_driven_modules(self, target_url: str) -> list:
        """Queries the attack graph for the highest-confidence next modules."""
        MODULE_TYPE_MAP = {
            "SQL_INJECTION": "tech_sqli",
            "XSS": "tech_fuzzer",
            "CROSS_SITE_SCRIPTING": "tech_fuzzer",
            "JWT_BYPASS": "tech_jwt",
            "BROKEN_AUTH": "tech_auth_bypass",
            "IDOR": "logic_doppelganger",
            "RACE_CONDITION": "logic_chronomancer",
            "LOGIC_ESCALATION": "logic_escalator",
            "FINANCIAL_MANIPULATION": "logic_tycoon",
        }
        
        predictions = graph_engine.predict_next("TARGET_ACQUIRED", target_url)
        modules = []
        for pred in predictions[:5]:  # Top 5 predictions
            suggestion = pred.get("suggestion", "").upper()
            module = MODULE_TYPE_MAP.get(suggestion)
            if module and module not in modules:
                modules.append(module)
        
        # Always include at least one fallback
        if not modules:
            modules = ["tech_fuzzer", "logic_doppelganger"]
        
        return modules

    # --- EVENT HANDLERS ---

    async def handle_target(self, event: HiveEvent):
        """Triggered when the system identifies a new target."""
        payload = event.payload
        target_url = payload.get("url")
        scan_id = event.scan_id
        if not target_url:
            return
            
        # Register campaign
        self._active_campaigns[scan_id] = {
            "target_url": target_url,
            "strategy": None,
            "dispatched_jobs": [],
            "confirmed_vulns": [],
            "adapted": False
        }
        
        await self.initiate_campaign(target_url, scan_id)

    async def handle_confirmed_vuln(self, event: HiveEvent):
        """
        Mid-Scan Adaptation: When vulnerabilities are confirmed,
        Omega reassesses and potentially dispatches follow-up chains.
        """
        scan_id = event.scan_id
        campaign = self._active_campaigns.get(scan_id)
        if not campaign:
            return

        vuln_data = event.payload
        campaign["confirmed_vulns"].append(vuln_data)

        # Check for chain opportunities using the graph engine
        vuln_type = str(vuln_data.get("type", "")).upper()
        vuln_url = str(vuln_data.get("url", ""))
        
        if not vuln_type or campaign.get("adapted"):
            return

        # Query graph for follow-up attack vectors
        chains = graph_engine.find_chains(max_depth=3)
        relevant_chains = [c for c in chains if any(
            step.get("type", "").upper() == vuln_type for step in c.get("chain", [])
        )]

        if relevant_chains and not campaign["adapted"]:
            campaign["adapted"] = True
            best_chain = relevant_chains[0]
            
            print(f"[{self.name}] [CHAIN ADAPT] Confirmed {vuln_type} → Deploying chain escalation (depth={best_chain['depth']})")
            
            await self.bus.publish(HiveEvent(
                type=EventType.LIVE_ATTACK,
                source=self.name,
                scan_id=scan_id,
                payload={
                    "url": vuln_url,
                    "arsenal": "Chain Escalation",
                    "action": f"Adapting strategy: {vuln_type} → Chain depth {best_chain['depth']}",
                    "payload": str(best_chain.get("chain", [])[:2])[:80]
                }
            ))
            
            # Dispatch follow-up jobs based on chain prediction
            for step in best_chain.get("chain", [])[1:]:  # Skip the already-confirmed first step
                step_type = step.get("type", "").upper()
                module = self._resolve_module_from_type(step_type)
                if module:
                    follow_up = JobPacket(
                        priority=TaskPriority.HIGH,
                        target=TaskTarget(url=campaign["target_url"]),
                        config=ModuleConfig(
                            module_id=module,
                            agent_id=AgentID.SIGMA,
                            aggression=8,
                            params={"chain_source": vuln_type, "escalation": True}
                        )
                    )
                    await self.dispatch_job(follow_up, scan_id)

    async def handle_job_completed(self, event: HiveEvent):
        """Tracks job completion for campaign progress monitoring."""
        job_id = event.payload.get("job_id", "")
        status = event.payload.get("status", "")
        self._job_results[job_id] = status

    def _resolve_module_from_type(self, vuln_type: str) -> str:
        """Maps vulnerability type names back to module IDs."""
        TYPE_TO_MODULE = {
            "SQL_INJECTION": "tech_sqli",
            "XSS": "tech_fuzzer",
            "JWT_BYPASS": "tech_jwt",
            "BROKEN_AUTH": "tech_auth_bypass",
            "IDOR": "logic_doppelganger",
            "RACE_CONDITION": "logic_chronomancer",
            "LOGIC_ESCALATION": "logic_escalator",
            "FINANCIAL_MANIPULATION": "logic_tycoon",
            "DATA_LEAK": "tech_fuzzer",
            "UNAUTHORIZED_ACCESS": "logic_skipper",
        }
        return TYPE_TO_MODULE.get(vuln_type)

    # --- CAMPAIGN EXECUTION ---

    async def initiate_campaign(self, target_url: str, scan_id: str = "GLOBAL"):
        """Core campaign orchestration logic with graph-driven intelligence."""
        
        # 1. STRATEGY GENERATION (AI-Powered + Graph Intelligence)
        ai_strategy = None
        if self.ai and self.ai.enabled:
            try:
                ai_strategy = await self.ai.select_attack_strategy(target_url)
                print(f"[{self.name}] [CORTEX AI] Strategy recommendation: {ai_strategy}")
            except Exception as e:
                print(f"[{self.name}] CORTEX strategy failed: {e}")
        
        strategy_name = self._select_strategy(target_url, ai_strategy)
        profile = self.STRATEGY_PROFILES[strategy_name]
        
        # Update campaign state
        if scan_id in self._active_campaigns:
            self._active_campaigns[scan_id]["strategy"] = strategy_name
        
        print(f"[{self.name}] ▶ Campaign Strategy: {strategy_name} | {profile['description']}")

        # 2. HYPOTHESIS GENERATION
        hypotheses = [
            "Changing user_id may expose another user's data (IDOR)",
            "Negative price may bypass payment validation (Logic Flaw)",
            "JWT algorithm change may bypass verification (Auth Bypass)",
            "Auth bypass → IDOR → Data Extraction (Chain Attack)",
            "Race condition on coupon application (Financial Exploit)",
            "Path traversal in file upload (Config Exposure)",
        ]
        selected_hypothesis = random.choice(hypotheses)

        # Broadcast campaign start
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            scan_id=scan_id,
            payload={
                "url": target_url,
                "arsenal": "Campaign Strategy",
                "action": f"Strategy: {strategy_name}",
                "payload": f"{profile['description'][:60]} | Hypothesis: {selected_hypothesis[:40]}"
            }
        ))

        await self.bus.publish(HiveEvent(
            type=EventType.LOG,
            source=self.name,
            scan_id=scan_id,
            payload={"message": f"👑 OMEGA: Campaign '{target_url}' | Strategy: {strategy_name} | Hypothesis: {selected_hypothesis}"}
        ))

        # 3. RESOLVE MODULES
        if strategy_name == "GRAPH_DRIVEN":
            modules = self._build_graph_driven_modules(target_url)
            print(f"[{self.name}] [GRAPH AI] Predicted modules: {modules}")
        else:
            modules = profile["modules"]

        # 4. DISPATCH JOBS
        target = TaskTarget(url=target_url)
        
        for module_id in modules:
            agent_id = AgentID.SIGMA
            if module_id.startswith("beta_"):
                agent_id = AgentID.BETA

            packet = JobPacket(
                priority=profile["priority"],
                target=target,
                config=ModuleConfig(
                    module_id=module_id,
                    agent_id=agent_id,
                    aggression=profile["aggression"],
                    ai_mode=True,
                    params={"attack_hypothesis": selected_hypothesis, "strategy": strategy_name}
                )
            )
            await self.dispatch_job(packet, scan_id)

        # 5. Always add a Sigma Generative payload for novel vector discovery
        if "sigma_generative_blast" not in modules:
            sigma_packet = JobPacket(
                priority=TaskPriority.NORMAL,
                target=target,
                config=ModuleConfig(
                    module_id="sigma_forge",
                    agent_id=AgentID.SIGMA,
                    aggression=profile["aggression"],
                    ai_mode=True,
                    params={"attack_hypothesis": selected_hypothesis}
                )
            )
            await self.dispatch_job(sigma_packet, scan_id)

        # 6. Learn from this campaign dispatch (feed the graph)
        await graph_engine.learn_from_chain([
            {"payload": {"type": "TARGET_ACQUIRED", "url": target_url}},
            {"payload": {"type": strategy_name, "url": target_url}}
        ])

    async def dispatch_job(self, packet: JobPacket, scan_id: str = "GLOBAL"):
        """Dispatches a job and tracks it in the campaign state."""
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source=self.name,
            scan_id=scan_id,
            payload=packet.model_dump()
        ))
        
        # Track in campaign
        campaign = self._active_campaigns.get(scan_id)
        if campaign:
            campaign["dispatched_jobs"].append(packet.id)
