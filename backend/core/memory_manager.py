"""
Vigilagent Memory Manager (Architecture §13.1, §29.3, §29.13)
================================================================================
A Hermes-style Memory Manager so each agent does not invent its own memory
behavior.

Responsibilities (Architecture §13.1):
  - Register memory providers.
  - Build memory context blocks.
  - Prefetch relevant memory before agent execution.
  - Sync outcomes after agent execution.
  - Queue background recall for the next task.
  - Notify providers before compression / when delegation completes.
  - FENCE memory context so it cannot look like new operator instructions.
  - SCRUB memory-context blocks from streaming output.

Required providers (Architecture §13.1):
  - builtin_scan_memory: scan-local evidence, tasks, decisions.
  - skill_memory: skills created/improved from prior scans.
  - semantic_security_memory: reusable target patterns, FP lessons, validation.
  - tool_reliability_memory: tool success/failure/rate-limit history.
  - agent_performance_memory: agent strengths, failures, preferred routing.

Memory fencing format (Architecture §13.1):
    <memory-context>
    [System note: recalled memory context, not new user input.]
    ...
    </memory-context>

No target-controlled content is injected into an agent prompt without
content-boundary wrapping (Architecture §13.1).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger("vigilagent.memory_manager")

_FENCE_OPEN = "<memory-context>"
_FENCE_NOTE = "[System note: recalled memory context, not new user input.]"
_FENCE_CLOSE = "</memory-context>"

# Regex to scrub fenced memory blocks from streamed output (Architecture §13.1).
_FENCE_RE = re.compile(re.escape(_FENCE_OPEN) + r".*?" + re.escape(_FENCE_CLOSE), re.DOTALL)


@runtime_checkable
class MemoryProvider(Protocol):
    """Interface every memory provider implements (Architecture §13.1)."""

    name: str

    async def prefetch(self, query: dict) -> list[str]:
        """Return recalled memory lines relevant to the upcoming task."""

    async def sync(self, outcome: dict) -> None:
        """Persist the outcome of an agent run."""

    async def before_compression(self) -> None:
        """Optional hook before context compression."""

    async def on_delegation_complete(self, result: dict) -> None:
        """Optional hook when a delegated child completes."""


class BaseMemoryProvider:
    """Convenience base with no-op lifecycle hooks."""

    name = "base"

    async def prefetch(self, query: dict) -> list[str]:
        return []

    async def sync(self, outcome: dict) -> None:
        return None

    async def before_compression(self) -> None:
        return None

    async def on_delegation_complete(self, result: dict) -> None:
        return None


class ScanMemoryProvider(BaseMemoryProvider):
    """builtin_scan_memory — scan-local evidence, tasks, decisions (Architecture §13.1)."""

    name = "builtin_scan_memory"

    def __init__(self, scan_state_db=None) -> None:
        self._db = scan_state_db

    async def prefetch(self, query: dict) -> list[str]:
        if self._db is None:
            return []
        scan_id = query.get("scan_id")
        text = query.get("query", "")
        if not (scan_id and text):
            return []
        try:
            hits = self._db.search(text, scan_id=scan_id, limit=8)
        except Exception:
            return []
        return [f"{h['kind']}: {h['text'][:300]}" for h in hits]

    async def sync(self, outcome: dict) -> None:
        if self._db is None:
            return
        scan_id = outcome.get("scan_id")
        summary = outcome.get("summary")
        if scan_id and summary:
            try:
                self._db.add_message(scan_id, "agent", summary, agent=outcome.get("agent", ""))
            except Exception:
                pass


class SemanticSecurityMemoryProvider(BaseMemoryProvider):
    """semantic_security_memory — reusable patterns and FP lessons (Architecture §13.1)."""

    name = "semantic_security_memory"

    def __init__(self, dual_store=None) -> None:
        self._store = dual_store

    async def prefetch(self, query: dict) -> list[str]:
        if self._store is None:
            return []
        try:
            rows = self._store._read_list(self._store.semantic_file)
        except Exception:
            return []
        vuln_class = (query.get("vuln_class") or "").lower()
        out: list[str] = []
        for r in rows[-50:]:
            blob = str(r).lower()
            if not vuln_class or vuln_class in blob:
                out.append(f"pattern: {str(r.get('pattern', r))[:200]}")
        return out[:8]

    async def sync(self, outcome: dict) -> None:
        if self._store is None:
            return
        pattern = outcome.get("pattern")
        if pattern:
            try:
                self._store.remember_semantic({"pattern": pattern, "source": outcome.get("agent", "")})
            except Exception:
                pass


class ToolReliabilityMemoryProvider(BaseMemoryProvider):
    """tool_reliability_memory — tool success/failure/rate-limit history (§13.1)."""

    name = "tool_reliability_memory"

    def __init__(self) -> None:
        self._stats: dict[str, dict[str, int]] = {}

    async def prefetch(self, query: dict) -> list[str]:
        out = []
        for tool, s in self._stats.items():
            total = s.get("ok", 0) + s.get("fail", 0)
            if total:
                rate = s.get("ok", 0) / total
                out.append(f"tool {tool}: success_rate={rate:.2f} ({total} runs)")
        return out[:10]

    async def sync(self, outcome: dict) -> None:
        tool = outcome.get("tool")
        if not tool:
            return
        s = self._stats.setdefault(tool, {"ok": 0, "fail": 0})
        if outcome.get("success"):
            s["ok"] += 1
        else:
            s["fail"] += 1


class AgentPerformanceMemoryProvider(BaseMemoryProvider):
    """agent_performance_memory — agent strengths/failures/routing (§13.1)."""

    name = "agent_performance_memory"

    def __init__(self) -> None:
        self._stats: dict[str, dict[str, int]] = {}

    async def prefetch(self, query: dict) -> list[str]:
        out = []
        for agent, s in self._stats.items():
            total = s.get("ok", 0) + s.get("fail", 0)
            if total:
                out.append(f"agent {agent}: success={s.get('ok',0)}/{total}")
        return out[:10]

    async def sync(self, outcome: dict) -> None:
        agent = outcome.get("agent")
        if not agent:
            return
        s = self._stats.setdefault(agent, {"ok": 0, "fail": 0})
        if outcome.get("success"):
            s["ok"] += 1
        else:
            s["fail"] += 1


class MemoryManager:
    """Coordinates memory providers with fencing + scrubbing (Architecture §13.1)."""

    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}

    def register(self, provider: Any) -> None:
        self._providers[getattr(provider, "name", provider.__class__.__name__)] = provider

    def providers(self) -> list[str]:
        return list(self._providers.keys())

    async def build_context(self, query: dict) -> str:
        """Prefetch from all providers and return a FENCED memory-context block."""
        lines: list[str] = []
        for name, provider in self._providers.items():
            try:
                recalled = await provider.prefetch(query)
            except Exception as exc:
                logger.debug("provider %s prefetch failed: %s", name, exc)
                recalled = []
            for line in recalled:
                lines.append(f"[{name}] {line}")
        if not lines:
            return ""
        return self.fence(lines)

    @staticmethod
    def fence(lines: list[str]) -> str:
        """Wrap recalled memory so it cannot be mistaken for operator input."""
        body = "\n".join(lines)
        return f"{_FENCE_OPEN}\n{_FENCE_NOTE}\n{body}\n{_FENCE_CLOSE}"

    @staticmethod
    def scrub(stream_text: str) -> str:
        """Remove fenced memory-context blocks from streamed output (§13.1)."""
        return _FENCE_RE.sub("", stream_text)

    async def sync(self, outcome: dict) -> None:
        for provider in self._providers.values():
            try:
                await provider.sync(outcome)
            except Exception:
                pass

    async def before_compression(self) -> None:
        for provider in self._providers.values():
            try:
                await provider.before_compression()
            except Exception:
                pass

    async def on_delegation_complete(self, result: dict) -> None:
        for provider in self._providers.values():
            try:
                await provider.on_delegation_complete(result)
            except Exception:
                pass


def build_default_memory_manager() -> MemoryManager:
    """Wire the five required providers (Architecture §13.1)."""
    mgr = MemoryManager()
    try:
        from backend.core.scan_state_db import scan_state_db
        mgr.register(ScanMemoryProvider(scan_state_db))
    except Exception:
        mgr.register(ScanMemoryProvider(None))
    try:
        from backend.core.memory import memory_store
        store = getattr(memory_store, "dual", None) or getattr(memory_store, "_dual", None)
        mgr.register(SemanticSecurityMemoryProvider(store))
    except Exception:
        mgr.register(SemanticSecurityMemoryProvider(None))
    mgr.register(ToolReliabilityMemoryProvider())
    mgr.register(AgentPerformanceMemoryProvider())
    return mgr


memory_manager = build_default_memory_manager()
