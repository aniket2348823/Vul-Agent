import asyncio
import logging
from abc import ABC, abstractmethod
from backend.core.protocol import JobPacket, ResultPacket, AgentStatus, TaskTarget, Vulnerability
from typing import Any

class BaseAgent(ABC):
    """
    The Thinking Entity. 
    It has an Inbox (Queue) and an Outbox.
    """
    def __init__(self, name: str, event_bus):
        self.name = name
        self.bus = event_bus
        self.inbox = asyncio.Queue()
        self.status = AgentStatus.IDLE
        # Hybrid AI Engine available to all agents
        self._cortex = None  # Lazy-loaded to avoid circular imports
        self.arsenal = {} # Loaded Modules

    async def start(self):
        logging.info(f"🤖 {self.name} Online.")
        while True:
            # Listen for tasks
            packet = await self.inbox.get()
            self.status = AgentStatus.WORKING
            
            try:
                await self.process(packet)
            except Exception as e:
                logging.error(f"💥 {self.name} Crashed: {e}")
            finally:
                self.status = AgentStatus.IDLE
                self.inbox.task_done()

    @abstractmethod
    async def process(self, packet: JobPacket):
        """The specific logic of the agent."""
        pass

class BaseArsenalModule(ABC):
    """
    The Weapon Template.
    """
    def __init__(self):
        self.name = "Unknown Module"
        self.description = "Generic Module"

    @abstractmethod
    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        """INPUT -> PAYLOADS. Must be pure, no execution."""
        pass

    @abstractmethod
    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        """OBSERVE. Pure string evaluation of all generated payloads."""
        pass
    
    @property
    def cortex(self):
        """Lazy-load CortexEngine for hybrid AI in arsenal modules."""
        if not hasattr(self, '_cortex') or self._cortex is None:
            from backend.ai.cortex import CortexEngine, get_cortex_engine
            self._cortex = get_cortex_engine()
        return self._cortex
    
    async def think(self, context: Any):
        """
        The AI Integration Slot.
        Override this with specific logic (LLM, Heuristic, etc).
        All agents/modules have access to self.cortex (CortexEngine) for hybrid AI.
        """
        pass
    
    async def async_fetch(self, url: str, timeout: int = 5):
        """Helper to fetch content from HTTP or local FILE protocol."""
        if url.startswith("file:///"):
            path = url.replace("file:///", "").replace("%20", " ")
            # Basic path safety check for prototype
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return await asyncio.to_thread(f.read)
            except Exception as e:
                return f"Error reading file: {e}"
        else:
            import aiohttp
            MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB cap (Omega Fix 4)
            # ELE-ST FIX 3: Strict timeout to prevent Tarpit stalled loops
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout, sock_read=timeout)) as resp:
                        # OMEGA FIX 4: Stream with size cap
                        chunks = []
                        bytes_read = 0
                        async for chunk in resp.content.iter_chunked(65536):
                            bytes_read += len(chunk)
                            if bytes_read > MAX_RESPONSE_SIZE:
                                break
                            chunks.append(chunk)
                        return b"".join(chunks).decode("utf-8", errors="replace")
            except asyncio.TimeoutError:
                return f"Error: Request timed out after {timeout}s (Possible Tarpit)"
            except aiohttp.ClientPayloadError as e:
                # OMEGA FIX 2: Network Guillotine (TCP FIN/RST mid-transfer)
                return f"Error: Server dropped connection mid-transfer ({e})"
            except aiohttp.ServerDisconnectedError as e:
                # OMEGA FIX 2: Network Guillotine
                return f"Error: Server disconnected abruptly ({e})"
            except Exception as e:
                return f"Error: Request failed {e}"

    @staticmethod
    def safe_json_parse(raw_text: str, max_depth: int = 100):
        """
        OMEGA FIX 1: Safe JSON parser with depth limiter.
        Prevents RecursionError from deeply nested JSON bombs.
        """
        import json
        # Quick depth check: count max consecutive '{' or '[' sequences
        depth = 0
        max_seen = 0
        for char in raw_text[:10000]:  # Only scan first 10KB for depth
            if char in ('{', '['):
                depth += 1
                if depth > max_seen:
                    max_seen = depth
            elif char in ('}', ']'):
                depth -= 1
        
        if max_seen > max_depth:
            return {"error": f"JSON depth {max_seen} exceeds limit {max_depth}", "truncated": True}
        
        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, RecursionError) as e:
            return {"error": f"JSON parse failed: {e}", "raw_preview": raw_text[:200]}

    def log(self, msg):
        logging.info(f"[{self.name}] {msg}")
