import asyncio
import re
import aiohttp
import os
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskTarget

class AgentDelta(BaseAgent):
    """
    AGENT DELTA: HYBRID BROWSER CONTROLLER (DOM + API FUSION)
    Role: Control PinchTab externally, execute client-side workflows, and extract live DOM evidence.
    """
    PINCHTAB_URL = "http://localhost:9867"
    PINCHTAB_CLI = "c:\\my2\\Vulagent\\pinchtab_core\\pinchtab.exe"

    def __init__(self, bus):
        super().__init__("agent_delta", bus)
        
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
        if not os.path.exists(self.PINCHTAB_CLI):
            print(f"[{self.name}] Native PinchTab binary missing at {self.PINCHTAB_CLI}")
            return False
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                self.PINCHTAB_CLI, "nav", url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=15.0)
            return proc.returncode == 0
        except Exception as e:
            print(f"[{self.name}] Native CLI Nav Error: {e}")
            return False
        finally:
            await self._safe_kill(proc)

    async def _pinch_text(self, session):
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                self.PINCHTAB_CLI, "text",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            decoded = stdout.decode('utf-8', errors='ignore')
            
            # V6-PRODUCTION: Structured Parsing
            try:
                import json
                parsed_dom = json.loads(decoded)
            except json.JSONDecodeError:
                parsed_dom = {"text": decoded, "inputs": [], "buttons": [], "forms": []}
                
            return parsed_dom if proc.returncode == 0 else {}
        except Exception:
            return {}
        finally:
            await self._safe_kill(proc)

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
        try:
            packet = JobPacket(**packet_dict)
            if packet.config.module_id == "delta_pinch_extract":
                await self.execute_pinchtab_flow(packet)
        except Exception: pass
             
    async def execute_pinchtab_flow(self, packet: JobPacket):
        target_url = packet.target.url
        async with aiohttp.ClientSession() as session:
            success = await self._pinch_nav(session, target_url)
            if not success: return
            dom_data = await self._pinch_text(session)
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
