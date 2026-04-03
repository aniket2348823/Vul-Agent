import asyncio
import difflib
import random
import re
import math
import collections
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskPriority, ModuleConfig
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

class GammaAgent(BaseAgent):
    """
    AGENT GAMMA: THE AUDITOR
    Role: Logic Verification & Bayesian Signal Classifier.
    Capabilities:
    - Deep heuristic signal processing (Leak, Oracle, Timing, Size, Logic).
    - Bayesian fusion equation for confidence grading.
    - AI Hybrid Fallback functionality.
    """
    def __init__(self, bus):
        super().__init__("agent_gamma", bus)
        
        # Arsenal stripped. Gamma is now purely a tactical router.
        self.cortex = get_cortex_engine()
        
        # Bayesian Signal Matrix mapping
        self.SIGNALS = {
            "data_leak":     {"func": self._check_data_leak, "weight": 0.30},
            "error_oracle":  {"func": self._check_error_oracle, "weight": 0.25},
            "size_anomaly":  {"func": self._check_size_anomaly, "weight": 0.15},
            "timing_delta":  {"func": self._check_timing, "weight": 0.10},
            "status_logic":  {"func": self._check_status_logic, "weight": 0.10},
            "reflection":    {"func": self._check_reflection, "weight": 0.10},
        }

    async def setup(self):
        self.bus.subscribe(EventType.VULN_CANDIDATE, self.audit_candidate)

    # --- FORENSIC SIGNALS ---

    def _check_data_leak(self, payload: dict) -> float:
        """Detects presence of sensitive unmasked data structures."""
        evidence = str(payload.get("data", "") + payload.get("evidence", "")).lower()
        if not evidence:
            return 0.0
            
        score = 0.0
        patterns = [
            (r"BEGIN[A-Z\s]*PRIVATE KEY", 1.0),     # RSA/SSH Key
            (r"aws_access_key_id", 0.9),           # AWS
            (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", 0.8), # JWT
            (r"\"password\"\s*:\s*\"[^\"]+\"", 0.7), # JSON password
            (r"[a-z0-9_]{10,}@[a-z0-9_]{3,}\.[a-z]{2,5}", 0.2) # High density emails
        ]
        
        for pattern, weight in patterns:
            if re.search(pattern, evidence, re.IGNORECASE):
                score = max(score, weight)
        return score

    def _check_error_oracle(self, payload: dict) -> float:
        """Flags verbose server-side stack traces."""
        evidence = str(payload.get("data", "") + payload.get("evidence", "")).lower()
        if not evidence:
             return 0.0
             
        keywords = ["syntax error", "mysql_fetch", "stack trace", "java.sql.SQLException", "Exception in thread", "pg_query"]
        return 1.0 if any(k in evidence for k in keywords) else 0.0

    def _check_size_anomaly(self, payload: dict) -> float:
        """Measures drastic response length changes from baseline."""
        try:
            baseline_len = float(payload.get("baseline_length", 0))
            attack_len = float(len(str(payload.get("data", payload.get("evidence", "")))))
            if baseline_len == 0:
                return 0.0
                
            delta = abs(attack_len - baseline_len) / baseline_len
            if delta > 0.5:  # > 50% change is highly anomalous
                return min((delta - 0.5) * 2, 1.0) # Scale to 0.0 -> 1.0
        except (ValueError, TypeError):
             pass
        return 0.0

    def _check_timing(self, payload: dict) -> float:
        """Identifies time-based vulnerability signatures."""
        try:
             req_latency = float(payload.get("latency", 0))
             expected_latency = float(payload.get("baseline_latency", 100)) # assume 100ms baseline if not provided
             
             # If latency exceeds 2000ms AND is 5x the baseline
             if req_latency > 2000 and req_latency > (expected_latency * 5):
                 return min(req_latency / 10000.0, 1.0) # Caps at 10s = 1.0
        except (ValueError, TypeError):
             pass
        return 0.0

    def _check_status_logic(self, payload: dict) -> float:
        """Looks for improper auth/state transitions."""
        status = int(payload.get("status", 0))
        baseline_status = int(payload.get("baseline_status", 0))
        
        if baseline_status in [401, 403] and status in [200, 201]:
            # Bypassed auth!
            return 1.0
        if status == 500:
            # Induced server crash
            return 0.6
        return 0.0

    def _check_reflection(self, payload: dict) -> float:
        """Verifies direct reflection of the attack vector in the response."""
        attack_vector = str(payload.get("attack_payload", "")).lower()
        evidence = str(payload.get("data", "") + payload.get("evidence", "")).lower()
        
        if not attack_vector or len(attack_vector) < 3:
            return 0.0
            
        if attack_vector in evidence:
            return 1.0
        return 0.0

    # --- FUSION ENGINE ---

    def _calculate_bayesian_fusion(self, payload: dict) -> tuple[float, list[str]]:
        """
        Combines individual signals using a weighted naive approach.
        Returns final confidence score and a list of triggered signals.
        """
        total_confidence = 0.0
        triggers = []
        
        for name, config in self.SIGNALS.items():
            func = config["func"]
            weight = config["weight"]
            
            signal_score = func(payload)
            if signal_score > 0:
                triggers.append(f"{name}({signal_score:.2f})")
            
            total_confidence += (signal_score * weight)
            
        return total_confidence, triggers


    async def audit_candidate(self, event: HiveEvent):
        """
        Antigravity V6: The Forensic Truth Kernel Audit
        Gamma evaluates candidate payloads generated by Beta.
        """
        payload = event.payload
        url = payload.get('url', 'Unknown')
        
        print(f"[{self.name}] Auditing Candidate Exploit on {url}")
        
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            scan_id=event.scan_id,
            payload={"url": url, "arsenal": "Forensic Audit", "action": "Auditing Candidate", "payload": str(payload.get('type', 'Unknown'))[:50]}
        ))
        
        # 1. APPLY HEURISTIC SIGNAL FUSION
        heuristic_conf, triggers = self._calculate_bayesian_fusion(payload)
        is_real_heuristic = heuristic_conf >= 0.65
        
        print(f"[{self.name}] [SIGNALS] Confidence: {heuristic_conf:.2f} | Triggers: {', '.join(triggers) if triggers else 'None'}")
        
        # Determine strict reject vs hybrid verification
        confidence = heuristic_conf
        is_real = is_real_heuristic
        reason = f"Heuristics Triggered: {', '.join(triggers)}" if triggers else "Insufficient logic deviation."

        # 2. HYBRID AI FALLBACK
        # If signals are ambiguous (between 0.3 and 0.65) or absent but AI is enabled, let Cortex check
        if (self.cortex and self.cortex.enabled) and (0.3 < heuristic_conf < 0.65 or heuristic_conf == 0.0):
            print(f"[{self.name}] Ambiguous or missing signals. Escalating to CORTEX ENGINE...")
            try:
                verdict = await self.cortex.audit_candidate(payload)
                ai_confidence = verdict.get('confidence', 0.5)
                is_real = verdict.get('is_real', True)
                reason = verdict.get('reasoning', reason)
                
                # Blend the AI confidence with the heuristic confidence
                confidence = max(heuristic_conf, ai_confidence)
                
                print(f"[{self.name}] [AI AUDIT] Real={is_real} Confidence={confidence:.1f} Reason={reason}")
            except Exception as e:
                print(f"[{self.name}] [AI AUDIT] CortexEngine error: {e}")

        # 3. VERDICT
        if not is_real and confidence > 0.7:
            print(f"[{self.name}] [VERDICT] FALSE POSITIVE suppressed.")
            await self.bus.publish(HiveEvent(
                type=EventType.LIVE_ATTACK,
                source=self.name,
                scan_id=event.scan_id,
                payload={"url": url, "arsenal": "False Positive Filter", "action": "Suppressed", "payload": reason[:50]}
            ))
            return
        
        # If verified, trigger VULN_CONFIRMED for Kappa to archive
        if is_real:
             payload["confidence"] = confidence
             payload["audit_reasoning"] = reason
             
             await self.bus.publish(HiveEvent(
                 type=EventType.VULN_CONFIRMED,
                 source=self.name,
                 scan_id=event.scan_id,
                 payload=payload
             ))
             await self.bus.publish(HiveEvent(
                 type=EventType.LIVE_ATTACK,
                 source=self.name,
                 scan_id=event.scan_id,
                 payload={"url": url, "arsenal": "Vulnerability Confirmed", "action": f"Confirmed ({confidence:.0%})", "payload": str(payload.get('type', ''))[:50]}
             ))
