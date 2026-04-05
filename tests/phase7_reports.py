"""
PHASE 7: REPORT GENERATION
Tests the automated PDF report generation API.
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
    # ── 7.1 List Reports ────────────────────────────────────────────────────
    try:
        r = requests.get(f"{API}/reports/", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        PASS("7.1 Reports listing is functional")
    except Exception as e:
        FAIL("7.1 List Reports", str(e))

    # ── 7.2 Download PDF Report ─────────────────────────────────────────────
    try:
        r = requests.get(f"{API}/reports/", timeout=5)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            first_report = data[0]["name"]
            r_dl = requests.get(f"{API}/reports/download/{first_report}", timeout=10)
            assert r_dl.status_code == 200, f"Expected 200, got {r_dl.status_code}"
            assert r_dl.headers.get("content-type") == "application/pdf" or first_report.endswith(".pdf"), "Not a PDF response"
            PASS(f"7.2 Downloaded PDF processing successful ({len(r_dl.content)} bytes)")
        else:
            print("  ⚠️ 7.2 Skipped Download PDF: No reports exist.")
    except Exception as e:
        FAIL("7.2 Download PDF Report", str(e))

except Exception as e:
    print(f"CRITICAL ERROR: {e}")

print("\n" + "="*60)
print(f"PHASE 7 COMPLETE: {P} passed, {F} failed")
if errors:
    print("FAILURES:")
    for e in errors: print(f"  ❌ {e}")
print("="*60)
