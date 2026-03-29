import asyncio
import gc
import os
import sys
import aiohttp

# Ensure the project root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.ai.cortex import get_cortex_engine
from backend.core.hive import EventBus
from backend.agents.alpha import AlphaAgent
from backend.agents.beta import BetaAgent
from backend.agents.sigma import SigmaAgent
# Add more agents if needed

async def diagnose_leaks():
    print("--- STARTING LEAK DIAGNOSIS ---")
    
    # 1. Start a temporary swarm
    bus = EventBus()
    engine = get_cortex_engine()
    
    # Test session creation
    session1 = aiohttp.ClientSession()
    print(f"Manual Session Created: {id(session1)}")
    await session1.close()
    
    # 2. Check for Cortex session
    if engine._session and not engine._session.closed:
        print(f"Cortex Session Active: {id(engine._session)}")
        await engine.shutdown()
        print("Cortex Session Closed.")
    
    # 3. Check for specific agents known to hold sessions
    sigma = SigmaAgent(bus)
    await sigma.start()
    print("Sigma Started.")
    await sigma.stop()
    print("Sigma Stopped.")
    
    # 4. Final GC and Session Audit
    gc.collect()
    
    found_any = False
    for obj in gc.get_objects():
        if isinstance(obj, aiohttp.ClientSession):
            if not obj.closed:
                print(f"LEAK DETECTED: Unclosed ClientSession {id(obj)}")
                found_any = True
                
    if not found_any:
        print("No sessions found in GC.")
    
    await bus.shutdown()
    print("--- DIAGNOSIS COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(diagnose_leaks())
