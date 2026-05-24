# Design Document: Deep OpenClaw + PinchTab Hybrid Integration

## Overview

This design implements the **deepest possible integration** of OpenClaw browser automation into the Antigravity Hive, working in **hybrid mode with PinchTab**. OpenClaw provides advanced browser automation, multi-step workflows, and human-like behavior, while PinchTab handles lightweight DOM scraping and token extraction.

**Integration Depth**: OpenClaw will be deeply embedded into **Sigma, Gamma, Beta, Alpha, Omega, Delta, Prism, Chi, Zeta, and Kappa** - transforming them from HTTP-only agents into hybrid browser-aware intelligent operators.

## Architecture

### Hybrid Browser Stack

```
┌─────────────────────────────────────────────────────────┐
│                   HiveOrchestrator                      │
├─────────────────────────────────────────────────────────┤
│  EventBus │ NeuroNegotiator │ Cortex AI │ Graph Engine │
├─────────────────────────────────────────────────────────┤
│              HYBRID BROWSER LAYER (NEW)                 │
│  ┌──────────────────┬──────────────────────────────┐   │
│  │   OpenClaw       │      PinchTab                │   │
│  │   (Deep Auto)    │      (Fast Scrape)           │   │
│  ├──────────────────┴──────────────────────────────┤   │
│  │         BrowserOrchestrator (Unified API)       │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                    ENHANCED AGENTS                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Omega  → Strategy + Browser Campaign Planning   │   │
│  │ Alpha  → HTTP + Browser Recon (Dual Mode)       │   │
│  │ Beta   → HTTP + Browser Exploitation            │   │
│  │ Sigma  → Payload Forge + Browser Testing        │   │
│  │ Gamma  → Audit + Browser Verification           │   │
│  │ Delta  → PinchTab + OpenClaw Hybrid Controller  │   │
│  │ Prism  → DOM Analysis (Both engines)            │   │
│  │ Chi    → Event Intercept + Dark Pattern Block   │   │
│  │ Zeta   → Governance + Browser Resource Monitor  │   │
│  │ Kappa  → Memory + Browser Session Persistence   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Hybrid Approach**: PinchTab for speed, OpenClaw for depth
2. **Deep Integration**: Every agent gets browser capabilities
3. **Unified API**: Single interface for both browser engines
4. **Backward Compatible**: HTTP functionality remains unchanged
5. **Intelligent Routing**: Auto-select best browser engine per task
6. **Sovereign Operation**: All data stays local

## Core Infrastructure

### 1. BrowserOrchestrator (Unified Interface)

**Location**: `backend/core/browser_orchestrator.py`

**Purpose**: Unified API that intelligently routes between OpenClaw and PinchTab


```python
from enum import Enum
from typing import Optional, Dict, Any, List
import asyncio

class BrowserEngine(Enum):
    OPENCLAW = "openclaw"      # Deep automation, workflows, stealth
    PINCHTAB = "pinchtab"      # Fast scraping, token extraction
    AUTO = "auto"              # Intelligent selection

class BrowserOrchestrator:
    """
    Unified browser interface that routes between OpenClaw and PinchTab.
    Provides a single API for all agents to use browser capabilities.
    """
    
    def __init__(self):
        self.openclaw = OpenClawEngine()
        self.pinchtab = PinchTabEngine()
        self.session_manager = HybridSessionManager()
        self.forensics = ForensicCollector()
        
    async def initialize(self):
        """Initialize both browser engines"""
        await self.openclaw.initialize()
        await self.pinchtab.initialize()
        
    async def navigate(self, url: str, engine: BrowserEngine = BrowserEngine.AUTO,
                      stealth: bool = False, wait_for: str = "networkidle"):
        """
        Navigate to URL using best engine for the task.
        
        AUTO mode logic:
        - Use PinchTab for: Simple DOM scraping, token extraction, fast recon
        - Use OpenClaw for: Complex workflows, stealth mode, multi-step attacks
        """
        selected_engine = self._select_engine(engine, stealth, url)
        
        if selected_engine == BrowserEngine.PINCHTAB:
            return await self.pinchtab.navigate(url)
        else:
            return await self.openclaw.navigate(url, stealth=stealth, wait_for=wait_for)
            
    async def extract_endpoints(self, url: str, deep: bool = False):
        """
        Extract API endpoints from page.
        
        deep=False: Use PinchTab (fast, surface-level)
        deep=True: Use OpenClaw (deep JS analysis, XHR interception)
        """
        if deep:
            return await self.openclaw.extract_endpoints_deep(url)
        else:
            return await self.pinchtab.extract_endpoints_fast(url)
            
    async def execute_workflow(self, workflow: Dict, scan_id: str):
        """Execute multi-step workflow (OpenClaw only)"""
        return await self.openclaw.execute_workflow(workflow, scan_id)
        
    async def extract_tokens(self, url: str):
        """Extract auth tokens (PinchTab optimized)"""
        return await self.pinchtab.extract_tokens(url)
        
    async def test_payload(self, url: str, payload: str, method: str = "GET"):
        """
        Test payload in browser context.
        Uses OpenClaw for XSS/CSRF, PinchTab for simple injection tests.
        """
        if any(x in payload.lower() for x in ["<script", "onerror", "onclick"]):
            # XSS needs real browser execution
            return await self.openclaw.test_xss_payload(url, payload)
        else:
            # Simple injection can use fast mode
            return await self.pinchtab.test_injection(url, payload, method)
            
    def _select_engine(self, requested: BrowserEngine, stealth: bool, url: str):
        """Intelligent engine selection"""
        if requested != BrowserEngine.AUTO:
            return requested
            
        # Auto-select based on requirements
        if stealth:
            return BrowserEngine.OPENCLAW
        if "login" in url or "auth" in url:
            return BrowserEngine.OPENCLAW  # Need session handling
        return BrowserEngine.PINCHTAB  # Default to fast mode
```

### 2. OpenClawEngine (Deep Automation)

**Location**: `backend/core/openclaw_engine.py`

**Purpose**: Advanced browser automation with OpenClaw


```python
class OpenClawBridge:
    """Bridge between Hive and OpenClaw framework"""
    
    def __init__(self):
        self.playwright_manager = None
        self.active_contexts = {}
        self.max_contexts = 5
        
    async def initialize(self):
        """Initialize OpenClaw and Playwright"""
        from openclaw import ClawClient  # Direct dependency
        self.claw_client = ClawClient()
        await self.claw_client.initialize()
        
    async def create_browser_context(self, scan_id: str, stealth: bool = False):
        """Create isolated browser context for a scan"""
        context = await self.claw_client.create_context(
            headless=not settings.THETA_DEBUG_MODE,
            stealth=stealth
        )
        self.active_contexts[scan_id] = context
        return context
        
    async def navigate(self, context, url: str, wait_for: str = "networkidle"):
        """Navigate to URL with OpenClaw"""
        return await context.navigate(url, wait_for=wait_for)
        
    async def extract_endpoints(self, context) -> list[str]:
        """Extract API endpoints from page using OpenClaw"""
        return await context.extract_api_endpoints()
        
    async def execute_workflow(self, context, workflow: dict):
        """Execute multi-step workflow via OpenClaw"""
        return await context.run_workflow(workflow)
```

### 3. BrowserSessionManager

**Location**: `backend/agents/theta_session.py`

**Purpose**: Manage persistent browser sessions, cookies, and authentication state


```python
class BrowserSessionManager:
    """Manage persistent browser sessions and authentication"""
    
    def __init__(self):
        self.session_store = Path("scan_states/browser_sessions")
        self.session_store.mkdir(parents=True, exist_ok=True)
        
    async def save_session(self, scan_id: str, context):
        """Persist browser session state"""
        session_data = {
            "cookies": await context.cookies(),
            "local_storage": await context.evaluate("() => Object.entries(localStorage)"),
            "session_storage": await context.evaluate("() => Object.entries(sessionStorage)"),
            "timestamp": datetime.now().isoformat()
        }
        session_file = self.session_store / f"{scan_id}.json"
        session_file.write_text(json.dumps(session_data, indent=2))
        
    async def restore_session(self, scan_id: str, context):
        """Restore saved browser session"""
        session_file = self.session_store / f"{scan_id}.json"
        if not session_file.exists():
            return False
            
        session_data = json.loads(session_file.read_text())
        await context.add_cookies(session_data["cookies"])
        
        # Restore storage
        for key, value in session_data["local_storage"]:
            await context.evaluate(f"localStorage.setItem('{key}', '{value}')")
        return True
        
    async def detect_auth_form(self, context) -> dict | None:
        """Detect login forms on current page"""
        return await context.evaluate("""() => {
            const forms = document.querySelectorAll('form');
            for (const form of forms) {
                const inputs = form.querySelectorAll('input');
                const hasPassword = Array.from(inputs).some(i => i.type === 'password');
                const hasUsername = Array.from(inputs).some(i => 
                    i.type === 'text' || i.type === 'email' || i.name.includes('user')
                );
                if (hasPassword && hasUsername) {
                    return {
                        action: form.action,
                        method: form.method,
                        fields: Array.from(inputs).map(i => ({
                            name: i.name,
                            type: i.type
                        }))
                    };
                }
            }
            return null;
        }""")
```


### 4. WorkflowOrchestrator

**Location**: `backend/agents/theta_workflow.py`

**Purpose**: Orchestrate multi-step attack workflows with AI-driven decision making

```python
class WorkflowOrchestrator:
    """Orchestrate multi-step browser-based attack workflows"""
    
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.cortex = get_cortex_engine()
        self.active_workflows = {}
        
    async def create_workflow(self, scan_id: str, target_url: str, 
                             vuln_type: str) -> AttackWorkflow:
        """Create AI-generated attack workflow"""
        
        # Ask Cortex AI to generate workflow steps
        workflow_plan = await self.cortex.generate_workflow(
            target=target_url,
            vulnerability=vuln_type,
            context="browser-based exploitation"
        )
        
        workflow = AttackWorkflow(
            scan_id=scan_id,
            target=target_url,
            steps=workflow_plan["steps"],
            max_retries=3
        )
        
        self.active_workflows[scan_id] = workflow
        return workflow
        
    async def execute_workflow(self, workflow: AttackWorkflow, context):
        """Execute workflow steps sequentially"""
        results = []
        
        for step in workflow.steps:
            try:
                # Publish progress
                await self.bus.publish(HiveEvent(
                    type=EventType.LIVE_ATTACK,
                    source="agent_theta",
                    scan_id=workflow.scan_id,
                    payload={
                        "url": workflow.target,
                        "arsenal": "Browser Automation",
                        "action": step["action"],
                        "payload": step.get("payload", "N/A")
                    }
                ))
                
                # Execute step
                result = await self._execute_step(context, step)
                results.append(result)
                
                # If step failed, try AI mutation
                if not result.success and step.get("retry_on_fail"):
                    mutated = await self.cortex.mutate_step(step, result.error)
                    result = await self._execute_step(context, mutated)
                    results.append(result)
                    
            except Exception as e:
                print(f"[WorkflowOrchestrator] Step failed: {e}")
                if not step.get("continue_on_error"):
                    break
                    
        return results
```


### 5. ForensicCollector

**Location**: `backend/agents/theta_forensics.py`

**Purpose**: Capture comprehensive forensic evidence for all browser actions

```python
class ForensicCollector:
    """Collect forensic evidence from browser operations"""
    
    def __init__(self):
        self.evidence_dir = Path("reports/forensics")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
    async def capture_screenshot(self, context, scan_id: str, 
                                label: str) -> Path:
        """Capture screenshot with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scan_id}_{label}_{timestamp}.png"
        filepath = self.evidence_dir / filename
        
        await context.screenshot(path=str(filepath), full_page=True)
        return filepath
        
    async def capture_network_log(self, context, scan_id: str) -> dict:
        """Capture all network requests/responses"""
        network_log = await context.evaluate("""() => {
            return window.performance.getEntries()
                .filter(e => e.entryType === 'resource')
                .map(e => ({
                    url: e.name,
                    method: e.initiatorType,
                    duration: e.duration,
                    size: e.transferSize
                }));
        }""")
        
        return {
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "requests": network_log
        }
        
    async def capture_dom_snapshot(self, context, scan_id: str, 
                                   label: str) -> Path:
        """Save DOM snapshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scan_id}_{label}_{timestamp}.html"
        filepath = self.evidence_dir / filename
        
        html = await context.content()
        filepath.write_text(html, encoding="utf-8")
        return filepath
        
    async def create_evidence_bundle(self, scan_id: str, 
                                    workflow_results: list) -> dict:
        """Package all evidence into forensic bundle"""
        bundle = {
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "agent": "agent_theta",
            "evidence": {
                "screenshots": [],
                "network_logs": [],
                "dom_snapshots": [],
                "workflow_results": workflow_results
            }
        }
        
        # Collect all evidence files for this scan
        for file in self.evidence_dir.glob(f"{scan_id}_*"):
            if file.suffix == ".png":
                bundle["evidence"]["screenshots"].append(str(file))
            elif file.suffix == ".html":
                bundle["evidence"]["dom_snapshots"].append(str(file))
                
        return bundle
```


## Integration Points

### EventBus Communication Flow

```
1. TARGET_ACQUIRED Event
   ↓
   Agent Theta receives event
   ↓
   Bid for NETWORK + CPU resources via NeuroNegotiator
   ↓
   Launch browser context via OpenClawBridge
   ↓
   Execute reconnaissance workflow
   ↓
   Publish RECON_PACKET events for discovered endpoints
   ↓
   Capture forensic evidence
   ↓
   Release resources

2. VULN_CANDIDATE Event (from Alpha/Beta)
   ↓
   Agent Theta evaluates if browser interaction needed
   ↓
   Create attack workflow via WorkflowOrchestrator
   ↓
   Execute multi-step exploitation
   ↓
   Publish VULN_CONFIRMED if successful
   ↓
   Package forensic evidence bundle

3. JOB_ASSIGNED Event (agent_id == THETA)
   ↓
   Parse JobPacket
   ↓
   Execute specific browser-based task
   ↓
   Publish JOB_COMPLETED with results
```

### Resource Management Integration

Agent Theta integrates with NeuroNegotiator for resource bidding:

```python
async def _bid_for_resources(self, priority: float = 0.7):
    """Bid for browser operation resources"""
    from backend.core.hyper_hive import ResourceType, Bid
    
    # Bid for network (HTTP requests from browser)
    network_bid = Bid(
        agent_id="agent_theta",
        resource_type=ResourceType.NETWORK,
        priority=priority,
        estimated_duration=30.0
    )
    
    # Bid for CPU (browser rendering)
    cpu_bid = Bid(
        agent_id="agent_theta",
        resource_type=ResourceType.CPU,
        priority=priority,
        estimated_duration=30.0
    )
    
    network_granted = await self.negotiator.request_resource(network_bid)
    cpu_granted = await self.negotiator.request_resource(cpu_bid)
    
    return network_granted and cpu_granted
```


### Agent Factory Integration

Update `backend/agents/factory.py` to include Agent Theta:

```python
AGENT_MODULES = [
    "backend.agents.alpha",
    "backend.agents.beta",
    "backend.agents.gamma",
    "backend.agents.kappa",
    "backend.agents.omega",
    "backend.agents.sigma",
    "backend.agents.zeta",
    "backend.agents.delta",
    "backend.agents.prism",
    "backend.agents.chi",
    "backend.agents.theta",  # NEW
]
```

### Protocol Extension

Add THETA to AgentID enum in `backend/core/protocol.py`:

```python
class AgentID(str, Enum):
    ALPHA = "ALPHA"
    BETA = "BETA"
    GAMMA = "GAMMA"
    SIGMA = "SIGMA"
    ZETA = "ZETA"
    KAPPA = "KAPPA"
    OMEGA = "OMEGA"
    DELTA = "DELTA"
    PRISM = "PRISM"
    CHI = "CHI"
    THETA = "THETA"  # NEW - Browser automation agent
```

## Data Models

### AttackWorkflow

```python
from pydantic import BaseModel
from typing import List, Optional

class WorkflowStep(BaseModel):
    action: str  # "navigate", "click", "fill", "extract", "wait"
    target: str  # CSS selector or URL
    payload: Optional[str] = None
    wait_for: str = "networkidle"
    retry_on_fail: bool = True
    continue_on_error: bool = False
    timeout: int = 30

class AttackWorkflow(BaseModel):
    scan_id: str
    target: str
    steps: List[WorkflowStep]
    max_retries: int = 3
    stealth_mode: bool = False
    current_step: int = 0
```


### BrowserReconResult

```python
class BrowserReconResult(BaseModel):
    scan_id: str
    target_url: str
    discovered_endpoints: List[str]
    javascript_framework: Optional[str] = None
    forms: List[dict]
    websockets: List[str]
    api_calls: List[dict]
    cookies: List[dict]
    local_storage_keys: List[str]
    evidence_bundle: dict

class ForensicEvidence(BaseModel):
    scan_id: str
    timestamp: str
    agent: str = "agent_theta"
    screenshots: List[str]
    network_logs: List[dict]
    dom_snapshots: List[str]
    workflow_results: List[dict]
```

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Agent Theta Configuration
THETA_ENABLED=true
THETA_DEBUG_MODE=false  # Set true for headed browser
THETA_MAX_CONTEXTS=5
THETA_STEALTH_MODE=true
THETA_AGGRESSION_LEVEL=5
THETA_TIMEOUT=60
THETA_SCREENSHOT_QUALITY=80

# OpenClaw Configuration
OPENCLAW_HEADLESS=true
OPENCLAW_BROWSER=chromium  # chromium, firefox, webkit
OPENCLAW_VIEWPORT_WIDTH=1920
OPENCLAW_VIEWPORT_HEIGHT=1080
```

### Settings Integration

Update `backend/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Agent Theta
    THETA_ENABLED: bool = True
    THETA_DEBUG_MODE: bool = False
    THETA_MAX_CONTEXTS: int = 5
    THETA_STEALTH_MODE: bool = True
    THETA_AGGRESSION_LEVEL: int = 5
    THETA_TIMEOUT: int = 60
    
    # OpenClaw
    OPENCLAW_HEADLESS: bool = True
    OPENCLAW_BROWSER: str = "chromium"
```


## Operational Workflows

### Workflow 1: Browser Reconnaissance

```
User initiates scan → TARGET_ACQUIRED event
↓
Agent Theta receives event
↓
Bid for resources (NETWORK + CPU)
↓
Resources granted → Create browser context
↓
Navigate to target URL
↓
Extract JavaScript routes via OpenClaw
↓
Identify framework (React/Vue/Angular)
↓
Catalog forms and input fields
↓
Detect WebSocket connections
↓
Capture network traffic
↓
Take forensic screenshots
↓
Publish RECON_PACKET for each discovered endpoint
↓
Save session state
↓
Release resources
```

### Workflow 2: Interactive Exploitation

```
VULN_CANDIDATE event received (e.g., XSS candidate)
↓
Agent Theta evaluates: "Does this need browser interaction?"
↓
If YES → Create attack workflow via Cortex AI
↓
Workflow steps generated:
  1. Navigate to vulnerable page
  2. Fill form with XSS payload
  3. Submit form
  4. Wait for response
  5. Check if payload executed
↓
Execute workflow step-by-step
↓
Capture screenshot before/after each step
↓
If payload executes → VULN_CONFIRMED
↓
Package forensic evidence bundle
↓
Publish to EventBus
```


### Workflow 3: Session-Based Testing

```
Target requires authentication
↓
Agent Theta detects login form
↓
Check if credentials available in config
↓
If YES → Fill credentials with stealth typing
↓
Submit form
↓
Wait for redirect/success indicator
↓
Save session state (cookies + localStorage)
↓
Continue with authenticated scanning
↓
Test post-auth endpoints
↓
If session expires → Restore from saved state
```

## Stealth Mode Implementation

When `THETA_STEALTH_MODE=true`, Agent Theta mimics human behavior:

```python
class StealthBehavior:
    """Human-like interaction patterns"""
    
    async def human_type(self, context, selector: str, text: str):
        """Type with human-like delays"""
        element = await context.query_selector(selector)
        for char in text:
            await element.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))
            
    async def human_click(self, context, selector: str):
        """Click with mouse movement simulation"""
        element = await context.query_selector(selector)
        box = await element.bounding_box()
        
        # Move mouse to element
        await context.mouse.move(
            box["x"] + random.uniform(5, box["width"] - 5),
            box["y"] + random.uniform(5, box["height"] - 5)
        )
        await asyncio.sleep(random.uniform(0.1, 0.3))
        await element.click()
        
    async def random_scroll(self, context):
        """Random scrolling behavior"""
        await context.evaluate("""() => {
            window.scrollBy(0, Math.random() * 500);
        }""")
        await asyncio.sleep(random.uniform(0.5, 1.5))
```


## Error Handling Strategy

### Browser Crash Recovery

```python
async def _execute_with_recovery(self, context, operation):
    """Execute operation with automatic crash recovery"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await operation(context)
        except PlaywrightError as e:
            if "Target closed" in str(e) or "Browser closed" in str(e):
                print(f"[Agent Theta] Browser crashed, attempt {attempt + 1}/{max_retries}")
                # Recreate context
                context = await self.openclaw_bridge.create_browser_context(
                    scan_id=context.scan_id,
                    stealth=self.stealth_mode
                )
                # Restore session if available
                await self.session_manager.restore_session(context.scan_id, context)
            else:
                raise
    raise Exception("Max retries exceeded after browser crashes")
```

### Network Error Handling

```python
async def _fetch_with_retry(self, context, url: str):
    """Navigate with exponential backoff"""
    backoff = 1
    for attempt in range(3):
        try:
            return await context.navigate(url, timeout=30000)
        except TimeoutError:
            print(f"[Agent Theta] Timeout on {url}, retry {attempt + 1}")
            await asyncio.sleep(backoff)
            backoff *= 2
    
    # Publish error event
    await self.bus.publish(HiveEvent(
        type=EventType.ERROR,
        source="agent_theta",
        payload={"url": url, "error": "Navigation timeout after retries"}
    ))
    return None
```


## Performance Optimization

### Browser Context Pooling

```python
class BrowserContextPool:
    """Reuse browser contexts for efficiency"""
    
    def __init__(self, max_size: int = 5):
        self.pool = asyncio.Queue(maxsize=max_size)
        self.active = {}
        
    async def acquire(self, scan_id: str) -> BrowserContext:
        """Get context from pool or create new"""
        if not self.pool.empty():
            context = await self.pool.get()
            self.active[scan_id] = context
            return context
        else:
            context = await self._create_new_context()
            self.active[scan_id] = context
            return context
            
    async def release(self, scan_id: str):
        """Return context to pool"""
        if scan_id in self.active:
            context = self.active.pop(scan_id)
            await context.clear_cookies()
            await self.pool.put(context)
```

### Memory Management

```python
async def _monitor_memory(self):
    """Monitor and manage browser memory usage"""
    while True:
        await asyncio.sleep(60)  # Check every minute
        
        memory_usage = await self._get_browser_memory()
        if memory_usage > settings.THETA_MAX_MEMORY_MB:
            print(f"[Agent Theta] Memory threshold exceeded: {memory_usage}MB")
            # Close idle contexts
            await self._close_idle_contexts()
```

## Testing Strategy

### Unit Tests

```python
# tests/test_theta_agent.py
async def test_theta_reconnaissance():
    """Test basic reconnaissance workflow"""
    bus = MockEventBus()
    agent = ThetaAgent(bus)
    
    event = HiveEvent(
        type=EventType.TARGET_ACQUIRED,
        source="test",
        payload={"url": "http://testsite.local"}
    )
    
    await agent.handle_target(event)
    
    # Verify RECON_PACKET events published
    assert bus.published_events[EventType.RECON_PACKET]
```


### Integration Tests

```python
# tests/test_theta_integration.py
async def test_full_browser_workflow():
    """Test complete browser-based attack workflow"""
    orchestrator = HiveOrchestrator()
    await orchestrator.initialize()
    
    # Trigger scan
    scan_id = await orchestrator.fire_scan("http://vulnerable-app.local")
    
    # Wait for Agent Theta to complete
    await asyncio.sleep(30)
    
    # Verify forensic evidence collected
    evidence_dir = Path(f"reports/forensics")
    screenshots = list(evidence_dir.glob(f"{scan_id}_*.png"))
    assert len(screenshots) > 0
```

## Security Considerations

### Sandbox Isolation

All browser operations run in isolated contexts:

```python
# Each scan gets isolated browser context
context = await browser.new_context(
    viewport={"width": 1920, "height": 1080},
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    java_script_enabled=True,
    bypass_csp=False,  # Respect CSP for realistic testing
    ignore_https_errors=False  # Validate certificates
)
```

### Data Sovereignty

All captured data stays local:
- Screenshots → `reports/forensics/`
- Session data → `scan_states/browser_sessions/`
- Network logs → In-memory, included in forensic bundles
- No external API calls (respects Sovereign Midnight principle)

### Credential Handling

```python
# Credentials never logged or transmitted
async def authenticate(self, context, credentials: dict):
    """Securely handle authentication"""
    # Credentials sanitized in logs
    print(f"[Agent Theta] Authenticating as {credentials.get('username', 'REDACTED')}")
    
    # Fill form
    await context.fill("input[name='username']", credentials["username"])
    await context.fill("input[type='password']", credentials["password"])
    
    # Clear from memory after use
    credentials.clear()
```


## Dependency Management

### Installation

Add to `backend/requirements.txt`:

```txt
# OpenClaw Integration
openclaw>=0.1.0
playwright==1.49.0  # Already present, ensure version compatibility
```

### Installation Script

```bash
# Install OpenClaw and browser binaries
pip install openclaw
playwright install chromium

# For development with local OpenClaw
pip install -e d:/projects/openclaw
```

### Import Structure

```python
# backend/agents/theta.py
from openclaw import ClawClient, WorkflowEngine
from openclaw.browser import BrowserContext
from openclaw.stealth import StealthMode

# Fallback if OpenClaw not available
try:
    from openclaw import ClawClient
    OPENCLAW_AVAILABLE = True
except ImportError:
    OPENCLAW_AVAILABLE = False
    print("[Agent Theta] OpenClaw not available, agent disabled")
```

## Monitoring and Observability

### Metrics

Agent Theta exposes metrics via EventBus:

```python
class ThetaMetrics(BaseModel):
    active_contexts: int
    total_pages_visited: int
    total_screenshots: int
    total_workflows_executed: int
    average_workflow_duration: float
    memory_usage_mb: float
    
async def publish_metrics(self):
    """Publish metrics to EventBus"""
    metrics = ThetaMetrics(
        active_contexts=len(self.openclaw_bridge.active_contexts),
        total_pages_visited=self.stats["pages_visited"],
        total_screenshots=self.stats["screenshots"],
        total_workflows_executed=self.stats["workflows"],
        average_workflow_duration=self.stats["avg_duration"],
        memory_usage_mb=await self._get_memory_usage()
    )
    
    await self.bus.publish(HiveEvent(
        type=EventType.METRICS,
        source="agent_theta",
        payload=metrics.model_dump()
    ))
```


### Dashboard Integration

Frontend displays Agent Theta status:

```javascript
// src/components/AgentStatus.jsx
const AgentTheta = ({ metrics }) => (
  <div className="glass-panel">
    <h3 className="text-glow">Agent Theta: The Phantom</h3>
    <div className="metrics">
      <Metric label="Active Browsers" value={metrics.active_contexts} />
      <Metric label="Pages Visited" value={metrics.total_pages_visited} />
      <Metric label="Screenshots" value={metrics.total_screenshots} />
      <Metric label="Memory" value={`${metrics.memory_usage_mb}MB`} />
    </div>
    {metrics.current_action && (
      <div className="current-action">
        <span className="pulse-dot" />
        {metrics.current_action}
      </div>
    )}
  </div>
);
```

## Migration Path

### Phase 1: Foundation (Week 1)
1. Install OpenClaw dependency
2. Create ThetaAgent skeleton
3. Implement OpenClawBridge
4. Add to agent factory
5. Basic EventBus integration

### Phase 2: Core Features (Week 2)
1. Implement BrowserSessionManager
2. Implement ForensicCollector
3. Basic reconnaissance workflow
4. Screenshot capture
5. Network logging

### Phase 3: Advanced Features (Week 3)
1. Implement WorkflowOrchestrator
2. AI-driven workflow generation
3. Multi-step exploitation
4. Session persistence
5. Stealth mode

### Phase 4: Polish & Testing (Week 4)
1. Error handling & recovery
2. Performance optimization
3. Integration tests
4. Dashboard integration
5. Documentation


## Correctness Properties

### Property 1: Resource Cleanup
**Validates: Requirement 8 (Resource Management)**

```python
@property_test
async def test_resources_always_released(target_url: str):
    """Browser resources must be released after operations"""
    agent = ThetaAgent(bus)
    initial_contexts = len(agent.openclaw_bridge.active_contexts)
    
    await agent.handle_target(HiveEvent(
        type=EventType.TARGET_ACQUIRED,
        payload={"url": target_url}
    ))
    
    # Wait for completion
    await asyncio.sleep(5)
    
    final_contexts = len(agent.openclaw_bridge.active_contexts)
    assert final_contexts == initial_contexts, "Resources not released"
```

### Property 2: Evidence Completeness
**Validates: Requirement 7 (Forensic Evidence)**

```python
@property_test
async def test_evidence_always_captured(workflow: AttackWorkflow):
    """Every workflow execution must produce forensic evidence"""
    collector = ForensicCollector()
    results = await orchestrator.execute_workflow(workflow, context)
    
    evidence = await collector.create_evidence_bundle(
        workflow.scan_id, 
        results
    )
    
    # Must have at least one piece of evidence
    assert (
        len(evidence["evidence"]["screenshots"]) > 0 or
        len(evidence["evidence"]["dom_snapshots"]) > 0 or
        len(evidence["evidence"]["network_logs"]) > 0
    ), "No forensic evidence captured"
```

### Property 3: Session Persistence
**Validates: Requirement 4 (Session Persistence)**

```python
@property_test
async def test_session_survives_restart(scan_id: str, target_url: str):
    """Saved sessions must be restorable"""
    manager = BrowserSessionManager()
    
    # Create and save session
    context1 = await create_context()
    await context1.navigate(target_url)
    await manager.save_session(scan_id, context1)
    await context1.close()
    
    # Restore in new context
    context2 = await create_context()
    restored = await manager.restore_session(scan_id, context2)
    
    assert restored == True, "Session restoration failed"
    
    # Verify cookies restored
    cookies1 = await context1.cookies()
    cookies2 = await context2.cookies()
    assert len(cookies2) == len(cookies1), "Cookies not restored"
```


### Property 4: Stealth Timing
**Validates: Requirement 5 (Stealth Behavior)**

```python
@property_test
async def test_stealth_mode_adds_delays(action_sequence: List[str]):
    """Stealth mode must add human-like delays between actions"""
    agent = ThetaAgent(bus)
    agent.stealth_mode = True
    
    start = time.time()
    for action in action_sequence:
        await agent._execute_action(context, action)
    duration_stealth = time.time() - start
    
    agent.stealth_mode = False
    start = time.time()
    for action in action_sequence:
        await agent._execute_action(context, action)
    duration_fast = time.time() - start
    
    # Stealth mode should be slower
    assert duration_stealth > duration_fast * 1.5, "Stealth mode not adding delays"
```

### Property 5: EventBus Communication
**Validates: Requirement 6 (EventBus Integration)**

```python
@property_test
async def test_events_always_published(target_url: str):
    """Agent must publish events for all significant actions"""
    bus = MockEventBus()
    agent = ThetaAgent(bus)
    
    await agent.handle_target(HiveEvent(
        type=EventType.TARGET_ACQUIRED,
        payload={"url": target_url}
    ))
    
    # Must publish at least LIVE_ATTACK and RECON_PACKET
    assert EventType.LIVE_ATTACK in bus.published_events
    assert EventType.RECON_PACKET in bus.published_events
```

## Risk Analysis

### High Risk Areas

1. **Browser Memory Leaks**
   - **Risk**: Unclosed contexts consume memory
   - **Mitigation**: Context pooling + automatic cleanup + memory monitoring

2. **Target Site Blocking**
   - **Risk**: Aggressive scanning triggers rate limits/bans
   - **Mitigation**: Stealth mode + configurable aggression + NeuroNegotiator throttling

3. **Credential Exposure**
   - **Risk**: Credentials logged or transmitted
   - **Mitigation**: Sanitized logging + no external calls + secure storage

4. **Browser Crashes**
   - **Risk**: Playwright crashes disrupt scans
   - **Mitigation**: Automatic recovery + retry logic + error events

### Medium Risk Areas

1. **Performance Degradation**
   - **Risk**: Multiple browsers slow system
   - **Mitigation**: Context limits + resource bidding + pooling

2. **Forensic Storage**
   - **Risk**: Screenshots fill disk
   - **Mitigation**: Configurable retention + compression + cleanup

## Success Criteria

The integration is successful when:

1. ✅ Agent Theta spawns alongside existing agents
2. ✅ Browser reconnaissance discovers 90%+ of endpoints found by manual testing
3. ✅ Multi-step workflows execute without manual intervention
4. ✅ Forensic evidence captured for 100% of operations
5. ✅ No memory leaks after 100 consecutive scans
6. ✅ Stealth mode evades basic bot detection
7. ✅ Session persistence works across browser restarts
8. ✅ Integration tests pass with 95%+ reliability
9. ✅ Dashboard displays real-time Agent Theta status
10. ✅ Zero external data leakage (Sovereign Midnight maintained)

---

**End of Design Document**
        else:
            return await self.openclaw.navigate(url, stealth=stealth, wait_for=wait_for)
            
    async def extract_endpoints(self, url: str, deep: bool = False):
        """Extract API endpoints - deep mode uses OpenClaw"""
        if deep:
            return await self.openclaw.extract_endpoints_deep(url)
        else:
            return await self.pinchtab.extract_endpoints_fast(url)
            
    async def execute_workflow(self, workflow: Dict, scan_id: str):
        """Execute multi-step workflow (OpenClaw only)"""
        return await self.openclaw.execute_workflow(workflow, scan_id)
        
    async def extract_tokens(self, url: str):
        """Extract auth tokens (PinchTab optimized)"""
        return await self.pinchtab.extract_tokens(url)
        
    async def test_payload(self, url: str, payload: str, method: str = "GET"):
        """Test payload in browser - auto-selects engine"""
        if any(x in payload.lower() for x in ["<script", "onerror", "onclick"]):
            return await self.openclaw.test_xss_payload(url, payload)
        else:
            return await self.pinchtab.test_injection(url, payload, method)
            
    def _select_engine(self, requested: BrowserEngine, stealth: bool, url: str):
        """Intelligent engine selection"""
        if requested != BrowserEngine.AUTO:
            return requested
        if stealth or "login" in url or "auth" in url:
            return BrowserEngine.OPENCLAW
        return BrowserEngine.PINCHTAB
```

### 2. OpenClawEngine (Deep Automation)

**Location**: `backend/core/openclaw_engine.py`

```python
from openclaw import ClawClient, WorkflowEngine
import asyncio

class OpenClawEngine:
    """Deep browser automation using OpenClaw"""
    
    def __init__(self):
        self.client = None
        self.active_contexts = {}
        self.workflow_engine = None
        
    async def initialize(self):
        """Initialize OpenClaw client"""
        self.client = ClawClient()
        await self.client.initialize()
        self.workflow_engine = WorkflowEngine(self.client)
        
    async def navigate(self, url: str, stealth: bool = False, wait_for: str = "networkidle"):
        """Navigate with OpenClaw"""
        context = await self.client.create_context(
            headless=not settings.OPENCLAW_DEBUG,
            stealth=stealth
        )
        page = await context.new_page()
        await page.goto(url, wait_until=wait_for)
        return {"context": context, "page": page}
        
    async def extract_endpoints_deep(self, url: str):
        """Deep endpoint extraction with JS analysis"""
        result = await self.navigate(url)
        page = result["page"]
        
        # Extract from window.location, fetch calls, XHR
        endpoints = await page.evaluate("""() => {
            const endpoints = new Set();
            
            // Intercept fetch
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                endpoints.add(args[0]);
                return originalFetch.apply(this, args);
            };
            
            // Intercept XHR
            const originalOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url) {
                endpoints.add(url);
                return originalOpen.apply(this, arguments);
            };
            
            // Extract from React Router
            if (window.__REACT_ROUTER__) {
                const routes = window.__REACT_ROUTER__.routes || [];
                routes.forEach(r => endpoints.add(r.path));
            }
            
            return Array.from(endpoints);
        }""")
        
        return endpoints
        
    async def execute_workflow(self, workflow: Dict, scan_id: str):
        """Execute multi-step workflow"""
        return await self.workflow_engine.execute(workflow, scan_id)
        
    async def test_xss_payload(self, url: str, payload: str):
        """Test XSS in real browser"""
        result = await self.navigate(url)
        page = result["page"]
        
        # Inject payload
        await page.evaluate(f"document.body.innerHTML += '{payload}'")
        
        # Check if alert fired
        alert_fired = await page.evaluate("window.alertFired || false")
        
        # Check DOM modification
        dom_modified = await page.evaluate("""() => {
            return document.body.innerHTML.includes('script');
        }""")
        
        return {
            "alert_triggered": alert_fired,
            "dom_modified": dom_modified,
            "exploited": alert_fired or dom_modified
        }
```

### 3. PinchTabEngine (Fast Operations)

**Location**: `backend/core/pinchtab_engine.py`

```python
from backend.integrations.pinchtab_client import PinchTabClient

class PinchTabEngine:
    """Fast DOM scraping using PinchTab"""
    
    def __init__(self):
        self.client = PinchTabClient()
        self.last_tab_id = None
        
    async def initialize(self):
        """Initialize PinchTab"""
        await self.client.health()
        
    async def navigate(self, url: str):
        """Fast navigation"""
        result = await self.client.navigate(url)
        self.last_tab_id = result.get("tabId")
        return result
        
    async def extract_endpoints_fast(self, url: str):
        """Fast endpoint extraction"""
        await self.navigate(url)
        text = await self.client.text(self.last_tab_id)
        
        # Quick regex extraction
        import re
        endpoints = re.findall(r'["\']/(api|v\d+)/[^"\']+["\']', text)
        return list(set(endpoints))
        
    async def extract_tokens(self, url: str):
        """Fast token extraction"""
        await self.navigate(url)
        text = await self.client.text(self.last_tab_id)
        
        # Extract JWT, Bearer tokens
        import re
        jwt_pattern = r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
        tokens = re.findall(jwt_pattern, text)
        return tokens
        
    async def test_injection(self, url: str, payload: str, method: str):
        """Fast injection test"""
        await self.navigate(f"{url}?test={payload}")
        text = await self.client.text(self.last_tab_id)
        return {"reflected": payload in text}
```

### 4. HybridSessionManager

**Location**: `backend/core/hybrid_session_manager.py`

```python
class HybridSessionManager:
    """Manage sessions across both browser engines"""
    
    def __init__(self):
        self.sessions = {}  # scan_id -> session data
        self.session_dir = Path("scan_states/browser_sessions")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
    async def save_session(self, scan_id: str, engine: BrowserEngine, context):
        """Save session from either engine"""
        if engine == BrowserEngine.OPENCLAW:
            session_data = await self._export_openclaw_session(context)
        else:
            session_data = await self._export_pinchtab_session(context)
            
        session_file = self.session_dir / f"{scan_id}.json"
        session_file.write_text(json.dumps(session_data, indent=2))
        
    async def restore_session(self, scan_id: str, engine: BrowserEngine, context):
        """Restore session to either engine"""
        session_file = self.session_dir / f"{scan_id}.json"
        if not session_file.exists():
            return False
            
        session_data = json.loads(session_file.read_text())
        
        if engine == BrowserEngine.OPENCLAW:
            await self._import_openclaw_session(context, session_data)
        else:
            await self._import_pinchtab_session(context, session_data)
            
        return True
        
    async def _export_openclaw_session(self, context):
        """Export OpenClaw session"""
        return {
            "cookies": await context.cookies(),
            "local_storage": await context.evaluate("() => Object.entries(localStorage)"),
            "session_storage": await context.evaluate("() => Object.entries(sessionStorage)")
        }
```

## Agent-Specific Integration

### OMEGA Integration

**File**: `backend/agents/omega.py`

**Changes**:
```python
class OmegaAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("agent_omega", bus)
        self.browser = BrowserOrchestrator()  # NEW
        
        # Add browser-aware strategies
        self.STRATEGY_PROFILES["BROWSER_DEEP_RECON"] = {
            "description": "Deep browser-based reconnaissance for SPAs",
            "modules": ["alpha_browser_recon", "beta_browser_exploit"],
            "aggression": 7,
            "priority": TaskPriority.HIGH,
            "requires_browser": True  # NEW
        }
        
    async def initiate_campaign(self, target_url, scan_id):
        # Detect if target requires browser
        is_spa = await self._detect_spa(target_url)
        
        if is_spa:
            print(f"[{self.name}] SPA detected. Launching browser campaign.")
            strategy = "BROWSER_DEEP_RECON"
        else:
            strategy = self._select_strategy(target_url, scan_id=scan_id)
            
        # Execute campaign with browser awareness
        await self._execute_campaign(strategy, target_url, scan_id)
        
    async def _detect_spa(self, url):
        """Detect if target is a Single Page Application"""
        # Quick check with PinchTab
        await self.browser.navigate(url, engine=BrowserEngine.PINCHTAB)
        text = await self.browser.get_page_text()
        
        # Look for SPA indicators
        spa_indicators = ["react", "vue", "angular", "__NEXT_DATA__", "ng-app"]
        return any(indicator in text.lower() for indicator in spa_indicators)
```

### ALPHA Integration

**File**: `backend/agents/alpha.py`

**Changes**:
```python
class AlphaAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("agent_alpha", bus)
        self.browser = BrowserOrchestrator()  # NEW
        
    async def handle_target_acquired(self, event: HiveEvent):
        target_url = event.payload.get("url")
        
        # HYBRID RECONNAISSANCE
        print(f"[{self.name}] Initiating hybrid recon: HTTP + Browser")
        
        # 1. HTTP Recon (existing)
        http_endpoints = await self._http_recon(target_url)
        
        # 2. Browser Recon (NEW)
        browser_endpoints = await self._browser_recon(target_url)
        
        # 3. Merge results
        all_endpoints = self._merge_endpoints(http_endpoints, browser_endpoints)
        
        # 4. Publish discoveries
        for endpoint in all_endpoints:
            await self.bus.publish(HiveEvent(
                type=EventType.RECON_PACKET,
                source=self.name,
                payload={
                    "url": endpoint,
                    "source": "alpha_hybrid",
                    "discovery_method": endpoint.get("method", "unknown")
                }
            ))
            
    async def _browser_recon(self, url):
        """Deep browser-based reconnaissance"""
        results = {
            "endpoints": [],
            "framework": None,
            "websockets": [],
            "api_calls": []
        }
        
        # Navigate with OpenClaw for deep analysis
        await self.browser.navigate(url, engine=BrowserEngine.OPENCLAW, wait_for="networkidle")
        
        # Extract JavaScript routes
        js_routes = await self.browser.extract_js_routes()
        results["endpoints"].extend(js_routes)
        
        # Detect framework
        results["framework"] = await self.browser.detect_framework()
        
        # Intercept network requests
        network_log = await self.browser.get_network_log()
        for req in network_log:
            if "/api/" in req["url"] or "/v1/" in req["url"]:
                results["api_calls"].append(req["url"])
                
        # Find WebSockets
        results["websockets"] = await self.browser.find_websockets()
        
        return results
```

### BETA Integration

**File**: `backend/agents/beta.py`

**Changes**:
```python
class BetaAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("agent_beta", bus)
        self.browser = BrowserOrchestrator()  # NEW
        
    async def handle_candidate(self, event: HiveEvent):
        payload = event.payload
        url = payload.get("url")
        tag = payload.get("tag")
        
        if tag == "XSS_CANDIDATE":
            # Test in real browser
            await self._test_xss_browser(url, payload.get("payload"))
        elif tag == "CSRF_CANDIDATE":
            await self._test_csrf_browser(url)
        elif tag == "API":
            # Existing HTTP-based testing
            await self._execute_real_attack(url, payload.get("payload"))
            
    async def _test_xss_browser(self, url, payload_str):
        """Test XSS in real browser context"""
        print(f"[{self.name}] Testing XSS in browser: {payload_str[:50]}")
        
        # Test with OpenClaw
        result = await self.browser.test_payload(url, payload_str)
        
        if result.get("exploited"):
            # Capture forensic evidence
            screenshot = await self.browser.capture_screenshot()
            dom = await self.browser.capture_dom()
            
            await self.bus.publish(HiveEvent(
                type=EventType.VULN_CONFIRMED,
                source=self.name,
                payload={
                    "type": "XSS_BROWSER_VERIFIED",
                    "url": url,
                    "payload": payload_str,
                    "severity": "HIGH",
                    "evidence": {
                        "screenshot": screenshot,
                        "dom_snapshot": dom,
                        "alert_triggered": result.get("alert_triggered"),
                        "dom_modified": result.get("dom_modified")
                    }
                }
            ))
```

### SIGMA Integration

**File**: `backend/agents/sigma.py`

**Changes**:
```python
class SigmaAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("agent_sigma", bus)
        self.browser = BrowserOrchestrator()  # NEW
        
    async def handle_generation_request(self, event: HiveEvent):
        packet = JobPacket(**event.payload)
        target_url = packet.target.url
        
        # BROWSER-AWARE PAYLOAD GENERATION
        if packet.config.params.get("browser_aware"):
            payloads = await self._generate_browser_aware_payloads(target_url)
        else:
            # Traditional payload generation
            payloads = await self._generate_traditional_payloads(target_url)
            
        # Ship to Beta
        await self._ship_payloads(payloads, target_url)
        
    async def _generate_browser_aware_payloads(self, url):
        """Generate payloads based on actual DOM structure"""
        # Analyze DOM with PinchTab (fast)
        await self.browser.navigate(url, engine=BrowserEngine.PINCHTAB)
        dom_structure = await self.browser.analyze_dom()
        
        payloads = []
        
        # Generate form-specific payloads
        for form in dom_structure.get("forms", []):
            for field in form.get("fields", []):
                field_type = field.get("type")
                field_name = field.get("name")
                
                if field_type == "email":
                    payloads.append({
                        "target": field_name,
                        "payload": "test@evil.com<script>alert(1)</script>",
                        "type": "XSS_EMAIL_FIELD"
                    })
                elif field_type == "number":
                    payloads.append({
                        "target": field_name,
                        "payload": "-999999",
                        "type": "NEGATIVE_NUMBER"
                    })
                    
        return payloads
```

## Configuration

### Environment Variables

Add to `.env`:

```bash
# OpenClaw Configuration
OPENCLAW_ENABLED=true
OPENCLAW_DEBUG=false
OPENCLAW_HEADLESS=true
OPENCLAW_BROWSER=chromium
OPENCLAW_STEALTH_MODE=true
OPENCLAW_MAX_CONTEXTS=5
OPENCLAW_TIMEOUT=60

# PinchTab Configuration  
PINCHTAB_ENABLED=true
PINCHTAB_URL=http://localhost:3000

# Hybrid Mode
BROWSER_AUTO_SELECT=true
BROWSER_PREFER_SPEED=false  # false = prefer OpenClaw depth
```

### Settings Integration

Update `backend/core/config.py`:

```python
class Settings(BaseSettings):
    # OpenClaw
    OPENCLAW_ENABLED: bool = True
    OPENCLAW_DEBUG: bool = False
    OPENCLAW_HEADLESS: bool = True
    OPENCLAW_BROWSER: str = "chromium"
    OPENCLAW_STEALTH_MODE: bool = True
    OPENCLAW_MAX_CONTEXTS: int = 5
    
    # PinchTab
    PINCHTAB_ENABLED: bool = True
    PINCHTAB_URL: str = "http://localhost:3000"
    
    # Hybrid
    BROWSER_AUTO_SELECT: bool = True
    BROWSER_PREFER_SPEED: bool = False
```

## Dependency Management

### Installation

Add to `backend/requirements.txt`:

```txt
# Browser Automation
playwright==1.49.0
openclaw>=0.1.0

# Existing
# ... rest of requirements
```

### Installation Commands

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Install Playwright browsers
playwright install chromium

# Install OpenClaw (if not via pip)
pip install -e d:/projects/openclaw
```

## Success Criteria

The deep integration is successful when:

1. ✅ All 10 agents have browser capabilities via BrowserOrchestrator
2. ✅ Hybrid mode intelligently routes between OpenClaw and PinchTab
3. ✅ Alpha discovers 90%+ endpoints on SPAs
4. ✅ Beta verifies XSS in real browser context
5. ✅ Sigma generates DOM-aware payloads
6. ✅ Gamma verifies exploits visually
7. ✅ Delta coordinates both browser engines
8. ✅ Sessions persist across scans
9. ✅ Zero memory leaks after 100 scans
10. ✅ Forensic evidence captured for all browser operations

---

**End of Design Document**
