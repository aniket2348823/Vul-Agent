import asyncio
import psutil
import time
import random
from typing import List, Dict, Any
from collections import deque
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket
from backend.core.queue import command_lane
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.content_boundary import content_boundary

# Browser Integration (Phase 4)
from backend.core.browser_orchestrator import BrowserOrchestrator
from backend.core.hybrid_session_manager import HybridSessionManager
from backend.core.forensic_collector import ForensicCollector

class ZetaAgent(BaseAgent):
    """
    AGENT ZETA: THE CORTEX
    Capabilities:
    - Predictive Auto-Scaling (Linear Regression).
    - Error Budget Economy.
    - QoS Multiplexing.
    - Dynamic IP Rotation.
    - SOTA: Sentiment Analysis (Server Stress).
    - SOTA: Adaptive Gaussian Jitter.
    - Browser resource monitoring and cleanup
    """
    def __init__(self, bus):
        super().__init__("agent_zeta", bus)
        
        self.latency_window = deque(maxlen=50) 
        self.error_window = deque(maxlen=50)   
        
        self.error_budget_max = 50
        self.error_budget_current = 50
        self.last_budget_refill = time.time()
        
        self.priority_queue = {0: [], 1: [], 2: []}
        # Hybrid AI Engine for stress analysis
        self.cortex = get_cortex_engine()
        
        # Browser Integration
        self.browser = BrowserOrchestrator()
        self.session_manager = HybridSessionManager()
        self.forensics = ForensicCollector()
        
        # Browser resource tracking
        self.browser_memory_threshold = 500 * 1024 * 1024  # 500MB
        self.max_browser_contexts = 5

    async def setup(self):
        self.bus.subscribe(EventType.JOB_COMPLETED, self.handle_job_completion)
        self.bus.subscribe(EventType.RECON_PACKET, self.handle_recon_packet)

    async def handle_recon_packet(self, event: HiveEvent):
        status = str(event.payload.get("status", event.payload.get("http_status", "")))
        evidence = str(event.payload.get("evidence", "")).lower()
        if status in {"403", "429"} or "forbidden" in evidence or "rate limit" in evidence:
            self.error_window.append(True)
            self.error_budget_current = max(0, self.error_budget_current - 2)

    async def handle_job_completion(self, event: HiveEvent):
        payload = event.payload
        # ScanContext: record event for transcript causality
        if hasattr(self.bus, "get_or_create_context"):
            _ctx = self.bus.get_or_create_context(getattr(event, "scan_id", "GLOBAL"))
            _ctx.append_event(event)
        if "duration_ms" in payload:
            self.latency_window.append(payload["duration_ms"])
        
        if "success" in payload:
            is_error = not payload["success"] 
            self.error_window.append(is_error)
            
            # HYBRID AI: Deep Server Stress Analysis
            if is_error and "data" in payload:
                 error_msg = str(payload["data"])
                 stress_analysis = await self.cortex.analyze_server_stress(error_msg)
                 stress_level = stress_analysis.get("stress_level", "NORMAL")
                 indicators = stress_analysis.get("indicators", [])
                 action = stress_analysis.get("recommended_action", "CONTINUE")
                 
                 if stress_level in ["HIGH", "MEDIUM"]:
                     penalty = 10 if stress_level == "HIGH" else 5
                     self.error_budget_current -= penalty
                     print(f"[{self.name}] Server Sentiment: {stress_level} (AI: {indicators}) -> Action: {action}")
                     
                     if action == "ABORT":
                         await self.broadcast_signal("STEALTH_MODE", {"reason": f"AI: Server Stress {stress_level}"})
                     elif action == "THROTTLE":
                         await self.broadcast_signal("THROTTLE", {"level": "HIGH", "reason": f"AI: {indicators}"})

    async def lifecycle(self):
        while self.active:
            await self.governance_cycle()
            await self.refill_budget()
            await self.drain_queue()
            await asyncio.sleep(1.0)

    async def governance_cycle(self):
        # 1. PREDICTIVE AUTO-SCALING
        if len(self.latency_window) > 10:
            trend = self.calculate_trend(list(self.latency_window))
            if trend > 0.5: 
                 await self.broadcast_signal("THROTTLE", {"level": "HIGH", "reason": "Latency Acceleration"})

        # 2. ERROR BUDGET CHECK
        if self.error_budget_current < 5:
             await self.broadcast_signal("STEALTH_MODE", {"reason": "Error Budget Depleted"})

        # 3. DYNAMIC IP ROTATION
        if len(self.error_window) > 20:
            block_count = sum(1 for x in self.error_window if x is True)
            block_rate = block_count / len(self.error_window)
            if block_rate > 0.02: 
                await self.broadcast_signal("INFRA_ROTATE", {"reason": "High Block Rate"})
                self.error_window.clear()

        # 4. STATISTICAL ANOMALY DETECTION (Z-Score)
        is_anomaly, reason = self.detect_anomalies()
        if is_anomaly:
            print(f"[{self.name}] ANOMALY DETECTED: {reason}")
            await self.broadcast_signal("THROTTLE", {"level": "CRITICAL", "reason": reason})
            self.error_budget_current -= 10  # Severe penalty for triggering defensive mechanisms

        telemetry = command_lane.telemetry
        if telemetry["active_count"] >= telemetry["max_concurrent"] or telemetry["total_timed_out"] > 0:
            await self.broadcast_signal("THROTTLE", {
                "level": "HIGH",
                "reason": f"CommandLane pressure active={telemetry['active_count']} timed_out={telemetry['total_timed_out']}"
            })

    def detect_anomalies(self) -> tuple[bool, str]:
        """SOTA: Z-Score Statistical Anomaly Detection for WAF/Firewall triggers."""
        if len(self.latency_window) > 15:
            latencies = list(self.latency_window)
            mean = sum(latencies) / len(latencies)
            variance = sum((x - mean) ** 2 for x in latencies) / len(latencies)
            std_dev = max(variance ** 0.5, 0.001)
            
            latest_latency = latencies[-1]
            z_score = (latest_latency - mean) / std_dev
            
            if z_score > 3.0: # 3 standard deviations = anomaly (e.g. sudden WAF tarpit)
                return True, f"Latency Spike Anomaly (Z-Score: {z_score:.2f})"
        return False, ""

    def calculate_jitter(self):
        """
        SOTA: Adaptive Gaussian Jitter.
        Instead of random(0, 5), use Gaussian distribution to mimic human variance.
        """
        # Mean = 1.5s, StdDev = 0.5s
        jitter = random.gauss(1.5, 0.5)
        return max(0.1, jitter)

    def calculate_trend(self, data: List[float]) -> float:
        n = len(data)
        if n < 2: return 0.0
        x = range(n)
        y = data
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denominator = sum((xi - x_mean) ** 2 for xi in x)
        return numerator / denominator if denominator != 0 else 0.0

    async def refill_budget(self):
        now = time.time()
        if now - self.last_budget_refill > 60:
            if self.error_budget_current < self.error_budget_max:
                self.error_budget_current += 1
            self.last_budget_refill = now

    async def drain_queue(self):
        """Process queued jobs from the priority queue."""
        for priority in [0, 1, 2]:  # 0 = highest priority
            while self.priority_queue[priority]:
                job = self.priority_queue[priority].pop(0)
                # Process or delegate job
                pass

    async def broadcast_signal(self, type: str, payload: Dict[str, Any]):
        await self.bus.publish(HiveEvent(
            type=EventType.CONTROL_SIGNAL,
            source=self.name,
            payload={"signal": type, "data": payload}
        ))
        # Broadcast to Dashboard: Governance action
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            payload={"url": "System", "arsenal": f"Governance: {type}", "action": type, "payload": str(payload.get('reason', ''))[:50]}
        ))
    
    def validate_job(self, packet: JobPacket) -> bool:
        """
        Cyber-Organism Protocol: Pre-Flight Check.
        Called by other agents before execution (Simulating synchronous RPC or shared state).
        """
        # 1. Latency Check (> 500ms?)
        if self.latency_window:
            avg_latency = sum(self.latency_window) / len(self.latency_window)
            if avg_latency > 500:
                print(f"[{self.name}]: DENY JOB {packet.id}. High Latency ({avg_latency:.1f}ms).")
                return False

        # 2. Budget Check (< 10?)
        if self.error_budget_current < 10:
             print(f"[{self.name}]: DENY JOB {packet.id}. Low Budget ({self.error_budget_current}).")
             return False

        return True

    # ============ BROWSER RESOURCE MONITORING (Phase 4) ============
    
    async def _monitor_browser_memory(self) -> dict:
        """Monitor browser memory usage and detect leaks."""
        try:
            # Get current process memory
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Check if browser memory exceeds threshold
            if memory_info.rss > self.browser_memory_threshold:
                print(f"[{self.name}] Browser memory threshold exceeded: {memory_info.rss / 1024 / 1024:.1f}MB")
                
                # Trigger cleanup
                await self._close_idle_contexts()
                
                return {
                    "memory_mb": memory_info.rss / 1024 / 1024,
                    "threshold_exceeded": True,
                    "action": "cleanup_triggered"
                }
            
            return {
                "memory_mb": memory_info.rss / 1024 / 1024,
                "threshold_exceeded": False
            }
            
        except Exception as e:
            print(f"[{self.name}] Browser memory monitoring failed: {e}")
            return {}
    
    async def _get_active_contexts(self) -> list:
        """Get list of active browser contexts."""
        try:
            # This would query OpenClaw for active contexts
            # Placeholder implementation
            active_contexts = []
            
            return active_contexts
        except Exception as e:
            print(f"[{self.name}] Context enumeration failed: {e}")
            return []
    
    async def _close_idle_contexts(self) -> int:
        """Close idle browser contexts to free memory."""
        try:
            print(f"[{self.name}] Closing idle browser contexts...")
            
            active_contexts = await self._get_active_contexts()
            
            closed_count = 0
            for context in active_contexts:
                # Check if context is idle (no activity for >5 minutes)
                if context.get("idle_time", 0) > 300:
                    # Close context
                    # This would call OpenClaw API to close context
                    closed_count += 1
            
            print(f"[{self.name}] Closed {closed_count} idle contexts")
            
            return closed_count
            
        except Exception as e:
            print(f"[{self.name}] Context cleanup failed: {e}")
            return 0
