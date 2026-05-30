"""
CVSS v3.1 Base Score Engine (Architecture §18, §29.11)
================================================================================
A real CVSS 3.1 base-score implementation (the official formula), replacing the
previous heuristic lookup ladder. Also keeps the legacy CVSSCalculator API and
adds a per-vuln-class default metric map so findings get deterministic scores.
"""
from __future__ import annotations

import math

# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

cortex = get_cortex_engine()


# ── Official CVSS 3.1 metric weights ──────────────────────────────────────────
_AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}        # Attack Vector
_AC = {"L": 0.77, "H": 0.44}                              # Attack Complexity
_UI = {"N": 0.85, "R": 0.62}                              # User Interaction
_PR_U = {"N": 0.85, "L": 0.62, "H": 0.27}                # Privileges (Scope Unchanged)
_PR_C = {"N": 0.85, "L": 0.68, "H": 0.50}                # Privileges (Scope Changed)
_CIA = {"H": 0.56, "L": 0.22, "N": 0.0}                  # C/I/A impact


def _roundup(x: float) -> float:
    """CVSS 3.1 Appendix A roundup to one decimal."""
    int_input = round(x * 100000)
    if int_input % 10000 == 0:
        return int_input / 100000.0
    return (math.floor(int_input / 10000) + 1) / 10.0


def cvss31_base(av="N", ac="L", pr="N", ui="N", s="U", c="N", i="N", a="N") -> tuple[float, str]:
    """Compute the official CVSS 3.1 base score and vector string."""
    pr_val = _PR_C[pr] if s == "C" else _PR_U[pr]
    iss = 1 - ((1 - _CIA[c]) * (1 - _CIA[i]) * (1 - _CIA[a]))
    if s == "U":
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
    exploitability = 8.22 * _AV[av] * _AC[ac] * pr_val * _UI[ui]
    if impact <= 0:
        base = 0.0
    elif s == "U":
        base = _roundup(min(impact + exploitability, 10))
    else:
        base = _roundup(min(1.08 * (impact + exploitability), 10))
    vector = f"CVSS:3.1/AV:{av}/AC:{ac}/PR:{pr}/UI:{ui}/S:{s}/C:{c}/I:{i}/A:{a}"
    return base, vector


def severity_band(score: float) -> str:
    """CVSS 3.1 qualitative severity rating."""
    if score == 0:
        return "none"
    if score < 4.0:
        return "low"
    if score < 7.0:
        return "medium"
    if score < 9.0:
        return "high"
    return "critical"


# Default base metrics per vulnerability class (Architecture §18 deterministic scoring).
# {class: (av, ac, pr, ui, s, c, i, a)}
_VULN_METRICS = {
    "SQL_INJECTION":       ("N", "L", "L", "N", "U", "H", "H", "N"),
    "SQLI":                ("N", "L", "L", "N", "U", "H", "H", "N"),
    "COMMAND_INJECTION":   ("N", "L", "L", "N", "C", "H", "H", "H"),
    "RCE":                 ("N", "L", "N", "N", "C", "H", "H", "H"),
    "XSS":                 ("N", "L", "N", "R", "C", "L", "L", "N"),
    "CROSS_SITE_SCRIPTING":("N", "L", "N", "R", "C", "L", "L", "N"),
    "IDOR":                ("N", "L", "L", "N", "U", "H", "N", "N"),
    "BROKEN_AUTH":         ("N", "L", "N", "N", "U", "H", "H", "N"),
    "AUTH_BYPASS":         ("N", "L", "N", "N", "U", "H", "H", "N"),
    "JWT_BYPASS":          ("N", "L", "N", "N", "U", "H", "H", "N"),
    "SSRF":                ("N", "L", "L", "N", "C", "H", "L", "N"),
    "PATH_TRAVERSAL":      ("N", "L", "L", "N", "U", "H", "N", "N"),
    "RACE_CONDITION":      ("N", "H", "L", "N", "U", "N", "H", "N"),
    "FINANCIAL_MANIPULATION": ("N", "H", "L", "N", "U", "N", "H", "N"),
    "DATA_LEAK":           ("N", "L", "N", "N", "U", "H", "N", "N"),
}


def score_for_vuln_class(vuln_type: str, *, data_leak: bool = False) -> tuple[float, str]:
    """Deterministic CVSS 3.1 score for a known vuln class (Architecture §18)."""
    metrics = _VULN_METRICS.get((vuln_type or "").upper())
    if not metrics:
        # Conservative default: medium-ish network finding.
        metrics = ("N", "L", "L", "N", "U", "L", "L", "N")
    av, ac, pr, ui, s, c, i, a = metrics
    if data_leak and c == "N":
        c = "H"
    return cvss31_base(av, ac, pr, ui, s, c, i, a)


class CVSSCalculator:
    """Backward-compatible calculator now backed by the real CVSS 3.1 formula."""

    def __init__(self, success_count: int, body_content: str = "", target_url: str = "", vuln_type: str = ""):
        self.success_count = success_count
        self.body_content = body_content.lower()
        self.target_url = target_url
        self.vuln_type = vuln_type

    def calculate(self):
        sensitive_keywords = ["token", "key", "password", "secret", "admin"]
        data_leak = any(k in self.body_content for k in sensitive_keywords)

        # If we know the vuln class, use its deterministic metric profile.
        if self.vuln_type:
            return score_for_vuln_class(self.vuln_type, data_leak=data_leak)

        # Otherwise derive metrics from observed signals (real formula, not a ladder).
        c = "H" if data_leak else "N"
        i = "H" if self.success_count >= 1 else "N"
        # Logic flaws default to high attack complexity.
        return cvss31_base(av="N", ac="H", pr="L", ui="N", s="U", c=c, i=i, a="N")

    async def calculate_hybrid(self):
        """Calculate CVSS with AI-powered contextual adjustment."""
        base_score, vector = self.calculate()
        if self.target_url and self.vuln_type:
            try:
                adjusted = await cortex.adjust_cvss_score(base_score, self.vuln_type, self.target_url)
                return adjusted, vector
            except Exception:
                return base_score, vector
        return base_score, vector
