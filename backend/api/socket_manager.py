from typing import List, Dict, Any
from fastapi import WebSocket
import json
import logging
import asyncio
import random
import time

# --- Adaptive 300 Monitoring Logic ---
def get_display_limit(rps):
    if rps <= 200:
        return rps
    elif rps <= 600:
        return int(rps * 0.6)
    else:
        return 400

def should_emit(event: Dict[str, Any], rps: float) -> bool:
    # Priority: Always show anomalies or high severity — NEVER drop these
    if event.get("anomaly") or event.get("severity") in ["high", "CRITICAL", "HIGH", "MEDIUM"]:
        return True
    
    # Always show if result indicates a security event
    result = str(event.get("result", "")).upper()
    if any(kw in result for kw in ["ERROR", "INJECTION", "BYPASS", "LEAK", "BLOCKED", "SENSITIVE", "API"]):
        return True
    
    # Low RPS: show everything
    if rps <= 100:
        return True
    
    # Adaptive sampling for low priority events at high RPS
    display_limit = get_display_limit(rps)
    display_rate = display_limit / max(rps, 1)
    
    return random.random() < display_rate

# Global scan target URL for filtering (set by orchestrator)
_active_scan_target = ""

def set_active_scan_target(url: str):
    global _active_scan_target
    _active_scan_target = url

def get_active_scan_target() -> str:
    return _active_scan_target

async def publish_request_event(data: Dict[str, Any]):
    """Publish a request event with adaptive sampling. Fully error-hardened."""
    try:
        if manager is None:
            return
        
        # Approximate current RPS based on manager's recent volume
        current_rps = getattr(manager, 'recent_rps', 0)
        
        if should_emit(data, current_rps):
            # Determine severity from event data
            raw_severity = str(data.get("severity", "")).upper()
            if not raw_severity or raw_severity == "NONE":
                # Derive severity from result/anomaly
                result_str = str(data.get("result", "")).upper()
                if data.get("anomaly") or any(kw in result_str for kw in ["INJECTION", "BYPASS", "LEAK", "ERROR"]):
                    raw_severity = "HIGH"
                elif "BLOCKED" in result_str:
                    raw_severity = "MEDIUM"
                elif "API" in result_str or "SENSITIVE" in result_str:
                    raw_severity = "MEDIUM"
                else:
                    raw_severity = "INFO"

            # Determine risk score from severity if not provided
            risk_score = data.get("risk_score")
            if risk_score is None or risk_score == 0:
                risk_map = {"CRITICAL": 95, "HIGH": 75, "MEDIUM": 50, "LOW": 25, "INFO": 10}
                risk_score = risk_map.get(raw_severity, 15)

            # Format for Dashboard.jsx
            url_raw = str(data.get("url", data.get("endpoint", "Unknown")))
            formatted_event = {
                "type": "LIVE_THREAT_LOG",
                "payload": {
                    "timestamp": data.get("timestamp", time.strftime("%H:%M:%S")),
                    "agent": data.get("agent", "alpha_recon"),
                    "threat_type": data.get("result", "TRAFFIC"),
                    "method": data.get("method", "GET"),
                    "endpoint": data.get("endpoint", url_raw[-40:]),
                    "url": url_raw,
                    "severity": raw_severity,
                    "risk_score": risk_score,
                    "status": data.get("status", 0),
                    "anomaly": data.get("anomaly", False),
                    "result": data.get("result", "OK")
                }
            }
            await manager.broadcast(formatted_event)
    except Exception as e:
        logging.getLogger("Antigravity.SocketManager").error(f"publish_request_event error: {e}")

# ------------------------------------------

class SocketManager:
    def __init__(self):
        self.ui_connections: List[WebSocket] = []
        self.spy_connections: List[WebSocket] = []
        self.logger = logging.getLogger("Antigravity.SocketManager")
        
        self.last_spy_activity = 0.0
        self.message_queue = collections.deque(maxlen=5000) # Memory Guard: Cap overflow
        self._batch_task = None
        
        # [NEW] RPS Tracking for Adaptive Sampling
        self.packet_count = 0
        self.recent_rps = 0
        self._rps_task = None
        self._running = False


    def _start_tasks(self):
        if self._running: return
        self._running = True
        if self._batch_task is None:
            self._batch_task = asyncio.create_task(self._process_batch_queue())
        if self._rps_task is None:
            self._rps_task = asyncio.create_task(self._track_rps())

    async def stop_tasks(self):
        """Cleanup Lifecycle: Stop background monitoring tasks."""
        self._running = False
        if self._batch_task:
            self._batch_task.cancel()
            self._batch_task = None
        if self._rps_task:
            self._rps_task.cancel()
            self._rps_task = None


    async def _track_rps(self):
        """Calculates RPS every second for adaptive sampling."""
        while self._running:
            await asyncio.sleep(1.0)
            self.recent_rps = self.packet_count
            self.packet_count = 0

    async def _process_batch_queue(self):
        """Batches messages and sends to UI at ~50 FPS."""
        while self._running:

            try:
                await asyncio.sleep(0.02)
                if self.message_queue:
                    # Thread-safe dequeue of all items
                    batch = []
                    while self.message_queue:
                        try:
                            batch.append(self.message_queue.popleft())
                        except IndexError: break
                    
                    if not batch: continue

                    
                    def sanitize_bytes(obj):
                        if isinstance(obj, bytes):
                            return obj.hex()
                        return str(obj)

                    async def send_with_timeout(connection, msg):
                        try:
                            await asyncio.wait_for(connection.send_text(msg), timeout=1.0)
                            return None
                        except Exception:
                            return connection

                    for event_obj in batch:
                        message = json.dumps(event_obj, default=sanitize_bytes)
                        if self.ui_connections:
                            results = await asyncio.gather(*(send_with_timeout(conn, message) for conn in self.ui_connections), return_exceptions=True)
                            for dead in results:
                                if isinstance(dead, WebSocket) and dead in self.ui_connections:
                                    self.ui_connections.remove(dead)
            except Exception as e:
                self.logger.error(f"Batch Error: {e}")
                await asyncio.sleep(1.0)

    def is_spy_online(self) -> bool:
        if len(self.spy_connections) > 0:
            return True
        return (time.time() - self.last_spy_activity) < 60.0

    async def mark_spy_alive(self):
        self.last_spy_activity = time.time()
        self.packet_count += 1 # Count for RPS

    async def connect(self, websocket: WebSocket, client_type: str = "ui"):
        self._start_tasks()
        await websocket.accept()
        if client_type == "spy":
            self.spy_connections.append(websocket)
            await self.broadcast_to_ui({
                "type": "SPY_STATUS",
                "payload": {"connected": True}
            })
        else:
            self.ui_connections.append(websocket)
            spy_is_online = self.is_spy_online()
            await websocket.send_text(json.dumps({
                "type": "SPY_STATUS",
                "payload": {"connected": spy_is_online}
            }))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.spy_connections:
            self.spy_connections.remove(websocket)
        elif websocket in self.ui_connections:
            self.ui_connections.remove(websocket)

    async def broadcast(self, data: dict):
        self.packet_count += 1
        await self.broadcast_to_ui(data)

    async def broadcast_to_ui(self, data: dict):
        self.message_queue.append(data)

manager = SocketManager()
