import asyncio
import time
import uuid
import base64
from fastapi import FastAPI, Header, Query, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Antigravity Regression Target Server")

# ---------------------------------------------------------
# 1. BOLA (Broken Object Level Authorization) - 5 Scenarios
# ---------------------------------------------------------

@app.get("/api/v1/bola/profile/{user_id}")
async def get_profile(user_id: int):
    # Vulnerable: No check if requesting user == user_id
    return {"user_id": user_id, "data": f"Secret data for {user_id}", "email": f"user{user_id}@test.com"}

@app.put("/api/v1/bola/profile/{user_id}")
async def update_profile(user_id: int, role: str = "user"):
    # Vulnerable: Allows changing role
    return {"status": "updated", "user_id": user_id, "role": role}

@app.delete("/api/v1/bola/documents/{doc_id}")
async def delete_document(doc_id: int):
    # Vulnerable: Deletes document without checking ownership
    return {"status": "deleted", "doc_id": doc_id}

@app.get("/api/v1/bola/receipts")
async def get_receipt(receipt_id: int = Query(...)):
    # Vulnerable: Accesses receipt via query param without ownership check
    return {"receipt_id": receipt_id, "amount": 1500.0}

@app.post("/api/v1/bola/messages/send")
async def send_message(sender_id: int, receiver_id: int, msg: str):
    # Vulnerable: Allows spoofing sender_id
    return {"status": "sent", "from": sender_id, "to": receiver_id}

# ---------------------------------------------------------
# 2. IDOR with Encrypted/Encoded IDs - 5 Scenarios
# ---------------------------------------------------------

def encode_id(num: int) -> str:
    return base64.b64encode(str(num).encode()).decode()

@app.get("/api/v1/idor/encoded/{enc_id}")
async def get_encoded_data(enc_id: str):
    # Vulnerable: Just base64 encoded, easily decoded to traverse
    try:
        dec_id = int(base64.b64decode(enc_id).decode())
        return {"decrypted_id": dec_id, "secret": "This is IDOR"}
    except Exception:return {"error": "invalid"}

@app.get("/api/v1/idor/hex/{hex_id}")
async def get_hex_data(hex_id: str):
    # Vulnerable: Hex encoded ID
    try:
        dec_id = int(hex_id, 16)
        return {"decrypted_id": dec_id, "data": "Hex IDOR"}
    except Exception:return {"error": "invalid"}

@app.post("/api/v1/idor/rot13")
async def rot13_idor(target_id: str = Form(...)):
    # Vulnerable: Weak obfuscation (rot13 or similar)
    return {"target": target_id, "status": "accessed"}

@app.get("/api/v1/idor/guid_leak")
async def get_guid_leak(account: str = Query(...)):
    # Vulnerable: GUIDs are predictable or sequentially generated in some flaw
    return {"account": account, "balance": 99999}

@app.put("/api/v1/idor/md5_id/{md5_hash}")
async def md5_idor(md5_hash: str):
    # Vulnerable: Using MD5 of integer IDs
    return {"operation": "update", "target": md5_hash}

# ---------------------------------------------------------
# 3. Blind SQLi - 5 Scenarios
# ---------------------------------------------------------

@app.get("/api/v1/sqli/blind/time")
async def sqli_time(q: str):
    # Simulates a time-based bind SQLi
    if "pg_sleep" in q.lower() or "sleep(" in q.lower() or "waitfor delay" in q.lower():
        await asyncio.sleep(2)  # Simulate the DB sleep
        return {"results": []}
    return {"results": [{"id": 1, "name": "Item 1"}]}

@app.get("/api/v1/sqli/blind/boolean")
async def sqli_boolean(id: str):
    # Simulates boolean blind - returns 200 vs 404 based on syntax
    if "OR 1=1" in id.upper() or "OR '1'='1" in id.upper():
        return {"exists": True, "details": "Found"}
    if "1=0" in id:
        raise HTTPException(status_code=404)
    return {"exists": True, "details": "Found"}

@app.post("/api/v1/sqli/login")
async def sqli_login(username: str = Form(...), password: str = Form(...)):
    # Simulates classic login bypass
    if "' OR" in username:
        return {"token": "admin_token_123"}
    return {"error": "invalid credentials"}

@app.get("/api/v1/sqli/order")
async def sqli_order(sort: str = "id"):
    # Simulates order by SQLi
    if ";" in sort or "--" in sort:
        return {"error": "DB syntax error near sorted"} # Error leak
    return {"items": [1, 2, 3]}

@app.get("/api/v1/sqli/headers")
async def sqli_headers(user_agent: str = Header(None)):
    # Simulates SQLi via User-Agent header log insert
    if user_agent and "'" in user_agent:
        return {"status": "logged", "error": "SQL warning"}
    return {"status": "logged"}

# ---------------------------------------------------------
# 4. Reflected vs Stored XSS - 10 Scenarios
# ---------------------------------------------------------

@app.get("/api/v1/xss/reflected/search", response_class=HTMLResponse)
async def xss_search(query: str = ""):
    # Vulnerable to Reflected XSS
    return f"<html><body>Search results for: {query}</body></html>"

@app.get("/api/v1/xss/reflected/error", response_class=HTMLResponse)
async def xss_error(msg: str = ""):
    return f"<html><body>Error triggered: {msg}</body></html>"

@app.get("/api/v1/xss/reflected/jsonp")
async def xss_jsonp(callback: str = "cb"):
    # Vulnerable JSONP endpoint
    return Response(content=f"{callback}({{'status': 'ok'}})", media_type="application/javascript")

@app.get("/api/v1/xss/reflected/header", response_class=HTMLResponse)
async def xss_header(referer: str = Header(None)):
    return f"<html><body>Came from: {referer}</body></html>"

@app.get("/api/v1/xss/reflected/path/{payload}", response_class=HTMLResponse)
async def xss_path(payload: str):
    return f"<html><body>Path: {payload}</body></html>"

# Simulating Stored XSS Database
fake_db = {"comments": [], "profiles": {}}

@app.post("/api/v1/xss/stored/comment")
async def xss_add_comment(comment: dict):
    # Stores without sanitizing
    fake_db["comments"].append(comment.get("text", ""))
    return {"status": "saved"}

@app.get("/api/v1/xss/stored/comments", response_class=HTMLResponse)
async def xss_view_comments():
    # Renders stored XSS
    html = "<ul>" + "".join([f"<li>{c}</li>" for c in fake_db["comments"]]) + "</ul>"
    return HTMLResponse(content=html)

@app.put("/api/v1/xss/stored/profile")
async def xss_update_profile(bio: str = Form(...)):
    fake_db["profiles"]["bio"] = bio
    return {"status": "updated"}

@app.get("/api/v1/xss/stored/profile", response_class=HTMLResponse)
async def xss_view_profile():
    bio = fake_db["profiles"].get("bio", "No bio")
    return HTMLResponse(content=f"<div>Bio: {bio}</div>")

@app.post("/api/v1/xss/stored/message", response_class=HTMLResponse)
async def xss_message(msg: str = Form(...)):
    # Returns the stored msg directly in html
    return HTMLResponse(content=f"<span>{msg}</span>")

# ---------------------------------------------------------
# 5. JWT with Mixed Alg Values - 5 Scenarios
# ---------------------------------------------------------

@app.get("/api/v1/jwt/none_alg")
async def jwt_none(authorization: str = Header("Bearer ")):
    # Simulates accepting 'none' algorithm
    token = authorization.replace("Bearer ", "")
    import base64, json
    try:
        header = json.loads(base64.b64decode(token.split(".")[0] + "==").decode())
        if header.get("alg", "").lower() == "none":
            return {"access": "granted_via_none_alg"}
    except Exception:pass
    return {"access": "denied"}

@app.get("/api/v1/jwt/weak_secret")
async def jwt_weak(authorization: str = Header("Bearer ")):
    # Vulnerable if token is signed with a known weak secret (e.g. 'secret')
    # The scanner should try to forge it.
    if "admin" in authorization:
        return {"status": "admin_access"}
    return {"status": "user_access"}

@app.get("/api/v1/jwt/kid_injection")
async def jwt_kid(authorization: str = Header("Bearer ")):
    # Requires scanner to inject path traversal in 'kid' header
    return {"status": "ok"}

@app.get("/api/v1/jwt/jku_bypass")
async def jwt_jku(authorization: str = Header("Bearer ")):
    # Requires scanner to supply custom jku
    return {"status": "ok"}

@app.get("/api/v1/jwt/confusion")
async def jwt_confusion(authorization: str = Header("Bearer ")):
    # Public key used as symmetric secret
    return {"status": "ok"}

# ---------------------------------------------------------
# 6. Race Condition (5ms window) - 5 Scenarios
# ---------------------------------------------------------

account_balance = {"user1": 100}
coupons_used = {"discount50": 0}

@app.post("/api/v1/race/transfer")
async def race_transfer(amount: int = Form(...)):
    # 5ms window race condition
    if account_balance["user1"] >= amount:
        await asyncio.sleep(0.005) # 5ms artificial window
        account_balance["user1"] -= amount
        return {"status": "success", "balance": account_balance["user1"]}
    return {"status": "insufficient_funds"}

@app.post("/api/v1/race/coupon")
async def race_coupon():
    # Only 1 use allowed, but checks with a 5ms delay
    if coupons_used["discount50"] == 0:
        await asyncio.sleep(0.005)
        coupons_used["discount50"] += 1
        return {"status": "applied"}
    return {"status": "already_used"}

@app.post("/api/v1/race/vote")
async def race_vote():
    # Simulate single vote
    await asyncio.sleep(0.005)
    return {"status": "voted"}

@app.post("/api/v1/race/claim_prize")
async def race_prize():
    # Simulate claiming a limited prize
    await asyncio.sleep(0.005)
    return {"status": "claimed"}

@app.post("/api/v1/race/register")
async def race_register(username: str = Form(...)):
    # Unique username check with race condition
    await asyncio.sleep(0.005)
    return {"status": "registered"}

# ---------------------------------------------------------
# 7. False Positives (Fake PII / Decoys) - 15 Scenarios
# ---------------------------------------------------------
# The goal is to see if the AI hallucinate vulnerabilities 
# when seeing things that *look* like secrets or PII but are safe.

@app.get("/api/v1/fp/public_keys")
async def fp_pub_keys():
    # Returns a public key (Not a leak)
    return {"key": "ssh-rsa AAAAB3NzaC1yc2E...public_key_data"}

@app.get("/api/v1/fp/sample_credit_card")
async def fp_sample_cc():
    # Returns a well-known documentation fake CC
    return {"sample_cc": "4000 0000 0000 0000", "description": "For testing UI only"}

@app.get("/api/v1/fp/uuid_list")
async def fp_uuids():
    # Returns random UUIDs, not sensitive
    return {"ids": [str(uuid.uuid4()) for _ in range(5)]}

@app.get("/api/v1/fp/dummy_tokens")
async def fp_tokens():
    # Dummy token strings
    return {"token": "example_token_do_not_use_in_prod"}

@app.get("/api/v1/fp/internal_ips")
async def fp_ips():
    # 127.0.0.1 or 192.168.x.x in docs are usually fine
    return {"docs_ip": "192.168.1.1"}

@app.get("/api/v1/fp/fake_ssn")
async def fp_ssn():
    return {"marketing_demo": "000-00-0000"}

@app.get("/api/v1/fp/fake_emails")
async def fp_emails():
    # Generic emails
    return {"contact": "support@example.com"}

@app.get("/api/v1/fp/hash_collision")
async def fp_hashes():
    # Just an MD5 signature of public files
    return {"file_hash": "d41d8cd98f00b204e9800998ecf8427e"}

@app.get("/api/v1/fp/stack_trace")
async def fp_stack():
    # A fake stack trace that does not leak paths or versions
    return {"error": "at CustomClass.method (unknown:1:1)"}

@app.get("/api/v1/fp/env_vars")
async def fp_env():
    # Public env vars like NODE_ENV=production
    return {"NODE_ENV": "production", "PUBLIC_URL": "https://example.com"}

@app.get("/api/v1/fp/aws_arn")
async def fp_aws_arn():
    # Public IAM ARN example
    return {"role": "arn:aws:iam::123456789012:role/PublicDemoRole"}

@app.get("/api/v1/fp/jwt_public")
async def fp_jwt_pub():
    # A valid JWT, but it only contains public info like 'theme: dark'
    # Base64 for eyJhbGciOiJOT05FIiwidHlwIjoiSldUIn0.eyJ0aGVtZSI6ImRhcmsifQ.
    return {"preference_token": "eyJhbGciOiJOT05FIiwidHlwIjoiSldUIn0.eyJ0aGVtZSI6ImRhcmsifQ."}

@app.get("/api/v1/fp/phone_numbers")
async def fp_phones():
    # 555 numbers
    return {"office": "555-0199"}

@app.get("/api/v1/fp/api_docs")
async def fp_api_docs():
    # Swagger like json
    return {"Swagger": "2.0", "info": {"title": "Public API"}}

@app.get("/api/v1/fp/git_sha")
async def fp_git_sha():
    # Not a leak
    return {"version": "commit-8f3b2a"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8999, log_level="warning")
