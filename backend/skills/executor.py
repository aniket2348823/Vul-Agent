"""
Skill runtime executor (Architecture §5.3.4, §5.3.3)
================================================================================
Every skill execution produces the structured output contract from §5.3.4 and
passes the same scope/approval/budget/evidence controls as every other
capability. This executor does NOT run arbitrary code; it orchestrates a skill's
declared tool runs through the governed Terminal Engine and records evidence.

Skill runtime contract (Architecture §5.3.4):
{
  "skill_id", "agent", "risk_class", "scope_decision", "approval_id",
  "inputs", "tool_runs", "evidence_ids", "findings", "confidence",
  "recommendations", "next_actions"
}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.core.iteration_budget import IterationBudget, budget_config
from backend.core.scope import ScopePolicy, ScopeViolation, scope_guard
from backend.skills.catalog import SkillMeta, skill_catalog
from backend.skills.policy import PromotionState, RiskClass, can_auto_execute, is_disabled, requires_approval

logger = logging.getLogger("vigilagent.skills.executor")


@dataclass
class SkillRunResult:
    """Structured skill runtime output (Architecture §5.3.4)."""
    skill_id: str
    agent: str
    risk_class: str
    scope_decision: str                       # allowed | blocked | needs_approval | disabled
    approval_id: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    tool_runs: list[dict] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "agent": self.agent,
            "risk_class": self.risk_class,
            "scope_decision": self.scope_decision,
            "approval_id": self.approval_id,
            "inputs": self.inputs,
            "tool_runs": self.tool_runs,
            "evidence_ids": self.evidence_ids,
            "findings": self.findings,
            "confidence": self.confidence,
            "recommendations": self.recommendations,
            "next_actions": self.next_actions,
            "error": self.error,
        }


class SkillExecutor:
    """Executes a catalog skill under scope/approval/budget controls."""

    def __init__(self, scope: ScopePolicy | None = None) -> None:
        self.scope = scope or scope_guard

    async def execute(
        self,
        skill_id: str,
        *,
        agent: str,
        scan_id: str = "GLOBAL",
        target: str = "",
        inputs: dict[str, Any] | None = None,
        budget: IterationBudget | None = None,
        approval_id: str = "",
    ) -> SkillRunResult:
        meta: Optional[SkillMeta] = skill_catalog.get(skill_id)
        if not meta:
            return SkillRunResult(skill_id, agent, "unknown", "blocked",
                                  error=f"skill not found: {skill_id}")

        risk = meta.risk_class
        result = SkillRunResult(
            skill_id=skill_id, agent=agent, risk_class=risk.value,
            scope_decision="allowed", approval_id=approval_id, inputs=inputs or {},
        )

        # 1. Disabled risk classes never run (Architecture §5.3.3, §9).
        if is_disabled(risk):
            result.scope_decision = "disabled"
            result.error = "skill risk class is disabled_by_default"
            return result

        # 2. Approval gate for intrusive skills (Architecture §9).
        if requires_approval(risk) and not approval_id:
            result.scope_decision = "needs_approval"
            result.error = "intrusive skill requires an approval ticket"
            return result

        # 3. Promotion/auto-execute gate for generated skills (Architecture §13.2).
        if meta.promotion_state != PromotionState.ACTIVE and not approval_id:
            if not can_auto_execute(risk, meta.promotion_state):
                result.scope_decision = "needs_approval"
                result.error = f"skill promotion state '{meta.promotion_state.value}' not auto-executable"
                return result

        # 4. Scope check for network-touching skills (Architecture §9, §29.14).
        if meta.requires_network and target:
            action = "validate" if risk in (RiskClass.CONTROLLED_VALIDATION,
                                             RiskClass.INTRUSIVE_VALIDATION) else "recon"
            try:
                self.scope.assert_allowed(target, action=action)
            except ScopeViolation as exc:
                result.scope_decision = "blocked"
                result.error = f"scope: {exc}"
                return result

        # 5. Budget consume (Architecture §5, §29.3).
        budget = budget or budget_config.make("skill_run", label=f"skill:{skill_id}")
        if not budget.consume(1):
            result.scope_decision = "blocked"
            result.error = "skill_run budget exhausted"
            return result

        # The catalog skill is a playbook reference. Concrete tool execution is
        # delegated to the requesting agent through the governed TerminalEngine /
        # payload delivery paths; here we return the prepared, authorized plan so
        # the agent can run the declared tools with full evidence capture.
        result.recommendations = [
            f"Run via {agent} using tools: {', '.join(meta.required_tools) or 'agent-native'}",
            f"Domain={meta.domain}, attack={meta.attack or 'n/a'}",
        ]
        result.next_actions = [f"execute_tool:{t}" for t in meta.required_tools]
        result.confidence = 0.5
        logger.info("[SkillExecutor] %s authorized for %s (risk=%s, scope=%s)",
                    skill_id, agent, risk.value, result.scope_decision)
        return result


# Global executor.
skill_executor = SkillExecutor()
