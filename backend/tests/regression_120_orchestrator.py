import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
import urllib.parse
import sys
import aiohttp
from collections import defaultdict

sys.path.insert(0, ".")

TARGET_URL = "http://127.0.0.1:8999"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(REPORT_DIR, "validation_120_history.json")

async def fetch_endpoint(path: str, method="GET", payload=None, headers=None) -> dict:
    url = f"{TARGET_URL}{path}"
    try:
        async with aiohttp.ClientSession() as session:
            start_t = time.perf_counter()
            if method == "GET":
                async with session.get(url, headers=headers, timeout=5) as resp:
                    text = await resp.text()
            elif method in ("POST", "PUT", "DELETE"):
                async with session.request(method, url, data=payload, headers=headers, timeout=5) as resp:
                    text = await resp.text()
            lat = (time.perf_counter() - start_t) * 1000
            if "resp" not in locals():
                return {"status": 500, "body": "", "lat": lat}
            return {"status": resp.status, "body": text, "lat": lat}
    except Exception as e:
        return {"status": 500, "body": str(e), "lat": 0}

async def fetch_scenario_list():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{TARGET_URL}/_metrics/scenarios") as resp:
            return await resp.json()

async def run_sweep(sweep_id: int):
    from backend.ai.cortex import CortexEngine, get_cortex_engine
    cortex = get_cortex_engine()
    
    # Optional warmup
    if sweep_id == 1:
        await cortex.warm_up()
        
    print(f"\n" + "=" * 80)
    print(f" 🚀 STARTING 120-SCENARIO VALIDATION SWEEP #{sweep_id}")
    print("=" * 80)
    
    # Fetch 120 scenarios dynamically
    endpoints = await fetch_scenario_list()
    if not endpoints:
        print("Failed to fetch scenarios.")
        return None

    results = []
    total_error = 0.0
    
    # Class-level metrics
    class_errors = defaultdict(float)
    class_counts = defaultdict(int)
    class_correct = defaultdict(int)

    # Global tracking
    overconfident_errors = 0
    fast_mode_count = 0
    deep_mode_count = 0
    total_latency = 0.0

    semantic_lock = asyncio.Semaphore(4) # Lowered to prevent Ollama timeout on 8GB RAM

    async def process_scenario(ep):
        async with semantic_lock:
            # 1. Alpha: Baseline
            baseline = await fetch_endpoint(ep["path"], ep["method"])
            
            # 2. Sigma: Payload Gen
            payloads = []
            if ep.get("active"):
                if ep["type"] == "RACE":
                    payloads = ["race_trigger"]
                else: 
                    payloads = [ep["val"]] # Fallback generic
            else:
                payloads = [None]
                
            attack_responses = []
            highest_latency = baseline["lat"]

            # 3. Beta: Fire
            if ep["type"] == "RACE":
                tasks = [fetch_endpoint(ep["path"], ep["method"]) for _ in range(5)]
                race_resps = await asyncio.gather(*tasks)
                attack_responses.extend(race_resps)
            else:
                for p in payloads:
                    if p is None:
                        attack_responses.append(baseline)
                        continue
                    
                    m_path = ep["path"]
                    m_data = None
                    m_headers = None
                    
                    if ep["method"] == "GET":
                        if "?" in m_path:
                            b, q = m_path.split("?", 1)
                            params = urllib.parse.parse_qs(q)
                            params[ep["param"]] = p
                            m_path = b + "?" + urllib.parse.urlencode(params, doseq=True)
                        elif "{" in m_path: # simplified
                            pass
                        elif ep["param"] in m_path:
                            m_path = m_path.replace(ep["param"], urllib.parse.quote(str(p)))
                        else: # Just append query
                            m_path = m_path + f"?{ep['param']}={urllib.parse.quote(str(p))}"
                            
                    elif ep["method"] == "POST":
                        m_data = {ep["param"]: p}
                        
                    resp = await fetch_endpoint(m_path, ep["method"], payload=m_data, headers=m_headers)
                    attack_responses.append(resp)
            
            # 4. Gamma: Diff Compute
            c_data = {
                "type": ep["type"],
                "url": ep["path"],
                "tag": f"Regression_{ep['type']}",
                "description": f"Baseline status: {baseline['status']}. Body: {baseline['body'][:100]}"
            }
            
            for r in attack_responses:
                highest_latency = max(highest_latency, r["lat"])
                if r["status"] != baseline["status"] or len(r["body"]) != len(baseline["body"]):
                    c_data["description"] = f"Mutation Triggered: {baseline['status']}->{r['status']}. Body: {r['body'][:200]}"
                    c_data["structural_anomaly"] = 60 # Push higher for dynamic diffs

            # 5. Cortex: Posterior Calc
            start_inf = time.perf_counter()
            try:
                audit = await cortex.audit_candidate(c_data)
                pred_v = audit.get("is_real", False)
                conf = audit.get("confidence", 0.0)
                reason = audit.get("reasoning", "")
                mode = "DEEP_MODE" if "DEEP_MODE" in reason else "FAST_MODE"
            except Exception as e:
                pred_v = False
                conf = 0.0
                reason = str(e)
                mode = "FAST_MODE"
            inf_lat = (time.perf_counter() - start_inf) * 1000

            # 6. Eval
            is_vuln_expected = (ep["ground_truth"] == "EXPLOITABLE")
            actual_y = 1.0 if is_vuln_expected else 0.0
            p_vuln = conf if pred_v else (1.0 - conf)
            
            calb_err = (actual_y - p_vuln) ** 2
            correct = (pred_v == is_vuln_expected)
            
            overconf = 1 if (not correct and conf > 0.8) else 0
            
            print(f"[{ep['type']:<5}] {ep['path'][:25]:<25} | Truth: {actual_y:.0f} | Pred: {pred_v!s:<5} "
                  f"| Conf: {conf:.2f} | Mode: {mode:<9} | Lat: {inf_lat:.0f}ms")

            return {
                "type": ep["type"],
                "err": calb_err,
                "correct": correct,
                "overconf": overconf,
                "mode": mode,
                "lat": inf_lat
            }

    tasks = [process_scenario(ep) for ep in endpoints]
    task_results = await asyncio.gather(*tasks)

    for tr in task_results:
        t_type = tr["type"]
        total_error += tr["err"]
        class_errors[t_type] += tr["err"]
        class_counts[t_type] += 1
        if tr["correct"]:
            class_correct[t_type] += 1
        if tr["overconf"]:
            overconfident_errors += 1
        if tr["mode"] == "FAST_MODE":
            fast_mode_count += 1
        else:
            deep_mode_count += 1
        total_latency += tr["lat"]

    n = len(endpoints)
    g_acc = sum(class_correct.values()) / n * 100
    g_brier = total_error / n
    avg_lat = total_latency / n
    f_ratio = (fast_mode_count / n) * 100

    print("\n" + "=" * 60)
    print(f" SWEEP #{sweep_id} SUMMARY ")
    print("=" * 60)
    print(f" Global Accuracy:       {g_acc:.1f}%")
    print(f" Global Brier:          {g_brier:.4f}")
    print(f" Overconfident Errors:  {overconfident_errors}")
    print(f" FAST_MODE Ratio:       {f_ratio:.1f}%")
    print(f" Average Latency:       {avg_lat:.0f}ms")
    
    print("\n [PER-CLASS BRIER]")
    for k in sorted(class_counts.keys()):
        c_acc = (class_correct[k] / class_counts[k]) * 100
        c_brier = class_errors[k] / class_counts[k]
        print(f"  {k:<6}: Acc {c_acc:5.1f}% | Brier {c_brier:.4f}")
        
    return {
        "sweep": sweep_id,
        "acc": g_acc,
        "brier": g_brier,
        "overconf": overconfident_errors,
        "fast_ratio": f_ratio,
        "avg_lat": avg_lat
    }

async def run_all_sweeps():
    print("Starting target server on port 8999...")
    server = subprocess.Popen([sys.executable, "backend/tests/scenario_server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    history = []
    
    try:
        time.sleep(3) # Wait for startup
        for i in range(1, 4):
            res = await run_sweep(i)
            if res:
                history.append(res)
            # Give Ollama breathing room between sweeps
            await asyncio.sleep(5)
            
        print("\n\n" + "=" * 80)
        print(" 🏆 FINAL 120-SCENARIO VALIDATION COMPLETE")
        print("=" * 80)
        for i, h in enumerate(history, 1):
             print(f" Sweep {i}: Brier {h['brier']:.4f} | Acc {h['acc']:.1f}% | Lat {h['avg_lat']:.0f}ms | Overconf {h['overconf']}")
             
        # Write history
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
            
    finally:
        server.terminate()
        server.wait()

if __name__ == "__main__":
    asyncio.run(run_all_sweeps())
