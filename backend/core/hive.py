import asyncio
import logging
from typing import Callable, Dict, List, Any, Awaitable
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime
import collections

# --- 1. THE VOCABULARY (Strict Schemas) ---

class EventType(str, Enum):
    SYSTEM_START = "SYSTEM_START"
    LOG = "LOG"
    TARGET_ACQUIRED = "TARGET_ACQUIRED"
    VULN_CANDIDATE = "VULN_CANDIDATE"
    VULN_CONFIRMED = "VULN_CONFIRMED"
    AGENT_STATUS = "AGENT_STATUS"
    JOB_ASSIGNED = "JOB_ASSIGNED"
    JOB_COMPLETED = "JOB_COMPLETED"
    CONTROL_SIGNAL = "CONTROL_SIGNAL"
    LIVE_ATTACK = "LIVE_ATTACK"
    RECON_PACKET = "RECON_PACKET"
    REPORT_READY = "REPORT_READY"

class HiveEvent(BaseModel):
    """
    The fundamental unit of communication.
    Every whisper in the hive must follow this structure.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scan_id: str = "GLOBAL"  # CRITICAL FIX 2: Scan Context Isolation
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: EventType
    source: str  # The Agent Name
    payload: Dict[str, Any] = {}

# --- 2. THE NERVOUS SYSTEM (Event Bus) ---

from backend.core.context import ScanContext

class EventBus:
    """
    The central message broker. 
    Decouples agents so they never talk directly.
    """
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable[[HiveEvent], Awaitable[None]]]] = {}
        self.history: List[HiveEvent] = [] # Optional: For replay/debugging
        self.scan_contexts: Dict[str, ScanContext] = {}
        self._context_tasks: Dict[str, asyncio.Task] = {}
        self._global_tasks = set()

    def get_or_create_context(self, scan_id: str) -> ScanContext:
        if scan_id not in self.scan_contexts:
            ctx = ScanContext(scan_id=scan_id)
            self.scan_contexts[scan_id] = ctx
            # CRITICAL FIX 3: Single consumer per scan ensures causal A->B->C ordering
            task = asyncio.create_task(self._scan_event_loop(ctx))
            self._context_tasks[scan_id] = task
        return self.scan_contexts[scan_id]

    async def _scan_event_loop(self, ctx: ScanContext):
        try:
            while not ctx.is_cancelled:
                event = await ctx.event_queue.get()
                if event.type in self.subscribers:
                    handlers = self.subscribers[event.type]
                    for handler in handlers:
                        # Wait strictly instead of fire-and-forget
                        await self._safe_execute(handler, event)
                ctx.event_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"[EventBus] Scan Loop failed for {ctx.scan_id}: {e}")

    def subscribe(self, event_type: EventType, handler: Callable[[HiveEvent], Awaitable[None]]):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        # logging.debug(f"🔌 Handler subscribed to {event_type}")

    def unsubscribe(self, event_type: EventType, handler: Callable[[HiveEvent], Awaitable[None]]):
        if event_type in self.subscribers and handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)

    async def publish(self, event: HiveEvent):
        """
        Broadcasts an event to all interested agents.
        Routes to purely causal queue isolation by default.
        """
        if event.scan_id == "GLOBAL":
            if event.type in self.subscribers:
                for handler in self.subscribers[event.type]:
                    task = asyncio.create_task(self._safe_execute(handler, event))
                    self._global_tasks.add(task)
                    task.add_done_callback(self._global_tasks.discard)
            return
            
        ctx = self.get_or_create_context(event.scan_id)
        
        # CRITICAL FIX 1: Exact-once deduplication window
        if event.id in ctx._recent_events:
            return  # Drop duplicate
            
        ctx._recent_events.add(event.id)
        if len(ctx._recent_events) > 1000:
            ctx._recent_events.pop()
            
        # Enqueue for causal execution
        await ctx.event_queue.put(event)

    async def _safe_execute(self, handler, event):
        try:
            await handler(event)
        except Exception as e:
            err_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            logging.error(f"[CRITICAL] Handler failed processing {event.type}: {err_msg}")

    async def shutdown(self):
        """Gracefully waits for and cancels all pending EventBus tasks."""
        for ctx in self.scan_contexts.values():
            ctx.is_cancelled = True
        for task in self._context_tasks.values():
            task.cancel()
        for task in self._global_tasks:
            task.cancel()
            
        if self._global_tasks:
            await asyncio.gather(*self._global_tasks, return_exceptions=True)
        if self._context_tasks:
            await asyncio.gather(*self._context_tasks.values(), return_exceptions=True)

# --- 3. THE DNA (Base Agent) ---

class BaseAgent:
    """
    The template for all Hive Agents.
    Enforces a standard lifecycle: Wake -> Think -> Act.
    """
    def __init__(self, name: str, bus: EventBus):
        self.name = name
        self.bus = bus
        self.active = False
        self.status = "IDLE"

    async def start(self):
        """Wakes the agent up."""
        self.active = True
        self.status = "ACTIVE"
        self._agent_tasks = set()
        logging.info(f"🤖 {self.name} is ONLINE.")
        
        # Subscribe to relevant events
        await self.setup()
        
        # Announce presence
        # Don't track this publish, it's safe to fire-and-forget to bus, because bus tracks it
        await self.bus.publish(HiveEvent(
            type=EventType.AGENT_STATUS,
            source=self.name,
            payload={"status": "ONLINE"}
        ))

        # Start the internal thinking loop (if needed)
        task = asyncio.create_task(self.lifecycle())
        self._agent_tasks.add(task)
        task.add_done_callback(self._agent_tasks.discard)

    async def stop(self):
        """Puts the agent to sleep."""
        self.active = False
        self.status = "OFFLINE"
        
        for task in getattr(self, "_agent_tasks", []):
            task.cancel()
        if getattr(self, "_agent_tasks", []):
            await asyncio.gather(*self._agent_tasks, return_exceptions=True)
            
        logging.info(f"💤 {self.name} is OFFLINE.")

    # --- ABSTRACT METHODS (Subclasses MUST implement these) ---

    async def setup(self):
        """Register subscriptions here."""
        pass

    async def lifecycle(self):
        """
        The Agent's internal 'Heartbeat'. 
        Some agents react (Event-driven), others act (Loop-driven).
        """
        pass

    async def think(self, context: Any):
        """
        The AI Integration Slot.
        Override this with specific logic (LLM, Heuristic, etc).
        """
        pass

    async def execute_task(self, packet):
        """
        Synchronous task execution for Defense API.
        Subclasses (Theta, Iota) should override this.
        """
        from backend.core.protocol import ResultPacket, Vulnerability
        
        # Default implementation - subclasses should override
        return ResultPacket(
            job_id=packet.id if hasattr(packet, 'id') else "unknown",
            source_agent=self.name,
            status="SAFE",
            vulnerabilities=[],
            execution_time_ms=0,
            data={}
        )
