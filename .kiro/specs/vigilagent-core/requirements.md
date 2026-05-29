# Requirements Document

## Introduction

Vigilagent Core is a **backend-only** re-architecture of the existing penetration-testing system ("Vulagent") into "Vigilagent", implemented in place at `d:\Antigravity 2\penetration testing system`. These requirements are derived directly from the approved design document (`design.md`) in this folder, which itself consolidates the solution set identified across the five analysis documents. The scope is strictly limited to the solutions captured in that design.

The work closes the backend architecture and intelligence gaps of the current system while keeping its existing capabilities — HTTP-based attack modules, browser-driven analysis (OpenClaw + PinchTab), and the existing Alpha recon pipeline. It adds hierarchical delegation, iteration budgets, intelligent memory, a unified knowledge graph, real (non-fake) adaptive intelligence, real recovery, a credential vault, evidence-based detection, checkpoint/resume, strict two-LLM enforcement, and a Vulagent→Vigilagent rebrand.

The following are explicitly **out of scope** and MUST NOT be introduced: any generic exploitation shell (no sqlmap/metasploit/hydra/crackmapexec shell-runner), OSI L2–L6 network attacks, post-exploitation/C2 or reverse shells, a browser session-bridge extension, any third LLM, and any frontend change. Recon CLI tools remain in use and are consolidated; exploitation stays on the HTTP and browser surface.

## Glossary

- **Vigilagent**: The rebranded backend system as a whole (formerly "Vulagent").
- **ScopePolicy**: The single authorization authority (`core/scope.py`) that decides whether a host, URL, CIDR, or action is in scope; configured by `config/scope.yaml`.
- **ExploitExecutionEngine**: The existing HTTP/browser exploitation engine (`core/exploit_engine.py`); retains `MultiLayerVerifier` and `AdaptivePlanner`.
- **ReconTerminal**: The consolidated recon execution module (`core/terminal.py`) wrapping `ProcessRunner` + `DockerSandbox` for the installed `D:\projects` recon CLI tools. Recon only — not an exploitation shell.
- **ReconCommandRunner**: The existing recon runner (`tools/recon/runner.py`) that becomes a thin shim over ReconTerminal.
- **Recon_Tool_Registry**: The tool matrix (`tools/recon/registry.py`) that is the source of truth for installed recon tools and their availability.
- **IterationBudget**: The thread-safe budget object (`core/iteration_budget.py`) limiting how many steps an agent or scan may take.
- **DelegationManager**: The control-plane component (`core/delegation_manager.py`) that spawns budgeted child agents and returns structured `ChildResult` values over the master/worker substrate.
- **EventBus**: The existing flat event/telemetry plane (`core/hive.py`) that drives the frontend WebSocket feed.
- **Recon_Commander / Attack_Commander**: Budgeted commander agents (`agents/commanders/*`) that wrap the Alpha recon pipeline and spawn HTTP/browser attack children.
- **Omega**: The campaign-commander agent (`agents/omega.py`) responsible for strategy formulation.
- **Beta**: The multi-vector HTTP breaker agent (`agents/beta.py`).
- **PayloadBandit**: An epsilon-greedy multi-armed bandit selecting payloads by `(vuln_class, vector, payload_family)`.
- **PayloadDeliveryEngine**: Multi-vector HTTP payload delivery component used by Beta.
- **UnifiedKnowledgeGraph**: The single merged graph (`core/unified_knowledge_graph.py`) replacing `graph_engine.py` and `knowledge_graph.py`.
- **Planner**: The pre-planning component (`core/planner.py`).
- **SkillLibrary**: The learned-skill store consumed during planning.
- **LearningIntegrator**: The component (`core/learning_integrator.py`) that delivers learned recommendations back to agents (read path).
- **RecoveryEngine**: The merged recovery module (`core/recovery_engine.py`) combining `self_healing_engine.py` and `strategy_adapter.py`.
- **CredentialVault**: The encrypted, deduplicated credential store (`core/credential_vault.py`).
- **Doppelganger**: The logic-test module (`modules/logic/doppelganger.py`) that uses CredentialVault tokens.
- **MultiLayerVerifier**: The differential-analysis verifier that confirms findings using multiple independent signals.
- **ContextCompressor**: The gemini-2.5-flash sliding-window summarizer (`core/context_compressor.py`).
- **MemoryProvider**: The memory interface (`core/memory.py`) replacing the 1000-entry hard cap with compressor-backed eviction.
- **StateManager**: The state component (`core/state.py`) providing checkpoint/resume.
- **CortexEngine**: The intelligence fusion engine (`ai/cortex.py`) wiring GI5 + the two LLMs.
- **LLMRouter**: The router that assigns tasks to the correct LLM tier.
- **GI5**: A deterministic, non-LLM pre-processor/fallback engine.
- **gpt-oss-20b**: OpenRouter model `openai/gpt-oss-20b`, the HIGH-tier deep-reasoning LLM.
- **gemini-2.5-flash**: Google model `gemini-2.5-flash`, the MID/LOW-tier fast tactical LLM.
- **Engagement_Window**: The `[window_start, window_end]` time range during which exploitation is authorized.
- **ChildResult**: The structured result returned by a spawned child agent.
- **VULN_CONFIRMED**: The event/state indicating a finding has been verified.

## Requirements

### Requirement 1: Scope Authority

**User Story:** As a security engineer, I want all outbound activity governed by a single declarative scope policy, so that the system only acts against authorized targets within an approved engagement window.

#### Acceptance Criteria

1. THE ScopePolicy SHALL load engagement scope from `config/scope.yaml`, including `allowed_hosts`, `allowed_cidrs`, `allowed_url_globs`, `denied_url_globs`, `window_start`, `window_end`, and the `authorized` master switch.
2. WHEN the ExploitExecutionEngine receives a plan, THE ExploitExecutionEngine SHALL call `ScopePolicy.assert_allowed` for the plan target before issuing any request.
3. IF a target fails `ScopePolicy.allows`, THEN THE ExploitExecutionEngine SHALL block the request and increment the `blocked_unsafe` telemetry counter.
4. WHEN authorizing an exploit request, THE ExploitExecutionEngine SHALL use ScopePolicy as the only authorization source, replacing the removed `ALLOWED_DOMAINS` list and `_is_allowed_domain` function.
5. WHEN evaluating a target, THE ScopePolicy SHALL apply host-glob matching, CIDR membership, and Engagement_Window checks.
6. WHERE no `scope.yaml` file is provided, THE ScopePolicy SHALL build scope from the single target URL via `from_target`, preserving the existing single-target behavior.
7. THE ScopePolicy SHALL serve as the single authorization authority for the HTTP client, browser orchestrator, ExploitExecutionEngine, and ReconTerminal.
8. WHILE `scope.authorized` is false OR the current time is outside the Engagement_Window, THE Vigilagent system SHALL run recon and passive activity only and SHALL emit a `LOG` event recording the degraded mode.

### Requirement 2: Consolidated Recon Execution

**User Story:** As a system maintainer, I want all recon CLI tools executed through one audited module, so that recon is consistent, sandboxed, and free of duplicated subprocess logic.

#### Acceptance Criteria

1. THE ReconTerminal SHALL provide a single execution path for recon CLI tools, wrapping `ProcessRunner` and `DockerSandbox`.
2. WHEN the ReconTerminal executes a recon command, THE ReconTerminal SHALL pass the command as an argv array and SHALL reject any argument containing shell metacharacters via the existing `tools/recon/guardrails` validation.
3. WHERE Docker is available, THE ReconTerminal SHALL execute the recon tool using the Docker sandbox backend.
4. IF Docker is unavailable, THEN THE ReconTerminal SHALL execute the recon tool using the local `ProcessRunner` backend.
5. WHEN a recon command targets a host or URL, THE ReconTerminal SHALL call `ScopePolicy.assert_allowed` for that target before execution.
6. WHEN a recon command completes, THE ReconTerminal SHALL parse output via the `parsers/recon` registry and write a database toolcall audit record.
7. THE ReconCommandRunner SHALL delegate execution to the ReconTerminal and SHALL retain its existing database toolcall logging without duplicating subprocess logic.
8. THE Recon_Tool_Registry SHALL represent every installed `D:\projects` recon tool and SHALL record each tool's availability via an availability check.
9. WHEN the ReconTerminal begins executing a recon command, THE ReconTerminal SHALL consume one unit from the supplied IterationBudget, and IF the budget is exhausted THEN THE ReconTerminal SHALL abort the execution.

### Requirement 3: Iteration Budgets

**User Story:** As an operator, I want every agent and scan to run under a bounded step budget, so that no agent or scan can run indefinitely.

#### Acceptance Criteria

1. THE IterationBudget SHALL provide thread-safe `consume` and `refund` operations.
2. WHEN `consume` is called while `remaining` is zero, THE IterationBudget SHALL return false and SHALL leave `remaining` at zero.
3. WHEN `child` is called, THE IterationBudget SHALL create a child budget whose consumption is independent of the parent budget.
4. WHEN a child budget is consumed, THE IterationBudget SHALL leave the parent budget's `remaining` count unchanged.
5. THE Vigilagent system SHALL assign per-role budgets from `config/budgets.yaml` with a parent budget of approximately 200, a commander budget of approximately 90, and a child budget of approximately 50.

### Requirement 4: Hierarchical Delegation

**User Story:** As a campaign commander, I want to spawn isolated, budget-capped child agents and receive structured results, so that coordination is directed rather than broadcast-and-hope.

#### Acceptance Criteria

1. THE DelegationManager SHALL spawn child agents with isolated memory, an assigned IterationBudget, and a structured ChildResult return.
2. WHEN the Omega agent initiates an attack campaign, THE Omega agent SHALL call `DelegationManager.spawn` and await a typed ChildResult instead of broadcasting an unaddressed job.
3. WHILE a child agent executes, THE child agent SHALL publish telemetry events (such as `LIVE_ATTACK`, `VULN_CONFIRMED`, and `RECON_PACKET`) to the EventBus.
4. WHEN a parent task is cancelled, THE DelegationManager SHALL propagate cancellation to the child subtree.
5. WHERE a MasterNode and Redis are available, THE DelegationManager SHALL enqueue child tasks onto the worker substrate and await the result.
6. IF Redis is unavailable, THEN THE DelegationManager SHALL run delegation in-process using the local EventBus.
7. WHEN a child task exceeds its configured timeout, THE DelegationManager SHALL return a ChildResult with status `timeout`.
8. THE EventBus SHALL remain the coordination and telemetry plane that drives the frontend WebSocket feed.

### Requirement 5: Unified Knowledge Graph

**User Story:** As Omega, I want one knowledge graph that indexes recon and findings, so that strategy can reason over a single, fast, persisted source of truth.

#### Acceptance Criteria

1. THE UnifiedKnowledgeGraph SHALL replace `graph_engine.py` and `knowledge_graph.py` as the single graph implementation.
2. THE UnifiedKnowledgeGraph SHALL maintain an adjacency index that provides constant-time neighbor lookups.
3. WHEN a `RECON_PACKET` is ingested, THE UnifiedKnowledgeGraph SHALL upsert host, service, endpoint, and parameter nodes using stable identifiers.
4. WHEN a `VULN_CONFIRMED` finding is ingested, THE UnifiedKnowledgeGraph SHALL upsert the corresponding vuln node and its edges.
5. THE UnifiedKnowledgeGraph SHALL serialize to and restore from a JSON-compatible dict via `to_dict` and `from_dict`.
6. WHEN the Omega agent or Planner formulates a plan, THE consuming component SHALL query the UnifiedKnowledgeGraph using `predict_next` and `find_chains`.
7. THE UnifiedKnowledgeGraph SHALL retain CHAIN_RULES-guided `find_chains` depth-first search and weight pruning.

### Requirement 6: Genuine Adaptive Intelligence (No Fakes)

**User Story:** As a stakeholder, I want every "intelligent" feature backed by real computation, so that the system never claims a capability it does not have.

#### Acceptance Criteria

1. THE Beta agent SHALL select payloads using an epsilon-greedy PayloadBandit keyed by `(vuln_class, vector, payload_family)`.
2. WHEN the MultiLayerVerifier returns a verification result, THE Beta agent SHALL update the PayloadBandit with the real success outcome.
3. THE PayloadDeliveryEngine SHALL deliver payloads across the query, json_body, form_body, header, cookie, and path HTTP vectors.
4. WHEN the Omega agent formulates strategy, THE Omega agent SHALL obtain the strategy choice and module ordering from a gpt-oss-20b reasoning call that consumes the UnifiedKnowledgeGraph summary and recon evidence, replacing the `random.choices` "Nash" computation.
5. THE Omega agent SHALL derive hypotheses from recon and graph evidence rather than from a hardcoded list.
6. IF the LLM circuit breaker is open, THEN THE Omega agent SHALL fall back to GI5 deterministic ranking.
7. WHEN the Planner performs pre-planning, THE Planner SHALL query `SkillLibrary.get_recommendations` and the UnifiedKnowledgeGraph.
8. THE LearningIntegrator SHALL provide a read path that delivers recommendations from the learning store out to agents.

### Requirement 7: Real Recovery & Self-Awareness

**User Story:** As an operator, I want recovery and strategy adaptation to take real corrective action, so that the system recovers from auth failures and adapts instead of returning canned responses.

#### Acceptance Criteria

1. THE RecoveryEngine SHALL merge `self_healing_engine.py` and `strategy_adapter.py` into one module that retains the circuit breaker and restart callbacks.
2. WHEN an authentication error occurs (HTTP 401, HTTP 403, or session expiry), THE RecoveryEngine SHALL retrieve a fresh credential from the CredentialVault and re-authenticate, replacing the stub that returned false.
3. WHEN selecting an adaptation, THE RecoveryEngine SHALL choose among `RETRY`, `SWITCH_VECTOR`, `DELEGATE`, `REDUCE_RATE`, and `ABORT` based on error class and diminishing returns, replacing the constant `SWITCH_TECHNIQUE` response.
4. WHEN a recovery resolves an error, THE RecoveryEngine SHALL write the resulting pattern to the SkillLibrary so the Planner can consume it.

### Requirement 8: Credential Vault

**User Story:** As an attacker agent, I want captured credentials stored securely and reused, so that authenticated and privilege-escalation tests use real tokens instead of a mock.

#### Acceptance Criteria

1. THE CredentialVault SHALL store each credential's secret encrypted using Fernet, reusing the forensic_collector encryption pattern.
2. THE CredentialVault SHALL assign each credential a stable `cred_id` derived from `sha256(target|service|principal)`.
3. WHEN a credential whose `cred_id` already exists is stored, THE CredentialVault SHALL retain a single entry for that `cred_id`.
4. WHEN the Doppelganger module performs an identity test, THE Doppelganger module SHALL obtain its tokens from the CredentialVault.
5. THE Vigilagent system SHALL use CredentialVault entries as the only source of privilege-escalation test identities, replacing the removed `MOCK_USER_B_TOKEN`.

### Requirement 9: Evidence-Based Detection

**User Story:** As a security analyst, I want findings confirmed by differential evidence, so that confirmations are trustworthy and not based on naive string matching.

#### Acceptance Criteria

1. WHEN a `modules/tech/*` or `modules/logic/*` module evaluates a response, THE module SHALL use the MultiLayerVerifier and differential analysis instead of substring matching.
2. WHEN comparing a baseline request against an injected request, THE MultiLayerVerifier SHALL evaluate status divergence, length delta, Jaccard similarity below 0.85, new sensitive keywords, and JSON structural difference.
3. WHEN marking a finding as `VULN_CONFIRMED`, THE module SHALL require at least two independent verification signals to agree.

### Requirement 10: Context Compression

**User Story:** As an agent, I want my working context compressed intelligently, so that long engagements do not overflow memory or lose critical findings.

#### Acceptance Criteria

1. WHEN a transcript exceeds the configured token budget, THE ContextCompressor SHALL summarize the middle segment using gemini-2.5-flash.
2. WHEN compressing a transcript, THE ContextCompressor SHALL preserve the system prompt, every `VULN_CONFIRMED` line, and the last N turns.
3. THE MemoryProvider SHALL replace the 1000-entry hard cap with compressor-backed eviction.
4. THE MemoryProvider SHALL preserve the existing `memory_store` API and the cosine-similarity semantic recall.

### Requirement 11: Checkpoint and Resume

**User Story:** As an operator, I want scans to checkpoint and resume, so that an interrupted engagement can continue without restarting from zero.

#### Acceptance Criteria

1. WHEN a scan reaches a phase boundary, THE StateManager SHALL persist a Checkpoint containing the phase, completed endpoints, pending endpoints, findings, graph snapshot, and budgets.
2. WHEN a scan is resumed from a Checkpoint, THE StateManager SHALL restore the phase, endpoints, findings, graph snapshot, and budgets from that Checkpoint.

### Requirement 12: Two-LLM Enforcement and Cortex Cleanup

**User Story:** As an architect, I want exactly two LLMs and a clean cortex, so that the system has a predictable, honest model surface with no dead third-model code paths.

#### Acceptance Criteria

1. THE Vigilagent system SHALL reach exactly two network LLM endpoints: OpenRouter `openai/gpt-oss-20b` and Google `gemini-2.5-flash`.
2. WHEN routing a HIGH-tier task (strategy, arbitration, remediation, or reporting), THE LLMRouter SHALL route the task to OpenRouter `openai/gpt-oss-20b`.
3. WHEN routing a MID-tier or LOW-tier task (payloads, validation, narrative, or embeddings), THE LLMRouter SHALL route the task to `gemini-2.5-flash`.
4. THE CortexEngine SHALL route the `_call_ollama` and `_call_nvidia_*` aliases onto `_call_gemini` and SHALL remove the dead third-model branches and the misleading Ollama header comment.
5. THE GI5 engine SHALL remain a non-LLM deterministic pre-pass and fallback.

### Requirement 13: Branding (Vulagent → Vigilagent)

**User Story:** As a product owner, I want the system rebranded to Vigilagent without breaking persistence, the cluster, or the frontend, so that the rename is user-facing only.

#### Acceptance Criteria

1. THE Vigilagent system SHALL present user-facing strings (banners, FastAPI `title`, log prefixes, and report headers) as "Vigilagent".
2. WHEN reading configuration, THE config loader SHALL read `VIGILAGENT_*` environment variables and SHALL fall back to the corresponding `VULAGENT_*` value when the `VIGILAGENT_*` variable is unset.
3. THE Vigilagent system SHALL preserve the following stable identifiers unchanged: Supabase table names, the Redis channel `xytherion_events` and queue keys, agent `source` strings, and scan-id prefixes (such as `HIVE-V5-...`).
4. THE Vigilagent system SHALL keep every existing REST route and WebSocket message shape byte-compatible, and any new endpoint or message type SHALL be additive only.

### Requirement 14: System-Wide Correctness Invariants

**User Story:** As a verifier, I want the system's correctness properties expressed as testable invariants, so that they can be checked at runtime and validated by light property tests.

#### Acceptance Criteria

1. WHEN any outbound HTTP request, browser navigation, or host-targeting recon command is about to execute, THE Vigilagent system SHALL confirm the target passes `ScopePolicy.allows` before execution (scope containment).
2. THE Vigilagent system SHALL reach no network LLM endpoint other than OpenRouter `openai/gpt-oss-20b` and Google `gemini-2.5-flash` (two-LLM exclusivity).
3. THE Vigilagent system SHALL ensure a child agent never exceeds its assigned budget and never consumes the parent's budget (budget boundedness).
4. THE Vigilagent system SHALL ensure the only CLI execution path is the ReconTerminal and that it runs only binaries in the recon allowlist, with no code path shelling out an exploitation tool against a target (no exploitation shell).
5. THE Vigilagent system SHALL keep every existing REST route and WebSocket message type at its current shape, adding new messages only additively (frontend contract invariance).
6. WHEN a recon command is executed, THE Vigilagent system SHALL pass it as an argv array and SHALL reject shell metacharacters, so no recon command reaches the operating system as a shell string (no shell strings).
7. WHEN a finding is marked `VULN_CONFIRMED`, THE Vigilagent system SHALL require at least two independent verification signals to agree and SHALL never confirm on a single string match (evidence-based confirmation).
8. WHILE `scope.authorized` is false OR the current time is outside the Engagement_Window, THE Vigilagent system SHALL run no exploitation and SHALL degrade to recon/passive only (authorization gate).
9. WHEN a credential, graph node, or finding is stored, THE Vigilagent system SHALL store it only once using stable hashed identifiers (idempotent dedup).
10. THE Vigilagent system SHALL back every shipped "intelligent" feature with real computation: a real PayloadBandit for Beta, a real LLM decision for Omega strategy, real re-authentication for auth recovery, and learning/skills read back by the Planner (no fake intelligence).
