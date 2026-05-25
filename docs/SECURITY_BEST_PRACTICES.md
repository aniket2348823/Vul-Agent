# Antigravity V5 - Security Best Practices

**Last Updated**: May 25, 2026  
**Version**: 5.0  
**Security Level**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Input Validation](#input-validation)
4. [Data Protection](#data-protection)
5. [Network Security](#network-security)
6. [Session Management](#session-management)
7. [Forensic Security](#forensic-security)
8. [Deployment Security](#deployment-security)
9. [Monitoring & Auditing](#monitoring--auditing)
10. [Security Checklist](#security-checklist)

---

## Overview

Antigravity V5 is designed with security as a core principle. This guide outlines best practices for maintaining a secure deployment.

### Security Features

✅ **Built-in Protection**:
- Rate limiting (token bucket algorithm)
- CSRF protection (cryptographic tokens)
- SSRF prevention (URL validation)
- Session sanitization (automatic PII masking)
- Forensic encryption (AES-256)
- Input validation (comprehensive)

---

## Authentication & Authorization

### API Authentication

**Always require authentication for sensitive endpoints:**

```python
from fastapi import Depends, HTTPException, Header

async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key from header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Validate against stored keys (use secure storage)
    if not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return x_api_key

@app.post("/api/scan")
async def start_scan(
    target: dict,
    api_key: str = Depends(verify_api_key)
):
    # Authenticated request
    return await run_scan(target)
```

### Role-Based Access Control

```python
from enum import Enum

class Role(Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

def require_role(required_role: Role):
    """Decorator to enforce role-based access."""
    async def check_role(user: User = Depends(get_current_user)):
        if user.role.value < required_role.value:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role

@app.delete("/api/scan/{scan_id}")
async def delete_scan(
    scan_id: str,
    user: User = Depends(require_role(Role.ADMIN))
):
    # Only admins can delete scans
    await delete_scan_data(scan_id)
```

### Token Management

```python
import secrets
from datetime import datetime, timedelta

class TokenManager:
    """Secure token management."""
    
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate cryptographically secure token."""
        token = secrets.token_urlsafe(32)
        
        # Store with expiration
        self.tokens[token] = {
            "user_id": user_id,
            "expires_at": datetime.now() + timedelta(seconds=expires_in)
        }
        
        return token
    
    def validate_token(self, token: str) -> bool:
        """Validate token and check expiration."""
        if token not in self.tokens:
            return False
        
        token_data = self.tokens[token]
        
        # Check expiration
        if datetime.now() > token_data["expires_at"]:
            del self.tokens[token]
            return False
        
        return True
```

---

## Input Validation

### URL Validation

**Always validate URLs before processing:**

```python
from backend.core.url_validator import URLValidator

validator = URLValidator()

def validate_scan_target(url: str) -> str:
    """Validate and sanitize scan target URL."""
    # 1. Basic format check
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    
    # 2. SSRF protection
    is_valid, reason = validator.validate(url)
    if not is_valid:
        raise ValueError(f"Invalid URL: {reason}")
    
    # 3. Length check
    if len(url) > 2048:
        raise ValueError("URL too long")
    
    return url

# Use in endpoint
@app.post("/api/scan")
async def start_scan(target_url: str):
    try:
        validated_url = validate_scan_target(target_url)
        return await run_scan(validated_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Parameter Validation

```python
from pydantic import BaseModel, validator, constr

class ScanRequest(BaseModel):
    """Validated scan request."""
    url: constr(min_length=1, max_length=2048)
    modules: list[str]
    duration: int
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        validator = URLValidator()
        is_valid, reason = validator.validate(v)
        if not is_valid:
            raise ValueError(reason)
        return v
    
    @validator('modules')
    def validate_modules(cls, v):
        """Validate module names."""
        allowed_modules = [
            "The Tycoon", "The Escalator", "SQL Injection Probe"
        ]
        for module in v:
            if module not in allowed_modules:
                raise ValueError(f"Invalid module: {module}")
        return v
    
    @validator('duration')
    def validate_duration(cls, v):
        """Validate scan duration."""
        if v < 1 or v > 3600:
            raise ValueError("Duration must be between 1 and 3600 seconds")
        return v

# Use in endpoint
@app.post("/api/scan")
async def start_scan(request: ScanRequest):
    # Request is automatically validated
    return await run_scan(request.dict())
```

### SQL Injection Prevention

```python
# ✅ GOOD: Use parameterized queries
async def get_scan_by_id(scan_id: str):
    query = "SELECT * FROM scans WHERE id = ?"
    result = await db.execute(query, (scan_id,))
    return result

# ❌ BAD: String concatenation
async def get_scan_by_id_bad(scan_id: str):
    query = f"SELECT * FROM scans WHERE id = '{scan_id}'"
    result = await db.execute(query)
    return result
```

---

## Data Protection

### Encryption at Rest

**Always encrypt sensitive data:**

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    """Encrypt sensitive data at rest."""
    
    def __init__(self):
        # Get encryption key from environment
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"antigravity-salt",  # Use unique salt per deployment
            iterations=100000
        )
        key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        self.cipher = Fernet(key_bytes)
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data."""
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data."""
        return self.cipher.decrypt(encrypted_data)

# Use for sensitive data
encryptor = DataEncryption()

# Encrypt before storage
sensitive_data = b"secret information"
encrypted = encryptor.encrypt(sensitive_data)

# Store encrypted data
with open("sensitive.enc", "wb") as f:
    f.write(encrypted)

# Decrypt when needed
with open("sensitive.enc", "rb") as f:
    encrypted = f.read()
    decrypted = encryptor.decrypt(encrypted)
```

### Session Data Sanitization

**Always sanitize session data:**

```python
from backend.core.hybrid_session_manager import HybridSessionManager

session_manager = HybridSessionManager()

# Session data is automatically sanitized
session_data = {
    "cookies": [
        {"name": "auth_token", "value": "secret123"},
        {"name": "session_id", "value": "abc456"}
    ],
    "localStorage": {
        "api_key": "sk_live_123456",
        "user_data": "{...}"
    }
}

# Save (automatically sanitizes sensitive data)
await session_manager.save_session("scan-001", session_data)

# Load (sensitive data is masked)
loaded = await session_manager.load_session("scan-001")
# auth_token and api_key are masked
```

### Forensic Data Protection

```python
from backend.core.forensic_collector import ForensicCollector

collector = ForensicCollector()

# All forensic data is automatically encrypted
await collector.capture_screenshot("scan-001", page, "evidence")
await collector.collect_evidence("scan-001", "network_log", network_data)

# Data is encrypted with AES-256 before storage
```

---

## Network Security

### Rate Limiting

**Protect all public endpoints:**

```python
from backend.core.rate_limiter import RateLimiter
from fastapi import Request

rate_limiter = RateLimiter()

# Configure limits
rate_limiter.configure_limit("/api/scan", 10)  # 10 requests/minute
rate_limiter.configure_limit("/api/report", 5)  # 5 requests/minute

@app.post("/api/scan")
async def start_scan(request: Request, target: dict):
    # Check rate limit
    client_ip = request.client.host
    await rate_limiter.check_rate_limit("/api/scan", client_ip)
    
    # Process request
    return await run_scan(target)
```

### SSRF Prevention

**Validate all external URLs:**

```python
from backend.core.url_validator import URLValidator

validator = URLValidator()

async def fetch_external_resource(url: str):
    """Safely fetch external resource."""
    # Validate URL
    is_valid, reason = validator.validate(url)
    if not is_valid:
        raise ValueError(f"Invalid URL: {reason}")
    
    # Fetch with timeout
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as response:
            return await response.text()

# Blocked patterns:
# - Cloud metadata: 169.254.169.254, metadata.google.internal
# - Private IPs: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
# - Localhost: 127.0.0.1, localhost
# - Dangerous protocols: file://, gopher://
```

### CSRF Protection

**Protect state-changing operations:**

```python
from backend.core.csrf_protection import CSRFProtection
from fastapi import Request, HTTPException

csrf = CSRFProtection()

@app.post("/api/login")
async def login(credentials: dict):
    """Login and generate CSRF token."""
    # Authenticate user
    session_id = authenticate(credentials)
    
    # Generate CSRF token
    csrf_token = csrf.generate_token(session_id)
    
    return {
        "session_id": session_id,
        "csrf_token": csrf_token
    }

@app.post("/api/update")
async def update_data(request: Request, data: dict):
    """Update data with CSRF protection."""
    session_id = request.cookies.get("session_id")
    csrf_token = request.headers.get("X-CSRF-Token")
    
    # Validate CSRF token
    if not csrf.validate_token(csrf_token, session_id):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    
    # Process update
    return await update(data)
```

---

## Session Management

### Secure Session Storage

```python
import secrets
from datetime import datetime, timedelta

class SecureSessionManager:
    """Secure session management."""
    
    def create_session(self, user_id: str) -> str:
        """Create secure session."""
        # Generate cryptographically secure session ID
        session_id = secrets.token_urlsafe(32)
        
        # Store session with expiration
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "ip_address": None,  # Set from request
            "user_agent": None   # Set from request
        }
        
        return session_id
    
    def validate_session(self, session_id: str, ip_address: str) -> bool:
        """Validate session with IP binding."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Check expiration
        if datetime.now() > session["expires_at"]:
            del self.sessions[session_id]
            return False
        
        # Check IP binding (optional, for extra security)
        if session["ip_address"] and session["ip_address"] != ip_address:
            return False
        
        return True
    
    def destroy_session(self, session_id: str):
        """Destroy session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
```

### Session Timeout

```python
# Set appropriate session timeouts
SESSION_TIMEOUT = 3600  # 1 hour for regular users
ADMIN_SESSION_TIMEOUT = 1800  # 30 minutes for admins

# Implement sliding window
def refresh_session(session_id: str):
    """Refresh session expiration."""
    if session_id in sessions:
        sessions[session_id]["expires_at"] = (
            datetime.now() + timedelta(seconds=SESSION_TIMEOUT)
        )
```

---

## Forensic Security

### Secure Evidence Collection

```python
from backend.core.forensic_collector import ForensicCollector

collector = ForensicCollector()

# All evidence is automatically encrypted
async def collect_secure_evidence(scan_id: str, page):
    """Collect evidence securely."""
    # Screenshot (encrypted)
    await collector.capture_screenshot(scan_id, page, "evidence_1")
    
    # Network logs (encrypted)
    network_logs = await capture_network_logs(page)
    await collector.collect_evidence(scan_id, "network", network_logs)
    
    # DOM snapshot (encrypted)
    dom = await page.content()
    await collector.collect_evidence(scan_id, "dom", dom)
    
    # Console logs (encrypted)
    console_logs = await capture_console_logs(page)
    await collector.collect_evidence(scan_id, "console", console_logs)
```

### Evidence Integrity

```python
import hashlib
import json

def compute_evidence_hash(evidence: dict) -> str:
    """Compute hash for evidence integrity."""
    # Serialize evidence
    evidence_json = json.dumps(evidence, sort_keys=True)
    
    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(evidence_json.encode())
    return hash_obj.hexdigest()

# Store hash with evidence
evidence = {"type": "screenshot", "data": "..."}
evidence_hash = compute_evidence_hash(evidence)

evidence["integrity_hash"] = evidence_hash

# Verify integrity later
def verify_evidence_integrity(evidence: dict) -> bool:
    """Verify evidence hasn't been tampered with."""
    stored_hash = evidence.pop("integrity_hash")
    computed_hash = compute_evidence_hash(evidence)
    return stored_hash == computed_hash
```

---

## Deployment Security

### Environment Variables

```bash
# .env file (never commit to git!)
ENCRYPTION_KEY=your-secret-key-here
FORENSIC_ENCRYPTION_KEY=another-secret-key
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
API_KEY=your-api-key

# Use strong, random keys
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Secure Configuration

```python
import os
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Secure application settings."""
    
    # Required settings
    encryption_key: str
    database_url: str
    
    # Optional with defaults
    debug: bool = False
    log_level: str = "INFO"
    
    @validator('encryption_key')
    def validate_encryption_key(cls, v):
        """Ensure encryption key is strong."""
        if len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Load settings
settings = Settings()

# Never log sensitive settings
logger.info(f"Debug mode: {settings.debug}")
# DON'T: logger.info(f"Encryption key: {settings.encryption_key}")
```

### HTTPS Only

```python
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Redirect HTTP to HTTPS in production
if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)
```

### Security Headers

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Specific methods only
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response
```

---

## Monitoring & Auditing

### Security Logging

```python
import logging

security_logger = logging.getLogger("security")

def log_security_event(event_type: str, details: dict):
    """Log security-relevant events."""
    security_logger.warning(
        f"Security Event: {event_type}",
        extra={
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            **details
        }
    )

# Log authentication attempts
log_security_event("auth_attempt", {
    "user": username,
    "ip": client_ip,
    "success": False
})

# Log rate limit violations
log_security_event("rate_limit_exceeded", {
    "endpoint": "/api/scan",
    "ip": client_ip,
    "limit": 10
})

# Log CSRF failures
log_security_event("csrf_validation_failed", {
    "session_id": session_id,
    "ip": client_ip
})
```

### Audit Trail

```python
class AuditLog:
    """Maintain audit trail of sensitive operations."""
    
    async def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        details: dict
    ):
        """Log auditable action."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details,
            "ip_address": None,  # Set from request
            "user_agent": None   # Set from request
        }
        
        # Store in database
        await self.db.insert("audit_log", entry)

# Use for sensitive operations
audit = AuditLog()

await audit.log_action(
    user_id="user-123",
    action="scan_started",
    resource="scan-001",
    details={"target": "https://example.com"}
)

await audit.log_action(
    user_id="user-123",
    action="scan_deleted",
    resource="scan-001",
    details={"reason": "user_request"}
)
```

---

## Security Checklist

### Pre-Deployment

- [ ] All secrets in environment variables
- [ ] Encryption keys are strong (32+ characters)
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] CSRF protection enabled
- [ ] URL validation enabled
- [ ] Session timeout configured
- [ ] Audit logging enabled
- [ ] Error messages don't leak sensitive info

### Post-Deployment

- [ ] Monitor security logs
- [ ] Review audit trail regularly
- [ ] Update dependencies
- [ ] Rotate encryption keys periodically
- [ ] Review access controls
- [ ] Test security features
- [ ] Backup encrypted data
- [ ] Document security procedures

### Ongoing

- [ ] Security patches applied promptly
- [ ] Regular security audits
- [ ] Penetration testing
- [ ] Incident response plan
- [ ] Security training for team
- [ ] Compliance requirements met

---

## See Also

- [API Reference](API_REFERENCE.md)
- [Usage Examples](USAGE_EXAMPLES.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Performance Tuning Guide](PERFORMANCE.md)

---

**Last Updated**: May 25, 2026  
**Security Level**: Production Ready  
**Maintainer**: Antigravity V5 Security Team
