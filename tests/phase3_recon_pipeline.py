"""
PHASE 3: RECON PIPELINE
Tests the intelligence ingestion pipeline including standard requests,
anomalies, and secrets keyring management.
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
    # ── 3.1 Ingest Valid Packet ─────────────────────────────────────────────
    try:
        payload = {
            "url": "http://localhost:8000/api/test",
            "method": "GET",
            "headers": {"content-type": "application/json"},
            "body": None,
            "timestamp": time.time()
        }
        r = requests.post(f"{API}/recon/ingest", json=payload, timeout=5)
        # Assuming the FastAPI router handles it. If the endpoint doesn't exist yet, this will fail with 404. Let's see.
        assert r.status_code == 200, f"Unexpected status: {r.status_code}"
        data = r.json()
        if data is not None:
            assert data.get("status") in ["ingested", "success", "archived", "ok"], f"Unexpected response: {data}"
        PASS("3.1 Recon ingest accepts valid packet")
    except Exception as e:
        FAIL("3.1 Ingest Valid Packet", str(e))

    # ── 3.2 Ingest Anomaly Packet ───────────────────────────────────────────
    try:
        payload = {
            "url": "http://target.local/etc/passwd",
            "method": "GET",
            "headers": {},
            "timestamp": time.time(),
            "anomaly": True
        }
        r = requests.post(f"{API}/recon/ingest", json=payload, timeout=5)
        assert r.status_code == 200, f"Failed with {r.status_code}"
        PASS("3.2 Recon ingest handles anomaly URL")
    except Exception as e:
        FAIL("3.2 Ingest Anomaly Packet", str(e))

    # ── 3.3 Keyring Read ─────────────────────────────────────────────────────
    try:
        r = requests.get(f"{API}/recon/keyring", timeout=5)
        assert r.status_code == 200, f"Keyring read failed: {r.status_code}"
        data = r.json()
        assert isinstance(data, list) or isinstance(data, dict), f"Keyring response type issue: {type(data)}"
        PASS("3.3 Keyring endpoint returns valid structure")
    except Exception as e:
        FAIL("3.3 Keyring Read", str(e))

    # ── 3.4 Keyring Ingest ───────────────────────────────────────────────────
    try:
        payload = {
            "url": "http://test.local",
            "keys": {"api_key": "test123", "secret": "s3cr3t"},
            "timestamp": time.time()
        }
        r = requests.post(f"{API}/recon/keys", json=payload, timeout=5)
        assert r.status_code == 200, f"Key ingest failed: {r.status_code}"
        data = r.json()
        assert data.get("status") == "archived", f"Expected archived, got {data}"
        PASS("3.4 Key ingestion archived successfully")
    except Exception as e:
        FAIL("3.4 Keyring Ingest", str(e))

except Exception as e:
    print(f"CRITICAL ERROR: {e}")

print("\n" + "="*60)
print(f"PHASE 3 COMPLETE: {P} passed, {F} failed")
if errors:
    print("FAILURES:")
    for e in errors: print(f"  ❌ {e}")
print("="*60)
