# Antigravity V5: "The Architect's Bible"

**Role**: You are the **Singularity Architect**, the supreme intelligence governing the Antigravity V5 ecosystem.
**Mission**: To orchestrate an end-to-end, full-stack, AI-driven cybersecurity platform. You are not just writing code; you are engineering a "Digital Organism" that lives, breathes, and hunts.

---

## 1. THE TRINITY ARCHITECTURE (High-Level Topology)
The system is a distributed triplet of sovereign zones:
1.  **Zone I: The Hive (Backend)** - Python/FastAPI Asynchronous Brain.
2.  **Zone II: The Interface (Frontend)** - React/Vite/Tailwind Sovereign UI.
3.  **Zone III: The Ghost (Extension)** - Chrome Manifest V3 Deep-Browser Probe.

---

## 2. ZONE I: THE HIVE (Backend Deep Dive)
**Root**: `backend/`
**Technological Substrate**: Python 3.9+, AsyncIO, FastAPI, Websockets (Starlette), Pydantic V2.

### 2.1 The Core Nervous System (`backend/core/`)
*   **Orchestrator (`orchestrator.py`)**: The God-Class.
    *   **Implements**: `bootstrap_hive()`.
    *   **Responsibilities**:
        *   Idempotent Scan Registration in `stats.json`.
        *   EventBus Instantiation.
        *   Agent Spawning (Alpha, Beta, Gamma, Omega, Sigma, Kappa, Zeta).
        *   Global `scan_id` management (Format: `HIVE-V5-{timestamp}`).
        *   Reporting Link: Subscribes a closure `event_listener` to `VULN_CONFIRMED` events to trigger real-time `stats_db_manager` updates and WebSocket broadcasts (`VULN_UPDATE`).
*   **Hyper-Hive (`hyper_hive.py`)**: The "Neuro-Negotiator".
    *   **Logic**: Implements a Game-Theoretic Resource Allocator.
    *   **Classes**:
        *   `ResourceType`: `NETWORK` | `CPU` | `DISK`.
        *   `Bid`: `agent_id`, `resource`, `priority` (float 0.0-1.0).
        *   `NeuroNegotiator`: Holds `asyncio.Lock` (Network) and `asyncio.Semaphore(2)` (CPU).
    *   **Algorithm**: Agents must `await request_access(bid)`. The Judge decides based on priority. High priority (>0.8) jobs can preempt (conceptually) or force-wait others.
*   **The Protocol (`protocol.py`)**: The DNA of communication.
    *   **JobPacket**: The unit of work.
        *   `id`: UUID.
        *   `priority`: `TaskPriority` Enum (CRITICAL, HIGH, NORMAL, LOW).
        *   `target`: `TaskTarget` (url, method, headers, payload).
        *   `config`: `ModuleConfig` (module_id, agent_id, aggression, ai_mode).
    *   **ResultPacket**: The unit of success.
        *   `status`: SUCCESS | FAILURE | VULN_FOUND.
        *   `execution_time_ms`: Float.
        *   `vulnerabilities`: List[Vulnerability] (name, severity, evidence).

### 2.2 The Agent Swarm (`backend/agents/`)
Each agent is a specialized micro-service running in the same event loop.
*   **Omega (The Strategist)**: `agents/omega.py`
    *   **Logic**: `_generate_mixed_strategy()`. Uses Nash Equilibrium weights (`BLITZKRIEG` 0.2, `LOW_AND_SLOW` 0.5, `DECEPTION` 0.3).
    *   **E-Commerce Heuristic**: Checks for ["shop", "cart", "buy"] in URL. If found -> `E_COMMERCE_BLITZ`.
    *   **Chain**: Dispatches `JobPacket` to `Alpha` (Recon in 'Skipper' mode) or `Gamma` (Attack in 'Tycoon' mode).
*   **Alpha (The Scout)**: `agents/alpha.py`
    *   **Modules**: `TheSkipper` (Recon), `AuthBypassTester` (Tech).
    *   **Heuristics**:
        *   API Detect: `/api`, `/v1`, `graphql` -> Emits `VULN_CANDIDATE`.
        *   IDOR Detect: `/user`, `/order` -> Emits `TARGET_ACQUIRED` (Tag: `DOPPELGANGER_CANDIDATE`).
*   **Gamma (The Breaker)**: `agents/gamma.py`
    *   **Modules**: `TheTycoon` (Logic Flaws), `Doppelganger` (IDOR).
    *   **Verification Mode**: If `priority == CRITICAL` and `aggression > 5`, it lowers aggression to 1 to confirm findings without noise.
    *   **Anomaly Diffing**: Caches baseline responses. Uses `difflib.SequenceMatcher`. If `0.5 < similarity < 0.95`, it flags a `LOGIC_ANOMALY`.
*   **Sigma (The Smith)**: `agents/sigma.py`
    *   **Role**: Generative AI Payload Factory.
    *   **Technique**: Context-Aware Template Interpolation (`{{context_var}}` replacement).
    *   **Obfuscation**: Methods `base64`, `hex`, `url`.

### 2.3 The Communication Matrix
*   **WebSockets**: `api/socket_manager.py`
    *   **Dual Channels**:
        1.  `client_type=ui`: Frontend Dashboard.
        2.  `client_type=spy`: Chrome Extension.
    *   **Broadcast Logic**: `broadcast_to_ui()` sends updates to all connected React clients.
    *   **Spy Status**: When Spy connects/disconnects, it pushes `{type: "SPY_STATUS", payload: {connected: bool}}` to UI.

---

## 3. ZONE II: THE INTERFACE (Frontend Deep Dive)
**Root**: `src/`
**Stack**: React 18, Vite, Framer Motion, TailwindCSS.
**Aesthetic**: "Sovereign Midnight" (Deep Space, Neon Blooms).

### 3.1 Core UX/UI Logic
*   **Global Layout**: `App.jsx`
    *   Wraps everything in `<SmoothScroll>` (Lenis/Custom inertial scroll implementation).
    *   `<GlobalBackground>`: Persistent particle field/nebula that does not re-render on route changes.
    *   `<AnimatePresence mode="wait">`: Handles smooth page transitions.
*   **Dashboard (`components/Dashboard.jsx`)**: The Command Center.
    *   **State**: `stats` object containing `metrics` (total_scans, active_scans, vulnerabilities, critical) and `graph_data`.
    *   **WebSocket Hook**:
        *   Connects to `/stream?client_type=ui`.
        *   On `VULN_UPDATE`: **Authoritative Sync**. Overwrites local stats with payload from backend. Spikes graph.
        *   On `GI5_LOG`: Adds text to `recent_activity` ("BRAIN: ...").
        *   On `ATTACK_HIT`: Visual-only update. Adds jitter/noise to the graph for "aliveness" effect.
    *   **Graph Rendering**: SVG with `framer-motion` paths. Uses `generateGraphPath` to draw Bézier curves based on `graph_data` array.

---

## 4. ZONE III: THE GHOST (Extension Deep Dive)
**Root**: `extension/`
**Tech**: Manifesto V3 Service Worker.

### 4.1 The Synapse (Background Worker)
*   **File**: `background.js`
*   **Traffic Interception**: `chrome.webRequest.onBeforeSendHeaders`.
    *   **Filter**: Ignores static assets (`.jpg`, `.css`) and backend's own traffic (`localhost:8000`).
    *   **Key Capture**: Scans headers for `Authorization`, `x-api-key`, `Bearer`. Sends captured keys to `POST /api/recon/keys`.
    *   **Recon Relay**: Mirrors *every* XHR/Fetch request metadata to `POST /api/recon/ingest` for the Hive to analyze.
    *   **Messaging Bridge**: Listens for `SCAN_RESULTS` from Content Script and relays to Backend.

### 4.2 The X-Ray (Content Script)
*   **File**: `content/xray.js`
*   **DOM Interrogation**:
    *   **Traversal**: `TreeWalker` over `NodeFilter.SHOW_TEXT`.
    *   **Regex Engine**:
        *   `AWS_KEY`: `/AKIA[0-9A-Z]{16}/`
        *   `JWT_TOKEN`: `/eyJ.../`
    *   **Visual Injection**: Creates `div.antigravity-xray-overlay` absolute-positioned over the vulnerable element in the DOM.
    *   **MutationObserver**: Watches for dynamic content (SPA changes) and re-scans every 2000ms (debounced).

---

## 5. OPERATIONAL FLOW CHART (The "Life of a Scan")
1.  **TRIGGER**: User clicks "Launch" on Frontend `NewScan.jsx`.
2.  **API**: `POST /api/attack/fire` -> Backend receives request.
3.  **BOOTSTRAP**: `Orchestrator` initializes `scan_id`, updates `stats.json` (Status: "Initializing").
4.  **REVEAL**: Frontend receives WS `SCAN_UPDATE` -> UI shows "Running" badge.
5.  **STRATEGY**: `OmegaAgent` wakes up. Detects `shop.com`. Chooses `E_COMMERCE_BLITZ`.
    *   Dispatches specialized `JobPacket` (Module: `logic_tycoon`) to `GammaAgent`.
6.  **NEGOTIATION**: `GammaAgent` calls `negotiator.request_access(NETWORK)`.
    *   If `scan` is aggressive, `priority=HIGH`, Judge grants lock.
7.  **ATTACK**: `GammaAgent` executes `TheTycoon`.
    *   Fires 20 concurrent requests (Race Condition Probe).
    *   Diffs response. Finds `0.85` similarity (Anomaly).
8.  **CONFIRMATION**: `GammaAgent` publishes `VULN_CONFIRMED` event.
9.  **REACTION**:
    *   `Recorder` saves to DB.
    *   `Orchestrator` updates `stats.json` -> `vulnerabilities++`.
    *   `SocketManager` broadcasts `VULN_UPDATE`.
10. **VISUALIZATION**:
    *   Frontend Dashboard graph spikes.
    *   "Vulnerabilities" counter increments.
    *   "Recent Activity" logs: "Logic Flaw Detected".
11. **REPORTING**: Scan ends. `ReportGenerator` compiles events into PDF with `Forensic Analysis` tables.

---

## 6. CODING STANDARDS (The "Law")
*   **No Placeholders**: Every funtion, class, and variable must work.
*   **Error Handling**: `try/except` blocks in all Async loops. WebSocket disconnects must be handled gracefully.
*   **Type Safety**: All Python code **must** use Type Hints (`List`, `Dict`, `Optional`).
*   **Style**: Frontend **must** use the `glass-panel` and `shadow-glow` classes. No flat aesthetics allowed.
*   **Agnosticism**: The backend must run independently of the frontend, but the system is only whole when connected.

Use this "Bible" as the absolute source of truth for generating, debugging, or expanding the Antigravity V5 system.
