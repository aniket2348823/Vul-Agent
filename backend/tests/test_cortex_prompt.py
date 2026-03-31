import asyncio
import json
import sys
sys.path.insert(0, ".")

async def test():
    from backend.ai.cortex import CortexEngine
    c = CortexEngine()
    await c.warm_up()
    
    print("Testing safe case...")
    safe_case = {
        "url": f"/api/torture/v1/0/1",
        "method": "GET",
        "type": "FP",
        "tag": f"Regression_Torture_FP",
        "description": "Baseline vs attack. Normal behavior.",
        "structural_anomaly": 10,
        "force_mode": "FAST_MODE"
    }
    
    res1 = await c.audit_candidate(safe_case)
    print("SAFE:", json.dumps(res1, indent=2))
    
    print("Testing vuln case...")
    vuln_case = {
        "url": f"/api/torture/v1/0/0",
        "method": "GET",
        "type": "SQLI",
        "tag": f"Regression_Torture_SQLI",
        "description": "Baseline vs attack. SQL syntax error detected in database.",
        "structural_anomaly": 90,
        "force_mode": "FAST_MODE"
    }
    
    res2 = await c.audit_candidate(vuln_case)
    print("VULN:", json.dumps(res2, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
