# Antigravity V5 - System Architecture

**System Identity**: "The Hyper-Mind"  
**Mission**: World's most advanced autonomous penetration testing system  
**Philosophy**: "Sovereign Aesthetics, Sovereign Logic"

---

## Table of Contents

1. [System Overview](#system-overview)
2. [The Trinity Architecture](#the-trinity-architecture)
3. [Zone I: The Hive (Backend)](#zone-i-the-hive-backend)
4. [Zone II: The Interface (Frontend)](#zone-ii-the-interface-frontend)
5. [Zone III: The Ghost (Extension)](#zone-iii-the-ghost-extension)
6. [Operational Workflow](#operational-workflow)
7. [Design Principles](#design-principles)
8. [Technology Stack](#technology-stack)

---

## System Overview

Antigravity V5 is a distributed, full-stack, AI-driven cybersecurity platform that operates as a "Digital Organism" - a living, breathing system that autonomously hunts for vulnerabilities across modern web applications.

### Core Capabilities

- **Autonomous Agent Swarm**: 10 specialized AI agents working in concert
- **Hybrid HTTP + Browser Testing**: Traditional HTTP + OpenClaw/PinchTab browser automation
- **Real-Time Intelligence**: WebSocket-driven live updates and visualization
- **Game-Theoretic Resource Management**: NeuroNegotiator for optimal resource allocation
- **Visual Verification**: Screenshot and DOM capture for exploit evidence
- **SPA Testing**: Full support for React/Vue/Angular applications

---

## The Trinity Architecture

The system comprises three interconnected sovereign zones:

```
┌─────────────────────────────────────────────────────────────┐
│                    ANTIGRAVITY V5                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   ZONE I     │◄──►│   ZONE II    │◄──►│  ZONE III    │ │
│  │  THE HIVE    │    │ THE INTERFACE│    │  THE GHOST   │ │
│  │  (Backend)   │    │  (Frontend)  │    │ (Extension)  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│       ▲                     ▲                    ▲          │
│       │                     │                    │          │
│   Python/FastAPI      React/Vite          Chrome MV3       │
│   AsyncIO/WS          Framer Motion       Content Scripts  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1. Zone I: The Hive (Backend)
- **Role**: Asynchronous Python-based swarm intelligence
- **Tech**: FastAPI, WebSocket, AsyncIO, Pydantic
- **Path**: `backend/`

### 2. Zone II: The Interface (Frontend)
- **Role**: React visualization layer with "Sovereign Midnight" aesthetics
- **Tech**: React 18, Vite, Framer Motion, TailwindCSS
- **Path**: `src/`

### 3. Zone III: The Ghost (Extension)
- **Role**: Chrome Extension for DOM interrogation
- **Tech**: Manifest V3, Native JS
- **Path**: `extension/`

---

## Zone I: The Hive (Backend)

### Core Architecture

```
backend/
├── core/                    # Core nervous system
│   ├── orchestrator.py      # Central coordinator
│   ├── hive.py             # EventBus pub/sub
│   ├── hyper_hive.py       # NeuroNegotiator (resource allocation)
│   ├── protocol.py         # Communication DNA (JobPacket, ResultPacket)
│   ├── state.py            # State management (stats.json)
│   ├── browser_orchestrator.py  # Browser automation coordinator
│   ├── openclaw_engine.py  # Deep browser automation
│   ├── pinchtab_engine.py  # Fast browser operations
│   └── reporting.py        # PDF generation
├── agents/                 # Agent swarm
│   ├── omega.py           # Strategist (Nash Equilibrium)
│   ├── alpha.py           # Scout (Reconnaissance)
│   ├── beta.py            # Breaker (Exploitation)
│   ├── sigma.py           # Smith (Payload generation)
│   ├── gamma.py           # Auditor (Verification)
│   ├── delta.py           # Hybrid Controller
│   ├── prism.py           # Sentinel (DOM analysis)
│   ├── chi.py             # Inspector (Event interception)
│   ├── zeta.py            # Cortex (Resource monitoring)
│   └── kappa.py           # Librarian (Knowledge retrieval)
├── api/                   # API endpoints
│   ├── endpoints/         # REST endpoints
│   └── socket_manager.py  # WebSocket management
└── modules/               # Attack modules
    ├── logic/            # Logic flaw modules
    └── tech/             # Technical modules
```

### The Hyper-Hive Core

#### 1. Orchestrator (`core/orchestrator.py`)
The central nervous system that:
- Initializes the EventBus
- Spawns all agents
- Manages scan lifecycle (Initializing → Running → Completed)
- Bridges Swarm ↔ Interface via WebSockets
- Handles global `scan_id` management

#### 2. NeuroNegotiator (`core/hyper_hive.py`)
Game-theoretic resource allocator that prevents:
- Target DDoS (network flooding)
- Self-impaired performance (CPU exhaustion)
- Resource conflicts between agents

**Resource Types:**
- `NETWORK`: HTTP requests
- `CPU`: Crypto/Diffing operations
- `DISK`: I/O operations

**Bidding Protocol:**
```python
class Bid:
    agent_id: str
    resource: ResourceType
    priority: float  # 0.0-1.0
```

Agents must bid for resources. High priority (>0.8) jobs get preferential access.

#### 3. EventBus (`core/hive.py`)
Pub/sub system for agent communication:
- `SCAN_START`: Scan initiated
- `TARGET_ACQUIRED`: New target found
- `VULN_CONFIRMED`: Vulnerability discovered
- `JOB_ASSIGNED`: Task dispatched
- `LOG`: System logging

#### 4. Browser Orchestrator (`core/browser_orchestrator.py`)
Unified API for hybrid browser automation:
- **OpenClaw**: Deep automation, stealth mode, XSS testing
- **PinchTab**: Fast operations, token extraction
- **Intelligent Routing**: Auto-selects best engine per task
- **Session Management**: Cross-engine session sharing
- **Forensic Collection**: Screenshots, DOM snapshots, network logs

### The Agent Swarm

#### Omega (The Strategist)
- **Role**: Campaign planning and strategy selection
- **Logic**: Nash Equilibrium mixed strategies
- **Strategies**: `BLITZKRIEG`, `LOW_AND_SLOW`, `DECEPTION`, `BROWSER_DEEP_RECON`
- **Context Detection**: E-Commerce, SPA, API-first applications

#### Alpha (The Scout)
- **Role**: Reconnaissance and endpoint discovery
- **Capabilities**:
  - HTTP-based reconnaissance
  - Browser-based SPA reconnaissance
  - JavaScript route extraction (React/Vue/Angular)
  - Network traffic interception
  - WebSocket discovery
  - 90%+ endpoint discovery on modern apps

#### Beta (The Breaker)
- **Role**: Exploitation and vulnerability testing
- **Capabilities**:
  - Real browser XSS testing
  - CSRF token extraction and testing
  - DOM-based XSS detection
  - Clickjacking tests
  - Visual exploit verification

#### Sigma (The Smith)
- **Role**: Generative payload factory
- **Capabilities**:
  - Context-aware payload generation
  - DOM-based payload customization
  - Framework-specific exploits (React/Vue/Angular)
  - Obfuscation (Base64, Hex, URL)
  - Pre-testing in browser

#### Gamma (The Auditor)
- **Role**: Verification and validation
- **Capabilities**:
  - Visual exploit verification
  - DOM mutation detection
  - Alert/prompt detection
  - Network traffic analysis
  - Anomaly diffing (baseline comparison)

#### Delta (Hybrid Controller)
- **Role**: Unified browser management
- **Capabilities**:
  - Coordinates OpenClaw + PinchTab
  - Token extraction pipeline
  - Session sharing between engines
  - Intelligent task routing

#### Prism (Sentinel)
- **Role**: Deep DOM analysis
- **Capabilities**:
  - Shadow DOM inspection
  - Hidden element detection
  - Iframe content analysis
  - Prompt injection detection

#### Chi (Inspector)
- **Role**: Real-time event interception
- **Capabilities**:
  - Click/form event monitoring
  - Dark pattern detection
  - Event blocking with evidence
  - Timing analysis

#### Zeta (Cortex)
- **Role**: Resource monitoring
- **Capabilities**:
  - Browser memory tracking
  - Context lifecycle management
  - Performance throttling
  - Health checks

#### Kappa (Librarian)
- **Role**: Knowledge management
- **Capabilities**:
  - Session archival
  - Session restoration
  - Session replay
  - RAG (Retrieval-Augmented Generation)

### Communication Protocol

#### JobPacket (Unit of Work)
```python
class JobPacket:
    id: UUID
    priority: TaskPriority  # CRITICAL, HIGH, NORMAL, LOW
    target: TaskTarget      # url, method, headers, payload
    config: ModuleConfig    # module_id, agent_id, aggression, ai_mode
```

#### ResultPacket (Unit of Success)
```python
class ResultPacket:
    status: Status          # SUCCESS, FAILURE, VULN_FOUND
    execution_time_ms: float
    vulnerabilities: List[Vulnerability]
```

---

## Zone II: The Interface (Frontend)

### Architecture

```
src/
├── components/
│   ├── Dashboard.jsx       # Command center
│   ├── NewScan.jsx        # Scan launcher
│   ├── Scans.jsx          # Scan history
│   ├── Library.jsx        # Vulnerability library
│   ├── Settings.jsx       # Configuration
│   ├── GlobalBackground.jsx  # Persistent particle field
│   └── SmoothScroll.jsx   # 120Hz inertial scrolling
├── hooks/
│   └── useWebSocket.js    # WebSocket connection
└── App.jsx                # Root component
```

### The "Sovereign Midnight" Design System

#### Visual Language
- **Background**: Deep void (`#06070B`)
- **Accents**: Bloom effects (`cyan-bloom`, `magenta-bloom`)
- **Glass Morphism**: `glass-panel` utility class
- **Glow Effects**: `shadow-glow`, `text-glow`

#### Typography
- **UI**: Inter
- **Headers**: Space Grotesk
- **Code/Logs**: Courier

#### Animation
- **Framer Motion**: All transitions
- **AnimatePresence**: Page transitions
- **Inertial Scrolling**: Lenis-based smooth scroll
- **120Hz Feel**: High-refresh-rate optimized

### Real-Time Synchronization

#### WebSocket Connection
```javascript
ws://localhost:8000/stream?client_type=ui
```

#### Event Types
- `SCAN_UPDATE`: Scan status changes
- `VULN_UPDATE`: Vulnerability counters (authoritative sync)
- `GI5_LOG`: Terminal logs from Hive
- `ATTACK_HIT`: Visual-only graph jitter
- `SPY_STATUS`: Extension connection status

### Dashboard Components

#### Live Scan Visualizer
- SVG-based graph with Bézier curves
- Real-time vulnerability spikes
- Framer Motion path animations
- Noise/jitter for "aliveness" effect

#### Metrics Display
- Total scans
- Active scans
- Vulnerabilities found
- Critical findings

---

## Zone III: The Ghost (Extension)

### Architecture

```
extension/
├── manifest.json          # Manifest V3 config
├── background.js          # Service worker
├── content/
│   ├── xray.js           # DOM scanner
│   └── vision.js         # Visual overlay
└── popup/
    └── popup.html        # Extension UI
```

### The Synapse (Background Worker)

#### Traffic Interception
```javascript
chrome.webRequest.onBeforeSendHeaders
```

**Capabilities:**
- Captures Authorization headers
- Extracts API keys (Bearer, x-api-key)
- Mirrors XHR/Fetch metadata to Hive
- Relays scan results from content script

**Filters:**
- Ignores static assets (`.jpg`, `.css`)
- Ignores backend traffic (`localhost:8000`)

### The X-Ray (Content Script)

#### DOM Interrogation
- **TreeWalker**: Traverses all text nodes
- **Regex Engine**: Pattern matching for secrets
  - AWS Keys: `/AKIA[0-9A-Z]{16}/`
  - JWT Tokens: `/eyJ.../`
  - Slack Tokens, Private Keys, etc.

#### Visual Injection
- Creates `div.antigravity-xray-overlay`
- Absolute-positioned over vulnerable elements
- Real-time highlighting in browser

#### MutationObserver
- Watches for SPA changes
- Re-scans every 2000ms (debounced)
- Handles dynamic content

---

## Operational Workflow

### The Life of a Scan

```
1. TRIGGER
   User clicks "Launch" → POST /api/attack/fire

2. BOOTSTRAP
   Orchestrator initializes scan_id
   Updates stats.json (Status: "Initializing")

3. REVEAL
   Frontend receives WS SCAN_UPDATE
   UI shows "Running" badge

4. STRATEGY
   OmegaAgent analyzes target
   Selects strategy (e.g., E_COMMERCE_BLITZ)
   Dispatches JobPackets to agents

5. NEGOTIATION
   Agents bid for resources
   NeuroNegotiator grants/denies access

6. EXECUTION
   Agents execute modules
   SigmaAgent forges payloads
   BetaAgent tests in browser
   GammaAgent verifies findings

7. DISCOVERY
   Vulnerability found
   EventBus: VULN_CONFIRMED

8. REACTION
   stats.json updated
   WebSocket broadcast: VULN_UPDATE
   Frontend graph spikes
   Recent activity logs update

9. REPORTING
   Scan completes
   PDF report generated
   "Executive Clarity" format
```

---

## Design Principles

### 1. Sovereign Aesthetics
- Every UI element must "float" and "glow"
- No flat design allowed
- Glass morphism and bloom effects required
- 120Hz-optimized animations

### 2. Sovereign Logic
- No placeholders - all code must work
- Type safety required (Python type hints)
- Error handling in all async loops
- Graceful WebSocket disconnect handling

### 3. Autonomous Operation
- Agents negotiate resources independently
- Self-healing on failures
- Real-time adaptation to target behavior
- No manual intervention required

### 4. Game-Theoretic Optimization
- Nash Equilibrium strategy selection
- Priority-based resource allocation
- Competitive bidding for resources
- Optimal performance under constraints

---

## Technology Stack

### Backend
- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Async**: AsyncIO
- **WebSocket**: Starlette
- **Validation**: Pydantic V2
- **Browser Automation**: OpenClaw (Playwright), PinchTab

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **Animation**: Framer Motion
- **Graphics**: Canvas API, SVG

### Extension
- **Manifest**: V3
- **Language**: Native JavaScript
- **APIs**: chrome.webRequest, chrome.runtime

### Infrastructure
- **Database**: JSON-based (stats.json)
- **Reports**: PDF generation (ReportLab)
- **Communication**: WebSocket (bidirectional)

---

## Coding Standards

### Python
- **Type Hints**: Required for all functions
- **Async/Await**: All I/O operations
- **Error Handling**: try/except in all loops
- **Naming**: snake_case for functions/variables

### React
- **Components**: Functional only (no classes)
- **Hooks**: Custom hooks for reusable logic
- **Styling**: Utility classes (glass-panel, shadow-glow)
- **Animation**: Framer Motion for all transitions

### General
- **No Placeholders**: All code must be functional
- **Documentation**: Inline comments for complex logic
- **Testing**: Unit tests for core components
- **Agnosticism**: Backend runs independently of frontend

---

## Maintainer Instructions

### Adding New Agents
1. Inherit from `BaseAgent`
2. Subscribe to `EventBus`
3. Implement `NeuroNegotiator` bidding
4. Define agent-specific logic
5. Add to `Orchestrator` spawn list

### Adding New Modules
1. Create in `backend/modules/logic/` or `backend/modules/tech/`
2. Implement module interface
3. Register with appropriate agent
4. Add to module registry

### Styling Guidelines
- **Never** use default HTML elements
- **Always** use `glass-panel` and `text-glow` classes
- **All motion** must be smooth (Framer Motion)
- **Maintain** "Sovereign Midnight" aesthetic

### Safety
- **Never** bypass NeuroNegotiator
- **Always** handle WebSocket disconnects
- **Validate** all user inputs
- **Rate limit** external requests

---

**Last Updated:** May 24, 2026  
**Version:** 5.0  
**Status:** Production Ready
