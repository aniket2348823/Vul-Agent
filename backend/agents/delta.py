import asyncio
import re
import aiohttp
import os
from backend.core.queue import command_lane, LanePriority
from backend.core.content_boundary import content_boundary
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskTarget
from backend.core.sandbox import TempWorkspace
from backend.integrations.pinchtab_client import PinchTabClient

class AgentDelta(BaseAgent):
    """
    AGENT DELTA: HYBRID BROWSER CONTROLLER (DOM + API FUSION)
    Role: Control PinchTab externally, execute client-side workflows, and extract live DOM evidence.
    """
    def __init__(self, bus):
        super().__init__("agent_delta", bus)
        self.pinchtab = PinchTabClient()
        self._last_tab_id = ""
        
    async def setup(self):
        # Triggered by Recon/Orchestrator when navigating routes
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_hybrid_request)

    async def _safe_kill(self, proc):
        if not proc or proc.returncode is not None:
            return
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except Exception:
            try:
                if os.name == 'nt':
                    # Windows Hard-Kill fallback for zombie Chromium processes
                    os.system(f"taskkill /F /T /PID {proc.pid}")
                else:
                    proc.kill()
            except Exception: pass

    async def _pinch_nav(self, session, url):
        try:
            await self.pinchtab.health()
            nav = await self.pinchtab.navigate(url)
            self._last_tab_id = str(nav.get("tabId") or nav.get("id") or nav.get("targetId") or "")
            return bool(self._last_tab_id)
        except Exception as e:
            print(f"[{self.name}] PinchTab HTTP Nav Error: {e}")
            return False

    async def _pinch_text(self, session):
        try:
            if not self._last_tab_id:
                return {}
            text = await self.pinchtab.text(self._last_tab_id)
            snapshot = await self.pinchtab.snapshot(self._last_tab_id)
            return {"text": str(text), "snapshot": snapshot, "inputs": [], "buttons": [], "forms": []}
        except Exception:
            return {}

    def _semantic_refine(self, dom_data: dict) -> dict:
        classification = "unknown"
        text_content = str(dom_data.get("text", "")).lower()
        if "password" in text_content or "login" in text_content:
            classification = "login"
        elif "checkout" in text_content or "card" in text_content:
            classification = "payment"
        elif "search" in text_content:
            classification = "search"
        
        actions = []
        for inp in dom_data.get("inputs", []):
            name = inp.get("name", inp.get("id", "unknown"))
            actions.append({"type": "input", "target": name, "intent": classification})
        for btn in dom_data.get("buttons", []):
            actions.append({"type": "click", "target": btn.get("text", "submit"), "intent": classification})

        return {"ui_type": classification, "actions_mapped": actions}

    async def handle_hybrid_request(self, event: HiveEvent):
        packet_dict = event.payload
        # ScanContext: record event for transcript causality
        if hasattr(self.bus, 'get_or_create_context'):
            _ctx = self.bus.get_or_create_context(getattr(event, 'scan_id', 'GLOBAL'))
            _ctx.append_event(event)
        try:
            packet = JobPacket(**packet_dict)
            if packet.config.module_id == "delta_pinch_extract":
                await self.execute_pinchtab_flow(packet)
        except Exception: pass
             
    async def execute_pinchtab_flow(self, packet: JobPacket):
        target_url = packet.target.url
        async with TempWorkspace(prefix="delta-pinchtab") as workspace:
            success = await self._pinch_nav(None, target_url)
            if not success: return
            dom_data = await self._pinch_text(None)
            workspace.write_file("dom_text.txt", dom_data.get("text", ""))
            workspace.write_file("snapshot.json", str(dom_data.get("snapshot", {})))
            semantic_state = self._semantic_refine(dom_data)
            token = self._extract_token(dom_data.get("text", ""))
            
            if token or semantic_state.get("actions_mapped"):
                 await self.bus.publish(HiveEvent(
                    type=EventType.JOB_COMPLETED,
                    source=self.name,
                    payload={
                        "job_id": packet.id,
                        "status": "SUCCESS",
                        "data": {
                            "dom_token": token, 
                            "source_url": target_url,
                            "semantic_state": semantic_state,
                            "raw_dom_evidence": True
                        }
                    }
                 ))
    
    def _extract_token(self, dom_text: str) -> str:
        match = re.search(r"(?:token|auth|session|bearer)['\"]?\s*[:=]\s*['\"]([^'\"]{20,})['\"]", dom_text, re.IGNORECASE)
        return match.group(1) if match else None
