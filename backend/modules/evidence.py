"""
Differential Evidence Helper for arsenal modules (Architecture §9, §17, §29.6)
================================================================================
Replaces naive substring detection (e.g. `if "admin" in text.lower()`) with
differential analysis requiring multiple independent signals to agree, via the
MultiLayerVerifier. A finding is only emitted when >= 2 signals agree
(Architecture §9.3, §17 verification model).

Modules receive `interactions: list[tuple[TaskTarget, str]]`. By convention the
FIRST interaction is the baseline/original request and subsequent ones are the
injected/test requests (this matches how Doppelganger and the workers build
their target lists). When a richer object with a status code is available we use
it; otherwise we compare response bodies structurally.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.core.exploit_engine import MultiLayerVerifier


@dataclass
class DiffEvidence:
    verified: bool
    confidence: int
    signals: int
    summary: str = ""


def _status_of(obj: Any) -> int:
    if isinstance(obj, dict):
        return int(obj.get("status", obj.get("status_code", 0)) or 0)
    return int(getattr(obj, "status", getattr(obj, "status_code", 0)) or 0)


def differential(baseline_text: str, test_text: str, *,
                 baseline_status: int = 200, test_status: int = 200) -> DiffEvidence:
    """Compare a baseline response against a test response.

    Returns DiffEvidence; ``verified`` is True only when the MultiLayerVerifier
    finds >= 2 independent signals (status divergence, length delta, Jaccard
    < 0.85, new sensitive keyword, JSON structural diff)."""
    verified, confidence, signals = MultiLayerVerifier.verify(
        {"status": baseline_status, "response": baseline_text or ""},
        {"status": test_status, "body": test_text or ""},
    )
    summary = (f"differential signals={signals} confidence={confidence}% "
               f"(status {baseline_status}->{test_status}, "
               f"len {len(baseline_text or '')}->{len(test_text or '')})")
    return DiffEvidence(verified=verified, confidence=confidence, signals=signals, summary=summary)


def first_baseline(interactions: list[tuple[Any, str]]) -> tuple[Any, str] | None:
    """Return the baseline (first) interaction, or None if empty."""
    return interactions[0] if interactions else None


def confirm_against_baseline(interactions: list[tuple[Any, str]], index: int) -> DiffEvidence:
    """Confirm the interaction at ``index`` differs materially from the baseline
    (index 0). Returns an unverified DiffEvidence when there's no baseline or the
    index is the baseline itself."""
    if not interactions or index <= 0 or index >= len(interactions):
        return DiffEvidence(False, 0, 0, "no baseline to compare")
    _btarget, btext = interactions[0]
    _ttarget, ttext = interactions[index]
    return differential(btext if isinstance(btext, str) else "",
                        ttext if isinstance(ttext, str) else "")


# ── Logic-flaw confirmation (Architecture §9.3, §17) ──────────────────────────
# Logic modules (mass assignment, workflow bypass, financial) often lack a clean
# baseline. We still require >= 2 independent signals to agree before confirming:
#   (1) a positive/success marker is present,
#   (2) NO denial/error marker is present,
#   (3) optionally, the injected payload value is reflected in the response.

_DENIAL_MARKERS = [
    "denied", "forbidden", "unauthorized", "not allowed", "error", "invalid",
    "failed", "must be", "cannot", "login required", "403", "401", "validation",
    "exception", "bad request",
]


def logic_confirm(text: str, *, positive_markers: list[str],
                  reflected: str | None = None) -> DiffEvidence:
    """Confirm a logic-flaw response using >= 2 independent signals."""
    low = (text or "").lower()
    signals = 0
    detail = []

    has_positive = any(m in low for m in positive_markers)
    if has_positive:
        signals += 1
        detail.append("positive_marker")

    no_denial = not any(m in low for m in _DENIAL_MARKERS)
    if no_denial:
        signals += 1
        detail.append("no_denial_marker")

    if reflected and str(reflected).lower() in low:
        signals += 1
        detail.append("payload_reflected")

    verified = has_positive and signals >= 2
    confidence = min(signals * 30, 100)
    return DiffEvidence(verified=verified, confidence=confidence, signals=signals,
                        summary=f"logic signals={signals} [{', '.join(detail)}]")
