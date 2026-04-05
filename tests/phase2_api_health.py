"""
PHASE 2: API HEALTH & ENDPOINT AVAILABILITY
Tests system readiness, connectivity, endpoint routes, CORS,
and generic error mapping.
"""
import os, sys, requests, time

P, F = 0, 0
errors = []

def PASS(n):
    global P; P += 1; print(f"  ✅ {n}")
def FAIL(n, r=""):
    global F; F += 1; errors.append(f"{n}: {r}"); print(f"  ❌ {n} — {r}")

BASE = "http://localhost:8000"
API = f"{BASE}/api"

try:
    # ── 2.1 Health Check ───────────────────────────────────────────────────
    try:
        r = requests.get(f"{API}/health", timeout=5)
        assert r.status_code == 200, f"Health check failed with {r.status_code}"
        data = r.json()
        assert data["status"] == "online", "API status is not online"
        assert "version" in data, "No version reported"
        PASS(f"2.1 Health check OK (version={data['version']})")
    except Exception as e:
        FAIL("2.1 Health Check", str(e))

    # ── 2.2 Endpoint Discovery ─────────────────────────────────────────────
    endpoints = [
        ("GET", "/api/health"),
        ("GET", "/api/dashboard/stats"),
        ("GET", "/api/dashboard/scans"),
        ("GET", "/api/dashboard/settings"),
        ("GET", "/api/dashboard/auth/status"),
        ("GET", "/api/reports/"),
        ("GET", "/api/defense/analyze"),
        ("GET", "/api/ai/status"),
    ]
    for method, path in endpoints:
        try:
            r = requests.request(method, f"{BASE}{path}", timeout=5)
            # We expect 200 (OK) or 401 (Unauthorized - if 2FA/auth is enforcing)
            assert r.status_code in [200, 401], f"Unexpected status {r.status_code} for {method} {path}"
            PASS(f"2.2 {method} {path} → {r.status_code}")
        except Exception as e:
            FAIL(f"2.2 {method} {path}", str(e))

    # ── 2.3 CORS Preflight ────────────────────────────────────────────────
    try:
        r = requests.options(f"{API}/health", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}, timeout=5)
        # The app uses CORSMiddleware. With allow_credentials=True, FastAPI echoes the exact origin
        assert r.status_code == 200, f"CORS Preflight failed: {r.status_code}"
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000", f"CORS origin mismatch: {r.headers.get('access-control-allow-origin')}"
        PASS("2.3 CORS preflight behaves correctly")
    except Exception as e:
        FAIL("2.3 CORS Preflight", str(e))

    # ── 2.4 Validation Error Handler (422 -> 400 mapping) ──────────────────
    try:
        # Pydantic normally returns 422 for missing fields. We wanted it to return 400 for TC004.
        r = requests.post(f"{API}/recon/ingest", json={}, timeout=5)
        assert r.status_code == 400, f"Expected 400 Bad Request, got {r.status_code}"
        data = r.json()
        assert "detail" in data, "No 'detail' message provided for validation error"
        PASS("2.4 Validation errors correctly mapped to 400")
    except Exception as e:
        FAIL("2.4 Validation Error Handler", str(e))

except Exception as e:
    print(f"CRITICAL ERROR: {e}")

print("\n" + "="*60)
print(f"PHASE 2 COMPLETE: {P} passed, {F} failed")
if errors:
    print("FAILURES:")
    for e in errors: print(f"  ❌ {e}")
print("="*60)
