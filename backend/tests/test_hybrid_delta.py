import asyncio
import threading
import sys
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.core.hive import EventBus, EventType, HiveEvent
from backend.core.protocol import JobPacket, TaskTarget, ModuleConfig, AgentID
from backend.agents.delta import AgentDelta

# 1. Local DOM Mock Target Server
HTML_PAYLOAD = b"""
<html>
<body>
    <h1>VulAgent Secure Vault</h1>
    <script>
        window.appState = {
            "session_token": "SECRET-VULAGENT-TEST-TOKEN-999"
        };
    </script>
    <div id="hidden_data">{"token": "SECRET-VULAGENT-TEST-TOKEN-999"}</div>
    <p>Welcome to the protected control panel.</p>
</body>
</html>
"""

class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self): self.do_GET()
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAYLOAD)
    def log_message(self, format, *args): pass # Silence logs

def run_mock_server():
    server = HTTPServer(('127.0.0.1', 8081), MockHandler)
    server.serve_forever()

async def run_hybrid_stress_test():
    print("[TEST] Bootstrapping Local Target DOM (Port 8081)...")
    server_thread = threading.Thread(target=run_mock_server, daemon=True)
    server_thread.start()
    
    # 2. Start Official PinchTab.exe
    pinchtab_path = os.path.join(os.path.dirname(__file__), "../../pinchtab_core/pinchtab.exe")
    if not os.path.exists(pinchtab_path):
         print("[TEST ERROR] pinchtab.exe not found.")
         return

    print("[TEST] Igniting PinchTab Headless Server (Port 9867)...")
    # For testing, we won't strictly enforce authorization so it boots cleanly out of the box
    pinch_proc = subprocess.Popen(
        [pinchtab_path, "server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3) # Give it time to bind the port
    
    try:
        # 3. Simulate Orchestrator Wiring
        print("[TEST] Binding EventBus to AgentDelta...")
        bus = EventBus()
        delta_agent = AgentDelta(bus)
        # Override token for this open local test 
        delta_agent.headers = {} 
        await delta_agent.start()
        
        test_success = False

        async def delta_listener(event: HiveEvent):
            nonlocal test_success
            if event.type == EventType.JOB_COMPLETED and event.source == "agent_delta":
                data = event.payload.get("data", {})
                tok = data.get("dom_token")
                print(f"[TEST SUCCESS] AgentDelta hijacked DOM state! Extracted Token: {tok}")
                test_success = True

        bus.subscribe(EventType.JOB_COMPLETED, delta_listener)
        
        # 4. Trigger the Hybrid Flow
        test_packet = JobPacket(
            target=TaskTarget(url="http://127.0.0.1:8081"),
            config=ModuleConfig(agent_id=AgentID.BETA, module_id="delta_pinch_extract")
        )

        print("[TEST] Dispatching AgentDelta targeting loopback DOM...")
        await bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="TestRunner",
            payload=test_packet.model_dump()
        ))
        
        # Wait for 30 seconds or success
        for _ in range(30):
            if test_success:
                break
            await asyncio.sleep(1)
            
        if not test_success:
             print("[TEST FAILED] AgentDelta failed to extract token before timeout.")

    finally:
        print("[TEST] Shutting down Sandboxed PinchTab Server...")
        pinch_proc.terminate()
        try:
             pinch_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
             pinch_proc.kill()
        print("[TEST] Exiting safely.")

if __name__ == "__main__":
    asyncio.run(run_hybrid_stress_test())
