# Architecture Deep Dive - Antigravity V5

Comprehensive technical architecture documentation for Antigravity V5.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Agent Architecture](#agent-architecture)
4. [Browser Infrastructure](#browser-infrastructure)
5. [Security Layer](#security-layer)
6. [Data Flow](#data-flow)
7. [Scalability & Performance](#scalability--performance)
8. [Design Patterns](#design-patterns)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                     WebSocket + REST API                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │  Recon   │  │  Attack  │  │ Reports  │   │
│  │Endpoints │  │Endpoints │  │Endpoints │  │Endpoints │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                    Core Orchestration                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Orchestrator │  │     Hive     │  │ Task Manager │     │
│  │   (Main)     │  │  (Cluster)   │  │   (Async)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                      Agent Layer                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │Alpha │ │ Beta │ │Gamma │ │Delta │ │Sigma │ │ Zeta │   │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                      │
│  │Prism │ │ Chi  │ │Kappa │ │Omega │                      │
│  └──────┘ └──────┘ └──────┘ └──────┘                      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Browser Infrastructure                      │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Browser          │  │ OpenClaw Engine  │               │
│  │ Orchestrator     │  │ (Playwright)     │               │
│  │                  │  └──────────────────┘               │
│  │ - Context Pool   │  ┌──────────────────┐               │
│  │ - Memory Monitor │  │ PinchTab Engine  │               │
│  │ - Lazy Init      │  │ (Selenium)       │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                    Storage & State                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PostgreSQL  │  │    Redis     │  │  File System │     │
│  │  (State DB)  │  │   (Cache)    │  │  (Forensics) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend**:
- Python 3.10+
- FastAPI (async web framework)
- SQLAlchemy (ORM)
- Playwright (browser automation)
- Selenium (legacy browser support)

**Frontend**:
- React 18
- Vite (build tool)
- TailwindCSS (styling)
- WebSocket (real-time updates)

**Infrastructure**:
- PostgreSQL 14+ (primary database)
- Redis 6+ (caching & queues)
- Nginx (reverse proxy)
- Docker (containerization)

---

## Core Components

### 1. Orchestrator

**Location**: `backend/core/orchestrator.py`

**Responsibilities**:
- Coordinate agent execution
- Manage scan lifecycle
- Handle state transitions
- Distribute work across agents

**Key Methods**:
```python
class Orchestrator:
    async def start_scan(self, scan_id: str, config: dict) -> None:
        """Initialize and start a security scan."""
        
    async def execute_agent(self, agent_name: str, context: dict) -> dict:
        """Execute a specific agent with context."""
        
    async def stop_scan(self, scan_id: str) -> None:
        """Stop a running scan gracefully."""
```

**Design Pattern**: Command Pattern
- Encapsulates agent execution as commands
- Supports undo/redo operations
- Enables queuing and scheduling

### 2. Hive (Cluster Manager)

**Location**: `backend/core/hive.py`

**Responsibilities**:
- Manage distributed workers
- Load balancing
- Fault tolerance
- Worker health monitoring

**Architecture**:
```
┌──────────────┐
│ Hive Master  │
└──────┬───────┘
       │
   ┌───┴───┬───────┬───────┐
   │       │       │       │
┌──▼───┐ ┌─▼────┐ ┌─▼────┐ ┌─▼────┐
│Worker│ │Worker│ │Worker│ │Worker│
│  1   │ │  2   │ │  3   │ │  4   │
└──────┘ └──────┘ └──────┘ └──────┘
```

**Key Features**:
- Automatic worker registration
- Heartbeat monitoring
- Work redistribution on failure
- Dynamic scaling

### 3. State Manager

**Location**: `backend/core/state.py`

**Responsibilities**:
- Centralized state management
- Scan progress tracking
- Finding storage
- State persistence

**State Schema**:
```python
{
    "scan_id": "uuid",
    "status": "running|completed|failed",
    "progress": {
        "current_phase": "recon|attack|report",
        "percentage": 0-100,
        "agents_completed": []
    },
    "findings": [
        {
            "id": "uuid",
            "severity": "critical|high|medium|low",
            "type": "xss|sqli|csrf|...",
            "evidence": {...}
        }
    ],
    "metadata": {
        "start_time": "timestamp",
        "end_time": "timestamp",
        "target_url": "url"
    }
}
```

### 4. Task Manager

**Location**: `backend/core/task_manager.py`

**Responsibilities**:
- Async task lifecycle management
- Prevent fire-and-forget tasks
- Proper error handling
- Resource cleanup

**Usage Pattern**:
```python
async with TaskManager() as tm:
    # Create tracked task
    task = await tm.create_task(
        some_async_function(),
        name="task_name"
    )
    
    # Task is automatically tracked and cleaned up
    result = await task
```

**Benefits**:
- No silent task failures
- Automatic cleanup on errors
- Task monitoring and debugging
- Memory leak prevention

---

## Agent Architecture

### Agent Hierarchy

```
BaseAgent (Abstract)
    │
    ├── BrowserEnabledAgent (Mixin)
    │   │
    │   ├── Alpha (Recon)
    │   ├── Beta (CSRF Testing)
    │   ├── Gamma (Network Analysis)
    │   ├── Delta (Hybrid Control)
    │   ├── Sigma (DOM Analysis)
    │   ├── Zeta (Context Management)
    │   ├── Prism (HTTP Probing)
    │   └── Chi (Event Prevention)
    │
    ├── Kappa (Archival)
    └── Omega (Strategy)
```

### Agent Lifecycle

```
┌──────────┐
│Initialize│
└────┬─────┘
     │
┌────▼─────┐
│Configure │
└────┬─────┘
     │
┌────▼─────┐
│ Execute  │◄──┐
└────┬─────┘   │
     │         │
┌────▼─────┐   │
│  Report  │   │
└────┬─────┘   │
     │         │
┌────▼─────┐   │
│ Cleanup  │   │
└────┬─────┘   │
     │         │
     ├─────────┘ (retry)
     │
┌────▼─────┐
│ Complete │
└──────────┘
```

### Agent Communication

**Event Bus Pattern**:
```python
# Agent publishes finding
await event_bus.publish("finding.discovered", {
    "agent": "alpha",
    "finding": {...}
})

# Other agents subscribe
@event_bus.subscribe("finding.discovered")
async def on_finding(event):
    # React to finding
    pass
```

### Individual Agent Details

#### Alpha Agent (Recon)
**Purpose**: Initial reconnaissance and endpoint discovery

**Capabilities**:
- SPA detection
- Endpoint enumeration
- API classification
- Technology fingerprinting

**Output**: List of endpoints and technologies

#### Beta Agent (CSRF Testing)
**Purpose**: Test CSRF protection mechanisms

**Capabilities**:
- Token validation testing
- Method override testing
- Referer bypass testing
- Origin bypass testing

**Output**: CSRF vulnerabilities

#### Gamma Agent (Network Analysis)
**Purpose**: Monitor and analyze network traffic

**Capabilities**:
- Request/response interception
- SSRF detection
- Data exfiltration detection
- Suspicious pattern identification

**Output**: Network-based findings

#### Delta Agent (Hybrid Control)
**Purpose**: Coordinate multiple browser engines

**Capabilities**:
- Engine selection
- Token extraction
- Session management
- Engine failover

**Output**: Coordinated browser actions

#### Sigma Agent (DOM Analysis)
**Purpose**: Analyze DOM structure and behavior

**Capabilities**:
- Framework detection
- DOM mutation monitoring
- XSS sink identification
- Client-side routing analysis

**Output**: DOM-based vulnerabilities

#### Zeta Agent (Context Management)
**Purpose**: Manage browser context lifecycle

**Capabilities**:
- Context creation/cleanup
- Idle context detection
- Resource monitoring
- Context pooling

**Output**: Optimized resource usage

#### Prism Agent (HTTP Probing)
**Purpose**: HTTP-level security testing

**Capabilities**:
- Security header analysis
- Iframe analysis
- Clickjacking detection
- HTTP method testing

**Output**: HTTP-level vulnerabilities

#### Chi Agent (Event Prevention)
**Purpose**: Detect and prevent malicious events

**Capabilities**:
- Event blocking
- Deceptive UI detection
- Clickjacking prevention
- Forensic capture

**Output**: Prevented attacks

#### Kappa Agent (Archival)
**Purpose**: Learn from and archive vulnerabilities

**Capabilities**:
- Pattern learning
- Vulnerability archival
- Session persistence
- Knowledge graph building

**Output**: Learned patterns

#### Omega Agent (Strategy)
**Purpose**: Select optimal attack strategies

**Capabilities**:
- Strategy selection
- Campaign planning
- SPA-aware routing
- Attack prioritization

**Output**: Attack strategy

---

## Browser Infrastructure

### Browser Orchestrator

**Location**: `backend/core/browser_orchestrator.py`

**Architecture**:
```
┌─────────────────────────────────────┐
│      Browser Orchestrator           │
│                                     │
│  ┌───────────────────────────────┐ │
│  │      Context Pool             │ │
│  │  ┌─────┐ ┌─────┐ ┌─────┐     │ │
│  │  │Ctx 1│ │Ctx 2│ │Ctx 3│ ... │ │
│  │  └─────┘ └─────┘ └─────┘     │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │    Memory Monitor             │ │
│  │  - Current: 450MB             │ │
│  │  - Threshold: 500MB           │ │
│  │  - Status: OK                 │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │    Engine Manager             │ │
│  │  ┌──────────┐ ┌──────────┐   │ │
│  │  │OpenClaw  │ │PinchTab  │   │ │
│  │  │(Primary) │ │(Fallback)│   │ │
│  │  └──────────┘ └──────────┘   │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Key Features**:

1. **Context Pooling**
   - Reuse browser contexts
   - 80% reduction in startup time
   - Automatic cleaning between uses

2. **Memory Monitoring**
   - Track memory usage
   - Automatic cleanup at threshold
   - Prevent memory leaks

3. **Lazy Initialization**
   - Initialize engines on demand
   - 50% faster startup
   - Reduced resource usage

4. **Isolation**
   - Separate contexts per scan
   - No cross-contamination
   - Automatic cleanup

### OpenClaw Engine

**Location**: `backend/core/openclaw_engine.py`

**Technology**: Playwright (Chromium)

**Advantages**:
- Modern browser automation
- Better performance
- Native async support
- Rich API

**Use Cases**:
- SPA scanning
- Modern web applications
- JavaScript-heavy sites

### PinchTab Engine

**Location**: `backend/core/pinchtab_engine.py`

**Technology**: Selenium (Multi-browser)

**Advantages**:
- Legacy browser support
- Mature ecosystem
- Wide compatibility

**Use Cases**:
- Legacy applications
- Fallback option
- Multi-browser testing

---

## Security Layer

### Defense in Depth

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│  - Input Validation                     │
│  - Output Encoding                      │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Security Components             │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐│
│  │   CSRF   │ │   Rate   │ │   URL   ││
│  │Protection│ │ Limiter  │ │Validator││
│  └──────────┘ └──────────┘ └─────────┘│
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Data Protection                 │
│  - Forensic Encryption                  │
│  - Session Sanitization                 │
│  - Secure Storage                       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Infrastructure                  │
│  - Context Isolation                    │
│  - Resource Limits                      │
│  - Network Segmentation                 │
└─────────────────────────────────────────┘
```

### Security Components

#### 1. CSRF Protection

**Location**: `backend/core/csrf_protection.py`

**Implementation**:
- Synchronizer token pattern
- Double-submit cookie
- SameSite cookie attribute
- Token expiration

**Token Generation**:
```python
token = secrets.token_urlsafe(32)
signature = hmac.new(
    secret_key.encode(),
    f"{session_id}:{token}".encode(),
    hashlib.sha256
).hexdigest()
```

#### 2. Rate Limiter

**Location**: `backend/core/rate_limiter.py`

**Algorithm**: Token Bucket

**Implementation**:
```python
class RateLimiter:
    def __init__(self, rate: int, window: int):
        self.rate = rate  # tokens per window
        self.window = window  # seconds
        self.buckets = {}  # client_ip -> bucket
    
    async def check_rate_limit(self, client_ip: str) -> bool:
        bucket = self.buckets.get(client_ip)
        if not bucket:
            bucket = TokenBucket(self.rate, self.window)
            self.buckets[client_ip] = bucket
        
        return bucket.consume()
```

#### 3. URL Validator

**Location**: `backend/core/url_validator.py`

**Protection Against**:
- SSRF attacks
- Cloud metadata access
- Internal network scanning
- Protocol smuggling

**Validation Rules**:
```python
BLOCKED_HOSTS = [
    '169.254.169.254',  # AWS metadata
    'metadata.google.internal',  # GCP metadata
    '127.0.0.1', 'localhost',  # Loopback
]

BLOCKED_PROTOCOLS = [
    'file://', 'gopher://', 'dict://',
    'ftp://', 'tftp://'
]
```

#### 4. Forensic Encryption

**Location**: `backend/core/forensic_collector.py`

**Encryption**: Fernet (AES-128-CBC + HMAC)

**Key Derivation**: PBKDF2-HMAC-SHA256

**Implementation**:
```python
def encrypt_data(self, data: bytes) -> bytes:
    """Encrypt forensic data."""
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    key = base64.urlsafe_b64encode(kdf.derive(self.key))
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data)
    return salt + encrypted
```

#### 5. Session Sanitization

**Location**: `backend/core/hybrid_session_manager.py`

**Sanitized Data**:
- Cookies (auth tokens, session IDs)
- localStorage (JWT, API keys)
- sessionStorage (temporary tokens)
- Headers (Authorization, API-Key)

**Pattern Matching**:
```python
SENSITIVE_PATTERNS = [
    r'token["\']?\s*[:=]\s*["\']([^"\']+)',
    r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']+)',
    r'password["\']?\s*[:=]\s*["\']([^"\']+)',
    r'secret["\']?\s*[:=]\s*["\']([^"\']+)',
]
```

---

## Data Flow

### Scan Execution Flow

```
1. User initiates scan
   │
   ▼
2. API receives request
   │
   ▼
3. Orchestrator creates scan
   │
   ▼
4. State Manager initializes state
   │
   ▼
5. Orchestrator executes agents
   │
   ├─► Alpha (Recon)
   │   │
   │   ▼
   │   Discovers endpoints
   │   │
   │   ▼
   ├─► Beta (CSRF Testing)
   │   │
   │   ▼
   │   Tests CSRF protection
   │   │
   │   ▼
   ├─► Gamma (Network Analysis)
   │   │
   │   ▼
   │   Monitors traffic
   │   │
   │   ▼
   └─► ... (other agents)
       │
       ▼
6. Findings collected
   │
   ▼
7. Report generated
   │
   ▼
8. User receives results
```

### Finding Processing Flow

```
Agent discovers finding
   │
   ▼
Validate finding
   │
   ▼
Deduplicate
   │
   ▼
Calculate severity (CVSS)
   │
   ▼
Store in database
   │
   ▼
Update state
   │
   ▼
Notify frontend (WebSocket)
   │
   ▼
Display to user
```

---

## Scalability & Performance

### Horizontal Scaling

**Load Balancer Configuration**:
```
┌──────────────┐
│Load Balancer │
└──────┬───────┘
       │
   ┌───┴───┬───────┬───────┐
   │       │       │       │
┌──▼───┐ ┌─▼────┐ ┌─▼────┐ ┌─▼────┐
│App 1 │ │App 2 │ │App 3 │ │App 4 │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
   │        │        │        │
   └────────┴────────┴────────┘
            │
    ┌───────┴────────┐
    │                │
┌───▼────┐    ┌──────▼──────┐
│Database│    │Redis Cluster│
└────────┘    └─────────────┘
```

### Performance Optimizations

1. **Context Pooling**
   - Reuse browser contexts
   - 80% faster context creation
   - Reduced memory usage

2. **Lazy Initialization**
   - Initialize on demand
   - 50% faster startup
   - Lower resource footprint

3. **Async Operations**
   - Non-blocking I/O
   - Parallel agent execution
   - Better throughput

4. **Caching**
   - Redis caching
   - Result memoization
   - DNS caching

5. **Database Optimization**
   - Connection pooling
   - Batch operations
   - Indexed queries

### Resource Limits

**Per-Scan Limits**:
- Max browser contexts: 5
- Max memory: 500MB
- Max execution time: 1 hour
- Max findings: 10,000

**System Limits**:
- Max concurrent scans: 10
- Max API requests/min: 100
- Max WebSocket connections: 1,000

---

## Design Patterns

### 1. Command Pattern
**Used in**: Orchestrator
**Purpose**: Encapsulate agent execution

### 2. Observer Pattern
**Used in**: Event Bus
**Purpose**: Agent communication

### 3. Factory Pattern
**Used in**: Agent Factory
**Purpose**: Agent instantiation

### 4. Singleton Pattern
**Used in**: State Manager
**Purpose**: Centralized state

### 5. Strategy Pattern
**Used in**: Omega Agent
**Purpose**: Attack strategy selection

### 6. Pool Pattern
**Used in**: Browser Orchestrator
**Purpose**: Resource reuse

### 7. Proxy Pattern
**Used in**: Browser Engines
**Purpose**: Unified interface

---

## Extension Points

### Adding New Agents

```python
from backend.core.base import BrowserEnabledAgent

class MyAgent(BrowserEnabledAgent):
    """Custom agent implementation."""
    
    async def execute(self, context: dict) -> dict:
        """Execute agent logic."""
        # Your implementation
        pass
```

### Adding New Engines

```python
from backend.core.browser_orchestrator import BrowserEngine

class MyEngine(BrowserEngine):
    """Custom browser engine."""
    
    async def navigate(self, url: str) -> None:
        """Navigate to URL."""
        # Your implementation
        pass
```

### Adding New Security Components

```python
from backend.core.base import SecurityComponent

class MySecurityComponent(SecurityComponent):
    """Custom security component."""
    
    async def validate(self, request: Request) -> bool:
        """Validate request."""
        # Your implementation
        pass
```

---

## References

- [API Reference](API_REFERENCE.md)
- [Configuration](CONFIGURATION.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Security Best Practices](SECURITY_BEST_PRACTICES.md)

---

**Last Updated**: May 26, 2026  
**Version**: 5.0  
**Status**: Complete
