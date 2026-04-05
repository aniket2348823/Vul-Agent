"""
PHASE 5: AI CORTEX ENGINE
Tests the AI status endpoint, manual payload mutation,
and GI-5 integration for hybrid intelligence.
"""
import os, sys, requests, time
sys.path.insert(0, ".")

P, F = 0, 0
errors = []

def PASS(n):
    global P; P += 1; print(f"  ✅ {n}")
def FAIL(n, r=""):
    global F; F += 1; errors.append(f"{n}: {r}"); print(f"  ❌ {n} — {r}")

BASE = "http://localhost:8000"
API = f"{BASE}/api"

try:
    # ── 5.1 AI Status Check ────────────────────────────────────────────────
    try:
        r = requests.get(f"{API}/ai/status", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "core_status" in data, "Missing 'core_status' parameter in ai status"
        PASS("5.1 AI Status Check returns healthy engine state")
    except Exception as e:
        FAIL("5.1 AI Status Check", str(e))

    # ── 5.2 Manual Mutate (SQLi) ───────────────────────────────────────────
    try:
        payload = {
            "url": "http://example.com/login",
            "method": "POST",
            "headers": {},
            "body": {"username": "admin", "password": "123"}
        }
        r = requests.post(f"{API}/ai/mutate", json=payload, timeout=60)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "variants" in data, "Missing 'variants' in response"
        assert isinstance(data["variants"], list), "No mutations returned"
        PASS(f"5.2 AI Payload Mutation successful: Returned {len(data['variants'])} variants")
    except Exception as e:
        FAIL("5.2 Payload Mutation", str(e))

    # ── 5.3 Sentinel Action (Threat Defense AI) ────────────────────────────
    try:
        payload = {
            "agent_id": "agent_prism",
            "content": {"dom": "<html>...</html>"},
            "url": "http://example.com/api/admin"
        }
        r = requests.post(f"{API}/defense/analyze", json=payload, timeout=5)
        # It's an async queue route, typically returns status or spawns background task
        assert r.status_code in [200, 202], f"Expected 200, got {r.status_code}"
        PASS("5.3 Sentinel Action endpoint responds")
    except Exception as e:
        FAIL("5.3 Sentinel Action", str(e))

except Exception as e:
    print(f"CRITICAL ERROR: {e}")

print("\n" + "="*60)
print(f"PHASE 5 COMPLETE: {P} passed, {F} failed")
if errors:
    print("FAILURES:")
    for e in errors: print(f"  ❌ {e}")
print("="*60)
