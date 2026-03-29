# FILE: backend/core/risk_engine.py
# ROLE: THE JUDGE
# RESPONSIBILITY: Centralized Risk Scoring Logic (AI-Enhanced)

from backend.ai.cortex import CortexEngine, get_cortex_engine

class RiskEngine:
    """
    The Risk Engine calculates a 0-100 score for any given threat.
    Uses AI contextual analysis when available, with deterministic fallback.
    """
    
    _ai = None  # Lazy-loaded singleton
    
    @classmethod
    def _get_ai(cls):
        if cls._ai is None:
            try:
                cls._ai = get_cortex_engine()
            except Exception:cls._ai = None
        return cls._ai

    @staticmethod
    def calculate_risk(threat_type: str, context: dict) -> int:
        # 1. DETERMINISTIC BASELINE SCORES
        base_scores = {
            "PROMPT_INJECTION": 95,
            "INVISIBLE_TEXT": 75,
            "DECEPTIVE_UI": 85,
            "PHISHING": 99,
            "ROACH_MOTEL": 80,
        }
        base_score = base_scores.get(threat_type, 50)

        # 2. AI CONTEXTUAL MODIFIER
        ai = RiskEngine._get_ai()
        if ai and ai.enabled and context.get("url"):
            try:
                ai_score = ai.assess_contextual_risk(
                    threat_type=threat_type,
                    target_url=context.get("url", ""),
                    context=context
                )
                # Blend: 60% AI assessment + 40% deterministic baseline
                base_score = int(ai_score * 0.6 + base_score * 0.4)
            except Exception:pass  # Keep deterministic score
        
        return min(base_score, 100)

    @staticmethod
    def get_verdict(risk_score: int) -> str:
        if risk_score >= 80:
            return "BLOCK"
        elif risk_score >= 50:
            return "WARN"
        else:
            return "ALLOW"
