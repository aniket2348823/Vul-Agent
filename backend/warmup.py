import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELS = ["qwen2.5-coder:0.5b", "phi4-mini", "qwen3.5:0.8b"]

def warmup():
    print("Initializing Deep Scan Warmup Sequence...\n")
    for model in MODELS:
        print(f"--> Pinging Neural Core [{model}]...")
        start = time.time()
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": model,
                "prompt": "Respond with the single word: READY",
                "stream": False,
                "options": {"num_predict": 5}
            }, timeout=60)
            
            if resp.status_code == 200:
                elapsed = time.time() - start
                result = resp.json().get("response", "").strip()
                print(f"    [OK] Model '{model}' loaded into memory. Response: '{result}' ({elapsed:.2f}s)")
            else:
                print(f"    [WARN] Failed to load '{model}'. Status: {resp.status_code}")
        except requests.exceptions.Timeout:
            print(f"    [WARN] Request to '{model}' timed out. It might be downloading or taking too long.")
        except requests.exceptions.ConnectionError:
            print(f"    [ERROR] Cannot connect to Ollama at {OLLAMA_URL}. Is it running?")
            return
            
    print("\n[SUCCESS] All LLMs are warmed up and ready for Deep Scan.")

if __name__ == "__main__":
    warmup()
