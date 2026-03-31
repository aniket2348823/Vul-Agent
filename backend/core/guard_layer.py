# ═══════════════════════════════════════════════════════════════════════════════
# ANTIGRAVITY :: ANTI-HALLUCINATION GUARD LAYER
# ═══════════════════════════════════════════════════════════════════════════════
# PURPOSE: Strict pre-filter that blocks ANY unverified or weak finding
#          from reaching the Qwen3 80B reasoning engine.
#          This is the single most important component for accuracy.
#
# RULE: IF not verified → NEVER send to Qwen 80B.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("GUARD_LAYER")


class GuardLayer:
    """
    Anti-Hallucination Guard Layer.
    Enforces strict evidence-based filtering before any finding
    reaches the cloud reasoning engine (Qwen3 80B).
    """

    # Minimum thresholds
    MIN_DIFF_SCORE = 0.3        # Response diff must exceed this if no GI5 match
    MIN_CONFIDENCE = 0.15       # Absolute minimum confidence to even consider
    MAX_PAYLOAD_AGE_S = 3600    # Findings older than 1 hour are stale

    def __init__(self):
        self._stats = {
            "total_received": 0,
            "passed": 0,
            "rejected_no_response": 0,
            "rejected_not_validated": 0,
            "rejected_weak_signal": 0,
            "rejected_low_confidence": 0,
            "rejected_duplicate": 0,
        }
        self._seen_hashes: set = set()

    def filter(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Primary entry point. Accepts a list of candidate findings,
        returns ONLY the ones that pass all verification gates.
        """
        valid = []
        for f in findings:
            self._stats["total_received"] += 1
            result, reason = self._validate_single(f)
            if result:
                valid.append(f)
                self._stats["passed"] += 1
            else:
                logger.debug(f"GUARD: Rejected finding [{reason}] — {f.get('url', 'unknown')}")
        return valid

    def filter_single(self, finding: Dict[str, Any]) -> bool:
        """Validate a single finding. Returns True if it passes the guard."""
        result, _ = self._validate_single(finding)
        return result

    def _validate_single(self, f: Dict[str, Any]) -> tuple:
        """
        Core validation logic. Returns (passed: bool, reason: str).
        """
        # ─── GATE 1: Response Existence ───────────────────────────────────
        response = f.get("response") or f.get("response_body") or f.get("raw_response")
        if not response:
            self._stats["rejected_no_response"] += 1
            return False, "no_response"

        # ─── GATE 2: Validation Status ────────────────────────────────────
        validation = str(f.get("validation", "")).upper()
        # Accept VALID or findings that came through the GI5 pipeline
        if validation not in ("VALID", "CONFIRMED", "TRUE_POSITIVE"):
            # Allow if it has strong GI5 signal even without explicit validation tag
            gi5_match = f.get("gi5_match", False)
            if not gi5_match:
                self._stats["rejected_not_validated"] += 1
                return False, "not_validated"

        # ─── GATE 3: Signal Strength ──────────────────────────────────────
        gi5_match = f.get("gi5_match", False)
        diff_score = float(f.get("response_diff_score", 0))
        gi5_risk = float(f.get("gi5_risk", f.get("risk_score", 0)))

        has_gi5_signal = gi5_match or gi5_risk > 50
        has_diff_signal = diff_score > self.MIN_DIFF_SCORE

        if not has_gi5_signal and not has_diff_signal:
            self._stats["rejected_weak_signal"] += 1
            return False, "weak_signal"

        # ─── GATE 4: Minimum Confidence ───────────────────────────────────
        confidence = float(f.get("confidence", 0))
        if confidence < self.MIN_CONFIDENCE:
            self._stats["rejected_low_confidence"] += 1
            return False, "low_confidence"

        # ─── GATE 5: Deduplication ────────────────────────────────────────
        dedup_key = self._compute_hash(f)
        if dedup_key in self._seen_hashes:
            self._stats["rejected_duplicate"] += 1
            return False, "duplicate"
        self._seen_hashes.add(dedup_key)

        return True, "passed"

    def _compute_hash(self, f: Dict[str, Any]) -> str:
        """
        Generate a deduplication hash based on endpoint + vuln_type + response signature.
        """
        endpoint = str(f.get("url", f.get("endpoint", ""))).split("?")[0].lower()
        vuln_type = str(f.get("vuln_type", f.get("type", ""))).upper()
        
        # Response signature: use first 200 chars of response body
        response = str(f.get("response", f.get("response_body", "")))[:200]
        response_sig = hashlib.md5(response.encode()).hexdigest()[:8]

        combined = f"{endpoint}|{vuln_type}|{response_sig}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def cluster_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Cluster identical findings by (endpoint_pattern, vuln_type, response_signature).
        Returns deduplicated clusters with variant counts.
        """
        clusters: Dict[str, Dict[str, Any]] = {}

        for f in findings:
            endpoint = str(f.get("url", f.get("endpoint", ""))).split("?")[0].lower()
            vuln_type = str(f.get("vuln_type", f.get("type", ""))).upper()
            cluster_id = f"{endpoint}|{vuln_type}"

            if cluster_id not in clusters:
                clusters[cluster_id] = {
                    "endpoint": endpoint,
                    "vuln_type": vuln_type,
                    "variants": 0,
                    "max_confidence": 0,
                    "representative": f,
                    "all_payloads": [],
                }

            cluster = clusters[cluster_id]
            cluster["variants"] += 1
            cluster["max_confidence"] = max(cluster["max_confidence"], float(f.get("confidence", 0)))
            cluster["all_payloads"].append(f.get("payload", ""))

        return list(clusters.values())

    def get_stats(self) -> dict:
        """Return guard layer statistics."""
        return dict(self._stats)

    def reset(self):
        """Reset deduplication state for a new scan."""
        self._seen_hashes.clear()
        for key in self._stats:
            self._stats[key] = 0


# ─── Global Singleton ─────────────────────────────────────────────────────────
guard_layer = GuardLayer()
