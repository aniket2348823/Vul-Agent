# Antigravity API Endpoint Scanner Deep Integration Blueprint V2

This is a second-pass extraction from the local CAI, Decepticon, and PentAGI repos, mapped to the current scanner code under `backend/`. I treated generated/vendor-like code as reference material, but focused the line-by-line reading on the runtime, middleware, tools, graph, memory, sandbox, controller, prompt, and schema layers that can actually make the scanner production-ready.

## Executive Summary

The scanner already has a good swarm skeleton: `HiveEvent`, scan isolation, Redis distribution, Supabase persistence, agents, modules, guard layer, memory, sandbox, reporting, and first-pass JWT/HTTP/parser additions. The next upgrade should not be another broad agent layer. It should harden the execution kernel and evidence model:

1. **PentAGI runtime discipline**: structured flow/task/subtask state, durable tool-call logs, strict output summarization, barrier tools, Docker lifecycle management, Langfuse/OpenTelemetry spans, and message-chain compaction.
2. **Decepticon offensive intelligence**: OPPLAN task tree, engagement scope/RoE enforcement, knowledge graph, attack-chain planning, importers for scanner outputs, HTTP/JWT/OAuth/cookie/GraphQL tooling, validation and report templates.
3. **CAI agent runtime safety**: guardrails, strict tool schemas, handoff/tool-use tracking, parallel tool executor, session recording, cost tracking, dynamic prompt rendering, and resilient message-list repair.

The highest-value production design is:

`HiveOrchestrator -> OPPLAN/Scope Gate -> Tool Executor -> Sandbox/HTTP Client -> Output Guard/Compactor -> Evidence Store -> Knowledge Graph -> Report`

## Source Feature Inventory

### CAI

High-value files and mechanics:

- `src/cai/agents/guardrails.py`
  - Unicode homoglyph normalization.
  - Prompt injection regex detection.
  - Base64/Base32 payload decoding before detection.
  - Input/output guardrails around agent messages.

- `src/cai/sdk/agents/_run_impl.py`
  - Tool use tracking, handoff handling, and output-schema validation.
  - Parallel execution of function/computer tool calls.
  - Guardrail span execution around inputs/outputs.
  - Partial result preservation when a run is interrupted.
  - Tool output truncation.

- `src/cai/sdk/agents/parallel_tool_executor.py`
  - Background queue for bounded parallel tool calls.
  - Per-agent result collection.
  - Timeout-aware result retrieval.

- `src/cai/sdk/agents/strict_schema.py`
  - Converts JSON schema into strict schema: explicit required fields, no extra properties, `$ref` handling.

- `src/cai/sdk/agents/run_to_jsonl.py`
  - JSONL session recorder.
  - Replayable conversation history.
  - Token/cost statistics over recorded runs.

- `src/cai/agents/patterns/pattern.py`
  - Reusable agent topologies: parallel, swarm, hierarchical, sequential, conditional.

- `src/cai/tools/common.py`
  - Shell sessions with friendly IDs.
  - Async/background command mode.
  - Docker/local/SSH/CTF execution routing.
  - Streaming tool output UX and token/cost display hooks.

- `src/cai/util.py`
  - CostTracker, model pricing, active/idle timers.
  - Prompt renderer and instruction appender.
  - Message repair helpers.
  - Tool output formatting and streaming lifecycle.

Best integrations:

- Port `strict_schema.py` into `backend/core/strict_schema.py`.
- Add CAI-style session recorder to `backend/core/run_recorder.py`.
- Add bounded parallel tool executor to `backend/core/tool_executor.py`.
- Add cost and token accounting to `backend/core/telemetry.py`.
- Expand current `backend/core/guard_layer.py` with CAI’s input/output guardrail concept, not just payload sanitization.

### Decepticon

High-value files and mechanics:

- `decepticon/middleware/opplan.py`
  - OPPLAN state injected into every model call.
  - Objective CRUD tools.
  - Status transitions with dependency checks.
  - Parent/child objective expansion and collapse.
  - Save/load `opplan.json`.
  - Prevention of parallel state-mutating OPPLAN calls.

- `decepticon/middleware/engagement.py`, `filesystem.py`, `notifications.py`, `skills.py`
  - Engagement context injection.
  - Filesystem isolation under engagement workspace.
  - Background job notifications.
  - Skill progressive disclosure via markdown frontmatter.

- `decepticon/backends/docker_sandbox.py`
  - Persistent tmux-backed Docker sandbox.
  - Background job tracking.
  - Bounded output truncation.
  - Better than a one-command container wrapper for long-running recon tools.

- `decepticon/core/schemas.py`
  - RoE, CONOPS, OPPLAN, Objective, Evidence, Finding, AttackPath.
  - A stronger evidence schema than ad hoc vulnerability payloads.

- `decepticon/tools/research/graph.py`
  - Knowledge graph with `NodeKind` and `EdgeKind`.
  - Nodes for host, domain, service, URL, user, credential, secret, session, vulnerability, CVE, misconfiguration, weakness, technique, entrypoint, crown jewel, finding, hypothesis, patch.
  - Edges for `HOSTS`, `RESOLVES_TO`, `EXPOSES`, `AUTHENTICATES_TO`, `HAS_SESSION`, `CAN_ACCESS`, `HAS_VULN`, `EXPLOITS`, `LEADS_TO`, `PIVOTS_TO`, `ESCALATES_TO`, `REACHES`, `VALIDATES`.

- `decepticon/tools/research/chain.py`
  - Attack chain planning from graph edges.
  - Critical path scoring.
  - Impact analysis, unexplored surface, credential reachability.

- `decepticon/tools/research/tools.py`
  - Importers for `nmap`, `nuclei`, `httpx`, `dnsx`, `katana`, `masscan`, `ffuf`, `testssl`, `crackmapexec`, SARIF.
  - CVE lookup and dependency enrichment.
  - JWT/OAuth/cookie findings promoted into graph nodes.
  - Finding validation helper.

- `decepticon/tools/web/http.py`
  - Immutable `HTTPRequest` and `HTTPResponse`.
  - Bounded HTTP history with search/dump/load.
  - Session cookies, default headers, replay, and response diffing.

- `decepticon/tools/web/jwt.py`, `oauth.py`, `session.py`, `graphql.py`
  - JWT parse/forge/HS crack.
  - OAuth callback audit.
  - Cookie entropy/framework/JWT/base64 analysis.
  - GraphQL introspection planning and IDOR candidate generation.

- `decepticon/tools/reporting/`
  - HackerOne, Bugcrowd, executive summary, timeline formats.

Best integrations:

- Replace current lightweight `GraphEngine` with a Decepticon-style typed knowledge graph in `backend/core/knowledge_graph.py`.
- Extend current `backend/core/objectives.py` into an OPPLAN task tree, with parent/child objectives and dependency gates.
- Upgrade `backend/modules/tech/http_client.py` to mirror Decepticon’s request/response history model.
- Add API-specific importers for external scanner output under `backend/modules/ingest/`.
- Add OAuth, cookie, and GraphQL modules under `backend/modules/tech/`.

### PentAGI

High-value files and mechanics:

- `backend/pkg/tools/executor.go`
  - Central custom executor.
  - Toolcall DB lifecycle: create running -> finish/fail.
  - Per-tool Langfuse observations.
  - Tool categories: environment, search network, agent, barrier, vector search/store.
  - Default 16 KB result limit.
  - Summarize only allowed tools.
  - Store only allowed tool results in vector memory.
  - Argument formatting and truncation before summary prompts.

- `backend/pkg/tools/registry.go`
  - Tool type enum and registry.
  - Barrier tool identification.
  - Allowed summarization/storing lists.
  - Strong central registry of tool schemas.

- `backend/pkg/csum/chain_summary.go`
  - Message-chain summarizer, not just stdout summarizer.
  - Preserves the last section.
  - Handles oversized tool-output pairs.
  - Summarizes old QA/tool sections.
  - Maintains a reserve budget.
  - Creates XML-ish summarization prompt containing tasks/messages/tool responses.

- `backend/pkg/cast/chain_ast.go`
  - Message chain AST: sections, headers, AI/tool body pairs.
  - Validates pending/unmatched tool calls.
  - Can force-repair broken chains with fallback tool responses/requests.
  - Normalizes provider-specific tool call IDs.
  - Clears provider-specific reasoning metadata when switching models.

- `backend/pkg/controller/flow.go`, `task.go`, `subtask.go`
  - Durable flow -> task -> subtask worker model.
  - Worker status transitions, stop/finish lifecycle.
  - Input queues with timeouts.
  - Provider switching.

- `backend/pkg/controller/*log*.go`
  - Message logs, agent logs, search logs, terminal logs, vector store logs.
  - Streaming update workers.

- `backend/pkg/docker/client.go`
  - Container lifecycle, per-flow container naming, port allocation, cleanup, copy-in/copy-out.

- `backend/pkg/graphiti/client.go`, `tools/graphiti_search.go`
  - Temporal memory search APIs.
  - Recent context, successful tools, entity relationships, episode context.

- `backend/pkg/templates/prompts/*.tmpl`
  - Production prompt set for task planning, subtasks, summarization, reporting, tool-call fixing, pentester/coder/reporter roles.

- `observability/*`
  - Langfuse, OpenTelemetry, Jaeger, Grafana, Loki stack.

Best integrations:

- Convert `executor.go`, `registry.go`, `chain_summary.go`, and `chain_ast.go` into Python first. These are the most valuable PentAGI mechanics.
- Add durable flow/task/subtask/toolcall/log tables to Supabase.
- Add `backend/core/conversation_compactor.py` for message-chain compaction.
- Add `backend/core/tool_registry.py` and `backend/core/tool_executor.py`.
- Add `backend/core/telemetry.py` with OpenTelemetry spans and optional Langfuse hooks.
- Extend `backend/core/sandbox.py` from one-shot Docker commands into managed scan containers.

## Current Scanner Gap Analysis

Already present:

- `backend/core/hive.py`: event bus, scan isolation, dead-letter queue, Redis distribution.
- `backend/core/orchestrator.py`: scan bootstrap, worker routing, module dispatch, browser worker, reporting lifecycle.
- `backend/core/guard_layer.py`: first-pass CAI-like payload guard.
- `backend/core/stdout_watchdog.py`: first-pass 16 KB output limiter.
- `backend/core/sandbox.py`: first-pass Docker sandbox.
- `backend/core/objectives.py`: simple objective transitions.
- `backend/core/memory.py`: local episodic/semantic memory.
- `backend/core/schema.sql`: vulnerabilities, exploit results, distributed tasks, memory, scan objectives.
- `backend/core/graph_engine.py`: simple weighted vuln graph.
- `backend/core/chain_analyzer.py`: static transition-matrix attack chains.
- `backend/modules/tech/jwt.py`, `http_client.py`, `parsers.py`: first-pass web tooling.

Main gaps:

- No single authoritative tool registry with schemas, categories, barriers, summarization policy, and memory policy.
- Tool calls are not fully durable from start to finish.
- Output limiting is payload-based, not message-chain-aware.
- The graph is vulnerability-only; it does not model hosts, services, URLs, identities, sessions, credentials, techniques, evidence, or validated attack paths.
- Objectives are flat; no parent/child task tree, no read-before-write rule, no dynamic OPPLAN context.
- Sandbox is one-shot; no per-scan lifecycle, long-running command/session support, copy-in/out, background jobs, or cleanup reconciliation.
- HTTP tooling needs first-class request/response records and diff/replay across modules.
- OAuth/cookie/GraphQL tooling is missing.
- Observability is ad hoc; no consistent spans across agents, tools, Redis events, DB writes, and model calls.
- Memory is local JSON with optional DB writes; production should make Supabase/pgvector primary and local JSON fallback.

## Target Architecture

### Runtime Kernel

New/expanded files:

- `backend/core/tool_registry.py`
- `backend/core/tool_executor.py`
- `backend/core/strict_schema.py`
- `backend/core/conversation_ast.py`
- `backend/core/conversation_compactor.py`
- `backend/core/telemetry.py`
- `backend/core/run_recorder.py`
- `backend/core/scope.py`
- `backend/core/approval.py`

Responsibilities:

- Tool registry owns tool definitions, JSON schemas, type/category, barrier status, memory-store eligibility, summarization eligibility, and mutating/safe classification.
- Tool executor wraps every tool call with:
  - scope check,
  - barrier approval check,
  - durable DB `toolcalls` row,
  - telemetry span,
  - output guard,
  - summarization/compaction,
  - optional memory storage,
  - final status update.
- Strict schema helper hardens all tool schemas before they reach LLM providers.
- Conversation AST/compactor ports PentAGI’s `cast` and `csum` packages to Python.
- Run recorder stores JSONL/Supabase replay logs.

### Objective/OPPLAN Layer

Upgrade:

- `backend/core/objectives.py`
- `backend/schemas/findings.py`
- `backend/core/schema.sql`

Add:

- `backend/core/opplan.py`
- `backend/api/endpoints/objectives.py`

Features:

- Parent/child objective tree.
- `add_objective`, `get_objective`, `list_objectives`, `update_objective`, `objective_expand`, `objective_collapse`.
- Read-before-write enforcement for updates.
- No parallel objective mutations.
- Objective completion requires evidence or finding IDs.
- Dependency gate: blocked objectives cannot execute until prerequisites complete.
- API scanner phases:
  - Scope and Recon
  - Surface Mapping
  - Passive Analysis
  - Active Detection
  - Verification
  - Exploit Safety Review
  - Reporting

### Knowledge Graph

Replace or wrap:

- `backend/core/graph_engine.py`
- `backend/core/chain_analyzer.py`

Add:

- `backend/core/knowledge_graph.py`
- `backend/core/attack_chain.py`
- `backend/modules/ingest/nmap.py`
- `backend/modules/ingest/nuclei.py`
- `backend/modules/ingest/httpx.py`
- `backend/modules/ingest/ffuf.py`
- `backend/modules/ingest/katana.py`
- `backend/modules/ingest/testssl.py`
- `backend/modules/ingest/sarif.py`

Graph model:

- Nodes: target, domain, host, service, URL, endpoint, parameter, auth scheme, token, cookie, session, credential, secret, vulnerability, CVE, weakness, finding, evidence, objective, attack path.
- Edges: resolves_to, exposes, contains_endpoint, accepts_parameter, authenticated_by, has_session, leaks_secret, has_vuln, validates, exploits, leads_to, pivots_to, escalates_to, reaches.

API-scanner chain examples:

- `JWT weak secret -> forged admin token -> IDOR endpoint -> data leak`
- `GraphQL introspection -> IDOR candidate -> unauthorized object access`
- `Missing auth on /users/{id} -> role escalation endpoint -> admin takeover`
- `SSRF endpoint -> internal metadata exposure -> credential leak`
- `CORS misconfig -> token theft route -> privileged API replay`

### Sandbox/Execution Isolation

Upgrade:

- `backend/core/sandbox.py`

Add:

- `backend/core/sandbox_sessions.py`
- `backend/core/background_jobs.py`

Features:

- Per-scan Docker container.
- Locked work directory.
- Copy-in/copy-out.
- Port allocation.
- Long-running background jobs.
- Session IDs/friendly IDs.
- Cleanup reconciliation on scan finish/crash.
- Mutating commands blocked unless approved.

### API/Web Tooling

Upgrade:

- `backend/modules/tech/http_client.py`
- `backend/modules/tech/jwt.py`

Add:

- `backend/modules/tech/oauth.py`
- `backend/modules/tech/cookies.py`
- `backend/modules/tech/graphql.py`
- `backend/modules/tech/cors.py`
- `backend/modules/tech/rate_limit.py`
- `backend/modules/tech/openapi.py`

Features:

- Immutable request/response history with IDs.
- Replay and diff.
- Scope-aware HTTP client.
- Automatic token/cookie extraction into graph.
- JWT parse/forge/crack.
- OAuth callback audit.
- Cookie entropy and framework detection.
- GraphQL introspection planning and IDOR candidate generation.
- OpenAPI/Swagger endpoint import and parameter graphing.

### Memory

Upgrade:

- `backend/core/memory.py`
- `backend/agents/kappa.py`

Add:

- `backend/core/vector_store.py`
- `backend/core/temporal_memory.py`

Features:

- Supabase/pgvector as primary vector store.
- Local JSON fallback only when DB unavailable.
- PentAGI-style tool-result chunking with metadata.
- CAI-style episodic vs semantic split.
- Graphiti-inspired search modes:
  - recent context,
  - successful tools,
  - entity relationships,
  - episode context,
  - similar endpoint patterns.

### Observability

Add:

- `backend/core/telemetry.py`
- `backend/api/endpoints/telemetry.py`

Features:

- Span per scan, agent, objective, toolcall, HTTP request, Redis event, DB write, model call.
- Cost/tokens per model call.
- Tool duration and result size.
- Barrier approvals and denials.
- Dead-letter queue surfaced in API.
- Optional Langfuse exporter.
- Optional OpenTelemetry exporter.

### Reporting

Upgrade:

- `backend/reporting/hackerone.py`
- `backend/reporting/sarif.py`
- `backend/core/reporting.py`

Add:

- `backend/reporting/bugcrowd.py`
- `backend/reporting/executive.py`
- `backend/reporting/timeline.py`
- `backend/reporting/evidence_bundle.py`

Features:

- Evidence-first reports.
- Attack path sections generated from graph, not just finding lists.
- HackerOne/Bugcrowd templates.
- SARIF export.
- Timeline export.
- Repro steps from HTTP history.

## Database Additions

Add to `backend/core/schema.sql`:

- `scans`
- `scan_flows`
- `scan_tasks`
- `scan_subtasks`
- `toolcalls`
- `agent_logs`
- `message_logs`
- `search_logs`
- `terminal_logs`
- `vector_store_logs`
- `http_requests`
- `http_responses`
- `kg_nodes`
- `kg_edges`
- `approvals`
- `scope_rules`
- `run_records`

Important indexes:

- `toolcalls(scan_id, status, created_at DESC)`
- `toolcalls(scan_id, tool_name, created_at DESC)`
- `http_requests(scan_id, method, url_hash)`
- `http_responses(request_id)`
- `kg_nodes(scan_id, kind, label)`
- `kg_edges(scan_id, src_id, kind)`
- `scan_objectives(scan_id, status, priority)`
- `message_logs(scan_id, created_at DESC)`

Use JSONB GIN indexes for node/edge props and HTTP metadata where filtering is common.

## Prioritized Implementation Order

### P0: Execution Safety and Determinism

1. Port CAI `strict_schema.py`.
2. Build `tool_registry.py`.
3. Build `tool_executor.py` from PentAGI `executor.go`.
4. Add `approvals` and barrier enforcement.
5. Route all active/mutating HTTP requests through scope and barrier checks.
6. Expand `guard_layer.py` to cover tool output and model output.

Exit criteria:

- Every tool has a schema, category, and policy.
- Every tool call is logged from running to success/failure.
- Unsafe/mutating actions can pause and request approval.
- Tool output cannot poison the main agent context.

### P1: Conversation and Output Compaction

1. Port PentAGI `chain_ast.go` to `conversation_ast.py`.
2. Port PentAGI `chain_summary.go` to `conversation_compactor.py`.
3. Replace simple output truncation in event/tool paths with compaction policies.
4. Preserve last section, summarize older tool responses, and repair unmatched tool calls.

Exit criteria:

- Large scans do not blow the context window.
- Broken provider-specific tool-call IDs can be normalized.
- Reasoning/tool metadata is scrubbed when switching providers.

### P1: OPPLAN Task Tree

1. Upgrade `objectives.py` to Decepticon-style parent/child objectives.
2. Add objective DB persistence.
3. Add objective API endpoints.
4. Have `HiveOrchestrator` create scan objectives from selected modules and discovered graph gaps.
5. Require evidence before completion.

Exit criteria:

- Scans have visible phases and objective progress.
- Agents cannot skip verification/reporting prerequisites.
- Stuck objectives become blocked with reasons instead of looping.

### P1: Knowledge Graph and Attack Chains

1. Port Decepticon `graph.py` to `knowledge_graph.py`.
2. Port relevant chain planning from `chain.py`.
3. Map current findings/modules into graph nodes and edges.
4. Add importers for `nmap`, `nuclei`, `httpx`, `ffuf`, `katana`, `testssl`, SARIF.
5. Generate objectives from graph gaps and chain candidates.

Exit criteria:

- Findings, endpoints, tokens, cookies, services, and evidence are linked.
- The scanner can explain why it is testing the next endpoint.
- Reports include attack paths backed by graph evidence.

### P2: Production Sandbox

1. Upgrade Docker sandbox to per-scan lifecycle.
2. Add long-running command sessions and background job notifications.
3. Add copy-in/copy-out APIs.
4. Add cleanup reconciliation.
5. Route exploit scripts, recon tools, and verification scripts through the sandbox.

Exit criteria:

- Active exploitation never touches host filesystem directly.
- Long-running tools can be monitored and stopped.
- Containers are cleaned after scan completion.

### P2: API/Web Tool Depth

1. Replace current HTTP client internals with Decepticon-style request/response history.
2. Add OAuth, cookies, GraphQL, CORS, rate-limit, and OpenAPI modules.
3. Store all HTTP interactions in DB and graph.
4. Generate reproducible replay steps for validated findings.

Exit criteria:

- API findings include exact request/response evidence.
- Replay/diff is available for verification and reporting.
- GraphQL/JWT/OAuth/session classes feed the same evidence model.

### P2: Memory and Learning

1. Make Supabase/pgvector primary memory.
2. Chunk tool results with metadata.
3. Add successful-tool and recent-context searches.
4. KappaAgent should retrieve by endpoint pattern, vuln type, graph neighborhood, and historical success.

Exit criteria:

- Similar targets reuse verified techniques.
- Memory retrieval is scoped, explainable, and does not leak stale scan state.

### P3: Observability and UI

1. Add OpenTelemetry/Langfuse optional exporter.
2. Add telemetry API.
3. Surface OPPLAN, toolcalls, graph, HTTP history, background jobs, and cost in the UI.
4. Add replayable JSONL/Supabase run records.

Exit criteria:

- A scan can be debugged from UI without reading logs.
- Cost spikes, stuck tools, and blocked approvals are obvious.

### P3: Reporting

1. Build evidence bundle.
2. Add Bugcrowd, executive, timeline exports.
3. Use graph attack paths in final report.
4. Add SARIF for CI/security-platform import.

Exit criteria:

- Reports are acceptable for real bug bounty/internal security workflows.
- Every claim links to evidence.

## Features to Avoid or Defer

Do not pull these into the API Endpoint Scanner unless the product scope expands:

- Decepticon AD/post-exploitation/C2-heavy workflows.
- CAI CTF-specific logic and terminal UI rendering.
- PentAGI’s full generated Langfuse API client.
- PentAGI installer wizard and full frontend wholesale.
- Binary/reversing/solidity fuzzing beyond SARIF/import support.
- Any auto-exploit path that bypasses scope, RoE, or approval gates.

## Direct File Mapping

| Source | Target |
|---|---|
| CAI `guardrails.py` | `backend/core/guard_layer.py` |
| CAI `strict_schema.py` | `backend/core/strict_schema.py` |
| CAI `_run_impl.py` | `backend/core/tool_executor.py`, `backend/core/agent_runtime.py` |
| CAI `parallel_tool_executor.py` | `backend/core/parallel_tools.py` |
| CAI `run_to_jsonl.py` | `backend/core/run_recorder.py` |
| CAI `patterns/pattern.py` | `backend/core/agent_patterns.py` |
| CAI `tools/common.py` | `backend/core/sandbox_sessions.py` |
| Decepticon `opplan.py` | `backend/core/opplan.py`, `backend/core/objectives.py` |
| Decepticon `core/schemas.py` | `backend/schemas/findings.py`, `backend/schemas/engagement.py` |
| Decepticon `graph.py` | `backend/core/knowledge_graph.py` |
| Decepticon `chain.py` | `backend/core/attack_chain.py` |
| Decepticon `research/tools.py` | `backend/modules/ingest/*`, `backend/modules/tech/*` |
| Decepticon `web/http.py` | `backend/modules/tech/http_client.py` |
| Decepticon `web/jwt.py` | `backend/modules/tech/jwt.py` |
| Decepticon `web/oauth.py` | `backend/modules/tech/oauth.py` |
| Decepticon `web/session.py` | `backend/modules/tech/cookies.py` |
| Decepticon `web/graphql.py` | `backend/modules/tech/graphql.py` |
| PentAGI `tools/executor.go` | `backend/core/tool_executor.py` |
| PentAGI `tools/registry.go` | `backend/core/tool_registry.py` |
| PentAGI `cast/chain_ast.go` | `backend/core/conversation_ast.py` |
| PentAGI `csum/chain_summary.go` | `backend/core/conversation_compactor.py` |
| PentAGI `controller/flow.go` | `backend/core/flow_controller.py` |
| PentAGI `controller/task.go` | `backend/core/task_controller.py` |
| PentAGI `controller/subtask.go` | `backend/core/subtask_controller.py` |
| PentAGI `docker/client.go` | `backend/core/sandbox.py`, `backend/core/sandbox_sessions.py` |
| PentAGI `graphiti/client.go` | `backend/core/temporal_memory.py` |
| PentAGI `templates/prompts` | `backend/prompts/*` |

## Recommended Next Code Milestone

Implement P0 in this order:

1. `backend/core/strict_schema.py`
2. `backend/core/tool_registry.py`
3. `backend/core/tool_executor.py`
4. `backend/core/approval.py`
5. Schema tables for `toolcalls`, `approvals`, `scope_rules`
6. Wrap existing HTTP/JWT/parser/sandbox tools in the registry
7. Add tests for schema strictness, barrier behavior, summarization, and durable toolcall status

This gives the scanner a production execution spine before adding more detection breadth.
