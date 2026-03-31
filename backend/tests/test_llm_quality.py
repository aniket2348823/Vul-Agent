"""
Antigravity V6 — LLM Quality, Ping & Latency Benchmark
Tests the Granite 4.0 (antigravity-cortex) model for:
  1. Response quality (JSON compliance, relevance)
  2. Ping / connectivity
  3. Call latency (cold + warm)
  4. Throughput under load
"""
import asyncio
import time
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.ai.cortex import CortexEngine, OLLAMA_BASE_URL, OLLAMA_MODEL

# ─── UTILITIES ───────────────────────────────────────────────────────────────

async def ping_ollama():
    """Raw HTTP ping to Ollama endpoint."""
    import aiohttp
    start = time.perf_counter()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                elapsed = (time.perf_counter() - start) * 1000
                data = await resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"status": "OK", "ping_ms": round(elapsed, 1), "models": models}
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {"status": "FAIL", "ping_ms": round(elapsed, 1), "error": str(e)}


async def measure_call(engine, prompt, label, temperature=0.2, max_tokens=128):
    """Measure a single LLM call: latency, token count, response quality."""
    start = time.perf_counter()
    try:
        result = await engine._call_ollama(prompt, temperature=temperature, max_tokens=max_tokens)
        elapsed = (time.perf_counter() - start) * 1000
        is_error = engine._is_error(result)
        return {
            "label": label,
            "latency_ms": round(elapsed, 1),
            "response_len": len(result),
            "is_error": is_error,
            "preview": result[:150].replace("\n", " "),
            "status": "FAIL" if is_error else "OK"
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "label": label,
            "latency_ms": round(elapsed, 1),
            "response_len": 0,
            "is_error": True,
            "preview": str(e)[:150],
            "status": "FAIL"
        }


async def test_json_compliance(engine):
    """Test whether Granite can return valid JSON."""
    prompt = """Classify this URL as API or web page. Return ONLY valid JSON:
{"is_api": true/false, "category": "string"}

URL: /api/v1/users/123/profile"""
    
    start = time.perf_counter()
    result = await engine._call_ollama(prompt, temperature=0.0, max_tokens=64)
    elapsed = (time.perf_counter() - start) * 1000
    
    try:
        # Strip markdown code fences if present
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.strip()
        
        parsed = json.loads(clean)
        return {
            "label": "JSON Compliance",
            "latency_ms": round(elapsed, 1),
            "status": "PASS",
            "parsed": parsed,
            "raw": result[:200]
        }
    except json.JSONDecodeError as e:
        return {
            "label": "JSON Compliance",
            "latency_ms": round(elapsed, 1),
            "status": "FAIL",
            "error": str(e),
            "raw": result[:200]
        }


async def test_security_reasoning(engine):
    """Test Granite's ability to reason about security vulns."""
    prompt = """Is this endpoint vulnerable to IDOR?
URL: GET /api/v1/user/1005
Response: {"id": 1005, "username": "victim_user", "email": "victim@corp.com"}
Answer with "yes" or "no" and one sentence of reasoning."""

    start = time.perf_counter()
    result = await engine._call_ollama(prompt, temperature=0.0, max_tokens=100)
    elapsed = (time.perf_counter() - start) * 1000
    
    has_yes = "yes" in result.lower()
    return {
        "label": "Security Reasoning",
        "latency_ms": round(elapsed, 1),
        "status": "PASS" if has_yes else "WARN",
        "detected_vuln": has_yes,
        "response": result[:200]
    }


# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("  ANTIGRAVITY V6 — GRANITE 4.0 LLM QUALITY BENCHMARK")
    print("=" * 70)
    print(f"  Model:    {OLLAMA_MODEL}")
    print(f"  Endpoint: {OLLAMA_BASE_URL}")
    print()

    # ── TEST 1: PING ──
    print("-" * 70)
    print("  TEST 1: OLLAMA PING")
    print("-" * 70)
    ping = await ping_ollama()
    print(f"  Status:   {ping['status']}")
    print(f"  Ping:     {ping['ping_ms']}ms")
    if ping["status"] == "OK":
        print(f"  Models:   {', '.join(ping['models'])}")
    else:
        print(f"  Error:    {ping.get('error', 'Unknown')}")
        print("\n  ❌ OLLAMA IS OFFLINE. Cannot proceed.")
        return False
    print()

    engine = CortexEngine()

    # ── TEST 2: COLD START LATENCY ──
    print("-" * 70)
    print("  TEST 2: COLD START LATENCY")
    print("-" * 70)
    cold = await measure_call(engine, "Reply with 'READY'.", "Cold Start", max_tokens=16)
    print(f"  Status:   {cold['status']}")
    print(f"  Latency:  {cold['latency_ms']}ms")
    print(f"  Response: {cold['preview']}")
    print()

    # ── TEST 3: WARM LATENCY (3 calls) ──
    print("-" * 70)
    print("  TEST 3: WARM LATENCY (3 sequential calls)")
    print("-" * 70)
    warm_results = []
    for i in range(3):
        w = await measure_call(engine, f"Reply with the number {i+1}.", f"Warm #{i+1}", max_tokens=16)
        warm_results.append(w)
        print(f"  Call {i+1}: {w['latency_ms']}ms | {w['status']} | '{w['preview']}'")
    avg_warm = sum(r["latency_ms"] for r in warm_results) / len(warm_results)
    print(f"  Average:  {avg_warm:.0f}ms")
    print()

    # ── TEST 4: JSON COMPLIANCE ──
    print("-" * 70)
    print("  TEST 4: JSON COMPLIANCE")
    print("-" * 70)
    json_test = await test_json_compliance(engine)
    print(f"  Status:   {json_test['status']}")
    print(f"  Latency:  {json_test['latency_ms']}ms")
    if json_test["status"] == "PASS":
        print(f"  Parsed:   {json_test['parsed']}")
    else:
        print(f"  Error:    {json_test.get('error', '')}")
        print(f"  Raw:      {json_test['raw']}")
    print()

    # ── TEST 5: SECURITY REASONING ──
    print("-" * 70)
    print("  TEST 5: SECURITY REASONING (IDOR Detection)")
    print("-" * 70)
    sec_test = await test_security_reasoning(engine)
    print(f"  Status:       {sec_test['status']}")
    print(f"  Latency:      {sec_test['latency_ms']}ms")
    print(f"  Detected:     {'Yes' if sec_test['detected_vuln'] else 'No'}")
    print(f"  Response:     {sec_test['response']}")
    print()

    # ── TEST 6: THROUGHPUT (5 concurrent) ──
    print("-" * 70)
    print("  TEST 6: CONCURRENT THROUGHPUT (5 simultaneous calls)")
    print("-" * 70)
    prompts = [
        ("Classify: SQL Injection", "Reply: SQLi"),
        ("Classify: XSS", "Reply: XSS"),
        ("Classify: IDOR", "Reply: IDOR"),
        ("Classify: Race Condition", "Reply: Race"),
        ("Classify: Auth Bypass", "Reply: AuthBypass"),
    ]
    start_batch = time.perf_counter()
    tasks = [measure_call(engine, p[0], p[1], max_tokens=32) for p in prompts]
    batch_results = await asyncio.gather(*tasks)
    batch_elapsed = (time.perf_counter() - start_batch) * 1000
    
    for r in batch_results:
        print(f"  {r['label']}: {r['latency_ms']}ms | {r['status']}")
    print(f"  Total Wall Time: {batch_elapsed:.0f}ms")
    print(f"  Avg Per Call:    {sum(r['latency_ms'] for r in batch_results)/len(batch_results):.0f}ms")
    print()

    # ── TELEMETRY ──
    print("-" * 70)
    print("  TELEMETRY SUMMARY")
    print("-" * 70)
    telemetry = engine.get_telemetry()
    print(f"  Total LLM Calls:   {telemetry.get('llm_calls', 0)}")
    print(f"  Successful:        {telemetry.get('llm_successes', 0)}")
    print(f"  Failures:          {telemetry.get('llm_failures', 0)}")
    print(f"  Avg Latency:       {telemetry.get('avg_llm_latency', 0):.0f}ms")
    print(f"  Input Tokens:      {telemetry.get('llm_input_tokens', 0)}")
    print(f"  Output Tokens:     {telemetry.get('llm_output_tokens', 0)}")
    print()

    # ── FINAL VERDICT ──
    all_ok = (
        ping["status"] == "OK" and
        cold["status"] == "OK" and
        all(r["status"] == "OK" for r in warm_results) and
        json_test["status"] == "PASS"
    )
    
    print("=" * 70)
    if all_ok:
        print("  ✅ GRANITE 4.0 LLM QUALITY: ALL TESTS PASSED")
    else:
        print("  ⚠️ GRANITE 4.0 LLM QUALITY: SOME ISSUES DETECTED")
    print("=" * 70)
    
    return all_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
