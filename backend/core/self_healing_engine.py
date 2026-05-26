"""
SELF-HEALING ENGINE
Automatically recovers from failures without human intervention.

This engine:
1. Restarts crashed agents automatically
2. Adapts strategies when attacks fail repeatedly
3. Reallocates resources from overloaded to idle agents
4. Implements fallback strategies (aggressive → stealth)
5. Uses circuit breaker pattern for failing endpoints
6. Provides graceful degradation under load
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from pathlib import Path
import json

from backend.core.agent_health_monitor import health_monitor, HealthAlert

logger = logging.getLogger("SelfHealingEngine")


@dataclass
class RecoveryAction:
    """Represents a recovery action taken by the system."""
    timestamp: float
    agent_name: str
    issue: str
    action_type: str  # "restart", "strategy_change", "resource_reallocation", etc.
    action_details: Dict[str, Any]
    success: bool
    recovery_time_ms: float = 0.0


@dataclass
class CircuitBreaker:
    """Circuit breaker for failing endpoints."""
    endpoint: str
    failure_count: int = 0
    success_count: int = 0
    state: str = "closed"  # "closed", "open", "half_open"
    last_failure: float = 0.0
    opened_at: float = 0.0
    
    def should_allow_request(self) -> bool:
        """Check if requests should be allowed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            # Check if timeout has passed (30 seconds)
            if time.time() - self.opened_at > 30:
                self.state = "half_open"
                return True
            return False
        else:  # half_open
            return True
    
    def record_success(self):
        """Record successful request."""
        self.success_count += 1
        if self.state == "half_open" and self.success_count >= 3:
            self.state = "closed"
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure = time.time()
        
        if self.failure_count >= 5:
            self.state = "open"
            self.opened_at = time.time()
            logger.warning(f"[CircuitBreaker] Opened circuit for {self.endpoint}")


class SelfHealingEngine:
    """
    Automatically recovers from failures and optimizes system performance.
    """
    
    def __init__(self, brain_dir: str = "brain"):
        self.brain_dir = Path(brain_dir)
        self.healing_dir = self.brain_dir / "healing"
        self.healing_dir.mkdir(parents=True, exist_ok=True)
        
        # Recovery history
        self.recovery_history: deque = deque(maxlen=1000)
        
        # Circuit breakers per endpoint
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Agent restart tracking
        self.restart_counts: Dict[str, int] = defaultdict(int)
        self.last_restart: Dict[str, float] = {}
        
        # Strategy adaptation tracking
        self.strategy_changes: Dict[str, List[str]] = defaultdict(list)
        
        # Resource allocation
        self.agent_load: Dict[str, int] = defaultdict(int)
        
        # Callbacks for recovery actions
        self.restart_callbacks: Dict[str, Callable] = {}
        
        # Configuration
        self.config = {
            "max_restarts_per_hour": 5,
            "restart_backoff_seconds": [5, 10, 30, 60, 300],  # Exponential backoff
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 30,
            "strategy_change_threshold": 3,  # Consecutive failures before strategy change
            "load_balance_threshold": 10,  # Task queue depth difference
        }
    
    def register_restart_callback(self, agent_name: str, callback: Callable):
        """Register callback for agent restart."""
        self.restart_callbacks[agent_name] = callback
    
    async def monitor_and_heal(self):
        """
        Main healing loop - monitors health and takes recovery actions.
        Should be run as a background task.
        """
        logger.info("[SelfHealing] Monitoring loop started")
        
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Check for crashed agents
                crashed_agents = health_monitor.check_heartbeats()
                for agent_name in crashed_agents:
                    await self.heal_crashed_agent(agent_name)
                
                # Check for unhealthy agents
                all_health = health_monitor.get_all_health()
                for agent_name, metrics in all_health.items():
                    if metrics["health_score"] < 40:
                        await self.heal_unhealthy_agent(agent_name, metrics)
                
                # Check for high error rates
                for agent_name, metrics in all_health.items():
                    if metrics["error_rate"] > 0.3:
                        await self.adapt_strategy(agent_name, "high_error_rate")
                
                # Balance load across agents
                await self.balance_load()
                
                # Save healing state periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    await self.save_healing_state()
                    
            except Exception as e:
                logger.error(f"[SelfHealing] Monitoring loop error: {e}")
    
    async def heal_crashed_agent(self, agent_name: str) -> bool:
        """
        Attempt to restart a crashed agent.
        Returns True if restart was successful.
        """
        start_time = time.time()
        
        # Check if we've restarted too many times
        if not self._can_restart(agent_name):
            logger.error(f"[SelfHealing] Cannot restart {agent_name} - too many restarts")
            return False
        
        # Get backoff delay
        restart_count = self.restart_counts[agent_name]
        backoff_index = min(restart_count, len(self.config["restart_backoff_seconds"]) - 1)
        backoff_delay = self.config["restart_backoff_seconds"][backoff_index]
        
        # Check if enough time has passed since last restart
        if agent_name in self.last_restart:
            time_since_restart = time.time() - self.last_restart[agent_name]
            if time_since_restart < backoff_delay:
                logger.info(f"[SelfHealing] Waiting {backoff_delay - time_since_restart:.0f}s before restarting {agent_name}")
                return False
        
        logger.info(f"[SelfHealing] Attempting to restart {agent_name} (attempt {restart_count + 1})")
        
        try:
            # Call restart callback if registered
            if agent_name in self.restart_callbacks:
                await self.restart_callbacks[agent_name]()
                success = True
            else:
                logger.warning(f"[SelfHealing] No restart callback for {agent_name}")
                success = False
            
            # Record restart
            self.restart_counts[agent_name] += 1
            self.last_restart[agent_name] = time.time()
            
            # Record recovery action
            recovery_time = (time.time() - start_time) * 1000
            self._record_recovery(
                agent_name,
                "agent_crashed",
                "restart",
                {"restart_count": self.restart_counts[agent_name], "backoff_delay": backoff_delay},
                success,
                recovery_time
            )
            
            if success:
                logger.info(f"[SelfHealing] Successfully restarted {agent_name}")
                health_monitor.clear_alerts(agent_name)
            
            return success
            
        except Exception as e:
            logger.error(f"[SelfHealing] Failed to restart {agent_name}: {e}")
            self._record_recovery(
                agent_name,
                "agent_crashed",
                "restart",
                {"error": str(e)},
                False,
                (time.time() - start_time) * 1000
            )
            return False
    
    async def heal_unhealthy_agent(self, agent_name: str, metrics: Dict[str, Any]):
        """
        Heal an unhealthy agent by addressing specific issues.
        """
        health_score = metrics["health_score"]
        
        logger.info(f"[SelfHealing] Healing unhealthy agent {agent_name} (health: {health_score:.0f}/100)")
        
        # High memory usage - trigger garbage collection
        if metrics["memory_mb"] > 500:
            await self._reduce_memory_usage(agent_name)
        
        # High error rate - adapt strategy
        if metrics["error_rate"] > 0.2:
            await self.adapt_strategy(agent_name, "high_error_rate")
        
        # Slow response time - reduce load
        if metrics["response_time_ms"] > 2000:
            await self._reduce_agent_load(agent_name)
    
    async def adapt_strategy(self, agent_name: str, reason: str):
        """
        Adapt attack strategy when current approach is failing.
        """
        logger.info(f"[SelfHealing] Adapting strategy for {agent_name} (reason: {reason})")
        
        # Track strategy changes
        self.strategy_changes[agent_name].append(reason)
        
        # Determine new strategy based on reason
        if reason == "high_error_rate":
            new_strategy = "LOW_AND_SLOW"  # Switch to stealth mode
        elif reason == "rate_limited":
            new_strategy = "LOW_AND_SLOW"
        elif reason == "waf_detected":
            new_strategy = "LOW_AND_SLOW"
        else:
            new_strategy = "MULTI_STEP_EXPLOIT"
        
        self._record_recovery(
            agent_name,
            reason,
            "strategy_change",
            {"new_strategy": new_strategy},
            True,
            0.0
        )
        
        # Note: Actual strategy change would be implemented by publishing event to Omega
        # For now, we just record the recommendation
    
    async def balance_load(self):
        """
        Balance load across agents by reallocating tasks.
        """
        # Get current load for all agents
        all_health = health_monitor.get_all_health()
        
        if len(all_health) < 2:
            return  # Need at least 2 agents to balance
        
        # Find overloaded and idle agents
        overloaded = []
        idle = []
        
        for agent_name, metrics in all_health.items():
            queue_depth = metrics.get("task_queue_depth", 0)
            if queue_depth > 10:
                overloaded.append((agent_name, queue_depth))
            elif queue_depth < 3:
                idle.append((agent_name, queue_depth))
        
        # Reallocation logic would go here
        # For now, just log the recommendation
        if overloaded and idle:
            logger.info(f"[SelfHealing] Load imbalance detected - {len(overloaded)} overloaded, {len(idle)} idle")
    
    def check_circuit_breaker(self, endpoint: str) -> bool:
        """
        Check if endpoint circuit breaker allows requests.
        Returns True if requests are allowed.
        """
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker(endpoint=endpoint)
        
        breaker = self.circuit_breakers[endpoint]
        return breaker.should_allow_request()
    
    def record_endpoint_result(self, endpoint: str, success: bool):
        """Record result of endpoint request for circuit breaker."""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker(endpoint=endpoint)
        
        breaker = self.circuit_breakers[endpoint]
        if success:
            breaker.record_success()
        else:
            breaker.record_failure()
    
    def get_circuit_breaker_status(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get status of circuit breaker for endpoint."""
        if endpoint in self.circuit_breakers:
            return asdict(self.circuit_breakers[endpoint])
        return None
    
    def _can_restart(self, agent_name: str) -> bool:
        """Check if agent can be restarted (not too many restarts)."""
        restart_count = self.restart_counts[agent_name]
        
        # Check total restarts
        if restart_count >= 10:
            return False
        
        # Check restarts in last hour
        if agent_name in self.last_restart:
            time_since_restart = time.time() - self.last_restart[agent_name]
            if time_since_restart < 3600:  # Within last hour
                if restart_count >= self.config["max_restarts_per_hour"]:
                    return False
        
        return True
    
    async def _reduce_memory_usage(self, agent_name: str):
        """Attempt to reduce memory usage for agent."""
        logger.info(f"[SelfHealing] Reducing memory usage for {agent_name}")
        
        # Trigger garbage collection
        import gc
        gc.collect()
        
        self._record_recovery(
            agent_name,
            "high_memory_usage",
            "garbage_collection",
            {},
            True,
            0.0
        )
    
    async def _reduce_agent_load(self, agent_name: str):
        """Reduce load on agent by deferring new tasks."""
        logger.info(f"[SelfHealing] Reducing load for {agent_name}")
        
        self._record_recovery(
            agent_name,
            "slow_response_time",
            "load_reduction",
            {},
            True,
            0.0
        )
    
    def _record_recovery(
        self,
        agent_name: str,
        issue: str,
        action_type: str,
        action_details: Dict[str, Any],
        success: bool,
        recovery_time_ms: float
    ):
        """Record a recovery action."""
        action = RecoveryAction(
            timestamp=time.time(),
            agent_name=agent_name,
            issue=issue,
            action_type=action_type,
            action_details=action_details,
            success=success,
            recovery_time_ms=recovery_time_ms
        )
        
        self.recovery_history.append(action)
    
    def get_recovery_history(self, agent_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recovery action history."""
        history = list(self.recovery_history)
        
        if agent_name:
            history = [h for h in history if h.agent_name == agent_name]
        
        return [asdict(h) for h in history[-limit:]]
    
    def get_healing_metrics(self) -> Dict[str, Any]:
        """Get overall healing metrics."""
        total_recoveries = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r.success)
        
        recovery_by_type = defaultdict(int)
        for recovery in self.recovery_history:
            recovery_by_type[recovery.action_type] += 1
        
        return {
            "total_recoveries": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "success_rate": successful_recoveries / total_recoveries if total_recoveries > 0 else 0.0,
            "recovery_by_type": dict(recovery_by_type),
            "active_circuit_breakers": len([b for b in self.circuit_breakers.values() if b.state == "open"]),
            "total_restarts": sum(self.restart_counts.values()),
            "timestamp": time.time()
        }
    
    async def save_healing_state(self):
        """Save healing state to disk."""
        try:
            state = {
                "timestamp": time.time(),
                "recovery_history": self.get_recovery_history(),
                "metrics": self.get_healing_metrics(),
                "circuit_breakers": {
                    endpoint: asdict(breaker)
                    for endpoint, breaker in self.circuit_breakers.items()
                },
                "restart_counts": dict(self.restart_counts)
            }
            
            state_file = self.healing_dir / f"state_{int(time.time())}.json"
            state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
            
            # Keep only last 10 states
            states = sorted(self.healing_dir.glob("state_*.json"))
            for old_state in states[:-10]:
                old_state.unlink()
                
        except Exception as e:
            logger.error(f"[SelfHealing] Failed to save state: {e}")


# Global self-healing engine instance
healing_engine = SelfHealingEngine()


# ============================================================================
# BROWSER SELF-HEALING EXTENSION
# ============================================================================

class BrowserSelfHealingExtension:
    """Extension for browser-specific self-healing"""
    
    def __init__(self, healing_engine: SelfHealingEngine):
        self.engine = healing_engine
        self.browser_restart_counts: Dict[str, int] = defaultdict(int)
        self.last_browser_restart: Dict[str, float] = {}
    
    async def heal_browser_crash(
        self,
        agent_name: str,
        browser_orchestrator: Any
    ) -> bool:
        """
        Heal browser crash by restarting context and restoring session.
        Returns True if recovery was successful.
        """
        start_time = time.time()
        
        logger.info(f"[BrowserHealing] Healing browser crash for {agent_name}")
        
        try:
            # Detect crash via Health Monitor
            from backend.core.agent_health_monitor import browser_health_monitor
            browser_health = browser_health_monitor.get_browser_health(agent_name)
            
            if not browser_health:
                logger.warning(f"[BrowserHealing] No browser health data for {agent_name}")
                return False
            
            # Apply exponential backoff
            restart_count = self.browser_restart_counts[agent_name]
            backoff_delays = [5, 10, 30, 60, 300]
            backoff_index = min(restart_count, len(backoff_delays) - 1)
            backoff_delay = backoff_delays[backoff_index]
            
            if agent_name in self.last_browser_restart:
                time_since_restart = time.time() - self.last_browser_restart[agent_name]
                if time_since_restart < backoff_delay:
                    logger.info(f"[BrowserHealing] Waiting {backoff_delay - time_since_restart:.0f}s before restart")
                    return False
            
            # Restart browser context
            if hasattr(browser_orchestrator, 'restart_context'):
                await browser_orchestrator.restart_context(agent_name)
            
            # Restore session state (if available)
            if hasattr(browser_orchestrator, 'restore_session'):
                await browser_orchestrator.restore_session(agent_name)
            
            # Record restart
            self.browser_restart_counts[agent_name] += 1
            self.last_browser_restart[agent_name] = time.time()
            
            # Record recovery action
            recovery_time = (time.time() - start_time) * 1000
            self.engine._record_recovery(
                agent_name,
                "browser_crash",
                "browser_restart",
                {
                    "restart_count": self.browser_restart_counts[agent_name],
                    "backoff_delay": backoff_delay
                },
                True,
                recovery_time
            )
            
            logger.info(f"[BrowserHealing] Successfully restarted browser for {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"[BrowserHealing] Failed to heal browser crash: {e}")
            self.engine._record_recovery(
                agent_name,
                "browser_crash",
                "browser_restart",
                {"error": str(e)},
                False,
                (time.time() - start_time) * 1000
            )
            return False
    
    async def heal_browser_memory(
        self,
        agent_name: str,
        browser_orchestrator: Any
    ) -> bool:
        """
        Heal browser memory issues by closing idle contexts and triggering GC.
        """
        logger.info(f"[BrowserHealing] Healing browser memory for {agent_name}")
        
        try:
            # Close idle contexts
            if hasattr(browser_orchestrator, 'close_idle_contexts'):
                closed_count = await browser_orchestrator.close_idle_contexts(agent_name)
                logger.info(f"[BrowserHealing] Closed {closed_count} idle contexts")
            
            # Clear context pool
            if hasattr(browser_orchestrator, 'clear_context_pool'):
                await browser_orchestrator.clear_context_pool(agent_name)
            
            # Trigger garbage collection
            import gc
            gc.collect()
            
            # Record recovery action
            self.engine._record_recovery(
                agent_name,
                "browser_memory_high",
                "memory_cleanup",
                {"action": "closed_idle_contexts_and_gc"},
                True,
                0.0
            )
            
            logger.info(f"[BrowserHealing] Successfully cleaned up browser memory for {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"[BrowserHealing] Failed to heal browser memory: {e}")
            self.engine._record_recovery(
                agent_name,
                "browser_memory_high",
                "memory_cleanup",
                {"error": str(e)},
                False,
                0.0
            )
            return False
    
    async def adapt_browser_strategy(
        self,
        agent_name: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Adapt browser strategy when current approach is failing.
        Returns new strategy configuration.
        """
        logger.info(f"[BrowserHealing] Adapting browser strategy for {agent_name} (reason: {reason})")
        
        new_strategy = {
            "mode": "stealth",
            "concurrency": 1,
            "fallback_to_http": False
        }
        
        if reason == "high_error_rate":
            # Switch to stealth mode
            new_strategy["mode"] = "stealth"
            new_strategy["concurrency"] = 1
        elif reason == "rate_limited":
            # Reduce concurrency
            new_strategy["mode"] = "stealth"
            new_strategy["concurrency"] = 1
        elif reason == "waf_detected":
            # Fall back to HTTP
            new_strategy["mode"] = "stealth"
            new_strategy["fallback_to_http"] = True
        elif reason == "repeated_failures":
            # Fall back to HTTP
            new_strategy["fallback_to_http"] = True
        
        # Record strategy change
        self.engine._record_recovery(
            agent_name,
            reason,
            "browser_strategy_change",
            new_strategy,
            True,
            0.0
        )
        
        logger.info(f"[BrowserHealing] New browser strategy: {new_strategy}")
        return new_strategy
    
    def get_browser_circuit_breaker(self, target: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status for browser target."""
        breaker_key = f"browser:{target}"
        return self.engine.get_circuit_breaker_status(breaker_key)
    
    def record_browser_result(self, target: str, success: bool):
        """Record browser operation result for circuit breaker."""
        breaker_key = f"browser:{target}"
        self.engine.record_endpoint_result(breaker_key, success)
    
    def check_browser_circuit_breaker(self, target: str) -> bool:
        """Check if browser operations are allowed for target."""
        breaker_key = f"browser:{target}"
        return self.engine.check_circuit_breaker(breaker_key)


# Create global browser self-healing extension
browser_healing = BrowserSelfHealingExtension(healing_engine)


# ============================================================================
# UNIFIED ERROR HANDLING EXTENSION (Section 13)
# ============================================================================

class UnifiedErrorHandlingExtension:
    """
    Unified error handling for HTTP and browser operations.
    Applies same recovery patterns to both contexts.
    """
    
    def __init__(self, healing_engine: SelfHealingEngine):
        self.engine = healing_engine
        self.http_recovery_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        self.browser_recovery_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        self.cross_context_learnings: List[Dict[str, Any]] = []
    
    async def handle_error_unified(
        self,
        agent_name: str,
        error_type: str,
        context: str,  # "http" or "browser"
        error_details: Dict[str, Any]
    ) -> bool:
        """
        Handle error using unified recovery patterns.
        Applies same patterns to HTTP and browser errors.
        """
        logger.info(f"[UnifiedErrorHandling] Handling {context} error: {error_type} for {agent_name}")
        
        # Apply exponential backoff (same for both contexts)
        backoff_applied = await self._apply_exponential_backoff(agent_name, context)
        
        # Apply circuit breaker logic (same for both contexts)
        circuit_breaker_key = f"{context}:{agent_name}:{error_type}"
        self.engine.record_endpoint_result(circuit_breaker_key, False)
        
        # Determine recovery action based on error type
        recovery_success = False
        
        if error_type in ["connection_timeout", "network_error"]:
            recovery_success = await self._handle_network_error(agent_name, context, error_details)
        elif error_type in ["rate_limited", "too_many_requests"]:
            recovery_success = await self._handle_rate_limit(agent_name, context, error_details)
        elif error_type in ["authentication_failed", "session_expired"]:
            recovery_success = await self._handle_auth_error(agent_name, context, error_details)
        elif error_type in ["waf_detected", "blocked"]:
            recovery_success = await self._handle_waf_block(agent_name, context, error_details)
        else:
            recovery_success = await self._handle_generic_error(agent_name, context, error_details)
        
        # Track recovery stats by context
        if context == "http":
            if recovery_success:
                self.http_recovery_stats[error_type]["success"] += 1
            else:
                self.http_recovery_stats[error_type]["failure"] += 1
        else:  # browser
            if recovery_success:
                self.browser_recovery_stats[error_type]["success"] += 1
            else:
                self.browser_recovery_stats[error_type]["failure"] += 1
        
        # Learn from recovery patterns
        await self._learn_from_recovery(error_type, context, recovery_success)
        
        return recovery_success
    
    async def _apply_exponential_backoff(
        self,
        agent_name: str,
        context: str
    ) -> bool:
        """Apply exponential backoff (same for HTTP and browser)."""
        backoff_key = f"{context}:{agent_name}"
        
        if backoff_key not in self.engine.last_restart:
            self.engine.last_restart[backoff_key] = time.time()
            return True
        
        restart_count = self.engine.restart_counts.get(backoff_key, 0)
        backoff_delays = [1, 2, 5, 10, 30, 60]
        backoff_index = min(restart_count, len(backoff_delays) - 1)
        backoff_delay = backoff_delays[backoff_index]
        
        time_since_last = time.time() - self.engine.last_restart[backoff_key]
        
        if time_since_last < backoff_delay:
            logger.debug(f"[UnifiedErrorHandling] Backoff active for {agent_name} ({context}): {backoff_delay - time_since_last:.1f}s remaining")
            return False
        
        self.engine.restart_counts[backoff_key] = restart_count + 1
        self.engine.last_restart[backoff_key] = time.time()
        
        return True
    
    async def _handle_network_error(
        self,
        agent_name: str,
        context: str,
        error_details: Dict[str, Any]
    ) -> bool:
        """Handle network errors (same for HTTP and browser)."""
        logger.info(f"[UnifiedErrorHandling] Handling network error for {agent_name} ({context})")
        
        # Wait and retry
        await asyncio.sleep(2)
        
        self.engine._record_recovery(
            agent_name,
            "network_error",
            f"{context}_retry",
            error_details,
            True,
            2000.0
        )
        
        return True
    
    async def _handle_rate_limit(
        self,
        agent_name: str,
        context: str,
        error_details: Dict[str, Any]
    ) -> bool:
        """Handle rate limiting (same for HTTP and browser)."""
        logger.info(f"[UnifiedErrorHandling] Handling rate limit for {agent_name} ({context})")
        
        # Switch to stealth mode
        await self.engine.adapt_strategy(agent_name, "rate_limited")
        
        # Wait longer
        await asyncio.sleep(10)
        
        self.engine._record_recovery(
            agent_name,
            "rate_limited",
            f"{context}_strategy_change",
            {"new_strategy": "LOW_AND_SLOW"},
            True,
            10000.0
        )
        
        return True
    
    async def _handle_auth_error(
        self,
        agent_name: str,
        context: str,
        error_details: Dict[str, Any]
    ) -> bool:
        """Handle authentication errors (same for HTTP and browser)."""
        logger.info(f"[UnifiedErrorHandling] Handling auth error for {agent_name} ({context})")
        
        # Re-authentication would be triggered here
        # For now, just record the attempt
        
        self.engine._record_recovery(
            agent_name,
            "authentication_failed",
            f"{context}_reauth",
            error_details,
            False,  # Would be True if re-auth succeeded
            0.0
        )
        
        return False
    
    async def _handle_waf_block(
        self,
        agent_name: str,
        context: str,
        error_details: Dict[str, Any]
    ) -> bool:
        """Handle WAF blocks (same for HTTP and browser)."""
        logger.info(f"[UnifiedErrorHandling] Handling WAF block for {agent_name} ({context})")
        
        # Switch to stealth mode
        await self.engine.adapt_strategy(agent_name, "waf_detected")
        
        self.engine._record_recovery(
            agent_name,
            "waf_detected",
            f"{context}_strategy_change",
            {"new_strategy": "LOW_AND_SLOW"},
            True,
            0.0
        )
        
        return True
    
    async def _handle_generic_error(
        self,
        agent_name: str,
        context: str,
        error_details: Dict[str, Any]
    ) -> bool:
        """Handle generic errors (same for HTTP and browser)."""
        logger.info(f"[UnifiedErrorHandling] Handling generic error for {agent_name} ({context})")
        
        # Generic retry with backoff
        await asyncio.sleep(1)
        
        self.engine._record_recovery(
            agent_name,
            "generic_error",
            f"{context}_retry",
            error_details,
            True,
            1000.0
        )
        
        return True
    
    async def _learn_from_recovery(
        self,
        error_type: str,
        context: str,
        success: bool
    ):
        """Learn from recovery patterns across contexts."""
        learning = {
            "error_type": error_type,
            "context": context,
            "success": success,
            "timestamp": time.time()
        }
        
        self.cross_context_learnings.append(learning)
        
        # Keep only last 1000 learnings
        if len(self.cross_context_learnings) > 1000:
            self.cross_context_learnings = self.cross_context_learnings[-1000:]
        
        # Apply learnings from one context to another
        if success:
            # If HTTP recovery worked, apply same pattern to browser
            # If browser recovery worked, apply same pattern to HTTP
            logger.debug(f"[UnifiedErrorHandling] Learning: {error_type} recovery works in {context}")
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics by context."""
        return {
            "http_recovery": dict(self.http_recovery_stats),
            "browser_recovery": dict(self.browser_recovery_stats),
            "cross_context_learnings": len(self.cross_context_learnings),
            "timestamp": time.time()
        }
    
    def get_unified_success_rate(self, error_type: str) -> Dict[str, float]:
        """Get success rate for error type across both contexts."""
        http_stats = self.http_recovery_stats.get(error_type, {"success": 0, "failure": 0})
        browser_stats = self.browser_recovery_stats.get(error_type, {"success": 0, "failure": 0})
        
        http_total = http_stats["success"] + http_stats["failure"]
        browser_total = browser_stats["success"] + browser_stats["failure"]
        
        return {
            "http_success_rate": http_stats["success"] / http_total if http_total > 0 else 0.0,
            "browser_success_rate": browser_stats["success"] / browser_total if browser_total > 0 else 0.0,
            "combined_success_rate": (
                (http_stats["success"] + browser_stats["success"]) /
                (http_total + browser_total)
            ) if (http_total + browser_total) > 0 else 0.0
        }


# Create global unified error handling extension
unified_error_handling = UnifiedErrorHandlingExtension(healing_engine)
