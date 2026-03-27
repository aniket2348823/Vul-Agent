import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
import urllib.request
import urllib.error
import glob

# Ensure we're in the right directory
import sys
sys.path.insert(0, ".")

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
TARGET_URL = "http://127.0.0.1:8999"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(REPORT_DIR, "calibration_drift.json")

# Ground truth mapping: endpoint path keywords -> EXPECTED VULN / SAFE
GROUND_TRUTH = {
    "/api/v1/bola/": True,
    "/api/v1/idor/": True,
    "/api/v1/sqli/": True,
    "/api/v1/xss/": True,
    "/api/v1/jwt/": True,
    "/api/v1/race/": True,
    "/api/v1/fp/": False,      # False Positives -> Expect Safe!
}

# -------------------------------------------------------------
# Test Harness
# -------------------------------------------------------------

async def fetch_endpoint(path: str, method="GET", payload=None, headers=None) -> dict:
    import aiohttp
    url = f"{TARGET_URL}{path}"
    try:
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=5) as resp:
                    text = await resp.text()
                    return {"status": resp.status, "body": text}
            elif method in ("POST", "PUT", "DELETE"):
                async with session.request(method, url, data=payload, headers=headers, timeout=5) as resp:
                    text = await resp.text()
                    return {"status": resp.status, "body": text}
    except Exception as e:
        return {"status": 500, "body": str(e)}

async def run_regression():
    from backend.ai.cortex import CortexEngine
    cortex = CortexEngine()
    
    # Let's warm up the model
    await cortex.warm_up()

    print("=" * 70)
    print(" ANTIGRAVITY V6 â€” 50+ SCENARIO REGRESSION & CALIBRATION SUITE")
    print("=" * 70)

    # 1. Discover all endpoints. In a real test, we might crawl or use an OpenAPI spec.
    # For this synthetic test, we will hardcode the paths we built in regression_target_server.py
    
    endpoints = [
        # BOLA
        {"path": "/api/v1/bola/profile/2", "method": "GET", "type": "BOLA"},
        {"path": "/api/v1/bola/profile/2", "method": "PUT", "payload": {"role": "admin"}, "type": "BOLA"},
        {"path": "/api/v1/bola/documents/100", "method": "DELETE", "type": "BOLA"},
        {"path": "/api/v1/bola/receipts?receipt_id=555", "method": "GET", "type": "BOLA"},
        {"path": "/api/v1/bola/messages/send", "method": "POST", "payload": {"sender_id": 1, "receiver_id": 2, "msg": "hack"}, "type": "BOLA"},
        
        # IDOR
        {"path": "/api/v1/idor/encoded/MTIz", "method": "GET", "type": "IDOR"}, # base64 "123"
        {"path": "/api/v1/idor/hex/7b", "method": "GET", "type": "IDOR"}, # hex "123"
        {"path": "/api/v1/idor/rot13", "method": "POST", "payload": {"target_id": "uvqqra"}, "type": "IDOR"},
        {"path": "/api/v1/idor/guid_leak?account=123", "method": "GET", "type": "IDOR"},
        {"path": "/api/v1/idor/md5_id/202cb962ac59075b964b07152d234b70", "method": "PUT", "type": "IDOR"}, # MD5 of "123"
        
        # SQLi
        {"path": "/api/v1/sqli/blind/time?q=A' OR pg_sleep(2)--", "method": "GET", "type": "SQLi"},
        {"path": "/api/v1/sqli/blind/boolean?id=1' OR 1=1--", "method": "GET", "type": "SQLi"},
        {"path": "/api/v1/sqli/login", "method": "POST", "payload": {"username": "admin' OR 1=1--", "password": "x"}, "type": "SQLi"},
        {"path": "/api/v1/sqli/order?sort=id;", "method": "GET", "type": "SQLi"},
        {"path": "/api/v1/sqli/headers", "method": "GET", "headers": {"User-Agent": "Mozilla' OR 1=1--"}, "type": "SQLi"},
        
        # XSS
        {"path": "/api/v1/xss/reflected/search?query=<script>alert(1)</script>", "method": "GET", "type": "XSS"},
        {"path": "/api/v1/xss/reflected/error?msg=<svg/onload=alert()>", "method": "GET", "type": "XSS"},
        {"path": "/api/v1/xss/reflected/jsonp?callback=<script>alert(1)</script>", "method": "GET", "type": "XSS"},
        {"path": "/api/v1/xss/reflected/header", "method": "GET", "headers": {"Referer": "<img src=x onerror=prompt()>"}, "type": "XSS"},
        {"path": "/api/v1/xss/reflected/path/<script>alert(1)</script>", "method": "GET", "type": "XSS"},
        {"path": "/api/v1/xss/stored/comment", "method": "POST", "payload": {"text": "<script>alert(1)</script>"}, "type": "XSS"},
        {"path": "/api/v1/xss/stored/comments", "method": "GET", "type": "XSS"},
        {"path": "/api/v1/xss/stored/profile", "method": "PUT", "payload": {"bio": "<svg/onload=alert()><svg>"}, "type": "XSS"},
        {"path": "/api/v1/xss/stored/profile", "method": "GET", "type": "XSS"},
        {"path": "/api/v1/xss/stored/message", "method": "POST", "payload": {"msg": "<b>bold</b><script>alert()</script>"}, "type": "XSS"},
        
        # JWT
        {"path": "/api/v1/jwt/none_alg", "method": "GET", "headers": {"Authorization": "Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyIjoiYWRtaW4ifQ."}, "type": "JWT"},
        {"path": "/api/v1/jwt/weak_secret", "method": "GET", "headers": {"Authorization": "Bearer admin_weak"}, "type": "JWT"},
        {"path": "/api/v1/jwt/kid_injection", "method": "GET", "headers": {"Authorization": "Bearer injected"}, "type": "JWT"},
        {"path": "/api/v1/jwt/jku_bypass", "method": "GET", "headers": {"Authorization": "Bearer jku"}, "type": "JWT"},
        {"path": "/api/v1/jwt/confusion", "method": "GET", "headers": {"Authorization": "Bearer param"}, "type": "JWT"},
        
        # Race Condition
        {"path": "/api/v1/race/transfer", "method": "POST", "payload": {"amount": 100}, "type": "Race"},
        {"path": "/api/v1/race/coupon", "method": "POST", "type": "Race"},
        {"path": "/api/v1/race/vote", "method": "POST", "type": "Race"},
        {"path": "/api/v1/race/claim_prize", "method": "POST", "type": "Race"},
        {"path": "/api/v1/race/register", "method": "POST", "payload": {"username": "admin"}, "type": "Race"},
        
        # False Positives
        {"path": "/api/v1/fp/public_keys", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/sample_credit_card", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/uuid_list", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/dummy_tokens", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/internal_ips", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/fake_ssn", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/fake_emails", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/hash_collision", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/stack_trace", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/env_vars", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/aws_arn", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/jwt_public", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/phone_numbers", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/api_docs", "method": "GET", "type": "FP"},
        {"path": "/api/v1/fp/git_sha", "method": "GET", "type": "FP"},
    ]

    results = []
    total_error = 0.0

    print(f"\n[+] Processing {len(endpoints)} Scenarios Concurrently...\n")
    
    semaphore = asyncio.Semaphore(10) # 10 concurrent requests
    
    async def process_endpoint(i, ep):
        async with semaphore:
            # 1. Fetch raw response
            resp = await fetch_endpoint(ep["path"], ep["method"], ep.get("payload"), ep.get("headers"))
            
            # 2. Prepare Audit Candidate 
            # (This simulates what the agents parse during a live scan)
            is_vuln_category = ep["type"] != "FP"
            
            candidate_data = {
                "type": ep["type"],
                "url": ep["path"],
                "tag": f"Regression_{ep['type']}",
                "description": f"Response status: {resp['status']}. Body extract: {resp['body'][:200]}"
            }

            # 3. Call Neural Engine
            try:
                audit = await cortex.audit_candidate(candidate_data)
                
                pred_is_vuln = audit.get("is_real", False)
                confidence = audit.get("confidence", 0.0)
            except Exception as e:
                pred_is_vuln = False
                confidence = 0.0
                reason = str(e)
                
            # 4. Evaluate Calibration
            actual = 1.0 if is_vuln_category else 0.0
            p_vuln = confidence if pred_is_vuln else (1.0 - confidence)
            
            calibration_error_sq = (actual - p_vuln) ** 2
            is_correct = (pred_is_vuln == is_vuln_category)
            
            icon = "âœ…" if is_correct else "âŒ"
            overconfident_flag = "âš ï¸ [OVERCONFIDENT]" if not is_correct and confidence > 0.8 else ""

            print(f"{i:02d}. {icon} {ep['type']:<5} | EP: {ep['path'][:25]:<25} | "
                  f"Exp: {actual:.1f} | Pred: {pred_is_vuln!s:<5} (Conf: {confidence:.2f}) {overconfident_flag}")

            return {
                "calibration_error_sq": calibration_error_sq,
                "result_dict": {
                    "path": ep["path"],
                    "category": ep["type"],
                    "expected_vuln": is_vuln_category,
                    "predicted_vuln": pred_is_vuln,
                    "confidence": confidence,
                    "p_vuln": p_vuln,
                    "correct": is_correct,
                    "reason": reason
                }
            }

    tasks = [process_endpoint(i, ep) for i, ep in enumerate(endpoints, 1)]
    task_results = await asyncio.gather(*tasks)

    for tr in task_results:
        total_error += tr["calibration_error_sq"]
        results.append(tr["result_dict"])

    # -------------------------------------------------------------
    # AI Quality & Calibration Metrics
    # -------------------------------------------------------------
    
    brier_score = total_error / len(endpoints)
    # Brier Score: 0 is perfect, 1.0 is totally wrong with 100% confidence.
    # Below 0.1 is amazing. 0.25 is random guessing.

    accuracy = sum(1 for r in results if r["correct"]) / len(endpoints) * 100
    
    overconfident_errors = sum(1 for r in results if not r["correct"] and r["confidence"] > 0.8)

    # -------------------------------------------------------------
    # Token Profile Tracking
    # -------------------------------------------------------------
    telemetry = cortex.get_telemetry()
    vulns_detected = sum(1 for r in results if r["predicted_vuln"])
    
    avg_input_tokens = telemetry.get("avg_input_tokens", 0)
    avg_output_tokens = telemetry.get("avg_output_tokens", 0)
    total_tokens = telemetry.get("llm_input_tokens", 0) + telemetry.get("llm_output_tokens", 0)
    tokens_per_vuln = total_tokens / vulns_detected if vulns_detected > 0 else 0

    print("\n" + "=" * 70)
    print(" ðŸ REGRESSION BENCHMARK & CALIBRATION RESULTS")
    print("=" * 70)
    
    print(f"\n[AI QUALITY]")
    print(f"  Accuracy:                 {accuracy:.1f}%")
    print(f"  Brier Score (Calb):       {brier_score:.4f} (Lower is better. <0.15 is great)")
    print(f"  Overconfident Errors:     {overconfident_errors}  (Model confidently wrong)")

    print(f"\n[TOKEN PROFILING]")
    print(f"  Avg Input Tokens/Call:    {avg_input_tokens}")
    print(f"  Avg Output Tokens/Call:   {avg_output_tokens}")
    print(f"  Total Tokens Burned:      {total_tokens}")
    print(f"  Tokens / Vuln Detected:   {tokens_per_vuln:.0f}")

    # -------------------------------------------------------------
    # Record Drift History
    # -------------------------------------------------------------
    run_date = datetime.now().isoformat()
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except Exception:pass

    record = {
        "timestamp": run_date,
        "accuracy": accuracy,
        "brier_score": brier_score,
        "overconfident_errors": overconfident_errors,
        "avg_input_tokens": avg_input_tokens,
        "avg_output_tokens": avg_output_tokens,
        "total_tokens": total_tokens,
        "tokens_per_vuln": tokens_per_vuln
    }
    history.append(record)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    print(f"\nðŸ’¾ Drift & token metrics appended to {HISTORY_FILE}")

if __name__ == "__main__":
    # Start the target server in background
    print("Starting target server on port 8999...")
    server_process = subprocess.Popen(
        [sys.executable, "backend/tests/regression_target_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        # Give it a second to bind
        time.sleep(2)
        
        # Check if actually running
        if server_process.poll() is not None:
            print("Failed to start target server.")
            sys.exit(1)

        # Run the regression loop
        asyncio.run(run_regression())
    finally:
        print("\nShutting down target server...")
        server_process.terminate()
        server_process.wait()

