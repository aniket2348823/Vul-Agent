import asyncio
import time
import uuid
import json
from fastapi import FastAPI, Request, Response, Form, Header, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Antigravity 120-Scenario Regression Target")

SCENARIOS = []

def register_endpoint(path: str, method: str, cat: str, active: bool, param: str, val: str, is_vuln: bool, func):
    SCENARIOS.append({
        "path": path,
        "method": method,
        "type": cat,
        "active": active,
        "param": param,
        "val": val,
        "ground_truth": "EXPLOITABLE" if is_vuln else "SAFE"
    })
    app.add_api_route(path, func, methods=[method])

# 1. SQLi Error-Based (15)
for i in range(15):
    async def sqli_error(req: Request, param_val: str = "1"):
        if "'" in param_val or "OR" in param_val.upper():
            return JSONResponse(status_code=500, content={"error": "SQL syntax error near 'EOF'"})
        return {"data": "valid_user"}
    
    register_endpoint(f"/api/v1/sqli/error/{i}", "GET", "SQLI", True, "param_val", "' OR 1=1--", True, sqli_error)

# 2. SQLi Blind/Time (15)
for i in range(15):
    async def sqli_time(req: Request, q: str = "test"):
        if "sleep(" in q.lower() or "pg_sleep" in q.lower():
            await asyncio.sleep(1)
            return {"results": []}
        return {"results": [{"id": 1}]}

    register_endpoint(f"/api/v1/sqli/time/{i}", "GET", "SQLI", True, "q", "' OR pg_sleep(1)--", True, sqli_time)

# 3. IDOR (15)
for i in range(15):
    async def idor_scenario(req: Request, user_id: int):
        # Always accepts requests for other IDs
        return {"user_id": user_id, "secret_data": f"Secret {user_id}"}
        
    register_endpoint(f"/api/v1/idor/{i}/view", "GET", "IDOR", True, "user_id", "999", True, idor_scenario)

# 4. BOLA (15) - Privilege Esc
for i in range(15):
    async def bola_scenario(req: Request, role: str = "user"):
        return {"assigned_role": role, "status": "updated"}
        
    register_endpoint(f"/api/v1/bola/{i}/update_role", "POST", "BOLA", True, "role", "admin", True, bola_scenario)

# 5. JWT (10)
for i in range(10):
    async def jwt_scenario(req: Request, authorization: str = Header("Bearer xyz")):
        if "none" in authorization.lower() or "admin" in authorization:
            return {"access": "granted_admin"}
        return {"access": "denied"}
        
    register_endpoint(f"/api/v1/jwt/{i}/admin", "GET", "JWT", True, "authorization", "Bearer eyJhbGciOiJub25lIn0.", True, jwt_scenario)

# 6. XSS (10)
for i in range(5):
    async def xss_reflected(req: Request, search: str = ""):
        return HTMLResponse(content=f"<html><body>{search}</body></html>")
    register_endpoint(f"/api/v1/xss/ref/{i}", "GET", "XSS", True, "search", "<script>alert(1)</script>", True, xss_reflected)

for i in range(5):
    async def xss_stored(req: Request, payload: dict):
        # Fake storing and rendering behavior based on POST payload length/content
        if "<" in payload.get("body", ""):
            return {"status": "saved", "rendered": payload["body"]}
        return {"status": "saved"}
    register_endpoint(f"/api/v1/xss/stored/{i}", "POST", "XSS", True, "body", "<img src=x onerror=prompt()>", True, xss_stored)

# 7. LOGIC (15)
for i in range(15):
    async def logic_scenario(req: Request, step: str = "1"):
        if step == "3":
            return {"status": "purchased_without_payment"}
        return {"status": "pending_payment"}
        
    register_endpoint(f"/api/v1/logic/{i}/checkout", "GET", "LOGIC", True, "step", "3", True, logic_scenario)

# 8. RACE (10)
for i in range(10):
    async def race_scenario(req: Request):
        await asyncio.sleep(0.01) # 10ms race window
        return {"status": "applied_coupon"}
        
    register_endpoint(f"/api/v1/race/{i}/apply", "POST", "RACE", True, "race", "race", True, race_scenario)

# 9. SAFE False Positives (15)
for i in range(15):
    async def safe_scenario(req: Request):
        # Looks sensitive but is hardcoded SAFE
        return {"dummy_key": "ssh-rsa AAAAB3NzaC1", "demo_cc": "4000 0000 0000 0000"}
        
    register_endpoint(f"/api/v1/fp/{i}/docs", "GET", "SAFE", False, "none", "none", False, safe_scenario)


@app.get("/_metrics/scenarios")
async def get_scenarios():
    return SCENARIOS

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8999, log_level="warning")
