import asyncio
import time
import json
import statistics
import sys
import os
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.ai.cortex import CortexEngine

async def benchmark_ai_methods():
    cortex = CortexEngine()
    results = []
    
    # 1. Ping Test (Standard connectivity)
    print("--- [AI PING TEST] ---")
    start_ping = time.perf_counter()
    ping_success = await cortex._call_ollama("echo ping", temperature=0.1, max_tokens=5)
    ping_time = (time.perf_counter() - start_ping) * 1000
    print(f"Ollama Ping: {ping_time:.2f}ms | Success: {not cortex._is_error(ping_success)}")
    
    test_cases = [
        ("Summary", cortex.generate_vulnerability_summary("SQL Injection", "id=1' OR '1'='1", "http://test.com")),
        ("Compliance", cortex.map_to_compliance("Broken Access Control")),
        ("Confidence", cortex.calculate_confidence_score("XSS", "<script>alert(1)</script>", "alert(1)")),
        ("Remediation Roadmap", cortex.generate_remediation_roadmap("- SQLi at /api\n- XSS at /login")),
        ("Verification Script", cortex.generate_verification_script("SQLi", "http://test.com/id=1", "1' OR '1'='1")),
        ("Attack Flow", cortex.generate_attack_flow_viz("IDOR", "http://test.com/user/5")),
        ("Business Risk", cortex.generate_business_risk_narrative("Found 5 critical SQL injections in auth module"))
    ]
    
    print("\n--- [AI METHOD BENCHMARKS] ---")
    for name, coro in test_cases:
        start = time.perf_counter()
        try:
            res = await coro
            duration = (time.perf_counter() - start) * 1000
            status = "PASS" if not cortex._is_error(str(res)) else "FAIL"
            print(f"{name:<25} | {duration:>8.2f}ms | {status}")
            results.append(duration)
        except Exception as e:
            print(f"{name:<25} | ERROR: {str(e)}")
            
    if results:
        avg = statistics.mean(results)
        print(f"\nAverage LLM Response Time: {avg:.2f}ms")
    
    # 2. Pipeline Integrity Check
    print("\n--- [PIPELINE INTEGRITY] ---")
    # Verify singleton access
    from backend.ai.cortex import cortex as cortex_singleton
    print(f"Cortex Singleton: {'READY' if cortex_singleton else 'ERROR'}")

if __name__ == "__main__":
    asyncio.run(benchmark_ai_methods())
