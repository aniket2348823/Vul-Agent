# Startup Rebuild And Alpha Implementation Plan

Date: 2026-05-17

This document is the current whole-project review plus the implementation plan for turning the codebase into a scalable startup MVP with Alpha as a production-grade reconnaissance engine.

Important legal/engineering boundary: do not paste large third-party source code from cloned GitHub repositories into this repo. Integrate their capabilities through CLI adapters, parser modules, stable schemas, optional service APIs, upstream licenses, and artifact ingestion. This keeps the product maintainable and avoids turning the app into an unpatchable vendor fork.

## 1. Current Product Summary

The project is an AI-assisted security orchestration platform with:

- React/Vite dashboard for scans, live monitoring, settings, reports, and library views.
- FastAPI backend with REST endpoints and WebSocket streaming.
- Hive/EventBus multi-agent runtime.
- Supabase persistence and Redis hot cache/distributed coordination.
- Agents for recon, mutation/execution, scoring, payload generation, memory, dark-pattern/token extraction, reporting, and planning.
- Early Alpha V6 recon scaffold with artifact storage, endpoint scoring, RAG hooks, knowledge graph updates, and PinchTab browser capture.
- Local external repos under `D:\projects` for the requested recon/tooling ecosystem.

The platform is not yet a clean startup MVP. It has strong pieces, but they are mixed with legacy behavior, broad exception handling, direct file writes, duplicated agent patterns, and uneven schema boundaries.

## 2. Architecture Summary

Current runtime flow:

```text
React UI
  -> FastAPI REST endpoints
  -> WebSocket stream
  -> StateManager / SocketManager
  -> HiveOrchestrator / EventBus
  -> Agents: Alpha, Sigma, Beta, Omega, Kappa, Chi, Delta, Gamma, Zeta, Prism
  -> ToolRegistry / ToolExecutor / HTTPClient / Sandbox / PinchTab
  -> Supabase, Redis, local artifacts, in-memory KnowledgeGraph
```

Current Alpha flow:

```text
TARGET_ACQUIRED
  -> AlphaAgent
  -> AlphaV6ReconOrchestrator when enabled
  -> Scope compilation
  -> Tool inventory
  -> Optional external command adapter layer
  -> Internal HTTP probing
  -> Optional PinchTab browser capture
  -> Endpoint scoring
  -> RECON_PACKET / RECON_COMPLETE
  -> Supabase recon tables, local artifacts, memory/RAG, knowledge graph
```

## 3. File Structure

Current high-value folders:

```text
backend/
  agents/                  Swarm agents and Alpha V6 recon package
  ai/                      Cortex, OpenRouter, NVIDIA clients
  api/                     FastAPI routers and WebSocket manager
  core/                    EventBus, DB, config, tools, guardrails, graph, state
  integrations/            PinchTab client
  modules/                 Attack/recon modules
  parsers/                 Recon parser namespace
  reporting/               CVSS, SARIF, HackerOne/report outputs
  schemas/                 Pydantic payload/finding schemas
  tools/recon/             Recon tool registry, command planner, runner
src/
  components/              React pages/components
  hooks/                   WebSocket and UI hooks
  lib/                     API client, constants, report download helpers
extension/                 Browser extension scanner/interceptor
tests/                     Phase-based smoke/integration tests
data/scans/                Alpha artifact outputs
D:\projects\               External tool source repos
```

Recommended startup folder structure:

```text
backend/
  app/
    api/                   Versioned routers: v1/scans, v1/runtime, v1/reports
    application/           Use cases: start scan, run recon phase, export report
    domain/                Scan, Scope, Finding, Evidence, ReconEntity models
    infrastructure/        Supabase, Redis, Neo4j, PinchTab, tool process runners
    workers/               Background scan and tool orchestration
  agents/
    alpha/                 Alpha domain orchestrator, phases, parsers, scoring
    omega/
    sigma/
  shared/
    events/
    telemetry/
    security/
frontend/
  app/
  components/
  features/
    scans/
    recon/
    findings/
    reports/
  lib/
```

Do this migration incrementally. Do not move everything at once.

## 4. Database Schema

Current schema already has a useful foundation:

- `vulnerabilities`, `exploit_results`, `attack_graph`, `remediation`, `patches`, `ci_cd_logs`
- `distributed_tasks` for worker coordination
- `scan_episodes`, `semantic_memory`, `scan_objectives`
- `toolcalls`, `approvals`, `scope_rules`
- `http_requests`, `http_responses`
- `kg_nodes`, `kg_edges`
- `recon_runs`, `recon_entities`, `recon_artifacts`, `recon_endpoint_scores`

Required Alpha additions:

```sql
CREATE TABLE recon_relationships (
  id TEXT PRIMARY KEY,
  scan_id TEXT NOT NULL,
  src_entity_id TEXT NOT NULL,
  dst_entity_id TEXT NOT NULL,
  relationship TEXT NOT NULL,
  confidence DOUBLE PRECISION DEFAULT 0,
  evidence JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE recon_tool_outputs (
  id TEXT PRIMARY KEY,
  scan_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  phase TEXT NOT NULL,
  parser_version TEXT NOT NULL DEFAULT 'v1',
  raw_artifact_id TEXT NOT NULL,
  normalized_count INTEGER DEFAULT 0,
  status TEXT NOT NULL,
  errors JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE recon_oob_interactions (
  id TEXT PRIMARY KEY,
  scan_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  interaction_type TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  source_endpoint TEXT DEFAULT '',
  raw JSONB NOT NULL DEFAULT '{}',
  severity TEXT DEFAULT 'high',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes:

- `(scan_id, kind, label)` on entities
- `(scan_id, score DESC)` on endpoint scores
- `(scan_id, tool_name, phase)` on tool outputs
- `(scan_id, relationship)` on relationships
- JSONB GIN indexes for normalized entity payloads and evidence

Neo4j should be optional at first. Keep Supabase as source of truth, then mirror graph data into Neo4j when `ALPHA_ENABLE_NEO4J=true`.

## 5. API Endpoints

Current endpoints:

- `GET /api/health`
- WebSockets: `/stream`, `/ws/live`
- Recon: `POST /api/recon/ingest`, `GET /api/recon/keyring`, `POST /api/recon/keys`
- Attack: `POST /api/attack/fire`, `POST /api/attack/replay/{vuln_id}`
- Runtime: `GET /api/runtime/tools`, `POST /api/runtime/tools/run`, approvals, graph, telemetry
- Dashboard: stats, scans, settings, auth/2FA, reset
- Reports: download, PDF, consolidated, diff, live report
- AI: mutate, autonomous engage, status
- Defense and data demo routes

Recommended production API:

```text
POST   /api/v1/scans
GET    /api/v1/scans
GET    /api/v1/scans/{scan_id}
POST   /api/v1/scans/{scan_id}/cancel
GET    /api/v1/scans/{scan_id}/events
GET    /api/v1/scans/{scan_id}/artifacts
GET    /api/v1/scans/{scan_id}/attack-surface
GET    /api/v1/scans/{scan_id}/graph
GET    /api/v1/scans/{scan_id}/findings
POST   /api/v1/scans/{scan_id}/approvals/{approval_id}/approve
POST   /api/v1/scans/{scan_id}/approvals/{approval_id}/deny
GET    /api/v1/tools
GET    /api/v1/tools/recon
GET    /api/v1/reports/{scan_id}
GET    /api/v1/reports/{scan_id}/sarif
GET    /api/v1/reports/{scan_id}/hackerone
WS     /api/v1/scans/{scan_id}/stream
```

Keep old endpoints as compatibility wrappers until the UI migrates.

## 6. UI Architecture

Current UI:

- `App.jsx` holds auth and page selection.
- Pages: Dashboard, Scans, NewScan, Settings, Library.
- Real-time data uses `useWebSocket`, a module-level singleton.
- API URL handling lives in `src/lib/api.js`.
- Components are mostly page-oriented rather than domain-feature-oriented.

Production UI model:

```text
features/scans/
  ScanCreateForm
  ScanList
  ScanStatusTimeline
features/recon/
  AttackSurfaceTable
  EndpointDrawer
  ToolRunTimeline
  ArtifactBrowser
  ScopePanel
features/findings/
  FindingList
  EvidenceViewer
  SeverityBadge
features/graph/
  ReconGraph
  GraphFilters
features/reports/
  ReportDownloadBar
```

Design principles:

- The first viewport should be the operator dashboard, not a marketing page.
- Use dense, scannable operational layouts.
- Every async panel needs loading, empty, error, stale, and reconnect states.
- Accessibility: keyboard navigation, visible focus, aria labels for icon buttons, table semantics, reduced-motion support.

## 7. Structural Problems

Highest-risk areas found:

- `backend/ai/cortex.py` is very large and mixes model routing, prompts, fallback heuristics, parsing, scoring, and error handling.
- `backend/core/orchestrator.py` and `backend/agents/beta.py` form an import cycle.
- Many broad `except Exception` blocks hide failures or return defaults.
- Legacy Alpha and Alpha V6 coexist with duplicate HTTP probing logic.
- Event payloads are still loose dicts in many places.
- Frontend navigation is state-based instead of route-based, making deep links and scan-specific pages harder.
- Tests are phase scripts, not standard unit/integration suites with fixtures and reliable isolation.
- Supabase is optional/fail-open in many code paths, which is good for local dev but risky for production observability.

## 8. Refactoring Strategy

Phase 1, low risk:

- Keep compatibility endpoints.
- Move shared event payloads to Pydantic schemas.
- Add typed recon command/parsing layers.
- Add structured logging to silent exception paths.
- Keep Alpha V6 behind feature flags.
- Add tests for scope enforcement, command planning, parser normalization, endpoint scoring.

Phase 2, medium risk:

- Split `CortexEngine` into model clients, prompt builders, classifiers, and fallback policies.
- Break `orchestrator <-> beta` import cycle with neutral interfaces.
- Move scan lifecycle into an application service.
- Replace ad hoc dashboard state mutation with scan-specific event reducers.

Phase 3, production hardening:

- Background worker queue for scans.
- Artifact retention policy.
- Neo4j/OpenCTI exporters.
- Multi-tenant auth and role-based scan permissions.
- Usage metering and audit logs.

## 9. Alpha Target Architecture

Alpha should be deterministic first, LLM-assisted second:

```text
AlphaPolicy
  -> PhaseController
  -> ScopeGate
  -> ToolCommandPlanner
  -> ToolRunner
  -> RawArtifactStore
  -> ParserRegistry
  -> Normalized ReconEntity/Endpoint/Relationship
  -> Dedupe/Confidence Engine
  -> RAG Ingest
  -> Supabase + KG + Neo4j optional mirror
  -> EventBus packets for Omega/Sigma/Beta/Kappa/Chi
```

Phase gates:

1. Initialization and scope validation
2. Passive OSINT and historical intelligence
3. DNS and infrastructure validation
4. HTTP probing and browser/network intelligence
5. Directory, route, and parameter discovery
6. API schema and GraphQL recon
7. Visual evidence
8. Template validation
9. Correlation, scoring, graph finalization, export

Never let the LLM compose shell commands. The LLM can select phase objectives and interpret normalized facts; the command planner builds approved argv arrays.

## 10. External Tool Integration Matrix

Use the cloned repos as upstream capability providers:

| Tool/repo | Integration type | Alpha phase |
| --- | --- | --- |
| SpiderFoot | CLI/API adapter and SQLite/CSV/JSON parser | Passive OSINT |
| Subfinder | CLI JSONL parser | Passive subdomains |
| Amass | CLI JSON/parser | Passive/active asset map |
| Cloudlist | CLI parser, credential-gated | Cloud assets |
| gau, waybackurls | CLI URL parser | Historical URLs |
| dnsx, shuffledns | CLI JSONL/line parser | DNS validation/bruteforce |
| Naabu, Nmap | CLI JSON/XML parser | Ports/services |
| tlsx | CLI JSON parser | TLS/cert intelligence |
| httpx | CLI JSONL parser | HTTP fingerprints |
| Katana, Hakrawler | CLI parser | Crawling/endpoints |
| LinkFinder, SecretFinder | Python module/CLI parser | JS routes/secrets |
| Gobuster, Feroxbuster, ffuf, dirsearch | CLI JSON/parser | Content/vhost/params |
| Nuclei | CLI JSONL parser and Interactsh integration | Validation |
| Interactsh | Client adapter and polling task | OOB callbacks |
| Aquatone, gowitness | CLI artifacts | Visual evidence |
| Kiterunner | CLI parser | API route discovery |
| InQL, GraphQL Voyager | CLI/library artifacts | GraphQL schema/visualization |
| SecLists, Assetnote wordlists | Path providers only | Wordlist construction |
| PayloadsAllTheThings | Taxonomy/reference only | Omega/Sigma context |
| Playwright, Puppeteer, Selenium | Browser fallback layers | Browser recon |
| Neo4j | Optional graph mirror | Correlation |
| OpenCTI | Optional CTI export | Enrichment/export |
| PinchTab | Primary browser control plane | Browser/network evidence |

## 11. What Was Implemented In This Pass

Added a safe external-tool adapter foundation:

- `backend/tools/recon/commands.py`
  - `ReconCommand`
  - `ReconCommandPlanner`
  - Passive command plans for Subfinder, Amass, gau, waybackurls, Cloudlist.
  - DNS and HTTP command plan builders for dnsx, shuffledns, httpx, katana.

- `backend/tools/recon/runner.py`
  - `ReconCommandRunner`
  - Bounded subprocess execution with argv arrays, no shell strings.
  - Timeout handling, stdout artifact writing, stderr capture, SHA-256, byte counts.
  - Toolcall persistence through `db_manager`.

- `backend/agents/alpha_v6/orchestrator.py`
  - Optional external passive tool execution behind `ALPHA_ENABLE_EXTERNAL_TOOLS`.
  - Raw artifacts are registered and RAG summaries are ingested.
  - Skips are recorded when binaries are not installed/on PATH.

- `backend/core/config.py`
  - `ALPHA_ENABLE_EXTERNAL_TOOLS=false` by default.
  - `ALPHA_TOOL_TIMEOUT_SECONDS=180`.

This is intentionally a safe MVP layer: it extracts capability by invoking maintained tools, not by copying their internals.

## 12. Next Alpha Implementation Batches

Batch A, passive intelligence:

- Add parsers:
  - `parse_subfinder_jsonl`
  - `parse_amass_json`
  - `parse_url_lines`
  - `extract_subdomains_from_urls`
  - `extract_params_from_urls`
  - `classify_historical_paths`
- Persist `Subdomain`, `HistoricalPath`, `Parameter`, `CloudAsset` entities.
- Emit high-confidence subdomain discoveries only after dedupe.

Batch B, DNS/infra:

- Build resolved subdomain file from passive results.
- Run `dnsx`.
- Parse CNAME/A/AAAA/MX/TXT.
- Detect dangling CNAME candidates.
- Add `naabu` and `nmap` command plans.
- Parse ports/services and link host -> IP -> port -> service.

Batch C, HTTP/browser:

- Run `httpx` on live hosts.
- Parse technologies, status, title, server, content length, favicon hash.
- Feed live high-value URLs into PinchTab.
- Persist screenshots, text, console, browser errors, network requests.

Batch D, crawling/JS:

- Run `katana`, `hakrawler`.
- Run LinkFinder/SecretFinder on JS assets.
- Redact secrets and emit `VULN_CANDIDATE` immediately.
- Convert browser network requests into endpoints.

Batch E, discovery/API/GraphQL:

- Target-specific wordlist builder from:
  - SecLists API/web discovery lists
  - Assetnote wordlists
  - historical paths
  - discovered path segments
  - detected framework vocabulary
- Add `feroxbuster`, `ffuf`, `dirsearch`, `gobuster`.
- Add OpenAPI/Swagger/Postman/Insomnia/Bruno schema discovery.
- Add Kiterunner and InQL adapters.

Batch F, validation/export:

- Interactsh scan-wide client.
- Nuclei adapter with severity/rate limits.
- Neo4j exporter.
- OpenCTI/STIX-like export.
- Maltego/GraphML export.

## 13. Startup MVP Build Plan

MVP user workflow:

1. User creates a scan with target, scope, mode, and authorization checkbox.
2. Backend creates `recon_run`, scope rules, artifact root, event stream.
3. Alpha runs passive-only by default, standard mode only after explicit confirmation.
4. Dashboard shows phase progress, tool status, discovered entities, and top attack surface.
5. User reviews approvals for active tools.
6. Alpha emits scored endpoints to Omega/Sigma/Beta.
7. Reports export evidence and attack-surface map.

Production principles:

- Passive-first by default.
- Explicit authorization for active scanning.
- Every raw tool output preserved.
- Every normalized fact has source/evidence/confidence.
- All state-changing tools require approval.
- UI clearly separates recon findings from verified vulnerabilities.

## 14. Verification Strategy

Immediate checks:

- `python -m compileall backend`
- Import smoke for Alpha V6 and recon command planner.
- Unit tests for command planning without running tools.
- Parser tests with tiny fixtures.
- Scope tests for out-of-scope and `.gov/.mil` refusal.

Integration checks:

- Passive scan against a local fixture domain/file corpus.
- HTTP-only scan against a local FastAPI test app.
- PinchTab unavailable path verifies Playwright fallback/skip behavior.
- Supabase unavailable path still writes local artifacts.

UI checks:

- `npm run build`
- WebSocket reconnect test.
- Scan stream renders RECON_PACKET and RECON_COMPLETE.
- Artifact and endpoint tables handle empty/loading/error states.

## 15. Critical Risks

- Copying third-party source code directly would create license and maintenance risk.
- Running aggressive recon by default would create legal and safety risk.
- Broad catches can hide broken scans.
- Tool outputs are inconsistent; parsers must be fixture-tested.
- Some external tools require binaries built from source even though repos are cloned.
- Full Neo4j/OpenCTI integration is too heavy for first MVP unless optional.

## 16. Definition Of Done For Alpha V1 Production

- Scope gate blocks out-of-scope targets and unauthorized `.gov/.mil`.
- Passive mode produces useful subdomains, URLs, params, historical paths.
- Standard mode produces live hosts, HTTP fingerprints, screenshots, JS/network endpoints.
- All tool outputs have artifacts and DB records.
- Dedupe prevents duplicate endpoints/events.
- Priority scoring sends only meaningful `RECON_PACKET` events.
- `RECON_COMPLETE` contains summary, attack surface, Omega/Sigma context, artifact paths.
- Tests cover command planning, parsers, scope, scoring, and no-tool fallback.
