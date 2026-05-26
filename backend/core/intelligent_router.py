"""
INTELLIGENT ROUTER
Routes between HTTP and browser methods based on learned patterns.

This router:
1. Recommends HTTP-only, browser-only, or hybrid approaches
2. Selects appropriate browser engine (PinchTab vs OpenClaw)
3. Learns method effectiveness from results
4. Adapts recommendations based on target characteristics
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger("IntelligentRouter")


@dataclass
class MethodRecommendation:
    """Recommendation for attack method"""
    method: str  # "http_only", "browser_only", "hybrid"
    confidence: float
    reasoning: List[str]
    browser_engine: Optional[str] = None  # "pinchtab", "openclaw", None


class IntelligentRouter:
    """
    Routes between HTTP and browser methods based on learned patterns.
    """
    
    def __init__(self, learning_engine: Any, browser_orchestrator: Any):
        self.learning_engine = learning_engine
        self.browser_orchestrator = browser_orchestrator
        
        # Method effectiveness tracking
        self.method_effectiveness: Dict[str, Dict[str, Any]] = {}
    
    async def recommend_method(
        self,
        target_url: str,
        target_characteristics: Optional[Dict[str, Any]] = None
    ) -> MethodRecommendation:
        """
        Recommend attack method based on learned patterns and target characteristics.
        Returns HTTP-only, browser-only, or hybrid recommendation.
        """
        characteristics = target_characteristics or {}
        
        # Query learned patterns
        from backend.core.learning_engine import browser_learning
        recommendations = await browser_learning.get_browser_recommendations(target_url)
        
        reasoning = []
        
        # Check if target has JavaScript framework
        framework = characteristics.get("framework")
        if framework:
            reasoning.append(f"Target uses {framework} framework")
            # Framework-heavy sites benefit from browser
            if recommendations["confidence"] > 0.5:
                return MethodRecommendation(
                    method="browser_only",
                    confidence=0.8,
                    reasoning=reasoning + ["Framework-heavy site benefits from browser automation"],
                    browser_engine="openclaw"
                )
        
        # Check if target has dynamic content
        has_dynamic_content = characteristics.get("has_dynamic_content", False)
        if has_dynamic_content:
            reasoning.append("Target has dynamic content")
            return MethodRecommendation(
                method="hybrid",
                confidence=0.7,
                reasoning=reasoning + ["Dynamic content requires both HTTP and browser"],
                browser_engine="openclaw"
            )
        
        # Check learned patterns
        if recommendations["confidence"] > 0.6:
            if len(recommendations["workflows"]) > 0:
                reasoning.append(f"Found {len(recommendations['workflows'])} successful browser workflows")
                return MethodRecommendation(
                    method="browser_only",
                    confidence=recommendations["confidence"],
                    reasoning=reasoning,
                    browser_engine="openclaw"
                )
        
        # Check if HTTP patterns exist
        http_patterns = await self.learning_engine.get_recommendations(target_url, {})
        if http_patterns.get("confidence", 0) > 0.7:
            reasoning.append("Strong HTTP patterns found")
            return MethodRecommendation(
                method="http_only",
                confidence=http_patterns["confidence"],
                reasoning=reasoning + ["HTTP methods have proven effective"],
                browser_engine=None
            )
        
        # Default to hybrid approach
        return MethodRecommendation(
            method="hybrid",
            confidence=0.5,
            reasoning=["No strong patterns found, using hybrid approach"],
            browser_engine="pinchtab"
        )
    
    def select_browser_engine(
        self,
        task_complexity: str,
        stealth_required: bool = False
    ) -> str:
        """
        Select appropriate browser engine based on task complexity.
        Returns "pinchtab" or "openclaw".
        """
        # OpenClaw for complex tasks
        if task_complexity in ["high", "complex"]:
            logger.info("[Router] Selected OpenClaw for complex task")
            return "openclaw"
        
        # OpenClaw for stealth requirements
        if stealth_required:
            logger.info("[Router] Selected OpenClaw for stealth requirements")
            return "openclaw"
        
        # PinchTab for simple tasks
        logger.info("[Router] Selected PinchTab for simple task")
        return "pinchtab"
    
    async def learn_method_effectiveness(
        self,
        target_url: str,
        method_used: str,
        success: bool,
        target_characteristics: Dict[str, Any]
    ):
        """
        Learn from method effectiveness to improve future recommendations.
        """
        # Extract target characteristics
        framework = target_characteristics.get("framework")
        has_dynamic_content = target_characteristics.get("has_dynamic_content", False)
        
        # Create effectiveness key
        key = f"{target_url}:{method_used}"
        
        if key not in self.method_effectiveness:
            self.method_effectiveness[key] = {
                "method": method_used,
                "success_count": 0,
                "failure_count": 0,
                "target_characteristics": target_characteristics,
                "first_seen": time.time()
            }
        
        # Update effectiveness
        if success:
            self.method_effectiveness[key]["success_count"] += 1
        else:
            self.method_effectiveness[key]["failure_count"] += 1
        
        self.method_effectiveness[key]["last_seen"] = time.time()
        
        # Calculate success rate
        total = (self.method_effectiveness[key]["success_count"] + 
                self.method_effectiveness[key]["failure_count"])
        success_rate = self.method_effectiveness[key]["success_count"] / total if total > 0 else 0.0
        
        self.method_effectiveness[key]["success_rate"] = success_rate
        
        logger.info(f"[Router] Method effectiveness for {method_used}: {success_rate:.1%}")
    
    def get_method_stats(self) -> Dict[str, Any]:
        """Get statistics about method effectiveness."""
        stats = {
            "http_only": {"success": 0, "failure": 0, "success_rate": 0.0},
            "browser_only": {"success": 0, "failure": 0, "success_rate": 0.0},
            "hybrid": {"success": 0, "failure": 0, "success_rate": 0.0}
        }
        
        for data in self.method_effectiveness.values():
            method = data["method"]
            if method in stats:
                stats[method]["success"] += data["success_count"]
                stats[method]["failure"] += data["failure_count"]
        
        # Calculate success rates
        for method in stats:
            total = stats[method]["success"] + stats[method]["failure"]
            if total > 0:
                stats[method]["success_rate"] = stats[method]["success"] / total
        
        return stats


# Global intelligent router instance (will be initialized with dependencies)
intelligent_router: Optional[IntelligentRouter] = None


def initialize_router(learning_engine: Any, browser_orchestrator: Any):
    """Initialize the global intelligent router."""
    global intelligent_router
    intelligent_router = IntelligentRouter(learning_engine, browser_orchestrator)
    return intelligent_router
