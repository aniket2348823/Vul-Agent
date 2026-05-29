"""
CONTINUOUS LEARNING ENGINE
Automatically extracts patterns from every scan to improve over time.

This engine:
1. Learns from successful vulnerabilities
2. Tracks success/failure rates
3. Adapts attack strategies based on historical data
4. Builds vulnerability correlation patterns
5. Improves payload generation
6. Adapts reconnaissance strategies
"""

import asyncio
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import re

from backend.core.memory import memory_store, cosine_similarity
from backend.core.unified_knowledge_graph import knowledge_graph

try:
    import redis
except ImportError:
    redis = None


@dataclass
class LearningPattern:
    """Represents a learned pattern with confidence scoring."""
    pattern_id: str
    pattern_type: str  # "vuln_correlation", "endpoint_pattern", "payload_success", "recon_strategy"
    pattern_data: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    success_count: int
    failure_count: int
    last_seen: float
    first_seen: float
    scan_count: int  # Number of scans this pattern appeared in
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def update_confidence(self):
        """Recalculate confidence based on success rate and sample size."""
        # Confidence increases with both success rate and sample size
        sample_factor = min(1.0, (self.success_count + self.failure_count) / 10.0)
        self.confidence = self.success_rate * sample_factor


@dataclass
class LearningMetrics:
    """Tracks learning progress over time."""
    total_patterns: int = 0
    high_confidence_patterns: int = 0  # confidence > 0.7
    total_scans_analyzed: int = 0
    total_vulns_learned: int = 0
    avg_pattern_confidence: float = 0.0
    learning_rate: float = 0.0  # Patterns learned per scan
    last_updated: float = 0.0


class ContinuousLearningEngine:
    """
    The brain that learns from every scan.
    Automatically extracts patterns and improves attack strategies.
    """
    
    def __init__(self, brain_dir: str = "brain", redis_client: Optional[Any] = None):
        self.brain_dir = Path(brain_dir)
        self.patterns_file = self.brain_dir / "learned_patterns.json"
        self.metrics_file = self.brain_dir / "learning_metrics.json"
        
        # In-memory pattern storage
        self.patterns: Dict[str, LearningPattern] = {}
        self.metrics = LearningMetrics()
        
        # Pattern extraction rules
        self.min_confidence_threshold = 0.3
        self.pattern_consolidation_threshold = 0.85  # Cosine similarity for merging patterns
        
        # Redis client for distributed locking and caching
        self.redis_client = redis_client
        self._learning_cache: Dict[str, bool] = {}
        
        self._ensure_files()
        self._load_patterns()
        self._load_metrics()
    
    def _ensure_files(self):
        """Ensure brain directory and files exist."""
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        if not self.patterns_file.exists():
            self.patterns_file.write_text("[]", encoding="utf-8")
        if not self.metrics_file.exists():
            self.metrics_file.write_text(json.dumps(asdict(self.metrics), indent=2), encoding="utf-8")
    
    def _load_patterns(self):
        """Load learned patterns from disk."""
        try:
            data = json.loads(self.patterns_file.read_text(encoding="utf-8"))
            for item in data:
                pattern = LearningPattern(**item)
                self.patterns[pattern.pattern_id] = pattern
            print(f"[LearningEngine] Loaded {len(self.patterns)} patterns from disk")
        except Exception as e:
            print(f"[LearningEngine] Failed to load patterns: {e}")
    
    def _save_patterns(self):
        """Save learned patterns to disk."""
        try:
            data = [asdict(p) for p in self.patterns.values()]
            self.patterns_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[LearningEngine] Failed to save patterns: {e}")
    
    def _load_metrics(self):
        """Load learning metrics from disk."""
        try:
            data = json.loads(self.metrics_file.read_text(encoding="utf-8"))
            self.metrics = LearningMetrics(**data)
        except Exception as e:
            print(f"[LearningEngine] Failed to load metrics: {e}")
    
    def _save_metrics(self):
        """Save learning metrics to disk."""
        try:
            self.metrics_file.write_text(json.dumps(asdict(self.metrics), indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[LearningEngine] Failed to save metrics: {e}")
    
    def _generate_pattern_id(self, pattern_type: str, pattern_data: Dict[str, Any]) -> str:
        """Generate unique pattern ID."""
        import hashlib
        data_str = json.dumps(pattern_data, sort_keys=True)
        hash_val = hashlib.sha256(f"{pattern_type}:{data_str}".encode()).hexdigest()[:16]
        return f"{pattern_type}_{hash_val}"
    
    async def learn_from_vulnerability(self, vuln_data: Dict[str, Any], scan_id: str):
        """
        Extract learning patterns from a confirmed vulnerability.
        This is called automatically when a vulnerability is confirmed.
        """
        vuln_type = vuln_data.get("type", "unknown")
        url = vuln_data.get("url", "")
        payload = vuln_data.get("payload", "")
        confidence = vuln_data.get("confidence", 0.0)
        
        if not vuln_type or not url:
            return
        
        print(f"[LearningEngine] Learning from {vuln_type} vulnerability at {url}")
        
        # 1. Learn endpoint pattern
        await self._learn_endpoint_pattern(vuln_type, url, success=True)
        
        # 2. Learn payload pattern
        await self._learn_payload_pattern(vuln_type, payload, success=True)
        
        # 3. Learn vulnerability correlation
        await self._learn_vuln_correlation(scan_id, vuln_type, url)
        
        # 4. Update metrics
        self.metrics.total_vulns_learned += 1
        self.metrics.last_updated = time.time()
        self._save_metrics()
    
    async def learn_from_failure(self, attack_data: Dict[str, Any], scan_id: str):
        """
        Learn from failed attacks to avoid repeating ineffective strategies.
        """
        vuln_type = attack_data.get("type", "unknown")
        url = attack_data.get("url", "")
        payload = attack_data.get("payload", "")
        
        if not vuln_type or not url:
            return
        
        # Update failure counts for patterns
        await self._learn_endpoint_pattern(vuln_type, url, success=False)
        await self._learn_payload_pattern(vuln_type, payload, success=False)
    
    async def _learn_endpoint_pattern(self, vuln_type: str, url: str, success: bool):
        """Extract and learn endpoint patterns."""
        # Convert specific URL to pattern
        pattern_url = self._extract_url_pattern(url)
        
        pattern_data = {
            "vuln_type": vuln_type,
            "url_pattern": pattern_url,
            "method": "GET"  # Could be extracted from request data
        }
        
        pattern_id = self._generate_pattern_id("endpoint_pattern", pattern_data)
        
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            if success:
                pattern.success_count += 1
            else:
                pattern.failure_count += 1
            pattern.last_seen = time.time()
            pattern.update_confidence()
        else:
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="endpoint_pattern",
                pattern_data=pattern_data,
                confidence=0.5,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                last_seen=time.time(),
                first_seen=time.time(),
                scan_count=1
            )
            pattern.update_confidence()
            self.patterns[pattern_id] = pattern
        
        self._save_patterns()
    
    async def _learn_payload_pattern(self, vuln_type: str, payload: str, success: bool):
        """Extract and learn payload patterns."""
        if not payload or len(payload) > 1000:
            return
        
        # Extract payload characteristics
        payload_features = self._extract_payload_features(payload)
        
        pattern_data = {
            "vuln_type": vuln_type,
            "payload_features": payload_features,
            "payload_sample": payload[:100]  # Store sample for reference
        }
        
        pattern_id = self._generate_pattern_id("payload_success", pattern_data)
        
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            if success:
                pattern.success_count += 1
            else:
                pattern.failure_count += 1
            pattern.last_seen = time.time()
            pattern.update_confidence()
        else:
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="payload_success",
                pattern_data=pattern_data,
                confidence=0.5,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                last_seen=time.time(),
                first_seen=time.time(),
                scan_count=1
            )
            pattern.update_confidence()
            self.patterns[pattern_id] = pattern
        
        self._save_patterns()
    
    async def _learn_vuln_correlation(self, scan_id: str, vuln_type: str, url: str):
        """Learn correlations between vulnerabilities in the same scan."""
        # Get other vulnerabilities from this scan
        episode_file = self.brain_dir / "episodes" / f"{scan_id}.json"
        if not episode_file.exists():
            return
        
        try:
            episodes = json.loads(episode_file.read_text(encoding="utf-8"))
            vuln_events = [e for e in episodes if e.get("type") == "vulnerability"]
            
            if len(vuln_events) < 2:
                return
            
            # Find correlations
            for other_vuln in vuln_events:
                other_type = other_vuln.get("payload", {}).get("type", "")
                if other_type and other_type != vuln_type:
                    pattern_data = {
                        "vuln_type_1": vuln_type,
                        "vuln_type_2": other_type,
                        "correlation": "co_occurrence"
                    }
                    
                    pattern_id = self._generate_pattern_id("vuln_correlation", pattern_data)
                    
                    if pattern_id in self.patterns:
                        pattern = self.patterns[pattern_id]
                        pattern.success_count += 1
                        pattern.last_seen = time.time()
                        pattern.update_confidence()
                    else:
                        pattern = LearningPattern(
                            pattern_id=pattern_id,
                            pattern_type="vuln_correlation",
                            pattern_data=pattern_data,
                            confidence=0.5,
                            success_count=1,
                            failure_count=0,
                            last_seen=time.time(),
                            first_seen=time.time(),
                            scan_count=1
                        )
                        pattern.update_confidence()
                        self.patterns[pattern_id] = pattern
            
            self._save_patterns()
        except Exception as e:
            print(f"[LearningEngine] Failed to learn correlations: {e}")
    
    def _extract_url_pattern(self, url: str) -> str:
        """Convert specific URL to reusable pattern."""
        # Replace UUIDs first (before IDs to avoid partial matches)
        pattern = re.sub(r'/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '/{uuid}', url)
        # Replace numeric IDs
        pattern = re.sub(r'/\d+', '/{id}', pattern)
        # Replace hash-like strings
        pattern = re.sub(r'/[a-f0-9]{32}', '/{hash}', pattern)
        # Remove query params
        pattern = re.sub(r'\?.*$', '', pattern)
        return pattern
    
    def _extract_payload_features(self, payload: str) -> Dict[str, Any]:
        """Extract features from payload for pattern matching."""
        payload_lower = payload.lower()
        features = {
            "length": len(payload),
            "has_script_tag": "<script" in payload_lower,
            "has_sql_keywords": any(kw in payload_lower for kw in ["select", "union", "drop", "insert", " or ", "and "]),
            "has_template_injection": "{{" in payload or "{%" in payload,
            "has_command_injection": any(cmd in payload_lower for cmd in ["system", "exec", "popen", "eval"]),
            "has_encoding": any(enc in payload for enc in ["%", "0x", "\\x"]),
            "has_special_chars": bool(re.search(r'[<>\'";]', payload))
        }
        return features
    
    async def get_recommendations(self, target_url: str, scan_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get attack recommendations based on learned patterns.
        This is called by Omega to adapt strategies.
        """
        url_pattern = self._extract_url_pattern(target_url)
        
        recommendations = {
            "priority_vulns": [],
            "effective_payloads": [],
            "correlated_vulns": [],
            "confidence": 0.0
        }
        
        # Find matching endpoint patterns
        matching_patterns = []
        for pattern in self.patterns.values():
            if pattern.pattern_type == "endpoint_pattern":
                if pattern.pattern_data.get("url_pattern") == url_pattern:
                    if pattern.confidence > self.min_confidence_threshold:
                        matching_patterns.append(pattern)
        
        # Sort by confidence
        matching_patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        # Extract recommendations
        for pattern in matching_patterns[:5]:
            vuln_type = pattern.pattern_data.get("vuln_type")
            recommendations["priority_vulns"].append({
                "type": vuln_type,
                "confidence": pattern.confidence,
                "success_rate": pattern.success_rate,
                "sample_size": pattern.success_count + pattern.failure_count
            })
        
        # Find effective payloads for recommended vulns
        for vuln_rec in recommendations["priority_vulns"]:
            vuln_type = vuln_rec["type"]
            payload_patterns = [
                p for p in self.patterns.values()
                if p.pattern_type == "payload_success" and
                p.pattern_data.get("vuln_type") == vuln_type and
                p.confidence > self.min_confidence_threshold
            ]
            payload_patterns.sort(key=lambda p: p.confidence, reverse=True)
            
            for pp in payload_patterns[:3]:
                recommendations["effective_payloads"].append({
                    "vuln_type": vuln_type,
                    "payload_sample": pp.pattern_data.get("payload_sample", ""),
                    "features": pp.pattern_data.get("payload_features", {}),
                    "confidence": pp.confidence
                })
        
        # Find correlated vulnerabilities
        for vuln_rec in recommendations["priority_vulns"]:
            vuln_type = vuln_rec["type"]
            correlations = [
                p for p in self.patterns.values()
                if p.pattern_type == "vuln_correlation" and
                (p.pattern_data.get("vuln_type_1") == vuln_type or
                 p.pattern_data.get("vuln_type_2") == vuln_type) and
                p.confidence > self.min_confidence_threshold
            ]
            
            for corr in correlations:
                other_type = (corr.pattern_data.get("vuln_type_2")
                             if corr.pattern_data.get("vuln_type_1") == vuln_type
                             else corr.pattern_data.get("vuln_type_1"))
                recommendations["correlated_vulns"].append({
                    "primary": vuln_type,
                    "correlated": other_type,
                    "confidence": corr.confidence
                })
        
        # Calculate overall confidence
        if matching_patterns:
            recommendations["confidence"] = sum(p.confidence for p in matching_patterns) / len(matching_patterns)
        
        return recommendations
    
    async def consolidate_patterns(self):
        """
        Consolidate similar patterns to prevent pattern explosion.
        Runs periodically to merge similar patterns.
        """
        print("[LearningEngine] Consolidating patterns...")
        
        # Group patterns by type
        by_type = defaultdict(list)
        for pattern in self.patterns.values():
            by_type[pattern.pattern_type].append(pattern)
        
        consolidated_count = 0
        
        for pattern_type, patterns in by_type.items():
            if len(patterns) < 2:
                continue
            
            # Find similar patterns and merge them
            to_remove = set()
            for i, p1 in enumerate(patterns):
                if p1.pattern_id in to_remove:
                    continue
                
                for p2 in patterns[i+1:]:
                    if p2.pattern_id in to_remove:
                        continue
                    
                    # Check similarity
                    if self._patterns_similar(p1, p2):
                        # Merge p2 into p1
                        p1.success_count += p2.success_count
                        p1.failure_count += p2.failure_count
                        p1.scan_count += p2.scan_count
                        p1.last_seen = max(p1.last_seen, p2.last_seen)
                        p1.update_confidence()
                        
                        to_remove.add(p2.pattern_id)
                        consolidated_count += 1
            
            # Remove merged patterns
            for pattern_id in to_remove:
                del self.patterns[pattern_id]
        
        if consolidated_count > 0:
            print(f"[LearningEngine] Consolidated {consolidated_count} patterns")
            self._save_patterns()
        
        return consolidated_count
    
    def _patterns_similar(self, p1: LearningPattern, p2: LearningPattern) -> bool:
        """Check if two patterns are similar enough to merge."""
        if p1.pattern_type != p2.pattern_type:
            return False
        
        # Type-specific similarity checks
        if p1.pattern_type == "endpoint_pattern":
            return (p1.pattern_data.get("vuln_type") == p2.pattern_data.get("vuln_type") and
                   p1.pattern_data.get("url_pattern") == p2.pattern_data.get("url_pattern"))
        
        elif p1.pattern_type == "payload_success":
            # Compare payload features
            f1 = p1.pattern_data.get("payload_features", {})
            f2 = p2.pattern_data.get("payload_features", {})
            
            # Count matching features
            matches = sum(1 for k in f1 if f1.get(k) == f2.get(k))
            total = len(f1)
            
            return matches / total > 0.8 if total > 0 else False
        
        elif p1.pattern_type == "vuln_correlation":
            # Same correlation regardless of order
            types1 = {p1.pattern_data.get("vuln_type_1"), p1.pattern_data.get("vuln_type_2")}
            types2 = {p2.pattern_data.get("vuln_type_1"), p2.pattern_data.get("vuln_type_2")}
            return types1 == types2
        
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current learning metrics."""
        # Update metrics
        self.metrics.total_patterns = len(self.patterns)
        self.metrics.high_confidence_patterns = sum(
            1 for p in self.patterns.values() if p.confidence > 0.7
        )
        
        if self.patterns:
            self.metrics.avg_pattern_confidence = sum(
                p.confidence for p in self.patterns.values()
            ) / len(self.patterns)
        
        if self.metrics.total_scans_analyzed > 0:
            self.metrics.learning_rate = self.metrics.total_patterns / self.metrics.total_scans_analyzed
        
        return asdict(self.metrics)
    
    async def analyze_scan_complete(self, scan_id: str):
        """
        Called when a scan completes to extract all learnings.
        """
        print(f"[LearningEngine] Analyzing completed scan: {scan_id}")
        
        # Update scan count
        self.metrics.total_scans_analyzed += 1
        
        # Consolidate patterns periodically
        if self.metrics.total_scans_analyzed % 10 == 0:
            await self.consolidate_patterns()
        
        self._save_metrics()


# Global learning engine instance
learning_engine = ContinuousLearningEngine()


# ============================================================================
# BROWSER LEARNING EXTENSION
# ============================================================================

class BrowserLearningExtension:
    """Extension for browser-specific learning with idempotency and caching"""
    
    def __init__(self, learning_engine: ContinuousLearningEngine):
        self.engine = learning_engine
        self.redis = learning_engine.redis_client
    
    def _generate_idempotency_key(self, vuln_data: Dict[str, Any]) -> str:
        """Generate idempotency key from vulnerability data"""
        import hashlib
        key_data = {
            "url": vuln_data.get("url", ""),
            "vuln_type": vuln_data.get("type", ""),
            "payload": vuln_data.get("payload", ""),
            "method": vuln_data.get("method", "GET")
        }
        data_str = json.dumps(key_data, sort_keys=True)
        return f"vuln:{hashlib.sha256(data_str.encode()).hexdigest()}"
    
    async def _acquire_lock(self, lock_key: str, ttl_seconds: int = 300) -> bool:
        """Acquire distributed lock using Redis"""
        if not self.redis:
            # No Redis, use in-memory cache
            if lock_key in self.engine._learning_cache:
                return False
            self.engine._learning_cache[lock_key] = True
            return True
        
        try:
            # Try to set key with NX (only if not exists) and EX (expiry)
            result = self.redis.set(lock_key, "1", nx=True, ex=ttl_seconds)
            return bool(result)
        except Exception as e:
            print(f"[BrowserLearning] Lock acquisition failed: {e}")
            return False
    
    async def _release_lock(self, lock_key: str):
        """Release distributed lock"""
        if not self.redis:
            self.engine._learning_cache.pop(lock_key, None)
            return
        
        try:
            self.redis.delete(lock_key)
        except Exception as e:
            print(f"[BrowserLearning] Lock release failed: {e}")
    
    async def learn_from_browser_vulnerability(
        self,
        vuln_data: Dict[str, Any],
        scan_id: str
    ) -> bool:
        """
        Learn from browser-based vulnerability with idempotency.
        Returns True if learning occurred, False if duplicate.
        """
        # Generate idempotency key
        idem_key = self._generate_idempotency_key(vuln_data)
        lock_key = f"lock:{idem_key}"
        
        # Acquire distributed lock
        if not await self._acquire_lock(lock_key, ttl_seconds=300):
            print(f"[BrowserLearning] Duplicate vulnerability, skipping: {idem_key}")
            return False
        
        try:
            # Extract browser-specific pattern
            pattern_data = {
                "vuln_type": vuln_data.get("type", "unknown"),
                "url": vuln_data.get("url", ""),
                "payload": vuln_data.get("payload", ""),
                "method": vuln_data.get("method", "GET"),
                "framework": vuln_data.get("framework"),
                "execution_context": "browser_required",
                "browser_requirements": {
                    "stealth": vuln_data.get("stealth_required", False),
                    "session": vuln_data.get("session_required", False),
                    "framework": vuln_data.get("framework")
                }
            }
            
            # Store pattern
            pattern_id = self.engine._generate_pattern_id("browser_vulnerability", pattern_data)
            
            if pattern_id in self.engine.patterns:
                pattern = self.engine.patterns[pattern_id]
                pattern.success_count += 1
                pattern.last_seen = time.time()
                pattern.update_confidence()
            else:
                pattern = LearningPattern(
                    pattern_id=pattern_id,
                    pattern_type="browser_vulnerability",
                    pattern_data=pattern_data,
                    confidence=0.7,
                    success_count=1,
                    failure_count=0,
                    last_seen=time.time(),
                    first_seen=time.time(),
                    scan_count=1
                )
                pattern.update_confidence()
                self.engine.patterns[pattern_id] = pattern
            
            self.engine._save_patterns()
            
            print(f"[BrowserLearning] Learned from browser vulnerability: {vuln_data.get('type')}")
            return True
            
        finally:
            await self._release_lock(lock_key)
    
    async def learn_browser_workflow(
        self,
        workflow: Dict[str, Any],
        success: bool
    ):
        """Learn from browser workflow execution"""
        workflow_id = workflow.get("id", "unknown")
        
        # Get existing workflow stats from Redis or memory
        stats_key = f"workflow:{workflow_id}"
        
        if self.redis:
            try:
                stats_data = self.redis.get(stats_key)
                if stats_data:
                    stats = json.loads(stats_data)
                else:
                    stats = {"success_count": 0, "failure_count": 0, "total_runs": 0}
            except Exception:
                stats = {"success_count": 0, "failure_count": 0, "total_runs": 0}
        else:
            stats = {"success_count": 0, "failure_count": 0, "total_runs": 0}
        
        # Update stats
        stats["total_runs"] += 1
        if success:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1
        
        stats["success_rate"] = stats["success_count"] / stats["total_runs"]
        
        # Store updated stats
        if self.redis:
            try:
                self.redis.set(stats_key, json.dumps(stats), ex=86400)  # 24 hour expiry
            except Exception as e:
                print(f"[BrowserLearning] Failed to store workflow stats: {e}")
        
        # Promote to skill if threshold reached (>70% success rate, >5 runs)
        if stats["success_rate"] > 0.7 and stats["total_runs"] >= 5:
            pattern_data = {
                "workflow_id": workflow_id,
                "workflow_steps": workflow.get("steps", []),
                "success_conditions": workflow.get("success_conditions", []),
                "success_rate": stats["success_rate"],
                "total_runs": stats["total_runs"]
            }
            
            pattern_id = self.engine._generate_pattern_id("browser_workflow", pattern_data)
            
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="browser_workflow",
                pattern_data=pattern_data,
                confidence=stats["success_rate"],
                success_count=stats["success_count"],
                failure_count=stats["failure_count"],
                last_seen=time.time(),
                first_seen=time.time(),
                scan_count=1
            )
            
            self.engine.patterns[pattern_id] = pattern
            self.engine._save_patterns()
            
            print(f"[BrowserLearning] Promoted workflow to skill: {workflow_id}")
    
    async def get_browser_recommendations(
        self,
        target_url: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get browser-specific recommendations based on learned patterns"""
        context = context or {}
        
        recommendations = {
            "workflows": [],
            "payloads": [],
            "framework_specific": [],
            "confidence": 0.0
        }
        
        # Find matching browser patterns
        matching_patterns = []
        url_pattern = self.engine._extract_url_pattern(target_url)
        
        for pattern in self.engine.patterns.values():
            if pattern.pattern_type in ["browser_vulnerability", "browser_workflow"]:
                pattern_url = pattern.pattern_data.get("url", "")
                if pattern_url and self.engine._extract_url_pattern(pattern_url) == url_pattern:
                    if pattern.confidence > self.engine.min_confidence_threshold:
                        matching_patterns.append(pattern)
        
        # Sort by confidence
        matching_patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        # Extract recommendations
        for pattern in matching_patterns[:10]:
            if pattern.pattern_type == "browser_workflow":
                recommendations["workflows"].append({
                    "workflow_id": pattern.pattern_data.get("workflow_id"),
                    "steps": pattern.pattern_data.get("workflow_steps", []),
                    "success_rate": pattern.success_rate,
                    "confidence": pattern.confidence
                })
            elif pattern.pattern_type == "browser_vulnerability":
                recommendations["payloads"].append({
                    "vuln_type": pattern.pattern_data.get("vuln_type"),
                    "payload": pattern.pattern_data.get("payload"),
                    "confidence": pattern.confidence,
                    "browser_requirements": pattern.pattern_data.get("browser_requirements", {})
                })
                
                # Framework-specific recommendations
                framework = pattern.pattern_data.get("framework")
                if framework:
                    recommendations["framework_specific"].append({
                        "framework": framework,
                        "vuln_type": pattern.pattern_data.get("vuln_type"),
                        "confidence": pattern.confidence
                    })
        
        # Calculate overall confidence
        if matching_patterns:
            recommendations["confidence"] = sum(p.confidence for p in matching_patterns) / len(matching_patterns)
        
        return recommendations
    
    async def learn_framework_pattern(
        self,
        framework: Optional[str],
        routes: List[str]
    ):
        """Learn framework-specific patterns"""
        if not framework or not routes:
            return
        
        # Deduplicate routes
        unique_routes = list(set(routes))
        
        # Get existing framework routes from Redis or memory
        routes_key = f"framework:{framework}:routes"
        
        if self.redis:
            try:
                existing_data = self.redis.get(routes_key)
                if existing_data:
                    existing_routes = set(json.loads(existing_data))
                else:
                    existing_routes = set()
            except Exception:
                existing_routes = set()
        else:
            existing_routes = set()
        
        # Add only new routes
        new_routes = [r for r in unique_routes if r not in existing_routes]
        
        if not new_routes:
            return
        
        # Update stored routes
        all_routes = list(existing_routes.union(set(new_routes)))
        
        if self.redis:
            try:
                self.redis.set(routes_key, json.dumps(all_routes), ex=86400 * 7)  # 7 day expiry
            except Exception as e:
                print(f"[BrowserLearning] Failed to store framework routes: {e}")
        
        # Extract route patterns
        pattern_data = {
            "framework": framework,
            "route_count": len(all_routes),
            "new_routes": new_routes,
            "route_patterns": self._extract_route_patterns(all_routes)
        }
        
        pattern_id = self.engine._generate_pattern_id("framework_pattern", pattern_data)
        
        if pattern_id in self.engine.patterns:
            pattern = self.engine.patterns[pattern_id]
            pattern.pattern_data["route_count"] = len(all_routes)
            pattern.last_seen = time.time()
        else:
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="framework_pattern",
                pattern_data=pattern_data,
                confidence=0.6,
                success_count=1,
                failure_count=0,
                last_seen=time.time(),
                first_seen=time.time(),
                scan_count=1
            )
            self.engine.patterns[pattern_id] = pattern
        
        self.engine._save_patterns()
        
        print(f"[BrowserLearning] Learned {len(new_routes)} new routes for {framework}")
    
    def _extract_route_patterns(self, routes: List[str]) -> List[str]:
        """Extract common patterns from routes"""
        patterns = set()
        
        for route in routes:
            # Replace IDs with placeholders
            pattern = re.sub(r'/\d+', '/:id', route)
            pattern = re.sub(r'/[a-f0-9-]{36}', '/:uuid', pattern)
            patterns.add(pattern)
        
        return list(patterns)


# Create global browser learning extension
browser_learning = BrowserLearningExtension(learning_engine)


# ============================================================================
# CROSS-SYSTEM LEARNING EXTENSION
# ============================================================================

class CrossSystemLearningExtension:
    """Extension for cross-system learning between HTTP and browser methods"""
    
    def __init__(self, learning_engine: ContinuousLearningEngine):
        self.engine = learning_engine
        self.redis = learning_engine.redis_client
    
    async def recommend_cross_method_verification(
        self,
        vuln_data: Dict[str, Any],
        discovery_method: str
    ) -> Dict[str, Any]:
        """
        Recommend cross-method verification.
        HTTP vulnerabilities recommend browser verification.
        Browser exploits recommend HTTP variants.
        """
        recommendations = {
            "should_verify": False,
            "verification_method": None,
            "confidence": 0.0,
            "reasoning": []
        }
        
        vuln_type = vuln_data.get("type", "unknown")
        
        # HTTP → Browser verification recommendations
        if discovery_method == "http":
            # XSS should always be verified in browser
            if vuln_type in ["XSS", "DOM_XSS", "Reflected_XSS"]:
                recommendations["should_verify"] = True
                recommendations["verification_method"] = "browser"
                recommendations["confidence"] = 0.9
                recommendations["reasoning"].append("XSS requires browser verification for execution")
            
            # CSRF benefits from browser verification
            elif vuln_type == "CSRF":
                recommendations["should_verify"] = True
                recommendations["verification_method"] = "browser"
                recommendations["confidence"] = 0.8
                recommendations["reasoning"].append("CSRF verification more reliable in browser context")
            
            # Check if target has JavaScript framework
            framework = vuln_data.get("framework")
            if framework:
                recommendations["should_verify"] = True
                recommendations["verification_method"] = "browser"
                recommendations["confidence"] = max(recommendations["confidence"], 0.7)
                recommendations["reasoning"].append(f"Target uses {framework}, browser verification recommended")
        
        # Browser → HTTP variant recommendations
        elif discovery_method == "browser":
            # Browser-discovered endpoints should be tested via HTTP
            if vuln_type in ["API_Endpoint", "Hidden_Endpoint"]:
                recommendations["should_verify"] = True
                recommendations["verification_method"] = "http"
                recommendations["confidence"] = 0.8
                recommendations["reasoning"].append("Browser-discovered endpoint should be tested via HTTP")
            
            # Browser XSS might have HTTP variant
            elif vuln_type == "XSS":
                recommendations["should_verify"] = True
                recommendations["verification_method"] = "http"
                recommendations["confidence"] = 0.6
                recommendations["reasoning"].append("Browser XSS might have HTTP-only variant")
        
        return recommendations
    
    async def identify_cross_context_patterns(
        self,
        http_patterns: List[LearningPattern],
        browser_patterns: List[LearningPattern]
    ) -> List[Dict[str, Any]]:
        """
        Identify patterns that work in both HTTP and browser contexts.
        Creates hybrid attack skills.
        """
        hybrid_patterns = []
        
        # Match patterns by URL and vulnerability type
        for http_pattern in http_patterns:
            http_url = self.engine._extract_url_pattern(http_pattern.pattern_data.get("url", ""))
            http_vuln_type = http_pattern.pattern_data.get("vuln_type")
            
            for browser_pattern in browser_patterns:
                browser_url = self.engine._extract_url_pattern(browser_pattern.pattern_data.get("url", ""))
                browser_vuln_type = browser_pattern.pattern_data.get("vuln_type")
                
                # Match if same URL pattern and vulnerability type
                if http_url == browser_url and http_vuln_type == browser_vuln_type:
                    hybrid_pattern = {
                        "pattern_type": "hybrid_attack",
                        "vuln_type": http_vuln_type,
                        "url_pattern": http_url,
                        "http_payload": http_pattern.pattern_data.get("payload"),
                        "browser_payload": browser_pattern.pattern_data.get("payload"),
                        "http_confidence": http_pattern.confidence,
                        "browser_confidence": browser_pattern.confidence,
                        "combined_confidence": (http_pattern.confidence + browser_pattern.confidence) / 2,
                        "execution_contexts": ["http", "browser"],
                        "success_rate": (http_pattern.success_rate + browser_pattern.success_rate) / 2
                    }
                    
                    hybrid_patterns.append(hybrid_pattern)
                    
                    # Store as new pattern
                    pattern_id = self.engine._generate_pattern_id("hybrid_attack", hybrid_pattern)
                    
                    if pattern_id not in self.engine.patterns:
                        pattern = LearningPattern(
                            pattern_id=pattern_id,
                            pattern_type="hybrid_attack",
                            pattern_data=hybrid_pattern,
                            confidence=hybrid_pattern["combined_confidence"],
                            success_count=http_pattern.success_count + browser_pattern.success_count,
                            failure_count=http_pattern.failure_count + browser_pattern.failure_count,
                            last_seen=time.time(),
                            first_seen=time.time(),
                            scan_count=1
                        )
                        self.engine.patterns[pattern_id] = pattern
        
        if hybrid_patterns:
            self.engine._save_patterns()
            print(f"[CrossSystemLearning] Identified {len(hybrid_patterns)} hybrid patterns")
        
        return hybrid_patterns
    
    async def extract_http_payload_from_browser_workflow(
        self,
        workflow: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract HTTP-equivalent payload from browser workflow.
        Stores as separate HTTP skill.
        """
        workflow_steps = workflow.get("steps", [])
        
        # Find HTTP requests in workflow
        http_requests = []
        for step in workflow_steps:
            if step.get("type") == "http_request":
                http_requests.append(step)
        
        if not http_requests:
            return None
        
        # Extract payload from HTTP requests
        http_payload = {
            "workflow_id": workflow.get("id"),
            "extracted_from": "browser_workflow",
            "requests": [],
            "success_conditions": workflow.get("success_conditions", [])
        }
        
        for req in http_requests:
            http_payload["requests"].append({
                "method": req.get("method", "GET"),
                "url": req.get("url"),
                "headers": req.get("headers", {}),
                "body": req.get("body"),
                "params": req.get("params", {})
            })
        
        # Store as HTTP pattern
        pattern_data = {
            "pattern_type": "http_from_browser",
            "workflow_id": workflow.get("id"),
            "http_payload": http_payload,
            "original_context": "browser"
        }
        
        pattern_id = self.engine._generate_pattern_id("http_from_browser", pattern_data)
        
        pattern = LearningPattern(
            pattern_id=pattern_id,
            pattern_type="http_from_browser",
            pattern_data=pattern_data,
            confidence=0.6,
            success_count=1,
            failure_count=0,
            last_seen=time.time(),
            first_seen=time.time(),
            scan_count=1
        )
        
        self.engine.patterns[pattern_id] = pattern
        self.engine._save_patterns()
        
        print(f"[CrossSystemLearning] Extracted HTTP payload from browser workflow: {workflow.get('id')}")
        
        return http_payload
    
    async def track_http_browser_correlation(
        self,
        http_result: Dict[str, Any],
        browser_result: Dict[str, Any],
        target_url: str
    ):
        """
        Track correlation between HTTP recon and browser discoveries.
        Stores correlation patterns for future optimization.
        """
        correlation_data = {
            "target_url": target_url,
            "http_endpoints_found": http_result.get("endpoints_found", 0),
            "browser_endpoints_found": browser_result.get("endpoints_found", 0),
            "http_vulns_found": http_result.get("vulns_found", 0),
            "browser_vulns_found": browser_result.get("vulns_found", 0),
            "overlap_endpoints": http_result.get("overlap_endpoints", 0),
            "unique_http_endpoints": http_result.get("unique_endpoints", 0),
            "unique_browser_endpoints": browser_result.get("unique_endpoints", 0),
            "timestamp": time.time()
        }
        
        # Calculate correlation metrics
        total_endpoints = (correlation_data["http_endpoints_found"] + 
                          correlation_data["browser_endpoints_found"])
        
        if total_endpoints > 0:
            correlation_data["overlap_rate"] = (
                correlation_data["overlap_endpoints"] / total_endpoints
            )
            correlation_data["browser_unique_rate"] = (
                correlation_data["unique_browser_endpoints"] / total_endpoints
            )
        else:
            correlation_data["overlap_rate"] = 0.0
            correlation_data["browser_unique_rate"] = 0.0
        
        # Store correlation pattern
        pattern_id = self.engine._generate_pattern_id("http_browser_correlation", correlation_data)
        
        if pattern_id in self.engine.patterns:
            pattern = self.engine.patterns[pattern_id]
            pattern.success_count += 1
            pattern.last_seen = time.time()
            
            # Update running averages
            old_data = pattern.pattern_data
            pattern.pattern_data["overlap_rate"] = (
                (old_data.get("overlap_rate", 0) * pattern.success_count + 
                 correlation_data["overlap_rate"]) / (pattern.success_count + 1)
            )
            pattern.pattern_data["browser_unique_rate"] = (
                (old_data.get("browser_unique_rate", 0) * pattern.success_count + 
                 correlation_data["browser_unique_rate"]) / (pattern.success_count + 1)
            )
        else:
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="http_browser_correlation",
                pattern_data=correlation_data,
                confidence=0.5,
                success_count=1,
                failure_count=0,
                last_seen=time.time(),
                first_seen=time.time(),
                scan_count=1
            )
            self.engine.patterns[pattern_id] = pattern
        
        self.engine._save_patterns()
        
        print(f"[CrossSystemLearning] Tracked HTTP-browser correlation: {correlation_data['overlap_rate']:.1%} overlap")
    
    def get_correlation_stats(self) -> Dict[str, Any]:
        """Get statistics about HTTP-browser correlations"""
        correlation_patterns = [
            p for p in self.engine.patterns.values()
            if p.pattern_type == "http_browser_correlation"
        ]
        
        if not correlation_patterns:
            return {
                "total_correlations": 0,
                "avg_overlap_rate": 0.0,
                "avg_browser_unique_rate": 0.0
            }
        
        total = len(correlation_patterns)
        avg_overlap = sum(
            p.pattern_data.get("overlap_rate", 0) for p in correlation_patterns
        ) / total
        avg_unique = sum(
            p.pattern_data.get("browser_unique_rate", 0) for p in correlation_patterns
        ) / total
        
        return {
            "total_correlations": total,
            "avg_overlap_rate": round(avg_overlap, 2),
            "avg_browser_unique_rate": round(avg_unique, 2),
            "timestamp": time.time()
        }


# Create global cross-system learning extension
cross_system_learning = CrossSystemLearningExtension(learning_engine)


# ============================================================================
# AUTHENTICATION PATTERN LEARNING (Section 16)
# ============================================================================

class AuthenticationPatternLearner:
    """
    Learns authentication patterns and enables session reuse.
    """
    
    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.auth_patterns: Dict[str, Dict[str, Any]] = {}
        self.session_store: Dict[str, Dict[str, Any]] = {}
    
    def extract_auth_pattern(
        self,
        auth_data: Dict[str, Any],
        success: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Extract authentication pattern from successful auth attempt.
        Returns auth pattern as reusable skill.
        """
        if not success:
            return None
        
        target_domain = auth_data.get("domain")
        auth_method = auth_data.get("method", "form")  # form, oauth, api_key, etc.
        
        pattern = {
            "domain": target_domain,
            "method": auth_method,
            "steps": auth_data.get("steps", []),
            "credentials_fields": auth_data.get("credentials_fields", []),
            "success_indicators": auth_data.get("success_indicators", []),
            "session_token_location": auth_data.get("session_token_location"),
            "extracted_at": time.time()
        }
        
        # Store pattern
        pattern_key = f"{target_domain}:{auth_method}"
        self.auth_patterns[pattern_key] = pattern
        
        logger.info(f"[AuthLearning] Extracted auth pattern for {target_domain} ({auth_method})")
        
        return pattern
    
    def store_auth_pattern_as_skill(
        self,
        pattern: Dict[str, Any],
        skill_library: Any
    ) -> Any:
        """Store authentication pattern as reusable skill."""
        from backend.core.skill_library import BrowserSkill
        
        skill = BrowserSkill(
            skill_id=f"auth_{hashlib.md5(pattern['domain'].encode()).hexdigest()[:12]}",
            name=f"Auth: {pattern['domain']} ({pattern['method']})",
            skill_type="authentication_workflow",
            execution_context="browser_required",
            browser_requirements={
                "session": True,
                "stealth": False
            },
            workflow_steps=pattern.get("steps", []),
            version="1.0.0",
            required_capabilities=frozenset(["browser", "authentication"]),
            success_rate=1.0,
            confidence=0.8,
            created_at=time.time(),
            tags=["authentication", "session", pattern["method"]],
            parameters={
                "credentials_fields": pattern.get("credentials_fields", []),
                "success_indicators": pattern.get("success_indicators", []),
                "session_token_location": pattern.get("session_token_location")
            }
        )
        
        # Add to skill library
        skill_library.add_browser_skill(skill, {})
        
        logger.info(f"[AuthLearning] Stored auth pattern as skill: {skill.name}")
        
        return skill
    
    def reuse_auth_pattern(
        self,
        target_domain: str,
        auth_method: str = "form"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve learned authentication pattern for reuse.
        Returns pattern if available.
        """
        pattern_key = f"{target_domain}:{auth_method}"
        
        if pattern_key in self.auth_patterns:
            pattern = self.auth_patterns[pattern_key]
            logger.info(f"[AuthLearning] Reusing auth pattern for {target_domain}")
            return pattern
        
        return None
    
    def store_session_state(
        self,
        target_domain: str,
        session_data: Dict[str, Any]
    ):
        """Store session state for reuse across scans."""
        self.session_store[target_domain] = {
            "session_data": session_data,
            "stored_at": time.time(),
            "expires_at": time.time() + session_data.get("ttl_seconds", 3600)
        }
        
        logger.info(f"[AuthLearning] Stored session state for {target_domain}")
    
    def get_session_state(
        self,
        target_domain: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve stored session state if not expired."""
        if target_domain not in self.session_store:
            return None
        
        session = self.session_store[target_domain]
        
        # Check if expired
        if time.time() > session["expires_at"]:
            logger.info(f"[AuthLearning] Session expired for {target_domain}")
            del self.session_store[target_domain]
            return None
        
        logger.info(f"[AuthLearning] Retrieved session state for {target_domain}")
        return session["session_data"]
    
    async def re_authenticate(
        self,
        target_domain: str,
        browser_orchestrator: Any,
        credentials: Dict[str, str]
    ) -> bool:
        """
        Re-authenticate using learned pattern when session expires.
        Returns True if re-authentication succeeded.
        """
        # Get learned pattern
        pattern = self.reuse_auth_pattern(target_domain)
        
        if not pattern:
            logger.warning(f"[AuthLearning] No auth pattern found for {target_domain}")
            return False
        
        logger.info(f"[AuthLearning] Re-authenticating to {target_domain}")
        
        try:
            # Execute auth steps (simplified - actual implementation would use browser_orchestrator)
            for step in pattern.get("steps", []):
                # Execute step
                pass
            
            # Store new session
            # self.store_session_state(target_domain, new_session_data)
            
            return True
            
        except Exception as e:
            logger.error(f"[AuthLearning] Re-authentication failed: {e}")
            return False
    
    def track_auth_method_effectiveness(
        self,
        target_type: str,
        auth_method: str,
        success: bool
    ):
        """Track which authentication methods work for which target types."""
        tracking_key = f"auth_effectiveness:{target_type}:{auth_method}"
        
        # Get current stats from Redis
        stats_json = self.redis.get(tracking_key)
        if stats_json:
            stats = json.loads(stats_json)
        else:
            stats = {"success_count": 0, "failure_count": 0}
        
        # Update stats
        if success:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1
        
        # Calculate success rate
        total = stats["success_count"] + stats["failure_count"]
        stats["success_rate"] = stats["success_count"] / total if total > 0 else 0.0
        
        # Store back to Redis
        self.redis.setex(tracking_key, 86400 * 30, json.dumps(stats))  # 30 days TTL
        
        logger.debug(f"[AuthLearning] Auth method {auth_method} for {target_type}: {stats['success_rate']:.1%}")
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication learning statistics."""
        return {
            "patterns_learned": len(self.auth_patterns),
            "sessions_stored": len(self.session_store),
            "active_sessions": sum(
                1 for s in self.session_store.values()
                if time.time() < s["expires_at"]
            ),
            "timestamp": time.time()
        }


# Global authentication pattern learner
auth_pattern_learner: Optional[AuthenticationPatternLearner] = None


def initialize_auth_learner(redis_client: Any):
    """Initialize the global authentication pattern learner."""
    global auth_pattern_learner
    auth_pattern_learner = AuthenticationPatternLearner(redis_client)
    return auth_pattern_learner
