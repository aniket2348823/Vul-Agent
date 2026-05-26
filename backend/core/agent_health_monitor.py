"""
AGENT HEALTH MONITOR
Tracks real-time health metrics for all agents in the hive.

This monitor:
1. Tracks performance metrics (response time, success rate, error rate)
2. Monitors resource usage (memory, CPU, task queue depth)
3. Detects anomalies (sudden performance drops, crashes)
4. Calculates health scores (0-100 scale)
5. Provides historical health trends
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from collections import deque
from pathlib import Path
import json

logger = logging.getLogger("AgentHealthMonitor")


@dataclass
class HealthMetrics:
    """Health metrics for a single agent."""
    agent_name: str
    timestamp: float
    
    # Performance metrics
    response_time_ms: float = 0.0
    success_rate: float = 1.0
    error_rate: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    
    # Resource metrics
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    task_queue_depth: int = 0
    
    # Status
    is_active: bool = True
    last_heartbeat: float = 0.0
    consecutive_failures: int = 0
    
    # Health score (0-100)
    health_score: float = 100.0
    
    def calculate_health_score(self) -> float:
        """Calculate overall health score based on metrics."""
        score = 100.0
        
        # Penalize high error rate (max -40 points)
        if self.error_rate > 0:
            score -= min(40, self.error_rate * 100)
        
        # Penalize slow response time (max -20 points)
        if self.response_time_ms > 1000:
            score -= min(20, (self.response_time_ms - 1000) / 100)
        
        # Penalize high memory usage (max -15 points)
        if self.memory_mb > 500:
            score -= min(15, (self.memory_mb - 500) / 50)
        
        # Penalize high CPU usage (max -15 points)
        if self.cpu_percent > 80:
            score -= min(15, (self.cpu_percent - 80) / 2)
        
        # Penalize consecutive failures (max -10 points)
        score -= min(10, self.consecutive_failures * 2)
        
        self.health_score = max(0.0, score)
        return self.health_score


@dataclass
class BrowserHealthMetrics:
    """Browser-specific health metrics."""
    agent_name: str
    timestamp: float
    active_contexts: int = 0
    context_memory_mb: float = 0.0
    page_load_time_ms: float = 0.0
    screenshot_time_ms: float = 0.0
    browser_error_rate: float = 0.0
    browser_health_score: float = 100.0
    
    def calculate_browser_health_score(self) -> float:
        """Calculate browser-specific health score."""
        score = 100.0
        
        # Penalize too many contexts (max -30 points)
        if self.active_contexts > 10:
            score -= min(30, (self.active_contexts - 10) * 3)
        
        # Penalize high memory usage (max -25 points)
        if self.context_memory_mb > 1000:
            score -= min(25, (self.context_memory_mb - 1000) / 40)
        
        # Penalize slow page loads (max -20 points)
        if self.page_load_time_ms > 3000:
            score -= min(20, (self.page_load_time_ms - 3000) / 200)
        
        # Penalize high error rate (max -25 points)
        if self.browser_error_rate > 0:
            score -= min(25, self.browser_error_rate * 100)
        
        self.browser_health_score = max(0.0, score)
        return self.browser_health_score


@dataclass
class HealthAlert:
    """Alert for health issues."""
    agent_name: str
    severity: str  # "warning", "critical"
    issue: str
    timestamp: float
    metrics: Dict[str, Any]


class AgentHealthMonitor:
    """
    Monitors health of all agents in the hive.
    Detects issues and triggers alerts for self-healing.
    """
    
    def __init__(self, brain_dir: str = "brain"):
        self.brain_dir = Path(brain_dir)
        self.health_dir = self.brain_dir / "health"
        self.health_dir.mkdir(parents=True, exist_ok=True)
        
        # Current health metrics per agent
        self.current_metrics: Dict[str, HealthMetrics] = {}
        
        # Browser health metrics per agent
        self.browser_metrics: Dict[str, BrowserHealthMetrics] = {}
        
        # Historical metrics (last 100 per agent)
        self.history: Dict[str, deque] = {}
        self.browser_history: Dict[str, deque] = {}
        
        # Active alerts
        self.alerts: List[HealthAlert] = []
        
        # Thresholds for alerts
        self.thresholds = {
            "error_rate_warning": 0.1,  # 10% error rate
            "error_rate_critical": 0.3,  # 30% error rate
            "response_time_warning": 2000,  # 2 seconds
            "response_time_critical": 5000,  # 5 seconds
            "memory_warning": 500,  # 500 MB
            "memory_critical": 1000,  # 1 GB
            "health_score_warning": 70,
            "health_score_critical": 40,
            "heartbeat_timeout": 30,  # 30 seconds
        }
        
        # Process handle for resource monitoring
        self.process = psutil.Process()
    
    def report_metrics(self, agent_name: str, metrics: Dict[str, Any]):
        """
        Report metrics from an agent.
        Called by agents periodically.
        """
        current_time = time.time()
        
        # Get or create metrics
        if agent_name not in self.current_metrics:
            self.current_metrics[agent_name] = HealthMetrics(
                agent_name=agent_name,
                timestamp=current_time,
                last_heartbeat=current_time
            )
            self.history[agent_name] = deque(maxlen=100)
        
        agent_metrics = self.current_metrics[agent_name]
        
        # Update metrics
        agent_metrics.timestamp = current_time
        agent_metrics.last_heartbeat = current_time
        
        if "response_time_ms" in metrics:
            agent_metrics.response_time_ms = metrics["response_time_ms"]
        
        if "success" in metrics:
            if metrics["success"]:
                agent_metrics.tasks_completed += 1
                agent_metrics.consecutive_failures = 0
            else:
                agent_metrics.tasks_failed += 1
                agent_metrics.consecutive_failures += 1
        
        if "memory_mb" in metrics:
            agent_metrics.memory_mb = metrics["memory_mb"]
        
        if "cpu_percent" in metrics:
            agent_metrics.cpu_percent = metrics["cpu_percent"]
        
        if "task_queue_depth" in metrics:
            agent_metrics.task_queue_depth = metrics["task_queue_depth"]
        
        # Calculate rates
        total_tasks = agent_metrics.tasks_completed + agent_metrics.tasks_failed
        if total_tasks > 0:
            agent_metrics.success_rate = agent_metrics.tasks_completed / total_tasks
            agent_metrics.error_rate = agent_metrics.tasks_failed / total_tasks
        
        # Calculate health score
        agent_metrics.calculate_health_score()
        
        # Store in history
        self.history[agent_name].append(asdict(agent_metrics))
        
        # Check for alerts
        self._check_alerts(agent_name, agent_metrics)
    
    def report_heartbeat(self, agent_name: str):
        """Report heartbeat from agent (still alive)."""
        current_time = time.time()
        
        # Create metrics if they don't exist
        if agent_name not in self.current_metrics:
            self.current_metrics[agent_name] = HealthMetrics(
                agent_name=agent_name,
                timestamp=current_time,
                last_heartbeat=current_time
            )
            self.history[agent_name] = deque(maxlen=100)
        
        # Update heartbeat
        self.current_metrics[agent_name].last_heartbeat = current_time
        self.current_metrics[agent_name].is_active = True
    
    def _check_alerts(self, agent_name: str, metrics: HealthMetrics):
        """Check if metrics trigger any alerts."""
        current_time = time.time()
        
        # Check error rate
        if metrics.error_rate >= self.thresholds["error_rate_critical"]:
            self._create_alert(
                agent_name,
                "critical",
                f"Critical error rate: {metrics.error_rate:.1%}",
                {"error_rate": metrics.error_rate}
            )
        elif metrics.error_rate >= self.thresholds["error_rate_warning"]:
            self._create_alert(
                agent_name,
                "warning",
                f"High error rate: {metrics.error_rate:.1%}",
                {"error_rate": metrics.error_rate}
            )
        
        # Check response time
        if metrics.response_time_ms >= self.thresholds["response_time_critical"]:
            self._create_alert(
                agent_name,
                "critical",
                f"Critical response time: {metrics.response_time_ms:.0f}ms",
                {"response_time_ms": metrics.response_time_ms}
            )
        elif metrics.response_time_ms >= self.thresholds["response_time_warning"]:
            self._create_alert(
                agent_name,
                "warning",
                f"Slow response time: {metrics.response_time_ms:.0f}ms",
                {"response_time_ms": metrics.response_time_ms}
            )
        
        # Check memory usage
        if metrics.memory_mb >= self.thresholds["memory_critical"]:
            self._create_alert(
                agent_name,
                "critical",
                f"Critical memory usage: {metrics.memory_mb:.0f}MB",
                {"memory_mb": metrics.memory_mb}
            )
        elif metrics.memory_mb >= self.thresholds["memory_warning"]:
            self._create_alert(
                agent_name,
                "warning",
                f"High memory usage: {metrics.memory_mb:.0f}MB",
                {"memory_mb": metrics.memory_mb}
            )
        
        # Check health score
        if metrics.health_score <= self.thresholds["health_score_critical"]:
            self._create_alert(
                agent_name,
                "critical",
                f"Critical health score: {metrics.health_score:.0f}/100",
                {"health_score": metrics.health_score}
            )
        elif metrics.health_score <= self.thresholds["health_score_warning"]:
            self._create_alert(
                agent_name,
                "warning",
                f"Low health score: {metrics.health_score:.0f}/100",
                {"health_score": metrics.health_score}
            )
        
        # Check consecutive failures
        if metrics.consecutive_failures >= 5:
            self._create_alert(
                agent_name,
                "critical",
                f"Agent failing repeatedly: {metrics.consecutive_failures} consecutive failures",
                {"consecutive_failures": metrics.consecutive_failures}
            )
    
    def _create_alert(self, agent_name: str, severity: str, issue: str, metrics: Dict[str, Any]):
        """Create a new alert."""
        alert = HealthAlert(
            agent_name=agent_name,
            severity=severity,
            issue=issue,
            timestamp=time.time(),
            metrics=metrics
        )
        
        # Avoid duplicate alerts (same issue within 60 seconds)
        recent_alerts = [
            a for a in self.alerts
            if a.agent_name == agent_name and
            a.issue == issue and
            time.time() - a.timestamp < 60
        ]
        
        if not recent_alerts:
            self.alerts.append(alert)
            logger.warning(f"[HealthMonitor] {severity.upper()}: {agent_name} - {issue}")
    
    def check_heartbeats(self) -> List[str]:
        """
        Check for agents that haven't sent heartbeat recently.
        Returns list of potentially crashed agents.
        """
        current_time = time.time()
        timeout = self.thresholds["heartbeat_timeout"]
        crashed_agents = []
        
        for agent_name, metrics in self.current_metrics.items():
            if metrics.is_active:
                time_since_heartbeat = current_time - metrics.last_heartbeat
                if time_since_heartbeat > timeout:
                    metrics.is_active = False
                    crashed_agents.append(agent_name)
                    self._create_alert(
                        agent_name,
                        "critical",
                        f"Agent unresponsive for {time_since_heartbeat:.0f}s",
                        {"time_since_heartbeat": time_since_heartbeat}
                    )
        
        return crashed_agents
    
    def get_agent_health(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get current health metrics for an agent."""
        if agent_name in self.current_metrics:
            return asdict(self.current_metrics[agent_name])
        return None
    
    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health metrics for all agents."""
        return {
            name: asdict(metrics)
            for name, metrics in self.current_metrics.items()
        }
    
    def get_agent_history(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get historical metrics for an agent."""
        if agent_name in self.history:
            history_list = list(self.history[agent_name])
            return history_list[-limit:]
        return []
    
    def get_alerts(self, severity: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        alerts = self.alerts[-limit:]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return [asdict(a) for a in alerts]
    
    def clear_alerts(self, agent_name: Optional[str] = None):
        """Clear alerts for an agent or all alerts."""
        if agent_name:
            self.alerts = [a for a in self.alerts if a.agent_name != agent_name]
        else:
            self.alerts = []
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        if not self.current_metrics:
            return {
                "total_agents": 0,
                "active_agents": 0,
                "avg_health_score": 0.0,
                "critical_alerts": 0,
                "warning_alerts": 0
            }
        
        active_agents = sum(1 for m in self.current_metrics.values() if m.is_active)
        avg_health = sum(m.health_score for m in self.current_metrics.values()) / len(self.current_metrics)
        
        critical_alerts = sum(1 for a in self.alerts if a.severity == "critical")
        warning_alerts = sum(1 for a in self.alerts if a.severity == "warning")
        
        return {
            "total_agents": len(self.current_metrics),
            "active_agents": active_agents,
            "avg_health_score": round(avg_health, 1),
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "timestamp": time.time()
        }
    
    async def save_health_snapshot(self):
        """Save current health state to disk."""
        try:
            snapshot = {
                "timestamp": time.time(),
                "metrics": self.get_all_health(),
                "alerts": self.get_alerts(),
                "summary": self.get_system_health_summary()
            }
            
            snapshot_file = self.health_dir / f"snapshot_{int(time.time())}.json"
            snapshot_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            
            # Keep only last 10 snapshots
            snapshots = sorted(self.health_dir.glob("snapshot_*.json"))
            for old_snapshot in snapshots[:-10]:
                old_snapshot.unlink()
                
        except Exception as e:
            logger.error(f"[HealthMonitor] Failed to save snapshot: {e}")


# Global health monitor instance
health_monitor = AgentHealthMonitor()


# ============================================================================
# BROWSER HEALTH MONITOR EXTENSION
# ============================================================================

class BrowserHealthMonitorExtension:
    """Extension for browser-specific health monitoring"""
    
    def __init__(self, health_monitor: AgentHealthMonitor):
        self.monitor = health_monitor
    
    def report_browser_metrics(
        self,
        agent_name: str,
        metrics: Dict[str, Any]
    ):
        """
        Report browser-specific metrics from an agent.
        """
        current_time = time.time()
        
        # Get or create browser metrics
        if agent_name not in self.monitor.browser_metrics:
            self.monitor.browser_metrics[agent_name] = BrowserHealthMetrics(
                agent_name=agent_name,
                timestamp=current_time
            )
            self.monitor.browser_history[agent_name] = deque(maxlen=100)
        
        browser_metrics = self.monitor.browser_metrics[agent_name]
        
        # Update metrics
        browser_metrics.timestamp = current_time
        
        if "active_contexts" in metrics:
            browser_metrics.active_contexts = metrics["active_contexts"]
        
        if "context_memory_mb" in metrics:
            browser_metrics.context_memory_mb = metrics["context_memory_mb"]
        
        if "page_load_time_ms" in metrics:
            browser_metrics.page_load_time_ms = metrics["page_load_time_ms"]
        
        if "screenshot_time_ms" in metrics:
            browser_metrics.screenshot_time_ms = metrics["screenshot_time_ms"]
        
        if "browser_error_rate" in metrics:
            browser_metrics.browser_error_rate = metrics["browser_error_rate"]
        
        # Calculate browser health score
        browser_metrics.calculate_browser_health_score()
        
        # Store in history
        self.monitor.browser_history[agent_name].append(asdict(browser_metrics))
        
        # Check if browser operations impact system health
        if browser_metrics.browser_health_score < 40:
            self._create_browser_alert(
                agent_name,
                "critical",
                f"Critical browser health: {browser_metrics.browser_health_score:.0f}/100",
                asdict(browser_metrics)
            )
        elif browser_metrics.browser_health_score < 70:
            self._create_browser_alert(
                agent_name,
                "warning",
                f"Low browser health: {browser_metrics.browser_health_score:.0f}/100",
                asdict(browser_metrics)
            )
        
        # Alert on high memory usage
        if browser_metrics.context_memory_mb > 1000:
            self._create_browser_alert(
                agent_name,
                "critical",
                f"High browser memory usage: {browser_metrics.context_memory_mb:.0f}MB",
                {"context_memory_mb": browser_metrics.context_memory_mb}
            )
        
        # Alert on too many contexts
        if browser_metrics.active_contexts > 15:
            self._create_browser_alert(
                agent_name,
                "warning",
                f"Too many browser contexts: {browser_metrics.active_contexts}",
                {"active_contexts": browser_metrics.active_contexts}
            )
    
    def get_browser_health(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get current browser health metrics for an agent."""
        if agent_name in self.monitor.browser_metrics:
            return asdict(self.monitor.browser_metrics[agent_name])
        return None
    
    def calculate_browser_health_score(self, agent_name: str) -> float:
        """Calculate browser health score for an agent."""
        if agent_name in self.monitor.browser_metrics:
            return self.monitor.browser_metrics[agent_name].calculate_browser_health_score()
        return 100.0
    
    def _create_browser_alert(
        self,
        agent_name: str,
        severity: str,
        issue: str,
        metrics: Dict[str, Any]
    ):
        """Create a browser-specific alert."""
        alert = HealthAlert(
            agent_name=agent_name,
            severity=severity,
            issue=issue,
            timestamp=time.time(),
            metrics=metrics
        )
        
        # Avoid duplicate alerts
        recent_alerts = [
            a for a in self.monitor.alerts
            if a.agent_name == agent_name and
            a.issue == issue and
            time.time() - a.timestamp < 60
        ]
        
        if not recent_alerts:
            self.monitor.alerts.append(alert)
            logger.warning(f"[BrowserHealth] {severity.upper()}: {agent_name} - {issue}")
    
    def get_all_browser_health(self) -> Dict[str, Dict[str, Any]]:
        """Get browser health metrics for all agents."""
        return {
            name: asdict(metrics)
            for name, metrics in self.monitor.browser_metrics.items()
        }
    
    def get_browser_health_summary(self) -> Dict[str, Any]:
        """Get overall browser health summary."""
        if not self.monitor.browser_metrics:
            return {
                "total_agents_with_browser": 0,
                "total_active_contexts": 0,
                "total_browser_memory_mb": 0.0,
                "avg_browser_health_score": 0.0,
                "browser_alerts": 0
            }
        
        total_contexts = sum(m.active_contexts for m in self.monitor.browser_metrics.values())
        total_memory = sum(m.context_memory_mb for m in self.monitor.browser_metrics.values())
        avg_health = sum(m.browser_health_score for m in self.monitor.browser_metrics.values()) / len(self.monitor.browser_metrics)
        
        browser_alerts = sum(
            1 for a in self.monitor.alerts
            if "browser" in a.issue.lower() or "context" in a.issue.lower()
        )
        
        return {
            "total_agents_with_browser": len(self.monitor.browser_metrics),
            "total_active_contexts": total_contexts,
            "total_browser_memory_mb": round(total_memory, 1),
            "avg_browser_health_score": round(avg_health, 1),
            "browser_alerts": browser_alerts,
            "timestamp": time.time()
        }


# Create global browser health monitor extension
browser_health_monitor = BrowserHealthMonitorExtension(health_monitor)
