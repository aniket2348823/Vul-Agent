import asyncio
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.ai.cortex import CortexEngine

async def test_cortex():
    print("Initializing CortexEngine...")
    engine = CortexEngine()
    print(f"Model: {engine.model}")
    
    prompt = "Reply with 'CORTEX_LIVE' if you can hear me."
    print(f"Sending prompt: {prompt}")
    
    try:
        response = await engine._call_ollama(prompt, temperature=0.0)
        print(f"Response: {response}")
        if "CORTEX_LIVE" in response:
            print("SUCCESS: Cortex is live.")
        else:
            print("WARNING: Unexpected response.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_cortex())
