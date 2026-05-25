# Antigravity V5 - Troubleshooting Guide

**Last Updated**: May 25, 2026  
**Version**: 5.0

---

## Table of Contents

1. [Common Issues](#common-issues)
2. [Browser Issues](#browser-issues)
3. [Performance Issues](#performance-issues)
4. [Security Issues](#security-issues)
5. [Database Issues](#database-issues)
6. [Network Issues](#network-issues)
7. [Debugging Techniques](#debugging-techniques)
8. [FAQ](#faq)

---

## Common Issues

### Scan Fails to Start

**Symptoms**: Scan status remains "Initializing" or fails immediately

**Possible Causes**:
1. Invalid target URL
2. Network connectivity issues
3. Browser engine not initialized
4. Insufficient resources

**Solutions**:

```python
# 1. Validate URL before scanning
from backend.core.url_validator import URLValidator

validator = URLValidator()
is_valid, reason = validator.validate(target_url)

if not is_valid:
    print(f"Invalid URL: {reason}")
    # Fix URL or reject request

# 2. Check network connectivity
import aiohttp

async def check_connectivity(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                return response.status == 200
    except Exception as e:
        print(f"Network error: {e}")
        return False

# 3. Verify browser initialization
orchestrator = BrowserOrchestrator()
await orchestrator.initialize()

stats = orchestrator.get_resource_stats()
print(f"Browser ready: {stats['active_contexts'] >= 0}")

# 4. Check system resources
import psutil

memory = psutil.virtual_memory()
print(f"Available memory: {memory.available / 1024**3:.2f} GB")

if memory.percent > 90:
    print("WARNING: Low memory available")
```

---

### Scan Hangs or Times Out

**Symptoms**: Scan runs indefinitely without completing

**Possible Causes**:
1. Target site is slow or unresponsive
2. Infinite loop in agent logic
3. Resource exhaustion
4. Deadlock in async code

**Solutions**:

```python
# 1. Add timeout to scan operations
import asyncio

async def scan_with_timeout(target_url, timeout=300):
    try:
        result = await asyncio.wait_for(
            run_scan(target_url),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        print(f"Scan timed out after {timeout} seconds")
        # Cancel scan and cleanup
        await cleanup_scan()
        raise

# 2. Monitor scan progress
async def monitor_scan(scan_id):
    start_time = time.time()
    last_progress = 0
    
    while True:
        await asyncio.sleep(10)
        
        scan_state = await state_manager.read_scan_state(scan_id)
        current_progress = scan_state.get("progress", 0)
        
        # Check if progress is stuck
        if current_progress == last_progress:
            elapsed = time.time() - start_time
            if elapsed > 60:  # No progress for 60 seconds
                print("WARNING: Scan appears stuck")
                # Take action: restart, cancel, etc.
        
        last_progress = current_progress

# 3. Check for resource exhaustion
stats = orchestrator.get_resource_stats()

if stats['memory_mb'] > 1000:  # Over 1GB
    print("WARNING: High memory usage")
    # Trigger cleanup
    await orchestrator.cleanup()
    await orchestrator.initialize()
```

---

### Rate Limit Errors

**Symptoms**: HTTP 429 errors, "Too Many Requests"

**Possible Causes**:
1. Too many concurrent requests
2. Rate limit configuration too strict
3. Multiple scans from same IP

**Solutions**:

```python
# 1. Configure appropriate rate limits
from backend.core.rate_limiter import RateLimiter

rate_limiter = RateLimiter()

# Adjust limits based on your needs
rate_limiter.configure_limit("/api/scan", 20)  # 20 requests/minute
rate_limiter.configure_limit("/api/report", 10)  # 10 requests/minute

# 2. Implement retry with backoff
async def request_with_retry(endpoint, max_retries=3):
    for attempt in range(max_retries):
        try:
            await rate_limiter.check_rate_limit(endpoint, client_ip)
            # Make request
            return await make_request()
        except HTTPException as e:
            if e.status_code == 429 and attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            else:
                raise

# 3. Distribute load across multiple IPs
# Use proxy rotation or load balancer
```

---

## Browser Issues

### Browser Fails to Launch

**Symptoms**: "Browser not found" or "Failed to launch browser"

**Possible Causes**:
1. Playwright not installed
2. Browser binaries missing
3. Insufficient permissions
4. Port conflicts

**Solutions**:

```bash
# 1. Install Playwright browsers
python -m playwright install

# 2. Install system dependencies (Linux)
python -m playwright install-deps

# 3. Check browser installation
python -m playwright install --help

# 4. Verify installation
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

```python
# 5. Use custom browser path
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(
        executable_path="/path/to/chrome",
        headless=True
    )
```

---

### Context Leaks

**Symptoms**: Memory usage grows over time, contexts not released

**Possible Causes**:
1. Contexts not properly released
2. Pages not closed
3. Event listeners not removed

**Solutions**:

```python
# 1. Always use try/finally for cleanup
context = None
page = None

try:
    context = await orchestrator.get_context(scan_id)
    page = await context.new_page()
    
    # Use page...
    
finally:
    if page:
        await page.close()
    if context:
        await orchestrator.release_context(scan_id)

# 2. Monitor context usage
stats = orchestrator.get_resource_stats()
print(f"Active contexts: {stats['active_contexts']}")
print(f"Pooled contexts: {stats['pooled_contexts']}")

if stats['active_contexts'] > 10:
    print("WARNING: Too many active contexts")
    # Investigate and cleanup

# 3. Set context timeout
context = await orchestrator.get_context(scan_id)
context.set_default_timeout(30000)  # 30 seconds
```

---

## Performance Issues

### Slow Scan Performance

**Symptoms**: Scans take much longer than expected

**Possible Causes**:
1. Target site is slow
2. Too many sequential operations
3. Inefficient resource usage
4. Network latency

**Solutions**:

```python
# 1. Enable parallel operations
import asyncio

async def scan_endpoints_parallel(endpoints):
    tasks = [scan_endpoint(ep) for ep in endpoints]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 2. Use context pooling
orchestrator = BrowserOrchestrator()
await orchestrator.initialize()  # Enables pooling by default

# 3. Optimize page loads
page = await context.new_page()

# Block unnecessary resources
await page.route("**/*.{png,jpg,jpeg,gif,svg,css}", lambda route: route.abort())

# Set aggressive timeouts
page.set_default_timeout(10000)  # 10 seconds

# 4. Monitor performance
import time

start = time.time()
result = await scan_operation()
elapsed = time.time() - start

print(f"Operation took {elapsed:.2f} seconds")

if elapsed > 30:
    print("WARNING: Slow operation detected")
```

---

### High Memory Usage

**Symptoms**: Memory usage exceeds 1GB, system becomes slow

**Possible Causes**:
1. Too many concurrent contexts
2. Large page content
3. Memory leaks
4. Forensic data accumulation

**Solutions**:

```python
# 1. Limit concurrent contexts
orchestrator = BrowserOrchestrator()
orchestrator.max_contexts = 5  # Limit to 5 concurrent

# 2. Monitor memory usage
import psutil

process = psutil.Process()
memory_mb = process.memory_info().rss / 1024**2

print(f"Memory usage: {memory_mb:.2f} MB")

if memory_mb > 1000:
    print("WARNING: High memory usage")
    # Trigger cleanup
    await orchestrator.cleanup()
    import gc
    gc.collect()

# 3. Clear forensic data periodically
# Implement rotation or archival strategy

# 4. Use memory profiling
import tracemalloc

tracemalloc.start()

# Run operation
await scan_operation()

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024**2:.2f} MB")
print(f"Peak memory: {peak / 1024**2:.2f} MB")

tracemalloc.stop()
```

---

## Security Issues

### CSRF Token Validation Fails

**Symptoms**: "Invalid CSRF token" errors on valid requests

**Possible Causes**:
1. Token expired
2. Session mismatch
3. Token not included in request
4. Clock skew

**Solutions**:

```python
# 1. Check token expiration
from backend.core.csrf_protection import CSRFProtection

csrf = CSRFProtection()

# Increase token lifetime if needed
csrf.token_lifetime = 3600  # 1 hour

# 2. Verify session ID matches
session_id = request.cookies.get("session_id")
csrf_token = request.headers.get("X-CSRF-Token")

if not session_id:
    return {"error": "No session"}

is_valid = csrf.validate_token(csrf_token, session_id)

# 3. Debug token validation
print(f"Session ID: {session_id}")
print(f"CSRF Token: {csrf_token}")
print(f"Valid: {is_valid}")

# 4. Regenerate token if expired
if not is_valid:
    new_token = csrf.generate_token(session_id)
    return {"error": "Token expired", "new_token": new_token}
```

---

### SSRF Validation Blocks Valid URLs

**Symptoms**: Legitimate URLs rejected by URL validator

**Possible Causes**:
1. Overly strict validation rules
2. Private IP ranges needed for testing
3. Custom TLDs not recognized

**Solutions**:

```python
# 1. Whitelist specific URLs for testing
from backend.core.url_validator import URLValidator

validator = URLValidator()

# Add to whitelist
validator.whitelist.add("http://localhost:8080")
validator.whitelist.add("http://192.168.1.100")

# 2. Disable validation for testing (NOT for production)
if os.getenv("TESTING") == "true":
    # Skip validation
    is_valid = True
else:
    is_valid, reason = validator.validate(url)

# 3. Custom validation logic
def custom_validate(url):
    # Your custom rules
    if url.startswith("http://internal.company.com"):
        return True, "Whitelisted"
    
    return validator.validate(url)
```

---

## Database Issues

### State File Corruption

**Symptoms**: "Failed to load state", JSON decode errors

**Possible Causes**:
1. Concurrent writes
2. Disk full
3. Process killed during write
4. File permissions

**Solutions**:

```python
# 1. Backup state file
import shutil
import os

state_file = "data/stats.json"
backup_file = f"{state_file}.backup"

if os.path.exists(state_file):
    shutil.copy2(state_file, backup_file)

# 2. Recover from backup
try:
    state_manager = StateManager()
except Exception as e:
    print(f"Failed to load state: {e}")
    
    # Try backup
    if os.path.exists(backup_file):
        shutil.copy2(backup_file, state_file)
        state_manager = StateManager()

# 3. Reset state if corrupted
if state_corrupted:
    os.remove(state_file)
    state_manager = StateManager()  # Creates new state

# 4. Check disk space
import shutil

disk = shutil.disk_usage("/")
free_gb = disk.free / 1024**3

print(f"Free disk space: {free_gb:.2f} GB")

if free_gb < 1:
    print("WARNING: Low disk space")
```

---

## Network Issues

### Connection Timeouts

**Symptoms**: "Connection timeout", "Failed to connect"

**Possible Causes**:
1. Target site is down
2. Firewall blocking requests
3. DNS resolution failure
4. Network congestion

**Solutions**:

```python
# 1. Increase timeouts
import aiohttp

timeout = aiohttp.ClientTimeout(
    total=60,  # Total timeout
    connect=10,  # Connection timeout
    sock_read=30  # Socket read timeout
)

async with aiohttp.ClientSession(timeout=timeout) as session:
    async with session.get(url) as response:
        return await response.text()

# 2. Implement retry logic
async def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return await response.text()
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise

# 3. Check DNS resolution
import socket

try:
    ip = socket.gethostbyname("example.com")
    print(f"Resolved to: {ip}")
except socket.gaierror as e:
    print(f"DNS resolution failed: {e}")

# 4. Test connectivity
import subprocess

result = subprocess.run(
    ["ping", "-c", "1", "example.com"],
    capture_output=True
)

if result.returncode == 0:
    print("Host is reachable")
else:
    print("Host is unreachable")
```

---

## Debugging Techniques

### Enable Debug Logging

```python
import logging

# Set log level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
logging.getLogger("HiveOrchestrator").setLevel(logging.DEBUG)
logging.getLogger("BrowserOrchestrator").setLevel(logging.DEBUG)
logging.getLogger("StateManager").setLevel(logging.DEBUG)
```

### Inspect Scan State

```python
# Read current scan state
scan_state = await state_manager.read_scan_state(scan_id)

# Pretty print
import json
print(json.dumps(scan_state, indent=2))

# Check specific fields
print(f"Status: {scan_state.get('status')}")
print(f"Progress: {scan_state.get('progress')}")
print(f"Errors: {scan_state.get('errors', [])}")
print(f"Findings: {len(scan_state.get('findings', []))}")
```

### Monitor Resource Usage

```python
import psutil
import asyncio

async def monitor_resources():
    while True:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        print(f"CPU: {cpu_percent}% | Memory: {memory_percent}% | Disk: {disk_percent}%")
        
        await asyncio.sleep(5)

# Start monitoring
asyncio.create_task(monitor_resources())
```

### Trace Async Operations

```python
import asyncio

# Enable asyncio debug mode
asyncio.get_event_loop().set_debug(True)

# Log slow callbacks
asyncio.get_event_loop().slow_callback_duration = 0.1  # 100ms

# Check for unclosed resources
import warnings
warnings.simplefilter('always', ResourceWarning)
```

---

## FAQ

### Q: How do I reset the system state?

```python
# Reset all scans
state_manager.wipe_scans()

# Reset stale scans only
cleaned = state_manager.reset_stale_scans()
print(f"Cleaned {cleaned} stale scans")
```

### Q: How do I export scan results?

```python
# Read scan state
scan_state = await state_manager.read_scan_state(scan_id)

# Export to JSON
import json

with open(f"scan_{scan_id}.json", "w") as f:
    json.dump(scan_state, f, indent=2)

# Generate PDF report
from backend.core.reporting import ReportGenerator

report_gen = ReportGenerator()
report_path = await report_gen.generate_report(scan_id)
```

### Q: How do I cancel a running scan?

```python
# Update scan status
scan_state = await state_manager.read_scan_state(scan_id)
scan_state["status"] = "Cancelled"
await state_manager.write_scan_state(scan_id, scan_state)

# Cleanup resources
await orchestrator.release_context(scan_id)
```

### Q: How do I configure custom modules?

```python
# Specify modules in target config
target_config = {
    "url": "https://example.com",
    "modules": [
        "The Tycoon",
        "SQL Injection Probe",
        "JWT Token Cracker"
    ],
    "duration": 300
}

await HiveOrchestrator.bootstrap_hive(target_config, scan_id="scan-001")
```

### Q: How do I handle SSL certificate errors?

```python
import aiohttp
import ssl

# Create SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Use with aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get(url, ssl=ssl_context) as response:
        return await response.text()

# Note: Only use for testing, not production!
```

---

## Getting Help

### Check Logs

```bash
# View application logs
tail -f logs/application.log

# View error logs
tail -f logs/error.log

# Search for specific errors
grep "ERROR" logs/application.log
```

### Report Issues

When reporting issues, include:
1. Error message and stack trace
2. Scan configuration
3. System information (OS, Python version)
4. Steps to reproduce
5. Expected vs actual behavior

### Community Support

- GitHub Issues: [github.com/antigravity/issues](https://github.com/antigravity/issues)
- Documentation: [docs.antigravity.io](https://docs.antigravity.io)
- Discord: [discord.gg/antigravity](https://discord.gg/antigravity)

---

## See Also

- [API Reference](API_REFERENCE.md)
- [Usage Examples](USAGE_EXAMPLES.md)
- [Performance Tuning Guide](PERFORMANCE.md)
- [Security Best Practices](SECURITY_BEST_PRACTICES.md)

---

**Last Updated**: May 25, 2026  
**Maintainer**: Antigravity V5 Team
