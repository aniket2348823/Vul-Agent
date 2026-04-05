"""
PHASE 6: DASHBOARD & STATE API
Tests reading real-time analytics, session states, and dashboard stats.
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
    # ── 6.1 Dashboard Stats ────────────────────────────────────────────────
    try:
        r = requests.get(f"{API}/dashboard/stats", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "metrics" in data, "Stats missing 'metrics'"
        assert "total_scans" in data["metrics"], "Stats missing 'total_scans'"
        assert "vulnerabilities" in data["metrics"], "Stats missing 'vulnerabilities'"
        PASS("6.1 Dashboard stats returning correctly")
    except Exception as e:
        FAIL("6.1 Dashboard Stats", str(e))

    # ── 6.2 Target Settings Update ──────────────────────────────────────────
    try:
        payload = {"global_target": "http://example.com"}
        r = requests.post(f"{API}/dashboard/settings", json=payload, timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        PASS("6.2 Dashboard Settings updated properly")
    except Exception as e:
        FAIL("6.2 Target Settings Update", str(e))

    # ── 6.3 Scan History Retrieval ──────────────────────────────────────────
    try:
        r = requests.get(f"{API}/dashboard/scans", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert isinstance(data, list), "Scans list expected"
        PASS(f"6.3 Scan History returned {len(data)} items")
    except Exception as e:
        FAIL("6.3 Scan History Retrieval", str(e))
        
except Exception as e:
    print(f"CRITICAL ERROR: {e}")

print("\n" + "="*60)
print(f"PHASE 6 COMPLETE: {P} passed, {F} failed")
if errors:
    print("FAILURES:")
    for e in errors: print(f"  ❌ {e}")
print("="*60)
