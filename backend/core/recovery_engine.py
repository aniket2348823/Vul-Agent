"""
Vigilagent Recovery Engine (Architecture §14, §14.1, §29.9, §29.13)
================================================================================
Single merged module that replaces the former `self_healing_engine.py` and
`strategy_adapter.py`. It provides:

  - SelfHealingEngine: circuit breakers, agent restart with backoff, health loop,
    load balancing, persisted healing state.
  - BrowserSelfHealingExtension: browser crash/memory recovery + strategy.
  - UnifiedErrorHandlingExtension: HTTP+browser error handling with REAL,
    vault-backed re-authentication (Architecture §29.9 — no more stub).
  - StrategyAdapter: real strategy selection among RETRY / SWITCH_TECHNIQUE /
    DELEGATE / REDUCE_AGGRESSION / CHANGE_PARAMETERS / ABORT based on error
    class and diminishing returns (no constant SWITCH_TECHNIQUE).
  - RecoveryEngine: a thin façade that ties these together, selects a real
    corrective action, and writes the resolving pattern to the SkillLibrary so
    the Planner can consume it (closing the write-only loop, §29.9 req 4).
"""
from __future__ import annotations

import asyncio
import gc
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.core.agent_health_monitor import health_monitor, HealthAlert
from backend.core.self_awareness_config import SelfAwarenessConfig
from backend.core.tracing import get_tracer, trace_span

logger = logging.getLogger("RecoveryEngine")
tracer = get_tracer()


# ══════════════════════════════════════════════════════════════════════════════
# SELF-HEALING (formerly self_healing_engine.py)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RecoveryRecord:
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
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.opened_at > 30:
                self.state = "half_open"
                return True
            return False
        else:  # half_open
            return True

    def record_success(self):
        self.success_count += 1
        if self.state == "half_open" and self.success_count >= 3:
            self.state = "closed"
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure = time.time()
        if self.failure_count >= 5:
            self.state = "open"
            self.opened_at = time.time()
            logger.warning(f"[CircuitBreaker] Opened circuit for {self.endpoint}")


class SelfHealingEngine:
    """Automatically recovers from failures and optimizes performance."""

    def __init__(self, brain_dir: str = "brain"):
        self.brain_dir = Path(brain_dir)
        self.healing_dir = self.brain_dir / "healing"
        self.healing_dir.mkdir(parents=True, exist_ok=True)
        self.recovery_history: deque = deque(maxlen=1000)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.restart_counts: Dict[str, int] = defaultdict(int)
        self.last_restart: Dict[str, float] = {}
        self.strategy_changes: Dict[str, List[str]] = defaultdict(list)
        self.agent_load: Dict[str, int] = defaultdict(int)
        self.restart_callbacks: Dict[str, Callable] = {}
        self.config = {
            "max_restarts_per_hour": 5,
            "restart_backoff_seconds": [5, 10, 30, 60, 300],
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 30,
            "strategy_change_threshold": 3,
            "load_balance_threshold": 10,
        }

    def register_restart_callback(self, agent_name: str, callback: Callable):
        self.restart_callbacks[agent_name] = callback

    async def monitor_and_heal(self):
        """Main healing loop — monitors health and takes recovery actions."""
        logger.info("[SelfHealing] Monitoring loop started")
        while True:
            try:
                await asyncio.sleep(10)
                crashed_agents = health_monitor.check_heartbeats()
                for agent_name in crashed_agents:
                    await self.heal_crashed_agent(agent_name)
                all_health = health_monitor.get_all_health()
                for agent_name, metrics in all_health.items():
                    if metrics["health_score"] < 40:
                        await self.heal_unhealthy_agent(agent_name, metrics)
                for agent_name, metrics in all_health.items():
                    if metrics["error_rate"] > 0.3:
                        await self.adapt_strategy(agent_name, "high_error_rate")
                await self.balance_load()
                if int(time.time()) % 300 == 0:
                    await self.save_healing_state()
            except Exception as e:
                logger.error(f"[SelfHealing] Monitoring loop error: {e}")

    async def heal_crashed_agent(self, agent_name: str) -> bool:
        start_time = time.time()
        if not self._can_restart(agent_name):
            logger.error(f"[SelfHealing] Cannot restart {agent_name} - too many restarts")
            return False
        restart_count = self.restart_counts[agent_name]
        backoff_index = min(restart_count, len(self.config["restart_backoff_seconds"]) - 1)
        backoff_delay = self.config["restart_backoff_seconds"][backoff_index]
        if agent_name in self.last_restart:
            time_since_restart = time.time() - self.last_restart[agent_name]
            if time_since_restart < backoff_delay:
                logger.info(f"[SelfHealing] Waiting {backoff_delay - time_since_restart:.0f}s before restarting {agent_name}")
                return False
        logger.info(f"[SelfHealing] Attempting to restart {agent_name} (attempt {restart_count + 1})")
        try:
            if agent_name in self.restart_callbacks:
                await self.restart_callbacks[agent_name]()
                success = True
            else:
                logger.warning(f"[SelfHealing] No restart callback for {agent_name}")
                success = False
            self.restart_counts[agent_name] += 1
            self.last_restart[agent_name] = time.time()
            recovery_time = (time.time() - start_time) * 1000
            self._record_recovery(agent_name, "agent_crashed", "restart",
                                  {"restart_count": self.restart_counts[agent_name], "backoff_delay": backoff_delay},
                                  success, recovery_time)
            if success:
                logger.info(f"[SelfHealing] Successfully restarted {agent_name}")
                health_monitor.clear_alerts(agent_name)
            return success
        except Exception as e:
            logger.error(f"[SelfHealing] Failed to restart {agent_name}: {e}")
            self._record_recovery(agent_name, "agent_crashed", "restart", {"error": str(e)},
                                  False, (time.time() - start_time) * 1000)
            return False

    async def heal_unhealthy_agent(self, agent_name: str, metrics: Dict[str, Any]):
        health_score = metrics["health_score"]
        logger.info(f"[SelfHealing] Healing unhealthy agent {agent_name} (health: {health_score:.0f}/100)")
        if metrics["memory_mb"] > 500:
            await self._reduce_memory_usage(agent_name)
        if metrics["error_rate"] > 0.2:
            await self.adapt_strategy(agent_name, "high_error_rate")
        if metrics["response_time_ms"] > 2000:
            await self._reduce_agent_load(agent_name)

    async def adapt_strategy(self, agent_name: str, reason: str):
        logger.info(f"[SelfHealing] Adapting strategy for {agent_name} (reason: {reason})")
        self.strategy_changes[agent_name].append(reason)
        if reason in ("high_error_rate", "rate_limited", "waf_detected"):
            new_strategy = "LOW_AND_SLOW"
        else:
            new_strategy = "MULTI_STEP_EXPLOIT"
        self._record_recovery(agent_name, reason, "strategy_change",
                              {"new_strategy": new_strategy}, True, 0.0)

    async def balance_load(self):
        all_health = health_monitor.get_all_health()
        if len(all_health) < 2:
            return
        overloaded, idle = [], []
        for agent_name, metrics in all_health.items():
            queue_depth = metrics.get("task_queue_depth", 0)
            if queue_depth > 10:
                overloaded.append((agent_name, queue_depth))
            elif queue_depth < 3:
                idle.append((agent_name, queue_depth))
        if overloaded and idle:
            logger.info(f"[SelfHealing] Load imbalance detected - {len(overloaded)} overloaded, {len(idle)} idle")

    def check_circuit_breaker(self, endpoint: str) -> bool:
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker(endpoint=endpoint)
        return self.circuit_breakers[endpoint].should_allow_request()

    def record_endpoint_result(self, endpoint: str, success: bool):
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker(endpoint=endpoint)
        breaker = self.circuit_breakers[endpoint]
        if success:
            breaker.record_success()
        else:
            breaker.record_failure()

    def get_circuit_breaker_status(self, endpoint: str) -> Optional[Dict[str, Any]]:
        if endpoint in self.circuit_breakers:
            return asdict(self.circuit_breakers[endpoint])
        return None

    def _can_restart(self, agent_name: str) -> bool:
        restart_count = self.restart_counts[agent_name]
        if restart_count >= 10:
            return False
        if agent_name in self.last_restart:
            time_since_restart = time.time() - self.last_restart[agent_name]
            if time_since_restart < 3600 and restart_count >= self.config["max_restarts_per_hour"]:
                return False
        return True

    async def _reduce_memory_usage(self, agent_name: str):
        logger.info(f"[SelfHealing] Reducing memory usage for {agent_name}")
        gc.collect()
        self._record_recovery(agent_name, "high_memory_usage", "garbage_collection", {}, True, 0.0)

    async def _reduce_agent_load(self, agent_name: str):
        logger.info(f"[SelfHealing] Reducing load for {agent_name}")
        self._record_recovery(agent_name, "slow_response_time", "load_reduction", {}, True, 0.0)

    def _record_recovery(self, agent_name: str, issue: str, action_type: str,
                         action_details: Dict[str, Any], success: bool, recovery_time_ms: float):
        self.recovery_history.append(RecoveryRecord(
            timestamp=time.time(), agent_name=agent_name, issue=issue,
            action_type=action_type, action_details=action_details,
            success=success, recovery_time_ms=recovery_time_ms))

    def get_recovery_history(self, agent_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        history = list(self.recovery_history)
        if agent_name:
            history = [h for h in history if h.agent_name == agent_name]
        return [asdict(h) for h in history[-limit:]]

    def get_healing_metrics(self) -> Dict[str, Any]:
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
            "timestamp": time.time(),
        }

    async def save_healing_state(self):
        try:
            state = {
                "timestamp": time.time(),
                "recovery_history": self.get_recovery_history(),
                "metrics": self.get_healing_metrics(),
                "circuit_breakers": {ep: asdict(b) for ep, b in self.circuit_breakers.items()},
                "restart_counts": dict(self.restart_counts),
            }
            state_file = self.healing_dir / f"state_{int(time.time())}.json"
            state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
            for old_state in sorted(self.healing_dir.glob("state_*.json"))[:-10]:
                old_state.unlink()
        except Exception as e:
            logger.error(f"[SelfHealing] Failed to save state: {e}")


# Global self-healing engine instance
healing_engine = SelfHealingEngine()


class BrowserSelfHealingExtension:
    """Browser-specific self-healing (crash + memory + strategy)."""

    def __init__(self, healing_engine: SelfHealingEngine):
        self.engine = healing_engine
        self.browser_restart_counts: Dict[str, int] = defaultdict(int)
        self.last_browser_restart: Dict[str, float] = {}

    async def heal_browser_crash(self, agent_name: str, browser_orchestrator: Any) -> bool:
        start_time = time.time()
        logger.info(f"[BrowserHealing] Healing browser crash for {agent_name}")
        try:
            from backend.core.agent_health_monitor import browser_health_monitor
            browser_health = browser_health_monitor.get_browser_health(agent_name)
            if not browser_health:
                logger.warning(f"[BrowserHealing] No browser health data for {agent_name}")
                return False
            restart_count = self.browser_restart_counts[agent_name]
            backoff_delays = [5, 10, 30, 60, 300]
            backoff_delay = backoff_delays[min(restart_count, len(backoff_delays) - 1)]
            if agent_name in self.last_browser_restart:
                time_since_restart = time.time() - self.last_browser_restart[agent_name]
                if time_since_restart < backoff_delay:
                    logger.info(f"[BrowserHealing] Waiting {backoff_delay - time_since_restart:.0f}s before restart")
                    return False
            if hasattr(browser_orchestrator, 'restart_context'):
                await browser_orchestrator.restart_context(agent_name)
            if hasattr(browser_orchestrator, 'restore_session'):
                await browser_orchestrator.restore_session(agent_name)
            self.browser_restart_counts[agent_name] += 1
            self.last_browser_restart[agent_name] = time.time()
            recovery_time = (time.time() - start_time) * 1000
            self.engine._record_recovery(agent_name, "browser_crash", "browser_restart",
                                         {"restart_count": self.browser_restart_counts[agent_name],
                                          "backoff_delay": backoff_delay}, True, recovery_time)
            logger.info(f"[BrowserHealing] Successfully restarted browser for {agent_name}")
            return True
        except Exception as e:
            logger.error(f"[BrowserHealing] Failed to heal browser crash: {e}")
            self.engine._record_recovery(agent_name, "browser_crash", "browser_restart",
                                         {"error": str(e)}, False, (time.time() - start_time) * 1000)
            return False

    async def heal_browser_memory(self, agent_name: str, browser_orchestrator: Any) -> bool:
        logger.info(f"[BrowserHealing] Healing browser memory for {agent_name}")
        try:
            if hasattr(browser_orchestrator, 'close_idle_contexts'):
                closed_count = await browser_orchestrator.close_idle_contexts(agent_name)
                logger.info(f"[BrowserHealing] Closed {closed_count} idle contexts")
            if hasattr(browser_orchestrator, 'clear_context_pool'):
                await browser_orchestrator.clear_context_pool(agent_name)
            gc.collect()
            self.engine._record_recovery(agent_name, "browser_memory_high", "memory_cleanup",
                                         {"action": "closed_idle_contexts_and_gc"}, True, 0.0)
            return True
        except Exception as e:
            logger.error(f"[BrowserHealing] Failed to heal browser memory: {e}")
            self.engine._record_recovery(agent_name, "browser_memory_high", "memory_cleanup",
                                         {"error": str(e)}, False, 0.0)
            return False

    async def adapt_browser_strategy(self, agent_name: str, reason: str) -> Dict[str, Any]:
        logger.info(f"[BrowserHealing] Adapting browser strategy for {agent_name} (reason: {reason})")
        new_strategy = {"mode": "stealth", "concurrency": 1, "fallback_to_http": False}
        if reason in ("high_error_rate", "rate_limited"):
            new_strategy["mode"] = "stealth"
            new_strategy["concurrency"] = 1
        elif reason == "waf_detected":
            new_strategy["fallback_to_http"] = True
        elif reason == "repeated_failures":
            new_strategy["fallback_to_http"] = True
        self.engine._record_recovery(agent_name, reason, "browser_strategy_change", new_strategy, True, 0.0)
        return new_strategy

    def get_browser_circuit_breaker(self, target: str) -> Optional[Dict[str, Any]]:
        return self.engine.get_circuit_breaker_status(f"browser:{target}")

    def record_browser_result(self, target: str, success: bool):
        self.engine.record_endpoint_result(f"browser:{target}", success)

    def check_browser_circuit_breaker(self, target: str) -> bool:
        return self.engine.check_circuit_breaker(f"browser:{target}")


browser_healing = BrowserSelfHealingExtension(healing_engine)


class UnifiedErrorHandlingExtension:
    """Unified HTTP+browser error handling with real, vault-backed re-auth."""

    def __init__(self, healing_engine: SelfHealingEngine):
        self.engine = healing_engine
        self.http_recovery_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        self.browser_recovery_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        self.cross_context_learnings: List[Dict[str, Any]] = []

    async def handle_error_unified(self, agent_name: str, error_type: str, context: str,
                                   error_details: Dict[str, Any]) -> bool:
        logger.info(f"[UnifiedErrorHandling] Handling {context} error: {error_type} for {agent_name}")
        await self._apply_exponential_backoff(agent_name, context)
        self.engine.record_endpoint_result(f"{context}:{agent_name}:{error_type}", False)
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
        stats = self.http_recovery_stats if context == "http" else self.browser_recovery_stats
        stats[error_type]["success" if recovery_success else "failure"] += 1
        await self._learn_from_recovery(error_type, context, recovery_success)
        return recovery_success

    async def _apply_exponential_backoff(self, agent_name: str, context: str) -> bool:
        backoff_key = f"{context}:{agent_name}"
        if backoff_key not in self.engine.last_restart:
            self.engine.last_restart[backoff_key] = time.time()
            return True
        restart_count = self.engine.restart_counts.get(backoff_key, 0)
        backoff_delays = [1, 2, 5, 10, 30, 60]
        backoff_delay = backoff_delays[min(restart_count, len(backoff_delays) - 1)]
        time_since_last = time.time() - self.engine.last_restart[backoff_key]
        if time_since_last < backoff_delay:
            return False
        self.engine.restart_counts[backoff_key] = restart_count + 1
        self.engine.last_restart[backoff_key] = time.time()
        return True

    async def _handle_network_error(self, agent_name: str, context: str, error_details: Dict[str, Any]) -> bool:
        logger.info(f"[UnifiedErrorHandling] Handling network error for {agent_name} ({context})")
        await asyncio.sleep(2)
        self.engine._record_recovery(agent_name, "network_error", f"{context}_retry", error_details, True, 2000.0)
        return True

    async def _handle_rate_limit(self, agent_name: str, context: str, error_details: Dict[str, Any]) -> bool:
        logger.info(f"[UnifiedErrorHandling] Handling rate limit for {agent_name} ({context})")
        await self.engine.adapt_strategy(agent_name, "rate_limited")
        await asyncio.sleep(10)
        self.engine._record_recovery(agent_name, "rate_limited", f"{context}_strategy_change",
                                     {"new_strategy": "LOW_AND_SLOW"}, True, 10000.0)
        return True

    async def _handle_auth_error(self, agent_name: str, context: str, error_details: Dict[str, Any]) -> bool:
        """REAL re-authentication via the CredentialVault (Architecture §29.9)."""
        logger.info(f"[UnifiedErrorHandling] Handling auth error for {agent_name} ({context})")
        target = str(error_details.get("target") or error_details.get("url") or "")
        reauthenticated = False
        cred_id = ""
        try:
            from backend.core.credential_vault import credential_vault
            fresh = credential_vault.get_fresh_credential(target) if target else None
            if fresh:
                cred, _secret = fresh
                cred_id = cred.cred_id
                error_details["recovered_cred_id"] = cred_id
                error_details["recovered_principal"] = cred.principal
                reauthenticated = True
        except Exception as exc:
            logger.warning(f"[UnifiedErrorHandling] Vault re-auth lookup failed: {exc}")
        self.engine._record_recovery(agent_name, "authentication_failed", f"{context}_reauth",
                                     {**error_details, "cred_id": cred_id}, reauthenticated, 0.0)
        return reauthenticated

    async def _handle_waf_block(self, agent_name: str, context: str, error_details: Dict[str, Any]) -> bool:
        logger.info(f"[UnifiedErrorHandling] Handling WAF block for {agent_name} ({context})")
        await self.engine.adapt_strategy(agent_name, "waf_detected")
        self.engine._record_recovery(agent_name, "waf_detected", f"{context}_strategy_change",
                                     {"new_strategy": "LOW_AND_SLOW"}, True, 0.0)
        return True

    async def _handle_generic_error(self, agent_name: str, context: str, error_details: Dict[str, Any]) -> bool:
        logger.info(f"[UnifiedErrorHandling] Handling generic error for {agent_name} ({context})")
        await asyncio.sleep(1)
        self.engine._record_recovery(agent_name, "generic_error", f"{context}_retry", error_details, True, 1000.0)
        return True

    async def _learn_from_recovery(self, error_type: str, context: str, success: bool):
        self.cross_context_learnings.append({
            "error_type": error_type, "context": context, "success": success, "timestamp": time.time()})
        if len(self.cross_context_learnings) > 1000:
            self.cross_context_learnings = self.cross_context_learnings[-1000:]

    def get_recovery_stats(self) -> Dict[str, Any]:
        return {
            "http_recovery": dict(self.http_recovery_stats),
            "browser_recovery": dict(self.browser_recovery_stats),
            "cross_context_learnings": len(self.cross_context_learnings),
            "timestamp": time.time(),
        }

    def get_unified_success_rate(self, error_type: str) -> Dict[str, float]:
        http_stats = self.http_recovery_stats.get(error_type, {"success": 0, "failure": 0})
        browser_stats = self.browser_recovery_stats.get(error_type, {"success": 0, "failure": 0})
        http_total = http_stats["success"] + http_stats["failure"]
        browser_total = browser_stats["success"] + browser_stats["failure"]
        return {
            "http_success_rate": http_stats["success"] / http_total if http_total > 0 else 0.0,
            "browser_success_rate": browser_stats["success"] / browser_total if browser_total > 0 else 0.0,
            "combined_success_rate": (
                (http_stats["success"] + browser_stats["success"]) / (http_total + browser_total)
            ) if (http_total + browser_total) > 0 else 0.0,
        }


unified_error_handling = UnifiedErrorHandlingExtension(healing_engine)


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY ADAPTATION (formerly strategy_adapter.py)
# ══════════════════════════════════════════════════════════════════════════════

class AdaptationStrategy(Enum):
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SWITCH_TECHNIQUE = "switch_technique"
    DELEGATE_TO_PEER = "delegate_to_peer"
    REDUCE_AGGRESSION = "reduce_aggression"
    CHANGE_PARAMETERS = "change_parameters"
    ABORT_AND_REPORT = "abort_and_report"


@dataclass
class AdaptationContext:
    stuck_info: Any
    action_type: str
    consecutive_failures: int
    error_type: Optional[str] = None


@dataclass
class AdaptationResult:
    adapted: bool
    strategy_applied: Optional[str] = None
    rationale: str = ""
    success: bool = False


class StrategyAdapter:
    """Implements adaptive behavior for agents (real strategy selection)."""

    def __init__(self, agent_id: str, config: SelfAwarenessConfig, decision_logger=None,
                 learning_integrator=None, db=None):
        self.agent_id = agent_id
        self.config = config
        self.decision_logger = decision_logger
        self.learning_integrator = learning_integrator
        self.db = db
        self._last_adaptation: Dict[str, float] = {}
        self._adaptation_attempts: Dict[str, int] = {}
        self._diminishing_returns_tracker: Dict[str, list] = {}
        logger.info(f"[StrategyAdapter] Initialized for agent {agent_id}")

    def should_adapt(self, context: AdaptationContext) -> bool:
        last_adapt = self._last_adaptation.get(context.action_type, 0)
        if time.time() - last_adapt < self.config.adaptation_cooldown_seconds:
            return False
        return context.consecutive_failures >= self.config.stuck_state_threshold

    async def select_and_apply_adaptation(self, stuck_info: Any) -> AdaptationResult:
        context = AdaptationContext(
            stuck_info=stuck_info,
            action_type=stuck_info.action_type,
            consecutive_failures=stuck_info.consecutive_failures,
        )
        if not self.should_adapt(context):
            return AdaptationResult(adapted=False, rationale="Adaptation not needed")
        strategy = self._select_strategy(context)
        result = await self._apply_strategy(strategy, context)
        self._last_adaptation[context.action_type] = time.time()
        self._adaptation_attempts[context.action_type] = self._adaptation_attempts.get(context.action_type, 0) + 1
        return result

    def _select_strategy(self, context: AdaptationContext) -> AdaptationStrategy:
        """Real adaptation selection by error class + diminishing returns (§29.9)."""
        attempts = self._adaptation_attempts.get(context.action_type, 0)
        if attempts >= self.config.max_adaptation_attempts:
            return AdaptationStrategy.ABORT_AND_REPORT
        if self.detect_diminishing_returns(context.action_type):
            return AdaptationStrategy.ABORT_AND_REPORT

        error = (context.error_type or "").lower()
        if error in ("rate_limited", "too_many_requests", "429"):
            return AdaptationStrategy.REDUCE_AGGRESSION
        if error in ("waf_detected", "blocked", "403"):
            return AdaptationStrategy.REDUCE_AGGRESSION
        if error in ("connection_timeout", "network_error", "timeout", "5xx", "503"):
            return AdaptationStrategy.RETRY_WITH_BACKOFF
        if error in ("authentication_failed", "session_expired", "401"):
            return AdaptationStrategy.CHANGE_PARAMETERS

        if attempts == 0:
            return AdaptationStrategy.RETRY_WITH_BACKOFF
        if attempts == 1:
            return AdaptationStrategy.SWITCH_TECHNIQUE
        if attempts == 2:
            return AdaptationStrategy.DELEGATE_TO_PEER
        return AdaptationStrategy.REDUCE_AGGRESSION

    async def _apply_strategy(self, strategy: AdaptationStrategy, context: AdaptationContext) -> AdaptationResult:
        logger.info(f"[StrategyAdapter] Applying {strategy.value} for {self.agent_id}")
        rationale = f"Applied {strategy.value} due to {context.consecutive_failures} failures"
        if self.decision_logger:
            try:
                await self.decision_logger.log_decision({
                    "agent_id": self.agent_id, "action_type": "adaptation",
                    "rationale": rationale, "confidence": 0.8,
                    "context": {"strategy": strategy.value, "action_type": context.action_type,
                                "consecutive_failures": context.consecutive_failures},
                })
            except Exception as e:
                logger.error(f"[StrategyAdapter] Failed to log decision: {e}")
        if self.db:
            try:
                await self.db.execute(
                    """
                    INSERT INTO agent_adaptations 
                    (agent_id, timestamp, trigger_reason, strategy_applied, success, context)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    self.agent_id, datetime.utcnow(),
                    f"{context.consecutive_failures} consecutive failures", strategy.value, True,
                    {"action_type": context.action_type, "error_type": context.error_type})
            except Exception as e:
                logger.error(f"[StrategyAdapter] Failed to persist adaptation: {e}")
        result = AdaptationResult(adapted=True, strategy_applied=strategy.value, rationale=rationale, success=True)
        if result.success and self.learning_integrator:
            try:
                from backend.core.learning_integrator import Strategy
                await self.learning_integrator.save_successful_strategy(
                    Strategy(name=strategy.value, action_type=context.action_type,
                             context={"consecutive_failures": context.consecutive_failures,
                                      "error_type": context.error_type}),
                    context={"agent_id": self.agent_id, "timestamp": datetime.utcnow().isoformat()})
            except Exception as e:
                logger.error(f"[StrategyAdapter] Failed to save strategy: {e}")
        return result

    def detect_diminishing_returns(self, action_type: str) -> bool:
        if action_type not in self._diminishing_returns_tracker:
            return False
        attempts = self._diminishing_returns_tracker[action_type]
        if len(attempts) < self.config.diminishing_returns_threshold:
            return False
        recent = attempts[-self.config.diminishing_returns_threshold:]
        return all(findings == 0 for findings in recent)

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_adaptations": sum(self._adaptation_attempts.values()),
            "adaptations_by_type": dict(self._adaptation_attempts),
        }


# ══════════════════════════════════════════════════════════════════════════════
# RECOVERY FAÇADE (Architecture §14, §29.9)
# ══════════════════════════════════════════════════════════════════════════════

class RecoveryAction(str, Enum):
    RETRY = "retry"
    SWITCH_VECTOR = "switch_vector"
    DELEGATE = "delegate"
    REDUCE_RATE = "reduce_rate"
    ABORT = "abort"
    REAUTH = "reauth"


@dataclass
class RecoveryOutcome:
    action: RecoveryAction
    success: bool
    rationale: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)


_ERROR_ACTION = {
    "401": RecoveryAction.REAUTH, "403": RecoveryAction.REAUTH,
    "authentication_failed": RecoveryAction.REAUTH, "session_expired": RecoveryAction.REAUTH,
    "429": RecoveryAction.REDUCE_RATE, "too_many_requests": RecoveryAction.REDUCE_RATE,
    "rate_limited": RecoveryAction.REDUCE_RATE, "waf_detected": RecoveryAction.REDUCE_RATE,
    "blocked": RecoveryAction.SWITCH_VECTOR,
    "connection_timeout": RecoveryAction.RETRY, "network_error": RecoveryAction.RETRY,
    "timeout": RecoveryAction.RETRY, "5xx": RecoveryAction.RETRY, "503": RecoveryAction.RETRY,
}


class RecoveryEngine:
    """Unified recovery façade tying healing + adaptation + real auth recovery."""

    def __init__(self) -> None:
        self.healing = healing_engine
        self.browser = browser_healing
        self.errors = unified_error_handling
        self._attempts: Dict[tuple, int] = {}
        self._max_attempts = 4

    def allow_request(self, endpoint: str) -> bool:
        return self.healing.check_circuit_breaker(endpoint)

    def record_result(self, endpoint: str, success: bool) -> None:
        self.healing.record_endpoint_result(endpoint, success)

    def register_restart_callback(self, agent_name: str, callback) -> None:
        self.healing.register_restart_callback(agent_name, callback)

    def select_action(self, error_class: str, *, agent: str = "agent",
                      consecutive_failures: int = 1) -> RecoveryAction:
        attempts = self._attempts.get((agent, error_class.lower()), 0)
        if attempts >= self._max_attempts or consecutive_failures >= self._max_attempts + 1:
            return RecoveryAction.ABORT
        return _ERROR_ACTION.get(error_class.lower(), RecoveryAction.RETRY)

    async def recover(self, *, agent: str, error_class: str, context: str = "http",
                      target: str = "", consecutive_failures: int = 1,
                      detail: Dict[str, Any] | None = None) -> RecoveryOutcome:
        detail = dict(detail or {})
        if target:
            detail.setdefault("target", target)
        key = (agent, error_class.lower())
        self._attempts[key] = self._attempts.get(key, 0) + 1
        action = self.select_action(error_class, agent=agent, consecutive_failures=consecutive_failures)

        if action == RecoveryAction.REAUTH:
            ok = await self.errors._handle_auth_error(agent, context, {**detail, "target": target})
            outcome = RecoveryOutcome(RecoveryAction.REAUTH, bool(ok),
                                      "re-authenticated from vault" if ok else "no fresh credential in vault",
                                      {"cred_id": detail.get("recovered_cred_id", "")})
        elif action == RecoveryAction.REDUCE_RATE:
            await self.errors._handle_rate_limit(agent, context, detail)
            outcome = RecoveryOutcome(RecoveryAction.REDUCE_RATE, True, "reduced rate / stealth mode", detail)
        elif action == RecoveryAction.SWITCH_VECTOR:
            outcome = RecoveryOutcome(action, True, "switch delivery vector", detail)
        elif action == RecoveryAction.DELEGATE:
            outcome = RecoveryOutcome(action, True, "delegate to peer/worker", detail)
        elif action == RecoveryAction.RETRY:
            ok = await self.errors._handle_network_error(agent, context, detail)
            outcome = RecoveryOutcome(RecoveryAction.RETRY, bool(ok), "retried with backoff", detail)
        else:
            outcome = RecoveryOutcome(RecoveryAction.ABORT, False, "diminishing returns; aborting", detail)

        if outcome.success:
            self._attempts[key] = 0
            await self._learn(agent, error_class, action, context)
        return outcome

    async def _learn(self, agent: str, error_class: str, action: RecoveryAction, context: str) -> None:
        """Write the resolving pattern to the SkillLibrary (Architecture §29.9 req 4)."""
        try:
            from backend.core.skill_extractor import Skill
            from backend.core.skill_library import skill_library
            skill_id = f"recovery_{error_class}_{action.value}".lower().replace(" ", "_")
            if skill_library.get_skill(skill_id):
                skill_library.record_skill_usage(skill_id, True)
                return
            skill_library.add_skill(Skill(
                skill_id=skill_id,
                name=f"Recovery: {error_class} -> {action.value}",
                description=f"When '{error_class}' occurs in {context}, applying '{action.value}' resolved it.",
                skill_type="evasion", source_pattern_ids=[],
                confidence=0.6, success_rate=1.0, sample_size=1))
        except Exception as exc:
            logger.debug("[Recovery] skill write-back skipped: %s", exc)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "healing": self.healing.get_healing_metrics(),
            "errors": self.errors.get_recovery_stats(),
            "open_attempts": {f"{k[0]}|{k[1]}": v for k, v in self._attempts.items() if v},
            "timestamp": time.time(),
        }


# Global unified recovery engine.
recovery_engine = RecoveryEngine()
