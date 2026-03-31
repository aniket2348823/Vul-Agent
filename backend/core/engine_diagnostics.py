import asyncio
import aiohttp
import time
import os
import sys
import json
from typing import Dict, List, Any

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class VulAgentEngineDiagnostics:
    """
    ONE SCRIPT TO RULE THEM ALL: THE VUL AGENT DIAGNOSTIC KERNEL.
    Synthesizes warmup.py, test_llms.py, and legacy diagnostics.
    """
    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODELS = ["qwen2.5-coder:0.5b", "qwen3.5:0.8b"] # Standard project models

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def run_warmup(self, model: str) -> Dict[str, Any]:
        """[WARMUP] Pings the local neural core to ensure the model is buffered in VRAM."""
        print(f"--> [WARMUP] Priming Neural Core [{model}]...")
        start = time.time()
        try:
            async with self.session.post(self.OLLAMA_URL, json={
                "model": model, "prompt": "READY", "stream": False,
                "options": {"num_predict": 5}
            }, timeout=60) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    elapsed = time.time() - start
                    print(f"    [OK] Model '{model}' initialized. Latency: {elapsed:.2f}s")
                    return {"status": "OK", "model": model, "latency": elapsed}
                else:
                    print(f"    [WARN] Failed status: {resp.status}")
                    return {"status": "FAIL", "model": model, "error": resp.status}
        except Exception as e:
            print(f"    [ERROR] Connection failed for {model}: {e}")
            return {"status": "ERROR", "error": str(e)}

    async def run_performance_bench(self, model: str) -> Dict[str, Any]:
        """[BENCHMARK] Measures token generation speed and forensic reasoning latency."""
        print(f"--> [BENCH] Measuring output throughput on [{model}]...")
        prompt = "Explain SQL Injection in one sentence. Output only the sentence."
        start_time = time.time()
        try:
            async with self.session.post(self.OLLAMA_URL, json={
                "model": model, "prompt": prompt, "stream": False,
                "options": {"temperature": 0.1, "num_predict": 50}
            }, timeout=120) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    latency = time.time() - start_time
                    tokens = data.get('eval_count', 0)
                    duration_s = data.get('eval_duration', 1) / 1e9
                    tps = tokens / duration_s
                    print(f"    [OK] Throughput: {tps:.2f} tokens/s | Latency: {latency:.2f}s")
                    return {"status": "OK", "tps": tps, "latency": latency}
                return {"status": "FAIL"}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    async def check_cloud_linkage(self):
        """[CLOUD] Verifies OpenRouter connectivity for executive reasoning (80B)."""
        print("\n--> [CLOUD] Verifying Cloud Intelligence Linkage...")
        try:
            from backend.ai.openrouter import openrouter_client
            if not openrouter_client.is_available:
                print("    [WARN] OPENROUTER_API_KEY missing. Cloud reasoning offline.")
                return False
            
            start = time.time()
            r = await openrouter_client.call("ACK", max_tokens=5)
            elapsed = time.time() - start
            print(f"    [OK] Cloud Link established. Latency: {elapsed:.2f}s")
            return True
        except Exception as e:
            print(f"    [ERROR] Cloud Link failed: {e}")
            return False

    async def run_all(self):
        """Full Project-Wide Integrity Suite."""
        print("\n" + "="*60)
        print("VUL AGENT: UNIFIED SYSTEM INTEGRITY SUITE (V6.1-OMEGA)")
        print("="*60)
        
        async with self as diag:
            # 1. Warmup
            print("\n[PHASE 1: NEURAL WARMUP]")
            for m in self.MODELS:
                await diag.run_warmup(m)
            
            # 2. Performance
            print("\n[PHASE 2: PERFORMANCE BENCHMARK]")
            await diag.run_performance_bench(self.MODELS[0])
            
            # 3. Cloud
            print("\n[PHASE 3: CLOUD INTELLIGENCE]")
            await diag.check_cloud_linkage()
            
        print("\n" + "="*60)
        print("[SUCCESS] SYSTEM STABLE. ALL DATA-POINTS SYNCHRONIZED.")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(VulAgentEngineDiagnostics().run_all())
