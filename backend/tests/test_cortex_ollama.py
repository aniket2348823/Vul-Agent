# ═══════════════════════════════════════════════════════════════════════════════
# ANTIGRAVITY :: CORTEX ENGINE TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════
# Verifies that the Ollama-backed CortexEngine is functional.
# PREREQUISITE: Ollama must be running locally (ollama serve)
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.ai.cortex import CortexEngine


def test_cortex_instantiation():
    """CortexEngine should instantiate without errors and without an API key."""
    engine = CortexEngine()
    assert engine is not None
    assert engine.model == "antigravity-cortex"
    assert "localhost" in engine.base_url
    print("[PASS] CortexEngine instantiated successfully")


def test_cortex_backward_compat():
    """CortexEngine should accept (and ignore) a legacy api_key parameter."""
    engine = CortexEngine(api_key="fake-gemini-key-12345")
    assert engine is not None
    print("[PASS] Backward compatibility (api_key ignored)")


def test_executive_brief():
    """generate_executive_brief should return a non-empty string."""
    engine = CortexEngine()
    result = engine.generate_executive_brief(
        target="http://example.com/api/checkout",
        success_count=8,
        total_count=20,
        duration="45.2s"
    )
    assert isinstance(result, str)
    assert len(result) > 10, f"Response too short: '{result}'"
    print(f"[PASS] Executive Brief ({len(result)} chars):")
    print(f"  → {result[:200]}...")


def test_payload_analysis():
    """analyze_payload_variant should return a non-empty string."""
    engine = CortexEngine()
    result = engine.analyze_payload_variant(
        variant="Race Condition #3",
        payload='{"item_id": 1, "qty": -1, "coupon": "FREEITEM"}',
        verdict="VULNERABLE"
    )
    assert isinstance(result, str)
    assert len(result) > 10, f"Response too short: '{result}'"
    print(f"[PASS] Payload Analysis ({len(result)} chars):")
    print(f"  → {result[:200]}...")


def test_payload_analysis_blocked():
    """analyze_payload_variant should handle BLOCKED verdicts."""
    engine = CortexEngine()
    result = engine.analyze_payload_variant(
        variant="SQLi Attempt #7",
        payload="' OR 1=1 --",
        verdict="BLOCKED"
    )
    assert isinstance(result, str)
    assert len(result) > 10, f"Response too short: '{result}'"
    print(f"[PASS] Blocked Payload Analysis ({len(result)} chars):")
    print(f"  → {result[:200]}...")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  CORTEX ENGINE TEST SUITE (Ollama Integration)")
    print("=" * 60 + "\n")

    tests = [
        test_cortex_instantiation,
        test_cortex_backward_compat,
        test_executive_brief,
        test_payload_analysis,
        test_payload_analysis_blocked,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
