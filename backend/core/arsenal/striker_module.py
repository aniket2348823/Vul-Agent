import asyncio
import aiohttp
import time
import random
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from backend.core.protocol import JobPacket, ResultPacket, TaskTarget

logger = logging.getLogger("Xytherion.Arsenal.Striker")

class StrikerModule:
    """
    STRIKER ARSENAL MODULE
    Extracted from BetaAgent for distributed worker execution.
    Role: High-velocity HTTP attack execution and evaluation.
    """
    def __init__(self, bus=None):
        self.bus = bus # Local EventBus on worker
        self.max_concurrency = 10

    async def execute_assault(self, target_url: str, payloads: list) -> list:
        """Executes a multi-vector assault using a list of weaponized payloads."""
        results = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._execute_single(session, target_url, p) for p in payloads]
            results = await asyncio.gather(*tasks)
        return results

    async def _execute_single(self, session, url: str, payload: str) -> Dict:
        """Executes a single payload and evaluates for anomalies."""
        start_t = time.time()
        result_data = {
            "payload": payload,
            "status": 0,
            "latency": 0,
            "anomaly": False,
            "result": "ERROR"
        }
        
        try:
            # Construct weaponized URL
            target = url + ("&" if "?" in url else "?") + f"test={payload}"
            
            async with session.get(target, timeout=10) as resp:
                text = await resp.text()
                status = resp.status
                latency = int((time.time() - start_t) * 1000)
                
                result_data.update({
                    "status": status,
                    "latency": latency,
                })
                
                # Anomaly Detection Heuristics
                text_lower = text.lower()
                p_lower = payload.lower()
                is_malicious = any(k in p_lower for k in ["'", '"', "<", ">", "script", "union", "select", "etc/passwd", "sleep(", "drop "])
                
                if status >= 500 or any(kw in text_lower for kw in ["syntax error", "unexpected", "sql", "mysql", "database", "warning"]):
                    result_data["anomaly"] = True
                    result_data["result"] = "ERROR / SYNTAX"
                elif status == 200 and is_malicious:
                    result_data["anomaly"] = True
                    result_data["result"] = "INJECTION / BYPASS"
                elif status == 403 or status == 401:
                    result_data["result"] = "WAF BLOCKED"
                else:
                    result_data["result"] = "OK"
                
                # If an anomaly is found, report it via the bus (if provided)
                if result_data["anomaly"] and self.bus:
                    from backend.core.hive import HiveEvent, EventType
                    await self.bus.publish(HiveEvent(
                        type=EventType.VULN_CANDIDATE,
                        source="Worker.Striker",
                        payload={
                            "url": url,
                            "payload": payload,
                            "description": text[:500],
                            "evidence": f"HTTP {status} triggered {result_data['result']}"
                        }
                    ))
                    
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            result_data["result"] = "CRASH"
            
        return result_data

    async def evaluate_rl_reward(self, result: Dict) -> float:
        """Calculates RL reward based on execution outcome."""
        if result["result"] == "INJECTION / BYPASS": return 1.0
        if result["result"] == "ERROR / SYNTAX": return 0.8
        if result["result"] == "WAF BLOCKED": return -0.5
        return 0.0
