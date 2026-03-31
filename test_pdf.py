import asyncio
import os
import sys

# Ensure backend modules can be imported
sys.path.append(os.path.abspath('.'))

from backend.core.reporting import ReportGenerator

async def test_report():
    print("Initializing ReportGenerator...")
    rg = ReportGenerator()
    
    events = [
        {
            "type": "VULN_CONFIRMED",
            "source": "GI-5 Omega",
            "timestamp": "2024-03-05 10:00:00",
            "payload": {
                "type": "SQL_INJECTION",
                "url": "http://example.com/api/users",
                "method": "POST",
                "param": "id",
                "data": "1' OR '1'='1",
                "headers": {"User-Agent": "Antigravity/V6"}
            }
        }
    ]
    
    telemetry = {
        "start_time": "2024-03-05 10:00:00",
        "end_time": "2024-03-05 10:01:00",
        "duration": "60",
        "total_requests": 1500,
        "avg_latency_ms": 35,
        "peak_concurrency": 10,
        "ai_calls": 5,
        "llm_avg_latency": 1500,
        "circuit_breaker_activations": 0
    }
    
    print("Triggering generate_report (This calls Cortex/Ollama)...")
    try:
        pdf_path = await rg.generate_report(
            scan_id="MANUAL_DEBUG_TEST",
            events=events,
            target_url="http://example.com",
            telemetry=telemetry
        )
        print(f"DONE. Report generated at: {pdf_path}")
    except Exception as e:
        print(f"CRASH: {e}")

if __name__ == "__main__":
    asyncio.run(test_report())
