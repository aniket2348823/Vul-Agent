# Alpha Agent Singularity V6 Implementation Plan

Deep implementation blueprint for upgrading `backend/agents/alpha.py` from a shallow HTTP path prober into a phased, scoped, evidence-preserving reconnaissance engine.

This plan is grounded in the local codebase and the cloned repos under `D:\projects`. It assumes Alpha is used only for authorized targets and that active recon remains gated by explicit scope, scan mode, rate limits, and approval policy.

## 1. Current State

### Current Alpha

File: `backend/agents/alpha.py`

Alpha currently:

- Subscribes to `TARGET_ACQUIRED` and `JOB_ASSIGNED`.
- Runs `aiohttp` probes against a fixed list of common paths.
- Emits minimal `RECON_PACKET`, `LIVE_ATTACK`, and simple `VULN_CANDIDATE` events.
- Uses `CortexEngine.classify_target()` to decide whether something looks API-like.
- Delegates jobs to Sigma after lightweight classification.
- Stores only visited URL state in `ctx.baseline_cache`.

This is useful as a dashboard heartbeat, but it is not a recon engine. It lacks passive-first workflow, durable tool outputs, rich entity modeling, deduplication, parser normalization, endpoint scoring, OOB monitoring, browser-network capture, and phase barriers.

### Existing Platform Pieces We Should Reuse

The repo already contains several building blocks that are exactly right for Alpha V6:

- `backend/core/hive.py`
  - EventBus, scan isolation, DLQ, `AGENT_STATUS`, `RECON_PACKET`, `VULN_CANDIDATE`, `CONTROL_SIGNAL`.
- `backend/core/tool_registry.py`
  - Central `ToolDefinition`, strict JSON schema conversion, tool metadata.
- `backend/core/tool_executor.py`
  - Durable tool lifecycle: create running toolcall, finish/fail, approval checks, output limiting, telemetry spans.
- `backend/core/default_tools.py`
  - Existing examples for registered tools.
- `backend/core/scope.py`
  - Basic `ScopePolicy`; must be expanded for wildcard domains, CIDR, suffix blocks, gov/mil guard, and cloud/CDN safe handling.
- `backend/core/knowledge_graph.py`
  - In-memory typed KG with nodes for domain, host, service, URL, endpoint, parameter, token, cookie, secret, vuln, evidence, attack path.
- `backend/core/schema.sql`
  - Existing tables for toolcalls, approvals, scope rules, HTTP exchanges, KG nodes/edges, vulnerabilities, memory.
- `backend/core/database.py`
  - Supabase helpers for vulnerabilities, toolcalls, approvals, HTTP exchanges.
- `backend/core/cluster/pinchtab.py`
  - Compatibility wrapper now prefers the real PinchTab control plane and preserves Playwright as a fallback path.
- `backend/modules/tech/http_client.py`
  - Scoped request recording foundation.
- `backend/schemas/findings.py`
  - Evidence/Finding/AttackPath models suitable for final output and report integration.

### Key Architectural Decision

Do not make the LLM directly run shell commands from the huge Alpha prompt.

Instead:

`AlphaAgent -> ReconPhaseOrchestrator -> Registered Tool Wrappers -> Parsers -> ReconStore/KG -> EventBus`

The master prompt becomes Alpha's reasoning policy, but actual execution is deterministic, scoped, typed, and phase-gated.

## 2. Local Repo Capability Inventory

### Passive OSINT And Asset Discovery

| Repo | Capability | Alpha V6 Role |
| --- | --- | --- |
| `D:\projects\spiderfoot` | OSINT automation with 200+ modules, CLI/UI, correlation rules, CSV/JSON/GEXF export, SQLite backend, TOR option, can call tools such as DNSTwist/WhatWeb/Nmap. | Phase 1 OSINT aggregator. Extract emails, people, netblocks, cert data, breach/paste references, related domains, GitHub mentions, technology hints. |
| `D:\projects\subfinder` | Fast passive subdomain enumeration from curated passive sources; JSON/file/stdout output; wildcard elimination/resolution support. | Phase 1 passive subdomain source. Store per-source evidence and confidence. |
| `D:\projects\amass` | OWASP attack surface mapping and external asset discovery with passive and active modes. | Phase 1 passive enumeration first; later optional standard/aggressive active expansion. |
| `D:\projects\gau` | Historical URL collection from OTX, Wayback, Common Crawl, URLScan. | Phase 1 historical URL mining, JS path extraction, parameter extraction, ghost endpoint inventory. |
| `D:\projects\waybackurls` | Historical URLs from Wayback. | Phase 1 secondary historical URL source. |
| `D:\projects\cloudlist` | Multi-cloud asset listing across providers/services; host/IP/service filters; stdout pipeline support. | Phase 1 cloud asset intake when cloud credentials/config are present. Do not brute-force cloud assets as passive unless mode permits provider existence checks. |

### DNS, Infra, Ports, TLS

| Repo | Capability | Alpha V6 Role |
| --- | --- | --- |
| `D:\projects\dnsx` | A/AAAA/CNAME/PTR/NS/MX/TXT/SRV/SOA queries, brute force, custom resolvers including TCP/UDP/DOH/DOT, wildcard handling, JSON output, ASN/CDN detection. | Phase 2 DNS validation, host/IP mapping, MX/TXT intel, dangling CNAME candidates, ASN/CDN tags. |
| `D:\projects\shuffledns` | MassDNS wrapper for subdomain brute force and resolution with wildcard handling. | Phase 2 optional DNS brute forcing in `STANDARD`/`AGGRESSIVE`, never `PASSIVE_ONLY`. |
| `D:\projects\naabu` | Fast SYN/CONNECT/UDP port scan, DNS/IP/CIDR/ASN input, passive Shodan InternetDB option, CDN/WAF exclusion, Nmap integration, service version detection, JSON output. | Phase 2 port inventory and service hints. Use conservative rates and CDN exclusion by default. |
| `D:\projects\nmap` | Service/version detection, NSE scripts, XML output. | Phase 2 deep service fingerprinting after Naabu, limited to discovered open ports and scope. |
| `D:\projects\tlsx` | TLS data collection: TLS probes, fallback, cipher/SNI/TLS selection, JARM/JA3, misconfigurations, ASN/CIDR/IP/HOST/URL input, TXT/JSON output. | Phase 2 TLS SAN expansion, expiry/self-signed/mismatch/cipher/TLS-version findings. |

### HTTP, Crawling, JS, Fuzzing

| Repo | Capability | Alpha V6 Role |
| --- | --- | --- |
| `D:\projects\httpx` | Multi-probe HTTP toolkit: status/title/content length/server/CNAME/TLS cert/CSP/websocket/response time/fav hash/body/header hashes/redirect chain/ASN/CDN/WAF, tech detection, screenshots, headless JS, JSONL output, scoped allow/deny. | Phase 3 liveness, fingerprinting, security-header audit, tech stack, screenshot bootstrap, WAF/CDN tagging. |
| `D:\projects\katana` | Standard/headless crawling, JavaScript parsing/crawling, automatic form filling, scope control, JSON output. | Phase 3 crawling and endpoint extraction. Prefer scoped/headless mode only after live hosts are known. |
| `D:\projects\hakrawler` | Fast Go crawler for URLs, JS file locations, forms, subdomain crawling. | Phase 3 crawler diversity and cross-check. |
| `D:\projects\LinkFinder` | JS endpoint/parameter extraction from URLs/files/folders/Burp exports; CLI/HTML output; optional cookies/domain mode. | Phase 3 JS hidden route extraction. |
| `D:\projects\SecretFinder` | JS sensitive data extraction: API keys, access tokens, auth, JWT, secrets via regex; CLI/HTML output. | Phase 3 secret candidate detection with mandatory redaction and evidence preservation. |
| `D:\projects\feroxbuster` | Fast recursive forced browsing/content discovery; extensions, headers, data bodies, auto-tune, recursive collection. | Phase 4 content discovery with target-specific wordlists, conservative defaults. |
| `D:\projects\dirsearch` | Web path discovery with recursion, extensions, session/config support. | Phase 4 secondary path discovery and parser cross-check. |
| `D:\projects\ffuf` | Fast web fuzzer: content discovery, vhost discovery, parameter fuzzing, POST data fuzzing, recursion time limits, filters. | Phase 4 parameter discovery and vhost discovery with response-baseline filtering. |
| `D:\projects\gobuster` | Directory/file, DNS, virtual host, S3, GCS, TFTP, fuzzing modes; concurrency and custom wordlists. | Phase 4 vhost/cloud-storage discovery where scope/mode permits. |
| `D:\projects\SecLists` | Security tester wordlists: usernames, passwords, URLs, sensitive data patterns, fuzzing payloads, web shells, etc. | Wordlist source. Alpha should use discovery/API lists only, not password lists, unless a later agent has approval. |
| `D:\projects\wordlists` | Assetnote/generated web content and technology wordlists. | High-signal target-specific and API route wordlist source. |

### API, GraphQL, Validation, Visual Evidence

| Repo | Capability | Alpha V6 Role |
| --- | --- | --- |
| `D:\projects\kiterunner` | API route discovery using Swagger-derived schemas; sends realistic methods, headers, parameters and values; supports scan/brute/replay and Assetnote wordlists. | Phase 5 API route discovery after API candidates are known. |
| `D:\projects\inql` | GraphQL analysis: query/mutation/subscription generation, points-of-interest, circular reference detection, batch queries, engine fingerprinting, schema bruteforcing, GraphiQL/Voyager integration. | Phase 5 GraphQL schema extraction and risk candidates. Avoid batch attack mode in Alpha; only detect support and pass to Omega. |
| `D:\projects\graphql-voyager` | Interactive GraphQL schema graph visualization with root selection, deprecation/Relay display options. | Phase 5/8 visualization artifact for GraphQL schemas. |
| `D:\projects\gowitness` | Chrome-headless screenshots; scan URL/CIDR/Nmap/Nessus inputs; capture request logs, console logs, headers, cookies; outputs SQLite/JSONL/CSV and web viewer. | Phase 6 visual evidence and browser-side metadata capture. |
| `D:\projects\aquatone` | Visual inspection over many hosts; transforms host/IP/domain input to URLs, screenshots, headers/bodies, similarity-clustered HTML report. | Phase 6 optional visual report, especially for large live-host sets. |
| `D:\projects\nuclei` | High-performance YAML-template scanner, multi-protocol, request clustering, vulnerability/misconfiguration/exposure/default-login/CVE/takeover templates. | Phase 7 template-driven validation. Run only on scoped live URLs with severity and rate limits. |
| `D:\projects\interactsh` | OOB interaction client/server for DNS/HTTP(S)/SMTP(S)/LDAP, encrypted zero-logging, self-hosted options, dynamic responses. | Scan-wide OOB monitor for SSRF/blind callbacks and nuclei integration. |

### Graph, Intelligence, Automation, Browser Control

| Repo | Capability | Alpha V6 Role |
| --- | --- | --- |
| `D:\projects\neo4j` | Mature graph DB with Cypher and ACID transactions. | Persistent attack-surface graph backend, optional alongside existing `kg_nodes/kg_edges`. |
| `D:\projects\opencti` | STIX2-based threat intelligence platform with GraphQL API, relationships, confidence, first/last seen, connectors. | Later CTI enrichment/export. For Alpha V6, map technologies/CVEs/observables into exportable STIX-like records. |
| `D:\projects\PayloadsAllTheThings` | Payloads, bypasses, exploitation notes. | Do not execute in Alpha. Use only as taxonomy/context for Sigma/Omega recommendations. |
| `D:\projects\playwright` | Browser automation/testing across Chromium/Firefox/WebKit with isolation, auto-waiting, locators, auth state reuse. | Fallback if PinchTab is unavailable. |
| `D:\projects\puppeteer` | Chrome DevTools automation and MCP support. | Optional fallback for Chrome-only capture. |
| `D:\projects\selenium` | Cross-browser automation ecosystem. | Compatibility fallback only. |
| `D:\projects\graphify` | Code/docs/media knowledge graph generation for querying projects. | Use for codebase analysis and local repo graphing, not target recon. |
| `D:\projects\pentagi` | Sandboxed automated security testing runtime, durable flow/task/tool-call logs, graphiti memory, telemetry, message compaction. | Already partially ported. Continue borrowing executor, lifecycle, telemetry, compaction, sandbox concepts. |
| `D:\projects\cai` | Agent runtime guardrails, strict schemas, parallel tool execution, session recording, cost tracking, message repair. | Already partially ported. Continue strict schemas and guardrails around tool outputs. |
| `D:\projects\Decepticon` | OPPLAN/RoE, Docker sandbox, evidence/finding/attack path schemas, typed KG, importers for nmap/nuclei/httpx/dnsx/katana/ffuf, JWT/OAuth/cookie/GraphQL tools. | Use importer and graph semantics as Alpha V6's normalization model. |

## 3. PinchTab Capability Extraction

Canonical repo: `D:\projects\pinchtab_core`

PinchTab is not just a browser wrapper. It is a local-first Chrome control plane with a Go server, bridge runtime, profiles, instances, tabs, HTTP API, dashboard, MCP tools, network capture, scheduler, and security gates.

### PinchTab Capabilities Relevant To Alpha

- Server/control plane on port `9867` by default.
- Managed profiles with persistent cookies, local storage, cache, extensions, saved auth state.
- Managed instances, each with one bridge process, one Chrome process, optional profile, many tabs.
- Tab-scoped navigation and browser state.
- Accessibility snapshots with stable element refs like `e0`, `e1`; token-efficient compared to screenshots.
- Text extraction with compact/raw modes.
- Actions: click, dblclick, type, fill, press, hover, focus, select, scroll, drag, check/uncheck, keyboard events.
- Waits: selector, text, URL, load/networkidle, function, fixed sleep.
- Screenshots and PDFs.
- Network logs, stream/export, HAR/NDJSON, detail retrieval with optional response body.
- Console logs and browser errors.
- Cookies read/write.
- Downloads/uploads/clipboard behind security gates.
- Solver framework for browser challenges.
- Activity API and scheduler tasks/batch tasks.
- MCP tool surface with 34 tools: navigate, snapshot, screenshot, get_text, interactions, keyboard, eval, pdf, find, tabs, cookies, waits, network, dialog.
- Security model: local-first, loopback bind, sensitive endpoint families disabled by default, IDPI allowlist for browsing, non-default gates for evaluate/download/upload/clipboard/attach/screencast.

### PinchTab Integration Model For Alpha

Replace `backend/core/cluster/pinchtab.py` as the primary browser runtime with an HTTP client adapter:

- `backend/integrations/pinchtab_client.py`
  - `health()`
  - `ensure_profile(scan_id, target_domain, mode)`
  - `start_instance(profile_id, headless=True)`
  - `open_tab(instance_id, url)`
  - `snapshot(tab_id, compact=True, interactive=True, max_tokens=1200)`
  - `text(tab_id, max_chars=20000)`
  - `screenshot(tab_id, output_path)`
  - `network(tab_id, filters)`
  - `network_detail(request_id, body=False)`
  - `export_network(tab_id, format="har|ndjson", redact=True)`
  - `cookies(tab_id)`
  - `console(tab_id)`
  - `errors(tab_id)`
  - `close_tab(tab_id)`
  - `stop_instance(instance_id)`

Use cases:

- Phase 3: browser-backed liveness and route extraction for SPAs.
- Phase 3C: discover JS-loaded API calls via network capture.
- Phase 5A: observe OpenAPI/Swagger UI runtime requests.
- Phase 5C: inspect GraphQL clients and schemas loaded in browser apps.
- Phase 6: screenshots, console error evidence, HAR/NDJSON artifacts.
- Chi baseline: DOM/text/network behavior baseline before exploit agents run.

Security controls:

- Keep PinchTab bound to loopback.
- Do not enable `allowEvaluate` for Alpha by default.
- Do not enable download/upload/clipboard for Alpha by default.
- Use IDPI domain allowlist equal to scan scope.
- Treat snapshot/text/network content as untrusted data. Do not feed raw page text into LLM prompts without guard-layer wrapping.

## 4. Target Alpha V6 Architecture

### Runtime Flow

```text
TARGET_ACQUIRED
  -> AlphaAgent.handle_target_acquired()
  -> ScopeCompiler.parse_target()
  -> ReconRun.init(scan_id, scope, mode, artifact_dir)
  -> PhaseScheduler.run_all()
      Phase 0: init/scope/OOB/profile
      Phase 1: passive OSINT
      Phase 2: DNS/infra/TLS/ports
      Phase 3: HTTP/browser/crawl/JS
      Phase 4: directory/route/vhost discovery
      Phase 5: API and GraphQL recon
      Phase 6: visual docs
      Phase 7: template validation
      Phase 8: correlation/scoring/graph export
      Phase 9: event finalization
  -> RECON_COMPLETE
```

### New Modules

Create:

- `backend/agents/alpha/`
  - `__init__.py`
  - `agent.py` or migrate current `backend/agents/alpha.py` to a package
  - `prompt.py`
  - `models.py`
  - `scope.py`
  - `run_state.py`
  - `phases.py`
  - `scheduler.py`
  - `scoring.py`
  - `events.py`
  - `normalizers.py`
  - `dedupe.py`
  - `wordlists.py`
  - `artifacts.py`
- `backend/tools/recon/`
  - `base.py`
  - `external.py`
  - `spiderfoot.py`
  - `subfinder.py`
  - `amass.py`
  - `gau.py`
  - `waybackurls.py`
  - `cloudlist.py`
  - `dnsx.py`
  - `shuffledns.py`
  - `naabu.py`
  - `nmap.py`
  - `tlsx.py`
  - `httpx.py`
  - `katana.py`
  - `hakrawler.py`
  - `linkfinder.py`
  - `secretfinder.py`
  - `feroxbuster.py`
  - `dirsearch.py`
  - `ffuf.py`
  - `gobuster.py`
  - `kiterunner.py`
  - `inql.py`
  - `nuclei.py`
  - `gowitness.py`
  - `aquatone.py`
  - `interactsh.py`
  - `pinchtab.py`
- `backend/parsers/recon/`
  - one parser per external tool output format
- `backend/integrations/`
  - `pinchtab_client.py`
  - `neo4j_client.py`
  - `opencti_export.py`

### Do Not Shell-String Everything

Each tool wrapper should:

- Build argv as a list, not concatenated shell.
- Run through `ToolExecutor`.
- Declare phase, scan mode compatibility, active/passive type, rate profile, expected output files, parser.
- Store raw stdout/stderr and file outputs under `data/scans/{scan_id}/raw/{tool}/`.
- Return typed `ToolRunResult`.
- Gracefully degrade when binary/repo/dependencies are unavailable.

## 5. Core Data Models

Add Pydantic models in `backend/agents/alpha/models.py`:

- `ScanMode`: `PASSIVE_ONLY`, `STANDARD`, `AGGRESSIVE`.
- `ReconScope`: base domain, allowed domains, allowed CIDRs, denied domains, denied CIDRs, denied URL globs, cloud/provider boundaries, max RPS, max depth.
- `ReconEntity`: base model with `id`, `scan_id`, `source_tools`, `confidence`, `first_seen`, `last_seen`.
- `SubdomainFinding`: fqdn, sources, confidence, resolved, cname, takeover_candidate.
- `IPAddressFinding`: ip, version, asn, cidr, cloud_provider, hostnames.
- `PortFinding`: host, ip, port, protocol, service, version, banner, tls.
- `TLSFinding`: host, san, cn, issuer, expiry, self_signed, expired, mismatch, versions, ciphers, ja3, jarm.
- `HTTPServiceFinding`: url, status, title, server, content_type, content_length, response_time, hashes, tech, waf, cdn, redirect_chain.
- `EndpointFinding`: url, method, path, normalized_path, status, parameters, auth_required, endpoint_type, risk_class, source.
- `ParameterFinding`: name, location, value_type, examples, endpoints.
- `SecretFinding`: secret_type, redacted_value, source_url, source_file, line, confidence.
- `SchemaFinding`: schema_type, url, spec_path, endpoints, auth_schemes, parameters.
- `GraphQLFinding`: endpoint, introspection_enabled, types, queries, mutations, sensitive_fields, deprecated_fields, batch_supported.
- `CloudAssetFinding`: provider, name, asset_type, url, public_access_state, source.
- `VisualArtifact`: url, screenshot_path, har_path, console_path, pinchtab_tab_id.
- `ReconPacket`: event payload with complete metadata.
- `ReconCompletePayload`: final event payload.

## 6. Phase Plan

### Phase 0: Initialization And Scope Validation

Implementation:

- Parse input URL/domain/CIDR.
- Compile `ReconScope`.
- Add hard stop for:
  - Empty scope.
  - Public suffix only.
  - `.gov` or `.mil` unless `explicit_authorization=True`.
  - Out-of-scope host/IP/CIDR.
- Derive scan mode:
  - `PASSIVE_ONLY`: OSINT/historical only; no target packets.
  - `STANDARD`: conservative active recon after passive.
  - `AGGRESSIVE`: deeper brute force/fuzzing with stricter operator confirmation.
- Create artifact dirs:
  - `data/scans/{scan_id}/raw`
  - `data/scans/{scan_id}/normalized`
  - `data/scans/{scan_id}/screenshots`
  - `data/scans/{scan_id}/browser`
  - `data/scans/{scan_id}/exports`
- Initialize run state:
  - `seen_domains`, `seen_hosts`, `seen_urls`, `seen_endpoints`, `seen_vuln_candidates`, `tool_failures`.
- Initialize Interactsh if available and active mode permits.
- Initialize PinchTab profile/instance only when Phase 3 needs browser work.
- Emit `AGENT_STATUS`.

Deliverables:

- `ScopeCompiler`
- `ReconRunState`
- `ArtifactStore`
- `OOBMonitor`

### Phase 1: Passive Intelligence

Tools:

- SpiderFoot
- Subfinder
- Amass passive
- crt.sh direct fetch or replacement parser
- gau
- waybackurls
- Cloudlist if provider configs exist

Outputs:

- Subdomains with source counts.
- Emails, people, netblocks, related domains.
- Historical URLs, paths, JS files, parameters.
- Cloud assets from configured providers.
- Risk-classified historical paths.

Important implementation notes:

- `PASSIVE_ONLY` stops after Phase 1/8/9.
- Do not perform bucket existence HTTP checks in strict passive mode.
- Historical URL parsing should use `urllib.parse`, not regex-only.
- Store source provenance per entity.

Events:

- `RECON_PACKET` only for high-value historical endpoints with score >= 50 and no active confirmation required.
- `AGENT_STATUS` phase progress.

### Phase 2: DNS, Infrastructure, Ports, TLS

Tools:

- dnsx
- shuffledns only in `STANDARD`/`AGGRESSIVE`
- naabu only after DNS resolution
- nmap only on ports discovered by naabu
- tlsx on HTTPS candidates

Outputs:

- Host-to-IP and IP-to-host mapping.
- CNAME/MX/TXT/PTR intelligence.
- Dangling CNAME candidates.
- Open ports and service versions.
- TLS certs, SAN expansion, weak TLS candidates.

Important implementation notes:

- Feed SAN-discovered domains back into DNS validation if in scope.
- Use cooldown/rate control from Zeta `CONTROL_SIGNAL`.
- Use CDN/WAF tagging to avoid scanning CDN IPs broadly.
- Emit immediate `VULN_CANDIDATE` only for non-invasive recon candidates such as dangling CNAME, exposed Docker API signature, unauthenticated service evidence from safe banner checks.

### Phase 3: HTTP Probing, Crawling, JS, Browser Intelligence

Tools:

- httpx
- Katana
- Hakrawler
- PinchTab
- LinkFinder
- SecretFinder

Outputs:

- Live URLs with status/title/server/tech/hash/CDN/WAF.
- HTTP security header gaps.
- Crawled endpoints/forms/JS files.
- Browser network API calls from PinchTab HAR/NDJSON.
- JS hidden endpoints and secret candidates.

PinchTab-specific workflow:

1. Open each high-value live URL in a scoped PinchTab tab.
2. Wait for `networkidle` or capped timeout.
3. Capture compact interactive snapshot.
4. Capture text.
5. Export network log redacted.
6. Pull console/errors.
7. Screenshot only high-value pages or if visual docs are enabled.
8. Normalize XHR/fetch URLs into `EndpointFinding`.

Important implementation notes:

- Do not use PinchTab `evaluate` by default.
- Redact cookies/auth headers in browser network exports.
- Use browser network capture to find SPA API calls that Katana misses.
- SecretFinder values must be redacted before events; raw artifact can be encrypted/local-only if needed.

### Phase 4: Directory, Route, Parameter, Vhost Discovery

Tools:

- WordlistBuilder with SecLists + Assetnote + target vocabulary.
- Feroxbuster
- Dirsearch
- ffuf
- Gobuster vhost

Outputs:

- Directories/files/routes.
- Parameters and likely value types.
- Virtual hosts with response-diff evidence.

Important implementation notes:

- Build wordlists from target vocabulary first.
- Generic wordlists are additive, not primary.
- Establish 404/error baselines per host before fuzzing.
- Use per-job max time and recursion depth caps.
- `PASSIVE_ONLY` skips all of Phase 4.
- `STANDARD` limits depth and threads.
- `AGGRESSIVE` enables deeper recursion only if scope has explicit permission.

### Phase 5: API-Specific Recon

Tools:

- OpenAPI/Swagger path prober.
- Kiterunner.
- InQL.
- GraphQL Voyager artifact generator.
- PinchTab network capture for Swagger UI and GraphQL clients.

Outputs:

- OpenAPI specs parsed into endpoint/parameter/schema/auth models.
- Postman/Insomnia/Bruno collection candidates.
- Kiterunner API route matches.
- GraphQL schema/queries/mutations/sensitive fields/deprecated fields.

Important implementation notes:

- Finding a schema is one of Alpha's highest-value outputs.
- Store original schema file plus normalized endpoint inventory.
- GraphQL introspection enabled is a `VULN_CANDIDATE` only if the endpoint looks production or public; otherwise classify as high-value recon finding.
- Alpha detects batch query support but does not run DoS-style tests.

### Phase 6: Visual Recon And Documentation

Tools:

- PinchTab
- gowitness
- aquatone

Outputs:

- Screenshots of admin/login/API-doc/error pages.
- HAR/NDJSON network logs.
- Console and browser error artifacts.
- Aquatone/gowitness reports for large surfaces.

Decision:

- Prefer PinchTab for integrated per-scan browser evidence and network capture.
- Use gowitness/aquatone as batch visual docs when live host count is high or report needs clustering.

### Phase 7: Template-Driven Validation

Tools:

- nuclei
- interactsh monitor

Outputs:

- Misconfig/exposure/CVE/default-login/takeover findings.
- OOB callbacks correlated to template/tool/endpoint.

Important implementation notes:

- Use severity filter and rate limit.
- Run templates matched to detected technologies first.
- Store raw nuclei JSONL.
- Immediate `VULN_CANDIDATE` for high/critical.
- No exploit chain execution in Alpha.

### Phase 8: Correlation, Graph, Scoring

Implementation:

- Merge all normalized entities.
- Deduplicate by stable IDs:
  - subdomain: lowercase FQDN.
  - IP: normalized IP.
  - endpoint: scheme + host + normalized path + method.
  - parameter: endpoint + location + name.
  - secret: source + secret type + hash of raw value.
- Upsert KG nodes/edges.
- Export to:
  - `kg_nodes/kg_edges`
  - Neo4j if configured
  - Maltego-compatible CSV/GraphML
  - GraphQL Voyager artifacts for GraphQL schemas
- Score endpoints.

Endpoint scoring:

- Base:
  - admin 90
  - auth 85
  - API with ID param 80
  - payment 80
  - upload 75
  - data endpoint 70
  - GraphQL 70
  - standard API 50
  - static 10
- Modifiers:
  - +20 no auth observed
  - +15 OpenAPI schema available
  - +15 historical path resurfaced
  - +10 numeric/UUID ID param
  - +10 detected tech with known CVE
  - +5 PUT/DELETE accepted from safe OPTIONS/httpx data
  - +5 secret/source exposure nearby
  - -10 CDN/WAF fronted

### Phase 9: Structured Output And Event Emission

Emit:

- `RECON_COMPLETE`
- `RECON_PACKET` for every endpoint with score >= 50.
- `VULN_CANDIDATE` immediately when found during phases.
- `AGENT_STATUS` at phase boundaries.
- `SCOPE_VIOLATION` should be added to `EventType`.

Current `EventType` lacks:

- `RECON_COMPLETE`
- `SCHEMA_DISCOVERED`
- `MOBILE_ENDPOINT_DISCOVERED`
- `SCOPE_VIOLATION`

Add these to `backend/core/hive.py`, then update dashboard consumers.

## 7. Tool Wrapper Contract

Every recon tool wrapper should implement:

```python
class ReconTool:
    name: str
    phase: int
    passive: bool
    allowed_modes: set[ScanMode]
    requires_network: bool
    requires_credentials: bool = False
    default_timeout_s: int

    async def available(self) -> ToolAvailability: ...
    async def build(self, run: ReconRunState, inputs: ToolInputs) -> ToolCommand: ...
    async def parse(self, result: ToolExecutionResult, artifact_store: ArtifactStore) -> NormalizedFindings: ...
```

`ToolCommand` should contain:

- `argv: list[str]`
- `cwd`
- `env`
- `timeout_s`
- `stdout_path`
- `stderr_path`
- `output_paths`
- `rate_profile`

No tool should hand raw shell text to `sandbox_run` unless the command is a controlled, pre-rendered adapter script.

## 8. Storage Plan

Keep using existing tables, but add recon-specific durable tables:

```sql
CREATE TABLE recon_runs (
  scan_id TEXT PRIMARY KEY,
  target TEXT NOT NULL,
  mode TEXT NOT NULL,
  scope JSONB NOT NULL DEFAULT '{}',
  artifact_root TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  started_at TIMESTAMPTZ DEFAULT now(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE recon_entities (
  id TEXT PRIMARY KEY,
  scan_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  label TEXT NOT NULL,
  normalized JSONB NOT NULL DEFAULT '{}',
  sources JSONB NOT NULL DEFAULT '[]',
  confidence DOUBLE PRECISION DEFAULT 0,
  first_seen TIMESTAMPTZ DEFAULT now(),
  last_seen TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE recon_artifacts (
  id TEXT PRIMARY KEY,
  scan_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL DEFAULT '',
  bytes INTEGER DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE recon_endpoint_scores (
  id TEXT PRIMARY KEY,
  scan_id TEXT NOT NULL,
  endpoint_id TEXT NOT NULL,
  score INTEGER NOT NULL,
  reasons JSONB NOT NULL DEFAULT '[]',
  omega_modules JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Also add DB helper methods:

- `create_recon_run`
- `finish_recon_run`
- `upsert_recon_entity`
- `create_recon_artifact`
- `upsert_endpoint_score`
- `bulk_upsert_kg`

## 9. Event Payload Upgrades

### `RECON_PACKET`

Payload should become:

```json
{
  "url": "https://api.example.com/v1/users/{id}",
  "method": "GET",
  "status_code": 200,
  "response_time_ms": 123,
  "content_type": "application/json",
  "content_length": 4211,
  "server_header": "nginx",
  "technologies": ["FastAPI", "Cloudflare"],
  "parameters": [{"name": "id", "location": "path", "type": "numeric"}],
  "auth_required": false,
  "priority_score": 90,
  "source": ["openapi", "katana", "pinchtab_network"],
  "baseline_response_hash": "sha256:...",
  "risk_class": "HIGH",
  "why": "Unauthenticated API endpoint with numeric ID parameter"
}
```

### `VULN_CANDIDATE`

Payload should become:

```json
{
  "vuln_type": "SECRET_EXPOSURE",
  "severity": "CRITICAL",
  "host": "app.example.com",
  "endpoint": "https://app.example.com/static/app.js",
  "evidence": "AWS key pattern found in JavaScript; value redacted",
  "tool_discovered_by": "SecretFinder",
  "requires_exploitation": false,
  "exploitation_module": "sigma_secret_validation",
  "artifact_id": "..."
}
```

### `RECON_COMPLETE`

Match the user's requested payload, but add:

- `scope_enforced: true`
- `scan_mode`
- `tools_run`
- `tools_skipped`
- `phase_timings`
- `artifact_manifest_path`
- `pinchtab_profile_id`
- `pinchtab_instance_id`

## 10. Prompt Integration

Place the Alpha master prompt in:

- `backend/agents/alpha/prompt.py`

Use it as policy/context for:

- deciding optional tools when multiple tools can answer the same question;
- prioritizing targets after deterministic collection;
- explaining why endpoint scores matter;
- generating Omega/Sigma instructions.

Do not let the prompt override:

- scope validation;
- scan mode barriers;
- rate limits;
- tool availability;
- approval requirements;
- output redaction.

## 11. Detailed Implementation Milestones

### Milestone 1: Package Refactor And Models

Files:

- Create `backend/agents/alpha/`.
- Move current Alpha logic into `backend/agents/alpha/legacy.py` or migrate to `agent.py`.
- Update imports in `backend/core/orchestrator.py`.
- Add Pydantic models.
- Add event type constants.

Acceptance:

- Existing tests still import/start Alpha.
- Current shallow recon still works behind `legacy_http_probe` feature flag.

### Milestone 2: Scope Compiler And Run State

Files:

- `backend/agents/alpha/scope.py`
- `backend/agents/alpha/run_state.py`
- `backend/agents/alpha/artifacts.py`

Acceptance:

- Unit tests for domain/wildcard/CIDR exclusions.
- `.gov/.mil` block test unless authorization flag set.
- Artifact dirs created predictably.

### Milestone 3: External Tool Execution Spine

Files:

- `backend/tools/recon/base.py`
- `backend/tools/recon/external.py`
- register wrappers in `backend/core/default_tools.py` or `backend/tools/recon/register.py`.

Acceptance:

- Tool availability checks produce `tools_skipped`.
- Raw stdout/stderr is stored.
- Toolcall rows are created/finished.
- Unavailable tools never crash the scan.

### Milestone 4: Passive Phase

Wrappers/parsers:

- Subfinder
- Amass passive
- gau
- waybackurls
- SpiderFoot basic CLI/API
- crt.sh fetcher

Acceptance:

- Given canned fixture outputs, parser dedupes subdomains and historical URLs.
- `PASSIVE_ONLY` does not hit the target.
- Source counts/confidence are correct.

### Milestone 5: DNS/Infra Phase

Wrappers/parsers:

- dnsx
- shuffledns
- naabu
- nmap XML
- tlsx

Acceptance:

- CNAME/takeover candidate logic works from fixture records.
- SANs feed back into scoped subdomain set.
- Port/service nodes appear in KG.

### Milestone 6: HTTP/Crawl/JS/Browser Phase

Wrappers/parsers:

- httpx JSONL
- katana output
- hakrawler output
- LinkFinder output
- SecretFinder output
- PinchTab client adapter

Acceptance:

- Live URL inventory has tech/status/title/header data.
- PinchTab network export creates endpoint findings.
- Secret findings are redacted in events.
- Security header gaps are informational/medium candidates, not overpromoted.

### Milestone 7: Discovery/Fuzz Phase

Wrappers/parsers:

- WordlistBuilder
- Feroxbuster
- Dirsearch
- ffuf
- Gobuster vhost

Acceptance:

- Target-specific wordlist contains path segments from Phase 1/3.
- Response-baseline filtering reduces false positives.
- `STANDARD` and `AGGRESSIVE` mode limits are enforced.

### Milestone 8: API/GraphQL Phase

Wrappers/parsers:

- OpenAPI path prober/parser
- Kiterunner
- InQL
- GraphQL Voyager artifact generator

Acceptance:

- OpenAPI specs produce normalized endpoint/parameter/auth records.
- GraphQL introspection fixture produces type/query/mutation nodes.
- Schema discovery emits `SCHEMA_DISCOVERED`.

### Milestone 9: Visual And Nuclei Phase

Wrappers/parsers:

- gowitness
- aquatone
- nuclei
- interactsh monitor

Acceptance:

- Screenshots and reports become `recon_artifacts`.
- Nuclei high/critical findings emit immediate `VULN_CANDIDATE`.
- Interactsh callback maps back to payload/tool/endpoint.

### Milestone 10: Correlation, Scoring, Final Output

Files:

- `backend/agents/alpha/normalizers.py`
- `backend/agents/alpha/dedupe.py`
- `backend/agents/alpha/scoring.py`
- `backend/agents/alpha/events.py`
- `backend/integrations/neo4j_client.py`

Acceptance:

- Final `RECON_COMPLETE` includes all requested summary fields.
- Endpoint priority queue is stable and explainable.
- Omega instructions and Sigma context are populated.
- KG export path, raw data path, screenshot path are valid.

## 12. Testing Strategy

Unit tests:

- Scope parsing/enforcement.
- URL normalization and endpoint dedupe.
- Parameter type inference.
- Secret redaction.
- Endpoint scoring.
- Parser fixtures for each tool.

Integration tests:

- `PASSIVE_ONLY` scan with fixture tool outputs.
- `STANDARD` scan against local test web app only.
- PinchTab adapter against local fixture pages.
- Nuclei parser with canned JSONL.
- GraphQL parser with local schema fixture.

Safety tests:

- Out-of-scope URL is rejected and emits `SCOPE_VIOLATION`.
- `.gov`/`.mil` blocked without authorization.
- Active tools skipped in `PASSIVE_ONLY`.
- Dangerous methods require approval.
- Raw cookies/auth headers redacted from artifacts by default.

Performance tests:

- 10k historical URLs dedupe under target time.
- 100k endpoint records normalized without memory blowup.
- EventBus does not emit duplicate `RECON_PACKET`s.

## 13. Configuration

Add settings:

```env
ALPHA_TOOL_ROOT=D:\projects
ALPHA_ARTIFACT_ROOT=data/scans
ALPHA_DEFAULT_MODE=STANDARD
ALPHA_DEFAULT_RPS=50
ALPHA_MAX_HTTPX_THREADS=50
ALPHA_MAX_CRAWL_DEPTH=3
ALPHA_ENABLE_PINCHTAB=true
PINCHTAB_BASE_URL=http://127.0.0.1:9867
ALPHA_ENABLE_NEO4J=false
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
ALPHA_ENABLE_OPENCTI_EXPORT=false
OPENCTI_URL=
OPENCTI_TOKEN=
```

## 14. Operator UX

Dashboard should show:

- Current phase and active tool.
- Tools skipped and why.
- Passive/active boundary marker.
- Scope summary.
- Live discovered counts.
- High-priority endpoint queue.
- Immediate vuln candidates.
- Artifact links for screenshots/HAR/raw outputs.
- PinchTab profile/instance health.

API should support:

- scan mode selection.
- explicit scope inclusions/exclusions.
- rate limit.
- active phase approval.
- stop/pause/resume.
- download artifact bundle.

## 15. Final Alpha Shape

When complete, Alpha should no longer be "60 paths and vibes."

It should be:

- phase-gated;
- passive-first;
- scope-hard;
- evidence-preserving;
- browser-aware through PinchTab;
- graph-native;
- tool-output-normalizing;
- deduplicating;
- scoring;
- Omega/Sigma/Kappa/Chi-ready.

The most important engineering principle: Alpha is not a pile of tool commands. Alpha is a correlation engine with disciplined tool execution.
