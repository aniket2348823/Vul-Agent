# Antigravity V5 - Usage Examples

**Last Updated**: May 25, 2026  
**Version**: 5.0

---

## Table of Contents

1. [Basic Scan Workflow](#basic-scan-workflow)
2. [Browser Automation](#browser-automation)
3. [Session Management](#session-management)
4. [Forensic Collection](#forensic-collection)
5. [Security Features](#security-features)
6. [Agent Usage](#agent-usage)
7. [Advanced Patterns](#advanced-patterns)

---

## Basic Scan Workflow

### Starting a Scan

```python
from backend.core.state import StateManager
from backend.core.orchestrator import HiveOrchestrator

# Initialize state manager
state_manager = StateManager()

# Register a new scan
scan_data = {
    "id": "scan-001",
    "status": "Initializing",
    "name": "https://example.com",
    "scope": "https://example.com",
    "modules": ["Alpha", "Beta", "Gamma"],
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

await state_manager.register_scan(scan_data)

# Start the scan
target_config = {
    "url": "https://example.com",
    "modules": ["Alpha", "Beta"],
    "duration": 300  # 5 minutes
}

await HiveOrchestrator.bootstrap_hive(target_config, scan_id="scan-001")
```

### Monitoring Scan Progress

```python
# Read scan state
scan_state = await state_manager.read_scan_state("scan-001")

print(f"Status: {scan_state.get('status')}")
print(f"Progress: {scan_state.get('progress', 0)}%")
print(f"Findings: {len(scan_state.get('findings', []))}")

# Update progress
scan_state["progress"] = 50
scan_state["current_phase"] = "Exploitation"
await state_manager.write_scan_state("scan-001", scan_state)
```

### Completing a Scan

```python
# Mark scan as complete
state_manager.sync_complete_scan(
    scan_id="scan-001",
    status="Completed",
    report_ready=True
)

# Generate report
from backend.core.reporting import ReportGenerator

report_gen = ReportGenerator()
report_path = await report_gen.generate_report("scan-001")
print(f"Report saved to: {report_path}")
```

---

## Browser Automation

### Basic Browser Usage

```python
from backend.core.browser_orchestrator import BrowserOrchestrator

# Initialize orchestrator
orchestrator = BrowserOrchestrator()
await orchestrator.initialize()

# Get a browser context
context = await orchestrator.get_context("scan-001")

# Create a page and navigate
page = await context.new_page()
await page.goto("https://example.com")

# Extract information
title = await page.title()
content = await page.content()

# Close page
await page.close()

# Release context back to pool
await orchestrator.release_context("scan-001")

# Cleanup
await orchestrator.cleanup()
```

### Using Browser Engines

```python
from backend.core.openclaw_engine import OpenClawEngine
from backend.core.pinchtab_engine import PinchTabEngine

# OpenClaw for reconnaissance
openclaw = OpenClawEngine()
await openclaw.initialize()

result = await openclaw.navigate("https://example.com")
endpoints = result.get("endpoints", [])
forms = result.get("forms", [])

print(f"Found {len(endpoints)} endpoints")
print(f"Found {len(forms)} forms")

# PinchTab for token extraction
pinchtab = PinchTabEngine()
await pinchtab.initialize()

tokens = await pinchtab.extract_tokens("https://example.com/login")
print(f"Extracted {len(tokens)} tokens")

# Cleanup
await openclaw.cleanup()
await pinchtab.cleanup()
```

### Context Pooling

```python
# Enable context pooling for better performance
orchestrator = BrowserOrchestrator()
await orchestrator.initialize()

# Get multiple contexts (reused from pool)
context1 = await orchestrator.get_context("scan-001")
context2 = await orchestrator.get_context("scan-002")
context3 = await orchestrator.get_context("scan-003")

# Use contexts...

# Release contexts (returned to pool)
await orchestrator.release_context("scan-001")
await orchestrator.release_context("scan-002")
await orchestrator.release_context("scan-003")

# Check resource usage
stats = orchestrator.get_resource_stats()
print(f"Active contexts: {stats['active_contexts']}")
print(f"Pooled contexts: {stats['pooled_contexts']}")
print(f"Memory usage: {stats['memory_mb']} MB")
```

---

## Session Management

### Saving and Loading Sessions

```python
from backend.core.hybrid_session_manager import HybridSessionManager

session_manager = HybridSessionManager()

# Capture session data
session_data = {
    "cookies": [
        {"name": "session_id", "value": "abc123", "domain": "example.com"},
        {"name": "auth_token", "value": "xyz789", "domain": "example.com"}
    ],
    "localStorage": {
        "user_id": "12345",
        "preferences": "{...}"
    },
    "sessionStorage": {
        "temp_data": "..."
    }
}

# Save session (automatically sanitized)
await session_manager.save_session("scan-001", session_data)

# Load session
loaded_session = await session_manager.load_session("scan-001")

# Sensitive data is sanitized
print(loaded_session.get("_sanitized"))  # True
```

### Session Replay

```python
# Load session for replay
session_data = await session_manager.load_session("scan-001")

# Apply session to browser context
context = await orchestrator.get_context("scan-001")

# Set cookies
for cookie in session_data.get("cookies", []):
    await context.add_cookies([cookie])

# Navigate with session
page = await context.new_page()
await page.goto("https://example.com/dashboard")

# Session is now active
```

---

## Forensic Collection

### Capturing Screenshots

```python
from backend.core.forensic_collector import ForensicCollector

collector = ForensicCollector()

# Capture screenshot
context = await orchestrator.get_context("scan-001")
page = await context.new_page()
await page.goto("https://example.com")

await collector.capture_screenshot("scan-001", page, "homepage")

# Screenshot is automatically encrypted
```

### Collecting Evidence

```python
# Collect network logs
network_logs = []

async def log_request(request):
    network_logs.append({
        "url": request.url,
        "method": request.method,
        "headers": request.headers
    })

page.on("request", log_request)
await page.goto("https://example.com")

# Save network logs as evidence
await collector.collect_evidence("scan-001", "network_logs", network_logs)

# Collect DOM snapshot
dom_snapshot = await page.content()
await collector.collect_evidence("scan-001", "dom_snapshot", dom_snapshot)

# Collect console logs
console_logs = []

async def log_console(msg):
    console_logs.append(msg.text)

page.on("console", log_console)

await collector.collect_evidence("scan-001", "console_logs", console_logs)
```

---

## Security Features

### Rate Limiting

```python
from backend.core.rate_limiter import RateLimiter
from fastapi import HTTPException

rate_limiter = RateLimiter()

# Configure limits
rate_limiter.configure_limit("/api/scan", 10)  # 10 requests/minute
rate_limiter.configure_limit("/api/report", 5)  # 5 requests/minute

# Check rate limit in endpoint
@app.post("/api/scan")
async def start_scan(request: Request):
    client_ip = request.client.host
    
    try:
        await rate_limiter.check_rate_limit("/api/scan", client_ip)
    except HTTPException as e:
        return {"error": "Rate limit exceeded", "retry_after": 60}
    
    # Process request
    return {"status": "started"}
```

### URL Validation

```python
from backend.core.url_validator import URLValidator

validator = URLValidator()

# Validate user-provided URL
user_url = request.json.get("url")

is_valid, reason = validator.validate(user_url)

if not is_valid:
    return {"error": f"Invalid URL: {reason}"}

# URL is safe to use
result = await scan_url(user_url)
```

### CSRF Protection

```python
from backend.core.csrf_protection import CSRFProtection

csrf = CSRFProtection()

# Generate token for session
@app.post("/api/login")
async def login(credentials: dict):
    # Authenticate user
    session_id = create_session(credentials)
    
    # Generate CSRF token
    csrf_token = csrf.generate_token(session_id)
    
    return {
        "session_id": session_id,
        "csrf_token": csrf_token
    }

# Validate token on state-changing operations
@app.post("/api/update")
async def update_data(request: Request, data: dict):
    session_id = request.cookies.get("session_id")
    csrf_token = request.headers.get("X-CSRF-Token")
    
    if not csrf.validate_token(csrf_token, session_id):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    
    # Process update
    return {"status": "updated"}
```

---

## Agent Usage

### Using AlphaAgent for Reconnaissance

```python
from backend.agents.alpha import AlphaAgent
from backend.core.hive import EventBus

# Create event bus
bus = EventBus()

# Initialize agent
alpha = AlphaAgent(bus)
await alpha.start()

# Discover endpoints
endpoints = await alpha.discover_endpoints("https://api.example.com")

print(f"Discovered endpoints:")
for endpoint in endpoints:
    print(f"  - {endpoint}")

# Classify APIs
api_types = await alpha.classify_apis(endpoints)

for endpoint, api_type in api_types.items():
    print(f"{endpoint}: {api_type}")
```

### Using BetaAgent for Testing

```python
from backend.agents.beta import BetaAgent

# Initialize agent
beta = BetaAgent(bus)
await beta.start()

# Test CSRF protection
result = await beta.test_csrf_bypass("https://example.com/api/update")

if result.get("vulnerable"):
    print("CSRF vulnerability found!")
    print(f"Bypass technique: {result.get('technique')}")
else:
    print("CSRF protection is effective")
```

### Using GammaAgent for Monitoring

```python
from backend.agents.gamma import GammaAgent

# Initialize agent
gamma = GammaAgent(bus)
await gamma.start()

# Analyze network traffic
analysis = await gamma.analyze_network_traffic("scan-001")

print(f"Suspicious requests: {analysis.get('suspicious_count')}")
print(f"SSRF attempts: {analysis.get('ssrf_attempts')}")
print(f"Data exfiltration: {analysis.get('exfiltration_detected')}")
```

---

## Advanced Patterns

### Concurrent Scanning

```python
import asyncio

async def scan_target(target_url, scan_id):
    """Scan a single target."""
    # Register scan
    scan_data = {
        "id": scan_id,
        "status": "Running",
        "name": target_url,
        "scope": target_url,
        "modules": ["Alpha", "Beta"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    await state_manager.register_scan(scan_data)
    
    # Run scan
    target_config = {"url": target_url, "modules": ["Alpha", "Beta"]}
    await HiveOrchestrator.bootstrap_hive(target_config, scan_id=scan_id)
    
    # Complete scan
    state_manager.sync_complete_scan(scan_id)

# Scan multiple targets concurrently
targets = [
    ("https://example1.com", "scan-001"),
    ("https://example2.com", "scan-002"),
    ("https://example3.com", "scan-003")
]

tasks = [scan_target(url, scan_id) for url, scan_id in targets]
await asyncio.gather(*tasks)
```

### Custom Event Handling

```python
from backend.core.hive import EventBus, EventType, HiveEvent

bus = EventBus()

# Subscribe to vulnerability events
async def handle_vulnerability(event: HiveEvent):
    print(f"Vulnerability found: {event.payload.get('type')}")
    print(f"Severity: {event.payload.get('severity')}")
    print(f"URL: {event.payload.get('url')}")
    
    # Send notification
    await send_alert(event.payload)

bus.subscribe(EventType.VULN_CONFIRMED, handle_vulnerability)

# Publish event
await bus.publish(HiveEvent(
    type=EventType.VULN_CONFIRMED,
    source="BetaAgent",
    scan_id="scan-001",
    payload={
        "type": "XSS",
        "severity": "High",
        "url": "https://example.com/search",
        "payload": "<script>alert(1)</script>"
    }
))
```

### Task Management

```python
from backend.core.task_manager import TaskManager

task_manager = TaskManager("ScanComponent")

# Create background tasks
async def monitor_progress():
    while True:
        await asyncio.sleep(5)
        stats = orchestrator.get_resource_stats()
        print(f"Memory: {stats['memory_mb']} MB")

async def cleanup_old_scans():
    while True:
        await asyncio.sleep(3600)  # Every hour
        state_manager.reset_stale_scans()

# Start tasks
monitor_task = task_manager.create_task(monitor_progress(), name="monitor")
cleanup_task = task_manager.create_task(cleanup_old_scans(), name="cleanup")

# Get active tasks
active = task_manager.get_active_tasks()
print(f"Active tasks: {len(active)}")

# Cancel all tasks on shutdown
await task_manager.cancel_all()
```

### Error Recovery

```python
async def resilient_scan(target_url, scan_id, max_retries=3):
    """Scan with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            # Attempt scan
            target_config = {"url": target_url, "modules": ["Alpha", "Beta"]}
            await HiveOrchestrator.bootstrap_hive(target_config, scan_id=scan_id)
            
            # Success
            return {"status": "completed", "scan_id": scan_id}
            
        except Exception as e:
            logger.error(f"Scan attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            else:
                # Final attempt failed
                state_manager.sync_complete_scan(scan_id, status="Failed")
                return {"status": "failed", "error": str(e)}

# Use resilient scan
result = await resilient_scan("https://example.com", "scan-001")
```

---

## See Also

- [API Reference](API_REFERENCE.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Security Best Practices](SECURITY_BEST_PRACTICES.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**Last Updated**: May 25, 2026  
**Maintainer**: Antigravity V5 Team
