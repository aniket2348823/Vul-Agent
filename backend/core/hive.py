import asyncio
import logging
import json
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

from backend.core.protocol import ModuleConfig, ResultPacket, Vulnerability
from backend.core.context import ScanContext
import collections

class EventBus:
    """
    The central message broker. 
    Decouples agents so they never talk directly.
    """
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable[[HiveEvent], Awaitable[None]]]] = {}
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
        
        # CRITICAL FIX 1: Exact-once deduplication window (FIFO)
        if hasattr(ctx, "_recent_events_fifo") is False:
            ctx._recent_events_fifo = collections.deque(maxlen=1000)

        if event.id in ctx._recent_events:
            return  # Drop duplicate
            
        ctx._recent_events.add(event.id)
        ctx._recent_events_fifo.append(event.id)
        
        # Maintain Set Size (Oldest removal)
        if len(ctx._recent_events) > 1000:
            try:
                oldest = ctx._recent_events_fifo.popleft()
                ctx._recent_events.discard(oldest)
            except IndexError: pass
            
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

    async def evict_scan_context(self, scan_id: str):
        """Standard Memory Guard: Purge historical scan state and tasks."""
        if scan_id in self.scan_contexts:
            ctx = self.scan_contexts.pop(scan_id)
            ctx.is_cancelled = True
            task = self._context_tasks.pop(scan_id, None)
            if task:
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass
            logging.info(f"🧹 Scan Context {scan_id} successfully evicted from Hive memory.")


class DistributedEventBus(EventBus):
    """
    XYTHERION DISTRIBUTED NERVOUS SYSTEM
    Role: Bridges local agent events to the global Redis cluster.
    """
    def __init__(self, redis_url: str):
        super().__init__()
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.is_running = False


    async def start(self):
        """Activates the distributed bridge."""
        self.is_running = True
        await self.pubsub.subscribe("xytherion_events")
        asyncio.create_task(self._listen_loop())
        logger.info("📡 Distributed Event Bus Online (Async).")


    async def _listen_loop(self):
        """Listens for global events and injects them into the local hive (Fixed Async)."""
        try:
            async for message in self.pubsub.listen():
                if not self.is_running: break
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event = HiveEvent(**event_data)
                        
                        # Local Broadcast
                        await super().publish(event)
                    except Exception as e:
                        logging.error(f"[DistributedEventBus] Remote injection failed: {e}")
        except Exception as e:
            if self.is_running:
                logging.error(f"[DistributedEventBus] Listen loop crash: {e}")


    async def publish(self, event: HiveEvent):
        """Broadcasts local events to the global cluster and routes jobs with safety locking."""
        # 1. Local Broadcast
        await super().publish(event)
        
        # 2. Global Broadcast (Redis Channel for UI/Sync)
        try:
            event_json = event.model_dump_json()
            await self.redis_client.publish("xytherion_events", event_json)
            
            # 3. WORKER ROUTING & SAFETY LOCKING (V6-HARDENED ASYNC)
            if event.type == EventType.JOB_ASSIGNED:
                task_id = event.payload.get("task_id", event.id)
                lock_key = f"job_lock:{task_id}"
                
                # Attempt to acquire a global lock (Async)
                if await self.redis_client.set(lock_key, "LOCKED", nx=True, ex=3600):
                    # ROUTE A: Audit Layer (Inspector)
                    await self.redis_client.lpush("xytherion_audit_queue", event_json)
                    
                    # ROUTE B: Work Queue (Master will redistribute)
                    task_payload = event.payload
                    if "task_id" not in task_payload:
                        task_payload["task_id"] = task_id
                    
                    # Log the Job Routing formally
                    logging.info(f"🚀 [Hive] Routing Job {task_id} to global work queue.")
                    await self.redis_client.lpush("pending_tasks", json.dumps(task_payload))
                else:
                    logging.debug(f"[DistributedEventBus] Job {task_id} already locked. Skipping global push.")

                
        except Exception as e:
            # Stage 10 Hardening: Capture and log the full error with source
            err_type = type(e).__name__
            logging.error(f"[DistributedEventBus] Global publishing failed ({err_type}): {e}")




# --- 3. THE DNA (Base Agent) ---

from backend.core.database import db_manager

class BaseAgent:
    """
    The template for all Hive Agents.
    Enforces a standard lifecycle: Wake -> Think -> Act.
    """
    def __init__(self, name: str, bus: EventBus):
        self.name = name
        self.bus = bus
        self.db = db_manager # Distributed Intelligence Backbone
        self.active = False
        self.status = "IDLE"

    async def start(self):
        """Wakes the agent up."""
        self.active = True
        self.status = "ACTIVE"
        self._agent_tasks = set()
        
        # Ensure DB connections are active
        await self.db.initialize()
        
        logging.info(f"🤖 {self.name} is ONLINE. Intelligence backbone synced.")
        
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
        
        # Shutdown AI Engine if it exists (CortexEngine holds aiohttp session)
        for attr in ["cortex", "ai"]:
            engine = getattr(self, attr, None)
            if engine and hasattr(engine, "shutdown"):
                await engine.shutdown()

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
        Subclasses (Prism, Chi) should override this.
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
