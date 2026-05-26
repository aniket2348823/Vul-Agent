"""
Feature flags for deep system integration.

This module provides feature flags for gradual rollout of integration features,
allowing safe deployment with instant rollback capability.
"""

import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout of integration features"""
    
    # Integration features
    enable_browser_learning: bool = False  # Start disabled
    enable_cross_system_healing: bool = False
    enable_forensic_learning: bool = False
    enable_intelligent_routing: bool = False
    enable_unified_knowledge_graph: bool = False
    
    # Rollout percentages (0-100)
    browser_learning_rollout_pct: int = 0
    cross_healing_rollout_pct: int = 0
    forensic_learning_rollout_pct: int = 0
    routing_rollout_pct: int = 0
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_s: int = 60
    
    # Performance limits
    max_concurrent_learning: int = 5
    event_batch_size: int = 10
    event_batch_timeout_ms: int = 1000
    
    # Resource management
    max_browser_contexts: int = 20
    browser_memory_limit_mb: int = 2048
    
    @classmethod
    def from_env(cls) -> "FeatureFlags":
        """Load feature flags from environment variables"""
        return cls(
            # Integration features
            enable_browser_learning=cls._get_bool_env("ENABLE_BROWSER_LEARNING", False),
            enable_cross_system_healing=cls._get_bool_env("ENABLE_CROSS_HEALING", False),
            enable_forensic_learning=cls._get_bool_env("ENABLE_FORENSIC_LEARNING", False),
            enable_intelligent_routing=cls._get_bool_env("ENABLE_INTELLIGENT_ROUTING", False),
            enable_unified_knowledge_graph=cls._get_bool_env("ENABLE_UNIFIED_KNOWLEDGE_GRAPH", False),
            
            # Rollout percentages
            browser_learning_rollout_pct=cls._get_int_env("BROWSER_LEARNING_ROLLOUT_PCT", 0),
            cross_healing_rollout_pct=cls._get_int_env("CROSS_HEALING_ROLLOUT_PCT", 0),
            forensic_learning_rollout_pct=cls._get_int_env("FORENSIC_LEARNING_ROLLOUT_PCT", 0),
            routing_rollout_pct=cls._get_int_env("ROUTING_ROLLOUT_PCT", 0),
            
            # Circuit breaker
            circuit_breaker_enabled=cls._get_bool_env("CIRCUIT_BREAKER_ENABLED", True),
            circuit_breaker_threshold=cls._get_int_env("CIRCUIT_BREAKER_THRESHOLD", 5),
            circuit_breaker_timeout_s=cls._get_int_env("CIRCUIT_BREAKER_TIMEOUT_S", 60),
            
            # Performance
            max_concurrent_learning=cls._get_int_env("MAX_CONCURRENT_LEARNING", 5),
            event_batch_size=cls._get_int_env("EVENT_BATCH_SIZE", 10),
            event_batch_timeout_ms=cls._get_int_env("EVENT_BATCH_TIMEOUT_MS", 1000),
            
            # Resources
            max_browser_contexts=cls._get_int_env("MAX_BROWSER_CONTEXTS", 20),
            browser_memory_limit_mb=cls._get_int_env("BROWSER_MEMORY_LIMIT_MB", 2048),
        )
    
    @staticmethod
    def _get_bool_env(key: str, default: bool) -> bool:
        """Get boolean from environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Get integer from environment variable"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer for {key}, using default {default}")
            return default
    
    def should_enable_for_scan(self, scan_id: str, feature: str) -> bool:
        """
        Determine if feature should be enabled for this scan (gradual rollout).
        
        Uses scan_id hash for consistent rollout - same scan always gets same result.
        
        Args:
            scan_id: Unique scan identifier
            feature: Feature name ("browser_learning", "cross_healing", etc.)
            
        Returns:
            True if feature should be enabled for this scan
        """
        # Check if feature is globally enabled
        feature_enabled = {
            "browser_learning": self.enable_browser_learning,
            "cross_healing": self.enable_cross_system_healing,
            "forensic_learning": self.enable_forensic_learning,
            "routing": self.enable_intelligent_routing,
            "knowledge_graph": self.enable_unified_knowledge_graph,
        }.get(feature, False)
        
        if not feature_enabled:
            return False
        
        # Get rollout percentage
        rollout_pct = {
            "browser_learning": self.browser_learning_rollout_pct,
            "cross_healing": self.cross_healing_rollout_pct,
            "forensic_learning": self.forensic_learning_rollout_pct,
            "routing": self.routing_rollout_pct,
        }.get(feature, 0)
        
        # Use scan_id hash for consistent rollout
        scan_hash = hash(scan_id) % 100
        return scan_hash < rollout_pct
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is globally enabled"""
        return {
            "browser_learning": self.enable_browser_learning,
            "cross_healing": self.enable_cross_system_healing,
            "forensic_learning": self.enable_forensic_learning,
            "routing": self.enable_intelligent_routing,
            "knowledge_graph": self.enable_unified_knowledge_graph,
        }.get(feature, False)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "integration_features": {
                "browser_learning": self.enable_browser_learning,
                "cross_system_healing": self.enable_cross_system_healing,
                "forensic_learning": self.enable_forensic_learning,
                "intelligent_routing": self.enable_intelligent_routing,
                "unified_knowledge_graph": self.enable_unified_knowledge_graph,
            },
            "rollout_percentages": {
                "browser_learning": self.browser_learning_rollout_pct,
                "cross_healing": self.cross_healing_rollout_pct,
                "forensic_learning": self.forensic_learning_rollout_pct,
                "routing": self.routing_rollout_pct,
            },
            "circuit_breaker": {
                "enabled": self.circuit_breaker_enabled,
                "threshold": self.circuit_breaker_threshold,
                "timeout_s": self.circuit_breaker_timeout_s,
            },
            "performance": {
                "max_concurrent_learning": self.max_concurrent_learning,
                "event_batch_size": self.event_batch_size,
                "event_batch_timeout_ms": self.event_batch_timeout_ms,
            },
            "resources": {
                "max_browser_contexts": self.max_browser_contexts,
                "browser_memory_limit_mb": self.browser_memory_limit_mb,
            }
        }


# Global instance - loaded from environment
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """Get global feature flags instance"""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags.from_env()
        logger.info("Feature flags loaded", extra=_feature_flags.to_dict())
    return _feature_flags


def reload_feature_flags() -> FeatureFlags:
    """Reload feature flags from environment (for hot-reload)"""
    global _feature_flags
    _feature_flags = FeatureFlags.from_env()
    logger.info("Feature flags reloaded", extra=_feature_flags.to_dict())
    return _feature_flags
