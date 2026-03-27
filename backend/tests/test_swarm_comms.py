import asyncio
import logging
from backend.core.hive import EventBus, EventType, HiveEvent
from backend.agents.alpha import AlphaAgent
from backend.agents.beta import BetaAgent
from backend.agents.sigma import SigmaAgent
from backend.agents.kappa import KappaAgent
from backend.core.protocol import JobPacket, TaskTarget, ModuleConfig, AgentID

# Configure Logging
# Configure Logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("SwarmTest")
logger.setLevel(logging.INFO)
fh = logging.FileHandler('backend/tests/swarm_test.log', mode='w')
fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
logger.addHandler(sh)

async def test_swarm_communication():
    logger.info("--- [START] SWARM CONNECTIVITY TEST ---")
    
    # 1. Initialize Nervous System
    bus = EventBus()
    
    # 2. Spawn Agents
    alpha = AlphaAgent(bus)
    beta = BetaAgent(bus)
    sigma = SigmaAgent(bus)
    kappa = KappaAgent(bus)
    
    # Inject Mock Config
    mission_config = {
        "modules": ["Singularity V5"], # Allow all
        "filters": ["Financial Logic"],
        "scope": "http://test-bank.local"
    }
    for agent in [alpha, beta, sigma, kappa]:
        agent.mission_config = mission_config
        await agent.start()
        
    logger.info("--- [AGENTS ONLINE] ---")

    # 3. Validation Flags
    results = {
        "ALPHA_TARGET_SEEN": False,
        "BETA_JOB_RECEIVED": False,
        "SIGMA_FORGE_RECEIVED": False,
        "KAPPA_ARCHIVE_RECEIVED": False
    }

    # 4. Define Spies (Event Listeners)
    async def spy_listener(event: HiveEvent):
        # The provided snippet for spy_listener was syntactically incorrect and referenced undefined variables.
        # Assuming the intent was to add a generic log for certain events or to modify Kappa's logging.
        # For now, keeping it as a pass-through as the original, or adding a generic log.
        # If the intent was to modify Kappa's behavior, that would be in check_kappa_reaction.
        # logger.info(f"UNKNOWN SIGNAL: {event.type} from {event.source}")
        pass

    async def check_beta_reaction(event: HiveEvent):
        if event.source == "agent_beta" and event.type == EventType.JOB_COMPLETED:
            results["BETA_JOB_RECEIVED"] = True
            results["BETA_JOB_RECEIVED"] = True
            logger.info("[OK] BETA: Executed Attack Job.")

    async def check_sigma_reaction(event: HiveEvent):
        if event.source == "agent_sigma" and event.type == EventType.JOB_COMPLETED:
            results["SIGMA_FORGE_RECEIVED"] = True
            results["SIGMA_FORGE_RECEIVED"] = True
            logger.info("[OK] SIGMA: Forged Payload.")

    async def check_kappa_reaction(event: HiveEvent):
        if event.source == "agent_kappa" and event.type == EventType.LOG:
             results["KAPPA_ARCHIVE_RECEIVED"] = True
             results["KAPPA_ARCHIVE_RECEIVED"] = True
             logger.info("[OK] KAPPA: Archived Finding.")

    # Subscribe Spies
    bus.subscribe(EventType.JOB_COMPLETED, check_beta_reaction)
    bus.subscribe(EventType.JOB_COMPLETED, check_sigma_reaction)
    bus.subscribe(EventType.LOG, check_kappa_reaction)
    
    # 5. TRIGGER: Simulate Alpha finding a Target
    # We simulate the ORCHESTRATOR assigning a job to ALPHA first
    logger.info("--- [TRIGGER] SIMULATING JOB ASSIGNMENT -> ALPHA ---")
    
    test_packet = JobPacket(
        target=TaskTarget(url="http://test-bank.local/api/transfer", method="POST"),
        config=ModuleConfig(module_id="logic_skipper", agent_id=AgentID.ALPHA)
    )
    
    await bus.publish(HiveEvent(
        type=EventType.JOB_ASSIGNED,
        source="Orchestrator",
        payload=test_packet.model_dump()
    ))
    
    # Allow propagation time
    await asyncio.sleep(2)
    
    # 6. TRIGGER: Simulate Beta needing Sigma
    logger.info("--- [TRIGGER] SIMULATING BETA REQUESTING PAYLOAD -> SIGMA ---")
    sigma_job = JobPacket(
        target=TaskTarget(url="http://test-bank.local/login"),
        config=ModuleConfig(module_id="sigma_bypass", agent_id=AgentID.SIGMA)
    )
    await bus.publish(HiveEvent(
        type=EventType.JOB_ASSIGNED,
        source="agent_beta",
        payload=sigma_job.model_dump()
    ))
    
    # Allow propagation time
    await asyncio.sleep(4)

    # 7. TRIGGER: Simulate Vulnerability for Kappa
    logger.info("--- [TRIGGER] SIMULATING VULN FOUND -> KAPPA ---")
    await bus.publish(HiveEvent(
        type=EventType.JOB_COMPLETED,
        source="agent_beta",
        payload={"status": "VULN_FOUND", "payload": {"type": "SQLI"}}
    ))
    
    await asyncio.sleep(5)

    logger.info("--- [RESULTS] ---")
    score = sum(1 for v in results.values() if v)
    logger.info(f"Connectivity Score: {score}/3 (Alpha is silent type in this test)")
    logger.info(results)
    
    if score >= 3:
        logger.info("[SUCCESS] SWARM CONNECTION VERIFIED: OPTIMAL")
    else:
        logger.error("[FAIL] SWARM FRACTURED")

if __name__ == "__main__":
    asyncio.run(test_swarm_communication())
