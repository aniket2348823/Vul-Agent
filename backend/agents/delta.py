import asyncio
import re
import aiohttp
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskTarget

class AgentDelta(BaseAgent):
    """
    AGENT DELTA: HYBRID BROWSER CONTROLLER (DOM + API FUSION)
    Role: Control PinchTab externally, execute client-side workflows, and extract live DOM evidence.
    """
    PINCHTAB_URL = "http://localhost:9867"
    # To be securely injected via environment/config, stubbed for integration layer
    PINCHTAB_TOKEN = "vlg_auth_delta_local"

    def __init__(self, bus):
        super().__init__("agent_delta", bus)
        self.headers = {"Authorization": f"Bearer {self.PINCHTAB_TOKEN}"}
        
    async def setup(self):
        # Triggered by Recon/Orchestrator when navigating routes
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_hybrid_request)

    async def _pinch_nav(self, session, url):
        try:
            async with session.post(f"{self.PINCHTAB_URL}/nav", json={"url": url}, headers=self.headers, timeout=5) as resp:
                return await resp.status == 200
        except Exception as e:
            return False

    async def _pinch_text(self, session):
        try:
            async with session.get(f"{self.PINCHTAB_URL}/text", headers=self.headers, timeout=5) as resp:
                if resp.status == 200:
                     return await resp.text()
        except: pass
        return ""

    async def handle_hybrid_request(self, event: HiveEvent):
        packet_dict = event.payload
        try:
            packet = JobPacket(**packet_dict)
        except Exception: return

        if packet.config.agent_id != AgentID.BETA and packet.config.module_id == "delta_pinch_extract":
             # We execute solely if explicitly flagged for Hybrid Extraction
             await self.execute_pinchtab_flow(packet)
             
    async def execute_pinchtab_flow(self, packet: JobPacket):
        """
        Executes a real Chromium action to extract DOM parameters/tokens.
        """
        target_url = packet.target.url
        
        await self.bus.publish(HiveEvent(
            type=EventType.LOG,
            source=self.name,
            payload={"message": f"ðŸŒ DELTA: Engaging Hybrid Array. Querying PinchTab Wrapper for ({target_url})..."}
        ))
        
        async with aiohttp.ClientSession() as session:
            # 1. Instruct Browser to Nav
            success = await self._pinch_nav(session, target_url)
            if not success:
                print(f"[{self.name}] PinchTab unreachable. Failing gracefully to standard API execution.")
                return

            # 2. Extract DOM Live Context
            dom_text = await self._pinch_text(session)
            
            # 3. Intelligence Token Miner
            token = self._extract_token(dom_text)
            
            if token:
                 await self.bus.publish(HiveEvent(
                     type=EventType.LOG,
                     source=self.name,
                     payload={"message": f"ðŸŒ DELTA: DOM Exfiltration Successful. Session Token captured for injection vector."}
                 ))
                 # Send token upstream to state/Sigma for Auth binding
                 await self.bus.publish(HiveEvent(
                    type=EventType.JOB_COMPLETED,
                    source=self.name,
                    payload={
                        "job_id": packet.id,
                        "status": "SUCCESS",
                        "data": {"dom_token": token, "source_url": target_url}
                    }
                 ))
    
    def _extract_token(self, dom_text: str) -> str:
        # Ground Truth regex hunting for localized DOM tokens in React states / LocalStorage dumps
        match = re.search(r"(?:token|auth|session)['\"]?\s*:\s*['\"]([^'\"]{20,})['\"]", dom_text, re.IGNORECASE)
        return match.group(1) if match else None
