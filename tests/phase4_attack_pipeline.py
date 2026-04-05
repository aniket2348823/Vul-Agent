"""
PHASE 4: ATTACK PIPELINE
Tests the attack API endpoint logic, orchestrator start pathway,
URL validation / SSRF protection, and attack replay logic.
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
    # ── 4.1 URL Validation - Allowed targets ────────────────────────────────
    try:
        from backend.api.endpoints.attack import validate_target_url
        valid_urls = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://192.168.1.100:3000",
            "http://example.com"
        ]
        for url in valid_urls:
            ok, reason = validate_target_url(url)
            assert ok is True, f"Failed for {url}: {reason}"
        PASS("4.1 URL Validation approves safe targets")
    except Exception as e:
        FAIL("4.1 URL Validation Safe", str(e))

    # ── 4.2 URL Validation - Blocked targets ────────────────────────────────
    try:
        from backend.api.endpoints.attack import validate_target_url
        blocked_urls = [
            "http://169.254.169.254/latest/meta-data",
            "http://metadata.google.internal",
            "file:///etc/passwd"
        ]
        for url in blocked_urls:
            ok, reason = validate_target_url(url)
            assert not ok, f"Should have blocked {url}"
        PASS("4.2 URL Validation blocks SSRF/LFI targets")
    except Exception as e:
        FAIL("4.2 URL Validation Block", str(e))

    # ── 4.3 Fire Attack (Valid Target) ───────────────────────────────────────
    scan_id = None
    try:
        payload = {
            "target_url": "http://localhost:8000",
            "method": "GET",
            "headers": {},
            "body": "",
            "velocity": 10,
            "concurrency": 5,
            "rps": 20,
            "modules": [],
            "filters": [],
            "duration": 3
        }
        r = requests.post(f"{API}/attack/fire", json=payload, timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "scan_id" in data, "No scan_id returned"
        assert data.get("status") == "Swarm Online", "Unexpected status"
        scan_id = data["scan_id"]
        PASS(f"4.3 Fire Attack succeeds and returns Scan ID: {scan_id[:12]}...")
    except Exception as e:
        FAIL("4.3 Fire Attack Valid", str(e))

    # ── 4.4 Fire Attack (Blocked Target) ─────────────────────────────────────
    try:
        payload = {
            "target_url": "http://169.254.169.254",
            "method": "GET"
        }
        r = requests.post(f"{API}/attack/fire", json=payload, timeout=5)
        # It's an SSRF target, so it should be blocked. Depends if backend sends 400 or 403.
        assert r.status_code in [400, 403], f"Expected 400/403 for SSRF, got {r.status_code}"
        PASS("4.4 SSRF target correctly rejected by attack endpoint")
    except Exception as e:
        FAIL("4.4 Fire Attack Blocked", str(e))

    # ── 4.5 Replay Attack Endpoint ───────────────────────────────────────────
    try:
        # Replaying a non-existent vuln id should return 404
        r = requests.post(f"{API}/attack/replay/nonexistent-vuln", timeout=5)
        assert r.status_code in [404, 500], f"Expected 404 or 500, got {r.status_code}"
        PASS("4.5 Attack Replay handles invalid vuln_id")
    except Exception as e:
        FAIL("4.5 Replay Attack Endpoint", str(e))

    # ── 4.6 Scan Persistence ─────────────────────────────────────────────────
    try:
        if scan_id:
            # Let the background task finish
            time.sleep(4)
            r = requests.get(f"{API}/dashboard/scans", timeout=5)
            assert r.status_code == 200
            scans = r.json()
            found = [s for s in scans if s.get("id") == scan_id or s.get("scan_id") == scan_id]
            assert len(found) > 0, f"Scan {scan_id} not found in state manager scans"
            PASS("4.6 Attack execution persists scan in dashboard state")
        else:
            WARN("4.6", "Skipped because scan_id wasn't created")
    except Exception as e:
        FAIL("4.6 Scan Persistence", str(e))

except Exception as e:
    print(f"CRITICAL ERROR: {e}")

print("\n" + "="*60)
print(f"PHASE 4 COMPLETE: {P} passed, {F} failed")
if errors:
    print("FAILURES:")
    for e in errors: print(f"  ❌ {e}")
print("="*60)
