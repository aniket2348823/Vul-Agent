"""
FORENSIC LEARNING BRIDGE
Connects forensic evidence collection with the learning engine.

This bridge:
1. Analyzes evidence quality for vulnerabilities
2. Learns evidence requirements from successful exploits
3. Adapts evidence collection strategies based on learned patterns
4. Tracks evidence value scores
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger("ForensicLearningBridge")


@dataclass
class EvidenceQualityScore:
    """Quality score for collected evidence"""
    vulnerability_id: str
    quality_score: float  # 0.0 to 1.0
    completeness: float  # 0.0 to 1.0
    gaps: List[str]
    evidence_types_present: List[str]
    evidence_types_missing: List[str]
    timestamp: float


class ForensicLearningBridge:
    """
    Bridges forensic evidence collection with learning engine.
    Learns what evidence is valuable and adapts collection strategies.
    """
    
    def __init__(self, learning_engine: Any, forensic_collector: Any):
        self.learning_engine = learning_engine
        self.forensic_collector = forensic_collector
        
        # Evidence requirements per vulnerability type
        self.evidence_requirements: Dict[str, Dict[str, float]] = {}
        
        # Evidence value scores
        self.evidence_values: Dict[str, float] = {}
        
        # Quality history
        self.quality_history: List[EvidenceQualityScore] = []
    
    def analyze_evidence_quality(
        self,
        vulnerability_id: str,
        evidence_data: Dict[str, Any]
    ) -> EvidenceQualityScore:
        """
        Analyze quality of collected evidence for a vulnerability.
        Returns quality score with identified gaps.
        """
        vuln_type = evidence_data.get("vuln_type", "unknown")
        
        # Get required evidence types for this vulnerability
        required_types = self._get_required_evidence_types(vuln_type)
        
        # Check what evidence is present
        present_types = []
        missing_types = []
        
        for evidence_type in required_types:
            if evidence_type in evidence_data.get("evidence", {}):
                present_types.append(evidence_type)
            else:
                missing_types.append(evidence_type)
        
        # Calculate completeness
        completeness = len(present_types) / len(required_types) if required_types else 1.0
        
        # Calculate quality score based on completeness and evidence richness
        quality_score = completeness
        
        # Bonus for having high-value evidence
        for evidence_type in present_types:
            value = self.evidence_values.get(evidence_type, 0.5)
            quality_score += value * 0.1  # Small bonus per high-value evidence
        
        quality_score = min(1.0, quality_score)
        
        # Identify gaps
        gaps = []
        if completeness < 1.0:
            gaps.append(f"Missing {len(missing_types)} required evidence types")
        
        if not evidence_data.get("evidence", {}).get("screenshot"):
            gaps.append("No screenshot evidence")
        
        if not evidence_data.get("evidence", {}).get("http_request"):
            gaps.append("No HTTP request captured")
        
        score = EvidenceQualityScore(
            vulnerability_id=vulnerability_id,
            quality_score=quality_score,
            completeness=completeness,
            gaps=gaps,
            evidence_types_present=present_types,
            evidence_types_missing=missing_types,
            timestamp=time.time()
        )
        
        self.quality_history.append(score)
        
        logger.info(f"[ForensicBridge] Evidence quality for {vulnerability_id}: {quality_score:.2f}")
        
        return score
    
    def learn_evidence_requirements(
        self,
        vuln_type: str,
        evidence_data: Dict[str, Any],
        exploit_success: bool
    ):
        """
        Learn what evidence types are valuable for a vulnerability type.
        Tracks which evidence correlates with successful exploits.
        """
        if vuln_type not in self.evidence_requirements:
            self.evidence_requirements[vuln_type] = {}
        
        # Track evidence types present
        evidence_types = list(evidence_data.get("evidence", {}).keys())
        
        for evidence_type in evidence_types:
            if evidence_type not in self.evidence_requirements[vuln_type]:
                self.evidence_requirements[vuln_type][evidence_type] = {
                    "success_count": 0,
                    "total_count": 0,
                    "value_score": 0.5
                }
            
            req = self.evidence_requirements[vuln_type][evidence_type]
            req["total_count"] += 1
            
            if exploit_success:
                req["success_count"] += 1
            
            # Calculate value score (correlation with success)
            if req["total_count"] > 0:
                req["value_score"] = req["success_count"] / req["total_count"]
            
            # Update global evidence value
            self.evidence_values[evidence_type] = req["value_score"]
        
        logger.info(f"[ForensicBridge] Learned evidence requirements for {vuln_type}")
    
    def adapt_evidence_collection(
        self,
        vuln_type: str
    ) -> Dict[str, Any]:
        """
        Get adapted evidence collection strategy based on learned requirements.
        Returns collection strategy with prioritized evidence types.
        """
        strategy = {
            "priority_evidence": [],
            "optional_evidence": [],
            "collection_method": "standard"
        }
        
        # Get learned requirements for this vulnerability type
        if vuln_type not in self.evidence_requirements:
            # No learned data, use default strategy
            strategy["priority_evidence"] = [
                "screenshot",
                "http_request",
                "http_response",
                "payload"
            ]
            return strategy
        
        requirements = self.evidence_requirements[vuln_type]
        
        # Sort evidence types by value score
        sorted_evidence = sorted(
            requirements.items(),
            key=lambda x: x[1]["value_score"],
            reverse=True
        )
        
        # High-value evidence (score > 0.7)
        for evidence_type, data in sorted_evidence:
            if data["value_score"] > 0.7:
                strategy["priority_evidence"].append(evidence_type)
            elif data["value_score"] > 0.4:
                strategy["optional_evidence"].append(evidence_type)
        
        # Determine collection method based on requirements
        if len(strategy["priority_evidence"]) > 5:
            strategy["collection_method"] = "comprehensive"
        elif len(strategy["priority_evidence"]) < 3:
            strategy["collection_method"] = "minimal"
        
        logger.info(f"[ForensicBridge] Adapted strategy for {vuln_type}: {len(strategy['priority_evidence'])} priority items")
        
        return strategy
    
    def _get_required_evidence_types(self, vuln_type: str) -> List[str]:
        """Get required evidence types for a vulnerability type."""
        # Default requirements
        default_requirements = [
            "screenshot",
            "http_request",
            "http_response",
            "payload"
        ]
        
        # Type-specific requirements
        type_requirements = {
            "XSS": ["screenshot", "http_request", "http_response", "payload", "dom_state"],
            "SQLi": ["http_request", "http_response", "payload", "database_error"],
            "CSRF": ["http_request", "http_response", "session_token"],
            "SSRF": ["http_request", "http_response", "internal_request"],
        }
        
        return type_requirements.get(vuln_type, default_requirements)
    
    def get_evidence_stats(self) -> Dict[str, Any]:
        """Get statistics about evidence learning."""
        total_analyzed = len(self.quality_history)
        
        if total_analyzed == 0:
            return {
                "total_analyzed": 0,
                "avg_quality_score": 0.0,
                "avg_completeness": 0.0,
                "learned_requirements": 0
            }
        
        avg_quality = sum(s.quality_score for s in self.quality_history) / total_analyzed
        avg_completeness = sum(s.completeness for s in self.quality_history) / total_analyzed
        
        return {
            "total_analyzed": total_analyzed,
            "avg_quality_score": round(avg_quality, 2),
            "avg_completeness": round(avg_completeness, 2),
            "learned_requirements": len(self.evidence_requirements),
            "evidence_types_tracked": len(self.evidence_values),
            "timestamp": time.time()
        }


# Global forensic learning bridge instance (will be initialized with dependencies)
forensic_learning_bridge: Optional[ForensicLearningBridge] = None


def initialize_bridge(learning_engine: Any, forensic_collector: Any):
    """Initialize the global forensic learning bridge."""
    global forensic_learning_bridge
    forensic_learning_bridge = ForensicLearningBridge(learning_engine, forensic_collector)
    return forensic_learning_bridge


# ============================================================================
# EVIDENCE COLLECTION SKILLS (Section 18.3, 18.5)
# ============================================================================

class EvidenceCollectionSkillManager:
    """
    Manages evidence collection patterns as skills.
    """
    
    def __init__(self, forensic_bridge: ForensicLearningBridge):
        self.bridge = forensic_bridge
        self.collection_skills: Dict[str, Dict[str, Any]] = {}
    
    def create_evidence_collection_skill(
        self,
        vuln_type: str,
        evidence_pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create evidence collection skill from learned pattern.
        """
        skill = {
            "skill_id": f"evidence_{vuln_type}_{int(time.time())}",
            "vuln_type": vuln_type,
            "priority_evidence": evidence_pattern.get("priority_evidence", []),
            "optional_evidence": evidence_pattern.get("optional_evidence", []),
            "collection_method": evidence_pattern.get("collection_method", "standard"),
            "created_at": time.time()
        }
        
        self.collection_skills[skill["skill_id"]] = skill
        
        logger.info(f"[EvidenceSkills] Created collection skill for {vuln_type}")
        
        return skill
    
    def get_collection_skill(self, vuln_type: str) -> Optional[Dict[str, Any]]:
        """Get evidence collection skill for vulnerability type."""
        for skill in self.collection_skills.values():
            if skill["vuln_type"] == vuln_type:
                return skill
        return None
    
    def enforce_required_evidence(
        self,
        vuln_type: str,
        collected_evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ensure required evidence is collected for vulnerability type.
        Returns validation result with missing evidence.
        """
        required_types = self.bridge._get_required_evidence_types(vuln_type)
        
        missing = []
        present = []
        
        for evidence_type in required_types:
            if evidence_type in collected_evidence:
                present.append(evidence_type)
            else:
                missing.append(evidence_type)
        
        result = {
            "complete": len(missing) == 0,
            "present": present,
            "missing": missing,
            "completeness": len(present) / len(required_types) if required_types else 1.0
        }
        
        if not result["complete"]:
            logger.warning(f"[EvidenceSkills] Missing required evidence for {vuln_type}: {missing}")
        
        return result
    
    def track_evidence_quality_over_time(
        self,
        vuln_type: str
    ) -> Dict[str, Any]:
        """Track evidence quality metrics over time."""
        # Get quality history for this vuln type
        relevant_scores = [
            score for score in self.bridge.quality_history
            if score.vulnerability_id.startswith(vuln_type)
        ]
        
        if not relevant_scores:
            return {
                "vuln_type": vuln_type,
                "samples": 0,
                "avg_quality": 0.0,
                "trend": "no_data"
            }
        
        # Calculate average quality
        avg_quality = sum(s.quality_score for s in relevant_scores) / len(relevant_scores)
        
        # Calculate trend (compare first half vs second half)
        mid = len(relevant_scores) // 2
        if mid > 0:
            first_half_avg = sum(s.quality_score for s in relevant_scores[:mid]) / mid
            second_half_avg = sum(s.quality_score for s in relevant_scores[mid:]) / (len(relevant_scores) - mid)
            
            if second_half_avg > first_half_avg + 0.1:
                trend = "improving"
            elif second_half_avg < first_half_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "vuln_type": vuln_type,
            "samples": len(relevant_scores),
            "avg_quality": round(avg_quality, 2),
            "trend": trend,
            "latest_quality": relevant_scores[-1].quality_score if relevant_scores else 0.0
        }


# Global evidence collection skill manager
evidence_skill_manager: Optional[EvidenceCollectionSkillManager] = None


def initialize_evidence_skills(forensic_bridge: ForensicLearningBridge):
    """Initialize the global evidence collection skill manager."""
    global evidence_skill_manager
    evidence_skill_manager = EvidenceCollectionSkillManager(forensic_bridge)
    return evidence_skill_manager
