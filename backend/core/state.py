import json
import os
import asyncio
import hashlib
import threading

from typing import List, Dict, Any

STATE_FILE = "stats.json"
TMP_STATE_FILE = "stats.json.tmp"

class StateManager:
    def __init__(self):
        self._dirty = False
        self._task = None
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        self._stats = {
            "scans": [],
            "active_scans": 0,
            "total_scans": 0,
            "total_requests": 0, # Total requests sent in active session
            "vulnerabilities": 0,
            "critical": 0,
            "history": [0] * 30,  # Initialize with flatline for graph
            # V6: New Metrics
            "v6_metrics": {
                "injections_blocked": 0,
                "deceptive_ui_blocked": 0,
                "risk_score": 0
            }
        }
        self._seen_signatures = {} # {scan_id: set(signatures)}
        self._load()
        
    def _load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    saved_data = json.load(f)
                    # Update local stats with saved data while preserving structure
                    self._stats.update(saved_data)
                    # Ensure scans list exists
                    if "scans" not in self._stats:
                        self._stats["scans"] = []
            except Exception as e:
                print(f"[StateManager] Load Error: {e}")

    async def _background_writer(self):
        while True:
            await asyncio.sleep(2.0)
            if self._dirty:
                async with self._lock:
                    self._save_sync()

    def _mark_dirty(self):
        self._dirty = True
        try:
            loop = asyncio.get_running_loop()
            if self._task is None or self._task.done():
                self._task = loop.create_task(self._background_writer())
        except RuntimeError:
            self.flush_immediate()

    def flush_immediate(self):
        """Immediately force-save state to disk (Critical for report readiness)."""
        asyncio.run_coroutine_threadsafe(self._async_save(), asyncio.get_event_loop()) if self._task else self._save_sync()

    async def _async_save(self):
        async with self._lock:
            self._save_sync()

    def _save_sync(self):
        with self._sync_lock:
            try:
                with open(TMP_STATE_FILE, "w") as f:
                    json.dump(self._stats, f, indent=4, default=str)
                os.replace(TMP_STATE_FILE, STATE_FILE)
                self._dirty = False
            except Exception as e:
                print(f"[StateManager] Save Error: {e}")

    # Aliasing remaining references to old _save()
    def _save(self):
        self._mark_dirty()

    def get_stats(self):
        return self._stats

    async def register_scan(self, scan_data: Dict[str, Any]):
        async with self._lock:
            # Initialize event buffer for this scan to satisfy reporting requirements
            if "events" not in scan_data:
                scan_data["events"] = []
            
            # $O(1) appending is safer for high frequency, reports can sort by timestamp
            self._stats["scans"].append(scan_data)
            self._stats["active_scans"] += 1
            self._stats["total_scans"] += 1
            self._save()

    async def add_scan_event(self, scan_id: str, event: Dict[str, Any]):
        """Append a live event to a specific scan record with auto-pruning (Max 500)."""
        async with self._lock:
            for s in self._stats["scans"]:
                if s["id"] == scan_id:
                    if "events" not in s:
                        s["events"] = []
                    
                    s["events"].append(event)
                    
                    # [V7] Auto-Pruning REMOVED as per user request for "Show All"
                    # We keep all events for the current active session.
                    
                    self._dirty = True
                    break

    async def increment_request_count(self, count: int = 1):
        """Atomically increment the global request counter for performance tracking."""
        async with self._lock:
            self._stats["total_requests"] += count
            self._dirty = True


    async def record_finding(self, scan_id: str, severity: str = "Medium", signature_data: Dict[str, Any] = None):
        """Real-time update for a found vulnerability with async-safe deduplication."""
        async with self._lock:
            if signature_data:
                # Generate stable signature
                sig_str = json.dumps(signature_data, sort_keys=True, default=str)
                sig = hashlib.sha256(sig_str.encode()).hexdigest()
                
                if scan_id not in self._seen_signatures:
                    self._seen_signatures[scan_id] = set()
                
                if sig in self._seen_signatures[scan_id]:
                    return # Skip duplicate
                
                self._seen_signatures[scan_id].add(sig)

            self._stats["vulnerabilities"] += 1
            
            if severity.upper() in ["CRITICAL", "HIGH"]:
                self._stats["critical"] += 1

            
        # Update history immediate for graph spike
        # We take the current total and append/update last point
        current_total = self._stats["vulnerabilities"]
        
        # Simple Logic: Append new total to history for the graph
        self._stats["history"].append(current_total)
        if len(self._stats["history"]) > 30:
            self._stats["history"].pop(0)
            
        self._save()

    async def record_threat(self, threat_type: str, risk_score: int):
        """V6: Record a detected threat for metrics (Async-Safe)."""
        async with self._lock:
            v6 = self._stats.get("v6_metrics", {})
            
            # Categorize by threat type
            if threat_type.upper() in ["PROMPT_INJECTION", "HIDDEN_TEXT", "INVISIBLE_TEXT"]:
                v6["injections_blocked"] = v6.get("injections_blocked", 0) + 1
            elif threat_type.upper() in ["DARK_PATTERN_BLOCK", "DECEPTIVE_UI", "PHISHING"]:
                v6["deceptive_ui_blocked"] = v6.get("deceptive_ui_blocked", 0) + 1
            
            # Update cumulative risk score (Track peak risk)
            current_risk = v6.get("risk_score", 0)
            v6["risk_score"] = max(current_risk, risk_score)
            
            self._stats["v6_metrics"] = v6
            self._save()

        
    def complete_scan(self, scan_id: str, results: List[Any], duration: float):
        self._stats["active_scans"] = max(0, self._stats["active_scans"] - 1)
        
        # Clean up ephemeral signatures for this scan
        if scan_id in self._seen_signatures:
            del self._seen_signatures[scan_id]


        seen_results = set()
        unique_results = []

        for r in results:
            # Re-verify deduplication for the final results list
            payload = r.get('payload', {})
            # Normalized signature for result storage
            sig_data = {
                "u": str(payload.get('url', '')).strip().lower(),
                "t": str(payload.get('type', '')).upper(),
                "d": str(payload.get('data', payload.get('payload', '')))
            }
            sig = hashlib.sha256(json.dumps(sig_data, sort_keys=True, default=str).encode()).hexdigest()
            
            if sig not in seen_results:
                seen_results.add(sig)
                unique_results.append(r)
                
                verdict = payload.get('severity', payload.get('verdict', 'VULNERABLE')).upper()
                if 'CRITICAL' in verdict or 'LEAK' in verdict or 'HIGH' in verdict:
                    # Note: record_finding already incremented global counters for real-time scans
                    # This method updates the scan record itself. 
                    # Global counts are managed in real-time to avoid double-counting at the end.
                    pass
        
        for s in self._stats["scans"]:
            if s["id"] == scan_id:
                s["status"] = "Finalizing" # V6: AI is building the report
                # Defensive duration formatting
                try:
                    s["duration"] = f"{float(duration):.2f}s"
                except (TypeError, ValueError):
                    s["duration"] = "N/A"
                s["results"] = unique_results
                s["report_ready"] = s.get("report_ready", False) 
                break
        
        self.flush_immediate()

    def sync_complete_scan(self, scan_id: str, status: str = "Completed", report_ready: bool = True):
        """Atomic completion to avoid race conditions between 'Completed' and 'Report Ready'."""
        self._stats["active_scans"] = max(0, self._stats["active_scans"] - 1)
        for s in self._stats["scans"]:
            if s["id"] == scan_id:
                s["status"] = status
                s["report_ready"] = report_ready
                break
        self.flush_immediate()

    def mark_report_ready(self, scan_id: str):
        """V6: Mark the AI report as generated and ready for instant download."""
        for s in self._stats["scans"]:
            if s["id"] == scan_id:
                s["report_ready"] = True
                # Safety: If it's ready, it shouldn't be in a 'Finalizing' or 'Running' state anymore
                if s["status"] in ["Finalizing", "Running"]:
                    s["status"] = "Completed"
                break
        self.flush_immediate()
                
    def wipe_scans(self):
        """Wipe all historical scan records from the database."""
        self._stats["scans"] = []
        self._stats["total_scans"] = 0
        self._stats["active_scans"] = 0
        self._stats["vulnerabilities"] = 0
        self._stats["critical"] = 0
        self._stats["history"] = [0] * 30
        self._save()
        print("[StateManager] All historical scans wiped successfully.")

    def reset_stale_scans(self):
        """Called on startup to clean up zombie scans."""
        cleaned = 0
        for s in self._stats["scans"]:
            if s["status"] == "Running":
                s["status"] = "Interrupted"
                cleaned += 1
        self._stats["active_scans"] = 0
        if cleaned > 0:
            self._save()
        return cleaned

# Singleton Instance
stats_db_manager = StateManager()
# Legacy Accessor (for backward compatibility if needed, but prefer manager)
stats_db = stats_db_manager._stats
