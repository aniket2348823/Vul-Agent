import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
import urllib.parse

import sys
sys.path.insert(0, ".")

TARGET_URL = "http://127.0.0.1:8999"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(REPORT_DIR, "calibration_drift.json")

# Ground truth schema with Active Mutation Requirements
ENDPOINTS = [
    # BOLA
    {"path": "/api/v1/bola/profile/2", "method": "GET", "type": "BOLA", "active": True, "param": "user_id", "val": "3"},
    {"path": "/api/v1/bola/profile/2", "method": "PUT", "payload": {"role": "user"}, "type": "BOLA", "active": True, "param": "role", "val": "admin"},
    {"path": "/api/v1/bola/documents/100", "method": "DELETE", "type": "BOLA", "active": True, "param": "doc_id", "val": "101"},
    
    # IDOR
    {"path": "/api/v1/idor/encoded/MTIz", "method": "GET", "type": "IDOR", "active": True, "param": "enc_id", "val": "MTI0"},
    {"path": "/api/v1/idor/rot13", "method": "POST", "payload": {"target_id": "uvqqra"}, "type": "IDOR", "active": True, "param": "target_id", "val": "mutated"},
    
    # SQLi
    {"path": "/api/v1/sqli/blind/time?q=test", "method": "GET", "type": "SQLI", "active": True, "param": "q", "val": "payload"},
    {"path": "/api/v1/sqli/login", "method": "POST", "payload": {"username": "user", "password": "x"}, "type": "SQLI", "active": True, "param": "username", "val": "payload"},
    
    # XSS
    {"path": "/api/v1/xss/reflected/search?query=test", "method": "GET", "type": "XSS", "active": True, "param": "query", "val": "payload"},
    {"path": "/api/v1/xss/stored/comment", "method": "POST", "payload": {"text": "hello"}, "type": "XSS", "active": True, "param": "text", "val": "payload"},
    
    # JWT
    {"path": "/api/v1/jwt/none_alg", "method": "GET", "headers": {"Authorization": "Bearer valid_token"}, "type": "JWT", "active": True, "param": "header", "val": "payload"},
    
    # Race Condition
    {"path": "/api/v1/race/transfer", "method": "POST", "payload": {"amount": 100}, "type": "RACE", "active": True, "param": "race", "val": "race"},
    
    # False Positives (Safe)
    {"path": "/api/v1/fp/public_keys", "method": "GET", "type": "FP", "active": False},
    {"path": "/api/v1/fp/sample_credit_card", "method": "GET", "type": "FP", "active": False},
    {"path": "/api/v1/fp/uuid_list", "method": "GET", "type": "FP", "active": False},
    {"path": "/api/v1/fp/internal_ips", "method": "GET", "type": "FP", "active": False},
]

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

async def run_active_regression():
    from backend.ai.cortex import CortexEngine
    cortex = CortexEngine()
    await cortex.warm_up()

    print("=" * 80)
    print(" ANTIGRAVITY V6 — BAYESIAN ACTIVE REGRESSION PIPELINE")
    print("=" * 80)
    
    results = []
    total_error = 0.0
    semaphore = asyncio.Semaphore(10)
    
    async def process_endpoint(i, ep):
        async with semaphore:
            # 1. Alpha: Baseline Fetch
            baseline = await fetch_endpoint(ep["path"], ep["method"], ep.get("payload"), ep.get("headers"))
            
            attack_responses = []
            
            # 2. Sigma: Payload Generation
            if ep.get("active") and ep["val"] == "payload":
                payloads = await cortex.generate_attack_payloads(
                    target_url=ep["path"],
                    attack_types=[ep["type"]],
                    target_field_type="string",
                    parameter_name=ep["param"]
                )
                if not payloads:
                    payloads = ["' OR 1=1--", "<script>alert(1)</script>"] # fallback
            elif ep.get("active") and ep["val"] == "race":
                payloads = ["race_trigger"]
            elif ep.get("active"):
                payloads = [ep["val"]] # IDOR/BOLA simple mutation
            else:
                payloads = [None] # Passive

            # 3. Beta: Fire Mutations
            best_candidate = {
                "type": ep["type"],
                "url": ep["path"],
                "tag": f"Regression_{ep['type']}",
                "description": f"Baseline status: {baseline['status']}. Body: {baseline['body'][:200]}"
            }
            
            highest_anomaly = 0
            
            if ep["type"] == "RACE" and ep.get("active"):
                import asyncio
                # Fire concurrently to trigger race condition
                tasks = [fetch_endpoint(ep["path"], ep["method"], ep.get("payload"), ep.get("headers")) for _ in range(5)]
                race_resps = await asyncio.gather(*tasks)
                attack_responses.extend(race_resps)
            else:
                for p in payloads:
                    if p is None:
                        # Passive, just analyze baseline
                        attack_responses.append(baseline)
                        continue
                        
                    mutated_path = ep["path"]
                    mutated_payload = dict(ep.get("payload", {})) if ep.get("payload") else None
                    mutated_headers = dict(ep.get("headers", {})) if ep.get("headers") else None
                    
                    if ep["method"] == "GET":
                        if "?" in mutated_path:
                            base, qs = mutated_path.split("?", 1)
                            params = urllib.parse.parse_qs(qs)
                            params[ep["param"]] = p
                            mutated_path = base + "?" + urllib.parse.urlencode(params, doseq=True)
                        elif ep["param"] in mutated_path:
                            mutated_path = mutated_path.replace(ep["param"], urllib.parse.quote(p))
                    elif mutated_payload and ep["param"] in mutated_payload:
                        mutated_payload[ep["param"]] = p
                    elif mutated_headers and ep["param"] in mutated_headers:
                        mutated_headers[ep["param"]] = p
                        
                    resp = await fetch_endpoint(mutated_path, ep["method"], mutated_payload, mutated_headers)
                    attack_responses.append(resp)
            
            # 4. Gamma: Diff Computation
            for resp in attack_responses:
                # Basic diff simulation for regression
                if resp["status"] != baseline["status"] or len(resp["body"]) != len(baseline["body"]):
                    # Flag as anomalous structural change
                    desc = f"Mutation triggered change. Status {baseline['status']}->{resp['status']}. Body: {resp['body'][:300]}"
                    candidate_data = dict(best_candidate)
                    candidate_data["description"] = desc
                    candidate_data["structural_anomaly"] = 50
                    best_candidate = candidate_data
            
            # 5. Cortex: Bayesian Classification
            try:
                # We enforce FAST_MODE for pure LLM performance testing, but allow DEEP to trigger via risk gate
                # Remove force_mode to test the true Bayesian hybrid gate
                audit = await cortex.audit_candidate(best_candidate)
                
                pred_is_vuln = audit.get("is_real", False)
                confidence = audit.get("confidence", 0.0)
                reason = audit.get("reasoning", "")
            except Exception as e:
                pred_is_vuln = False
                confidence = 0.0
                reason = str(e)
                
            # Evaluate Calibration
            is_vuln_category = (ep["type"] != "FP")
            actual = 1.0 if is_vuln_category else 0.0
            p_vuln = confidence if pred_is_vuln else (1.0 - confidence)
            
            calibration_error_sq = (actual - p_vuln) ** 2
            is_correct = (pred_is_vuln == is_vuln_category)
            
            icon = "✅" if is_correct else "❌"
            
            print(f"{i:02d}. {icon} {ep['type']:<5} | EP: {ep['path'][:25]:<25} | Exp: {actual:.1f} | Pred: {pred_is_vuln!s:<5} (Conf: {confidence:.2f})")

            return {
                "calibration_error_sq": calibration_error_sq,
                "result_dict": {"path": ep["path"], "category": ep["type"], "correct": is_correct, "confidence": confidence}
            }

    tasks = [process_endpoint(i, ep) for i, ep in enumerate(ENDPOINTS, 1)]
    task_results = await asyncio.gather(*tasks)

    for tr in task_results:
        total_error += tr["calibration_error_sq"]
        results.append(tr["result_dict"])

    brier_score = total_error / len(ENDPOINTS)
    accuracy = sum(1 for r in results if r["correct"]) / len(ENDPOINTS) * 100
    
    print("\n" + "=" * 80)
    print(" 🏁 ACTIVE REGRESSION & BAYESIAN CALIBRATION RESULTS")
    print("=" * 80)
    print(f"  Accuracy:                 {accuracy:.1f}%")
    print(f"  Brier Score (Calb):       {brier_score:.4f} (Target <0.15)")
    print("=" * 80)

if __name__ == "__main__":
    print("Starting target server on port 8999...")
    server_process = subprocess.Popen([sys.executable, "backend/tests/regression_target_server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(2)
        asyncio.run(run_active_regression())
    finally:
        server_process.terminate()
        server_process.wait()
