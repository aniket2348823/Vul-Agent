import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# --- MOCKING NETWORK LAYER ---
import aiohttp

class MockAioResponse:
    def __init__(self, text="Mocked Response", status=200):
        self._text = text
        self.status = status
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass
    async def text(self): return self._text
    async def json(self): return {"status": "mock_success"}

def mock_network_call(*args, **kwargs):
    url = str(args[0]) if args else ""
    print(f"\n[NETWORK-MOCK] Blocking Call to: {url}")
    
    if "checkout" in url:
        return MockAioResponse(text="CRITICAL ERROR: NEGATIVE INVENTORY", status=500)
    elif "api" in url:
        return MockAioResponse(text="API Endpoint Active", status=200)
        
    return MockAioResponse(text="Standard Baseline", status=200)

# Patch aiohttp globally
aiohttp.ClientSession.get = MagicMock(side_effect=mock_network_call)
aiohttp.ClientSession.post = MagicMock(side_effect=mock_network_call)
aiohttp.ClientSession.request = MagicMock(side_effect=mock_network_call)

# --- SYSTEM IMPORTS ---
from backend.core.orchestrator import HiveOrchestrator
from backend.api.socket_manager import manager

async def run_test():
    print("\n>>> STARTING ANTIGRAVITY V7 FUNCTIONALITY TEST")
    
    # 1. Mock WebSocket Manager & Capture Logs
    async def capture_broadcast(message):
        m_type = message.get("type")
        payload = message.get("payload")
        if m_type == "GI5_LOG":
            print(f"[HIVE-LOG] {payload}")
            if "REPORT GENERATED" in str(payload):
                print(f"\n>>> SUCCESS! REPORT DETECTED: {payload}")
        if m_type == "SCAN_UPDATE":
            print(f"[STATUS] Scan State: {payload.get('status')}")

    manager.broadcast = AsyncMock(side_effect=capture_broadcast)
    manager.connect = AsyncMock()
    
    # 2. Config Target
    target_config = {
        "url": "http://simulation-target.com/api/cart/checkout",
        "method": "POST",
        "headers": {"User-Agent": "Antigravity-Test-Suite"},
        "payload": "{\"item_id\": 1, \"qty\": 1}",
        "velocity": "LIGHTSPEED"
    }
    
    scan_id = "TEST-FUNCTIONALITY-002"
    
    # 3. Launch Hive 
    orchestrator_task = asyncio.create_task(
        HiveOrchestrator.bootstrap_hive(target_config, scan_id)
    )
    
    print(">>> HIVE BOOTSTRAPPED. WAITING FOR SWARM CONVERGENCE (15s)...")
    
    try:
        await asyncio.sleep(15)
    except asyncio.CancelledError:
        pass
    
    print("\n>>> TERMINATING TEST SESSION (Sending Cancel Signal)...")
    orchestrator_task.cancel()
    
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        print(">>> HIVE SHUTDOWN GRACEFULLY")
    except Exception as e:
        print(f">>> HIVE CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
