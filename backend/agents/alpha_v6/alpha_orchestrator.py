"""Alpha V6 Deep Recon Orchestrator — Full Multi-Phase Pipeline."""
from __future__ import annotations
import asyncio, logging, re, time
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse

from backend.agents.alpha_v6.artifacts import ArtifactStore
from backend.agents.alpha_v6.dedupe import SeenSet, classify_path, normalize_endpoint_key, normalize_url
from backend.agents.alpha_v6.models import (
    EndpointFinding, HTTPServiceFinding, ParameterFinding, ReconEntity,
    ReconRunResult, ReconRunSummary, ReconScope, ScanMode, SourceRef, ToolSkip, stable_id,
)
from backend.agents.alpha_v6.rag import ReconRAGPipeline
from backend.agents.alpha_v6.scoring import score_endpoint
from backend.agents.alpha_v6.phase_controller import PhaseController, PhaseState, PhaseResult
from backend.agents.alpha_v6.entity_engine import EntityEngine
from backend.agents.alpha_v6.pinchtab_intel import PinchTabIntelligence
from backend.agents.alpha_v6.wordlist_builder import WordlistBuilder
from backend.agents.alpha_v6.scope_gate import ScopeGate, ScopeGateViolation
from backend.agents.alpha_v6.live_feed import recon_live_feed
from backend.agents.alpha_v6.interactsh_adapter import InteractshAdapter
from backend.agents.alpha_v6.schema_discovery import SchemaDiscovery
from backend.agents.alpha_v6.approval_hooks import approval_manager
from backend.agents.alpha_v6.event_schemas import (
    ReconStartedEvent, ReconCompleteEvent, PhaseStartedEvent, PhaseCompletedEvent,
    ToolCompletedEvent, VulnCandidateEvent, ScopeViolationEvent,
)
import backend.agents.alpha_v6.db_extensions  # patches db_manager
from backend.core.config import settings
from backend.core.database import db_manager
from backend.core.hive import EventType, HiveEvent
from backend.core.unified_knowledge_graph import EdgeKind, KGNode, NodeKind, knowledge_graph
from backend.core.scope import ScopePolicy, ScopeViolation
from backend.core.telemetry import telemetry
from backend.integrations.pinchtab_client import PinchTabClient
from backend.modules.tech.http_client import http_client
from backend.tools.recon import RECON_TOOLS, ReconCommandPlanner, ReconCommandRunner, check_tool_availability
from backend.parsers.recon import PARSER_REGISTRY
from backend.parsers.recon.base import ParsedEntity

logger = logging.getLogger("alpha")


class AlphaOrchestrator:
    """Production-grade multi-phase recon orchestrator."""

    def __init__(self, bus, *, agent_name: str = "agent_alpha"):
        self.bus = bus
        self.agent_name = agent_name
        self._seen_packets = SeenSet()

    async def run(self, target_url: str, *, scan_id: str = "GLOBAL",
                  mode: str | ScanMode | None = None) -> ReconRunResult:
        started = time.time()
        scan_mode = self._coerce_mode(mode or getattr(settings, "ALPHA_DEFAULT_MODE", "STANDARD"))
        scope = self._compile_scope(target_url, scan_mode)

        # Scope Gate Validation — blocks .gov/.mil, private networks, unauthorized active scans
        gate = ScopeGate(scope)
        try:
            gate.validate_target(target_url)
        except ScopeGateViolation as exc:
            logger.error(f"[SCOPE] Target rejected: {exc}")
            await recon_live_feed.on_error(scan_id, str(exc), "scope_gate")
            raise

        artifacts = ArtifactStore(scan_id)
        rag = ReconRAGPipeline(scan_id, str(artifacts.root))
        planner = ReconCommandPlanner()
        runner = ReconCommandRunner()
        phases = PhaseController(scope)
        entities = EntityEngine(scan_id)
        tools_run: list[str] = []
        tools_skipped: list[ToolSkip] = []
        endpoints: list[EndpointFinding] = []

        # Interactsh OOB client
        interactsh = InteractshAdapter(scan_id, artifacts.root)
        oob_url = await interactsh.start()
        phases.state.interactsh_url = oob_url

        await db_manager.initialize()
        await db_manager.create_recon_run(scan_id=scan_id, target=target_url,
            mode=scan_mode.value, scope=scope.model_dump(mode="json"),
            artifact_root=str(artifacts.root), status="running")

        await recon_live_feed.on_phase_started(scan_id, "initialization")
        await self._emit_status(scan_id, "initialized", {"target": target_url, "mode": scan_mode.value})
        await rag.ingest_tool_summary("alpha_scope", {"target": target_url, "mode": scan_mode.value})

        with telemetry.span("alpha.recon", kind="agent", scan_id=scan_id):
            # Phase: Tool Inventory
            await self._inventory_tools(scan_mode, tools_skipped, rag)

            # Phase 1: Passive Intelligence
            if phases.should_run(phases.PHASE_ORDER[1]):
                await self._run_phase_passive(phases, planner, runner, artifacts, rag,
                    entities, scan_id, scope, tools_run, tools_skipped)

            # Phase 2: DNS & Infrastructure
            if phases.should_run(phases.PHASE_ORDER[2]):
                await self._run_phase_dns(phases, planner, runner, artifacts, rag,
                    entities, scan_id, scope, tools_run, tools_skipped)

            # Phase 3: HTTP & Browser Intelligence
            if phases.should_run(phases.PHASE_ORDER[3]):
                await self._run_phase_http(phases, planner, runner, artifacts, rag,
                    entities, scan_id, scope, target_url, tools_run, tools_skipped, endpoints)

            # Phase 4: Directory & Route Discovery
            if phases.should_run(phases.PHASE_ORDER[4]):
                await self._run_phase_discovery(phases, planner, runner, artifacts, rag,
                    entities, scan_id, scope, tools_run, tools_skipped)

            # Phase 5: API Reconnaissance
            if phases.should_run(phases.PHASE_ORDER[5]):
                await self._run_phase_api(phases, planner, runner, artifacts, rag,
                    entities, scan_id, scope, tools_run, tools_skipped)

            # Phase 6: Visual Documentation
            if phases.should_run(phases.PHASE_ORDER[6]):
                await self._run_phase_visual(phases, planner, runner, artifacts, rag,
                    entities, scan_id, scope, tools_run, tools_skipped)

            # Phase 7: Template Validation
            if phases.should_run(phases.PHASE_ORDER[7]):
                await self._run_phase_validation(phases, planner, runner, artifacts, rag,
                    entities, scan_id, scope, tools_run, tools_skipped)

            # Stop Interactsh and collect OOB findings
            oob_interactions = await interactsh.stop()
            if oob_interactions:
                tools_run.append("interactsh")
                for oob in oob_interactions:
                    entities.ingest(ParsedEntity(
                        kind="oob_interaction", label=oob.get("interaction_type", "unknown"),
                        confidence=0.9, source_tool="interactsh",
                        phase="template_validation", scan_id=scan_id,
                        properties=oob.get("raw", {})))

            # Final: Correlation & Scoring
            endpoints = self._dedupe_and_sort(endpoints)
            summary = self._summarize(endpoints, phases.state, entities)
            result = ReconRunResult(
                scan_id=scan_id, target=target_url, mode=scan_mode,
                duration_seconds=int(time.time() - started), summary=summary,
                attack_surface=endpoints, tools_run=tools_run,
                tools_skipped=tools_skipped, raw_data_path=str(artifacts.raw_dir),
                screenshots_path=str(artifacts.screenshots_dir),
                artifact_manifest_path=str(artifacts.manifest_path))

            await artifacts.write_json("exports/recon_complete.json",
                result.model_dump(mode="json"), tool_name="alpha",
                artifact_type="recon_complete", scan_id=scan_id)
            await db_manager.finish_recon_run(scan_id=scan_id, status="completed")
            await recon_live_feed.on_scan_complete(scan_id, summary.model_dump())
            await self._emit_complete(result)
            return result

    # ── Phase Implementations ─────────────────────────────────────

    async def _run_phase_passive(self, phases, planner, runner, artifacts, rag,
                                  entities, scan_id, scope, tools_run, tools_skipped):
        from backend.agents.alpha_v6.models import ReconPhase
        pr = phases.start_phase(ReconPhase.PASSIVE)
        await self._emit_status(scan_id, "phase_passive_started", {})
        cmds = planner.passive_commands(scope, artifacts.raw_dir)
        parsed = await self._run_and_parse(cmds, runner, artifacts, rag, scan_id,
            tools_run, tools_skipped, pr)
        phases.complete_phase(ReconPhase.PASSIVE, parsed)

    async def _run_phase_dns(self, phases, planner, runner, artifacts, rag,
                              entities, scan_id, scope, tools_run, tools_skipped):
        from backend.agents.alpha_v6.models import ReconPhase
        if not phases.state.subdomains:
            phases.skip_phase(ReconPhase.INFRA, "no_subdomains_from_passive")
            return
        pr = phases.start_phase(ReconPhase.INFRA)
        await self._emit_status(scan_id, "phase_dns_started", {"subs": len(phases.state.subdomains)})
        sub_file = phases.state.build_subdomain_file(artifacts.raw_dir)
        hosts_file = phases.state.build_hosts_file(artifacts.raw_dir)
        cmds = planner.dns_commands(scope, artifacts.raw_dir, sub_file)
        cmds += planner.port_commands(scope, artifacts.raw_dir, hosts_file)
        cmds += planner.tls_commands(scope, artifacts.raw_dir, hosts_file)
        parsed = await self._run_and_parse(cmds, runner, artifacts, rag, scan_id,
            tools_run, tools_skipped, pr)
        phases.complete_phase(ReconPhase.INFRA, parsed)

    async def _run_phase_http(self, phases, planner, runner, artifacts, rag,
                               entities, scan_id, scope, target_url, tools_run,
                               tools_skipped, endpoints):
        from backend.agents.alpha_v6.models import ReconPhase
        pr = phases.start_phase(ReconPhase.HTTP)
        await self._emit_status(scan_id, "phase_http_started", {})
        hosts_file = phases.state.build_hosts_file(artifacts.raw_dir)
        cmds = planner.http_commands(scope, artifacts.raw_dir, hosts_file)
        parsed = await self._run_and_parse(cmds, runner, artifacts, rag, scan_id,
            tools_run, tools_skipped, pr)
        # Internal HTTP probe
        http_client.scope = ScopePolicy.from_target(target_url)
        svc = await self._http_probe(target_url, scan_id)
        for s in svc:
            ep = score_endpoint(self._service_to_endpoint(s))
            endpoints.append(ep)
            if ep.priority_score >= 50:
                await self._emit_recon_packet(scan_id, ep)
        # PinchTab deep capture with Playwright fallback
        browser_used = False
        if getattr(settings, "ALPHA_ENABLE_PINCHTAB", True):
            pt = PinchTabIntelligence(scan_id, artifacts, rag)
            targets = [e.url for e in endpoints if e.priority_score >= 40][:20]
            targets += phases.state.http_services[:10]
            pt_result = await pt.full_capture(list(set(targets)))
            if pt_result.get("used"):
                tools_run.append("pinchtab")
                parsed.extend(pt_result.get("entities", []))
                browser_used = True
            elif pt_result.get("reason"):
                tools_skipped.append(ToolSkip(name="pinchtab", phase="http_browser_intelligence",
                    reason=pt_result["reason"]))
        # Playwright fallback when PinchTab unavailable
        if not browser_used:
            try:
                from backend.agents.alpha_v6.playwright_fallback import PlaywrightFallback
                pw = PlaywrightFallback(scan_id, artifacts.root)
                capture_targets = [e.url for e in endpoints if e.priority_score >= 50][:10]
                capture_targets += phases.state.http_services[:5]
                for url in list(set(capture_targets))[:15]:
                    cap = await pw.capture_page(url)
                    if cap.get("used"):
                        parsed.extend(pw.extract_entities(cap))
                        browser_used = True
                await pw.close()
                if browser_used:
                    tools_run.append("playwright")
            except Exception as pw_exc:
                logger.debug(f"Playwright fallback skipped: {pw_exc}")
                tools_skipped.append(ToolSkip(name="playwright", phase="http_browser_intelligence",
                    reason=str(pw_exc)[:100]))
        # JS analysis
        js_files = list(set(phases.state.js_files + [e.label for e in parsed if e.kind == "js_file"]))
        if js_files:
            js_cmds = planner.js_analysis_commands(scope, artifacts.raw_dir, js_files[:50])
            js_parsed = await self._run_and_parse(js_cmds, runner, artifacts, rag, scan_id,
                tools_run, tools_skipped, pr)
            parsed.extend(js_parsed)
        phases.complete_phase(ReconPhase.HTTP, parsed)

    async def _run_phase_discovery(self, phases, planner, runner, artifacts, rag,
                                    entities, scan_id, scope, tools_run, tools_skipped):
        from backend.agents.alpha_v6.models import ReconPhase
        live = list(set(phases.state.http_services))[:100]
        if not live:
            phases.skip_phase(ReconPhase.DISCOVERY, "no_live_hosts")
            return
        pr = phases.start_phase(ReconPhase.DISCOVERY)
        await self._emit_status(scan_id, "phase_discovery_started", {"hosts": len(live)})
        # Build custom wordlist
        wb = WordlistBuilder()
        wl = wb.build(raw_dir=artifacts.raw_dir,
            discovered_paths=[e.label for e in phases.state.all_entities if e.kind == "crawled_endpoint"],
            historical_urls=[e.label for e in phases.state.all_entities if e.kind == "historical_url"],
            technologies=[])
        cmds = planner.discovery_commands(scope, artifacts.raw_dir, live, wl)
        parsed = await self._run_and_parse(cmds, runner, artifacts, rag, scan_id,
            tools_run, tools_skipped, pr)
        phases.complete_phase(ReconPhase.DISCOVERY, parsed)

    async def _run_phase_api(self, phases, planner, runner, artifacts, rag,
                              entities, scan_id, scope, tools_run, tools_skipped):
        from backend.agents.alpha_v6.models import ReconPhase
        live = list(set(phases.state.http_services))[:20]
        if not live:
            phases.skip_phase(ReconPhase.API, "no_live_hosts")
            return
        pr = phases.start_phase(ReconPhase.API)
        await self._emit_status(scan_id, "phase_api_started", {})
        # Schema discovery (OpenAPI/Swagger/GraphQL introspection)
        try:
            sd = SchemaDiscovery(scan_id, http_client=http_client)
            schema_entities = await sd.discover_all(live)
            if schema_entities:
                for se in schema_entities:
                    entities.ingest(se)
                pr.entities_found += len(schema_entities)
                tools_run.append("schema_discovery")
                await rag.ingest_tool_summary("schema_discovery",
                    {"schemas_found": len(schema_entities)})
        except Exception as sd_exc:
            logger.warning(f"Schema discovery failed: {sd_exc}")
        cmds = planner.api_commands(scope, artifacts.raw_dir, live)
        parsed = await self._run_and_parse(cmds, runner, artifacts, rag, scan_id,
            tools_run, tools_skipped, pr)
        phases.complete_phase(ReconPhase.API, parsed)

    async def _run_phase_visual(self, phases, planner, runner, artifacts, rag,
                                 entities, scan_id, scope, tools_run, tools_skipped):
        from backend.agents.alpha_v6.models import ReconPhase
        live = list(set(phases.state.http_services))[:100]
        if not live:
            phases.skip_phase(ReconPhase.VISUAL, "no_live_hosts")
            return
        pr = phases.start_phase(ReconPhase.VISUAL)
        cmds = planner.visual_commands(scope, artifacts.raw_dir, live)
        parsed = await self._run_and_parse(cmds, runner, artifacts, rag, scan_id,
            tools_run, tools_skipped, pr)
        phases.complete_phase(ReconPhase.VISUAL, parsed)

    async def _run_phase_validation(self, phases, planner, runner, artifacts, rag,
                                     entities, scan_id, scope, tools_run, tools_skipped):
        from backend.agents.alpha_v6.models import ReconPhase
        live = list(set(phases.state.http_services))[:200]
        if not live:
            phases.skip_phase(ReconPhase.VALIDATION, "no_live_hosts")
            return
        pr = phases.start_phase(ReconPhase.VALIDATION)
        await self._emit_status(scan_id, "phase_validation_started", {})
        cmds = planner.validation_commands(scope, artifacts.raw_dir, live,
            phases.state.interactsh_url)
        parsed = await self._run_and_parse(cmds, runner, artifacts, rag, scan_id,
            tools_run, tools_skipped, pr)
        phases.complete_phase(ReconPhase.VALIDATION, parsed)

    # ── Core Helpers ──────────────────────────────────────────────

    async def _run_and_parse(self, cmds, runner, artifacts, rag, scan_id,
                              tools_run, tools_skipped, phase_result) -> list[ParsedEntity]:
        """Run commands and parse their outputs through the parser registry."""
        all_parsed: list[ParsedEntity] = []
        ext_tools_enabled = getattr(settings, "ALPHA_ENABLE_EXTERNAL_TOOLS", False)

        for cmd in cmds:
            avail = check_tool_availability(cmd.tool_name)
            if not avail.get("installed") or not ext_tools_enabled:
                tools_skipped.append(ToolSkip(name=cmd.tool_name, phase=cmd.phase,
                    reason="not_installed" if not avail.get("installed") else "external_tools_disabled"))
                phase_result.tools_skipped.append(
                    ToolSkip(name=cmd.tool_name, phase=cmd.phase, reason="unavailable"))
                continue

            try:
                result = await runner.execute(cmd)
                tools_run.append(cmd.tool_name)
                phase_result.tools_run.append(cmd.tool_name)

                # Register raw output
                if cmd.output_path.exists():
                    await artifacts.register(cmd.output_path, tool_name=cmd.tool_name,
                        artifact_type="raw_output", scan_id=scan_id)

                # Parse through registry
                parser = PARSER_REGISTRY.get(cmd.tool_name)
                parse_path = cmd.output_path
                if cmd.metadata.get("json_file"):
                    alt = Path(cmd.metadata["json_file"])
                    if alt.exists():
                        parse_path = alt
                if cmd.metadata.get("xml_file"):
                    alt = Path(cmd.metadata["xml_file"])
                    if alt.exists():
                        parse_path = alt

                if parser and parse_path.exists():
                    try:
                        parsed = parser(parse_path)
                        all_parsed.extend(parsed)
                        await rag.ingest_tool_summary(cmd.tool_name,
                            {"entities": len(parsed), "phase": cmd.phase})
                    except Exception as pe:
                        logger.warning(f"Parser failed for {cmd.tool_name}: {pe}")
                        phase_result.errors.append(f"parse_error:{cmd.tool_name}:{pe}")

            except Exception as exc:
                logger.warning(f"Tool {cmd.tool_name} failed: {exc}")
                phase_result.errors.append(f"exec_error:{cmd.tool_name}:{exc}")
                tools_skipped.append(ToolSkip(name=cmd.tool_name, phase=cmd.phase,
                    reason=f"exec_failed:{exc}"))

        return all_parsed

    async def _inventory_tools(self, mode, tools_skipped, rag):
        """Check which tools are available on this system."""
        inventory = {}
        for name, spec in RECON_TOOLS.items():
            avail = check_tool_availability(name)
            inventory[name] = avail
        await rag.ingest_tool_summary("tool_inventory", inventory)

    def _compile_scope(self, target_url: str, mode: ScanMode) -> ReconScope:
        parsed = urlparse(target_url)
        domain = (parsed.hostname or "").lower()
        # When user explicitly fires a scan from the UI, private/local targets
        # are implicitly authorized — the user chose to scan them.
        is_local = domain in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or \
                   domain.startswith("192.168.") or domain.startswith("10.") or \
                   domain.startswith("172.16.") or domain.endswith(".local")
        return ReconScope(
            base_domain=domain, target_url=target_url, scan_mode=mode,
            base_url=f"{parsed.scheme}://{parsed.hostname}" if parsed.hostname else target_url,
            max_depth=3 if mode == ScanMode.AGGRESSIVE else 2,
            max_rps=200 if mode == ScanMode.AGGRESSIVE else 50,
            explicit_authorization=is_local,
        )

    def _coerce_mode(self, val) -> ScanMode:
        if isinstance(val, ScanMode): return val
        try: return ScanMode(str(val).upper())
        except (ValueError, KeyError): return ScanMode.STANDARD

    async def _http_probe(self, target_url: str, scan_id: str) -> list[HTTPServiceFinding]:
        """Internal scoped HTTP probe used even when external tools are disabled."""
        common_paths = [
            "", "/api", "/api/v1", "/api/v2", "/api/health", "/api/status",
            "/swagger", "/swagger.json", "/docs", "/openapi.json", "/api-docs",
            "/graphql", "/admin", "/login", "/auth", "/token",
            "/users", "/user", "/account", "/profile", "/settings",
            "/orders", "/order", "/cart", "/payment", "/checkout",
            "/products", "/items", "/search", "/export",
            "/robots.txt", "/sitemap.xml", "/.env", "/config",
            "/wp-admin", "/wp-login.php", "/.git/config",
        ]
        parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
        base_url = f"{parsed.scheme or 'https'}://{parsed.netloc or parsed.path}".rstrip("/")
        services: list[HTTPServiceFinding] = []
        async def probe(path: str) -> None:
            url = normalize_url(urljoin(base_url + "/", path.lstrip("/")))
            try:
                record = await http_client.request("GET", url, scan_id=scan_id, timeout=10)
                headers = {str(k): str(v) for k, v in record.response_headers.items()}
                services.append(HTTPServiceFinding(
                    url=url,
                    status_code=record.status,
                    response_time_ms=record.elapsed_ms,
                    content_type=headers.get("Content-Type", headers.get("content-type", "")),
                    content_length=len(record.response_body or ""),
                    server=headers.get("Server", headers.get("server", "")),
                    server_header=headers.get("Server", headers.get("server", "")),
                    technologies=self._detect_tech(headers, record.response_body),
                    source="alpha_http",
                    response_hash=self._hash_body(record.response_body),
                    headers=headers,
                    body_preview=(record.response_body or "")[:500],
                ))
            except ScopeViolation:
                await self.bus.publish(HiveEvent(
                    type=EventType.SCOPE_VIOLATION,
                    source=self.agent_name,
                    scan_id=scan_id,
                    payload={"url": url, "reason": "out_of_scope"},
                ))
            except Exception:
                return

        await asyncio.gather(*(probe(path) for path in common_paths))
        return services

    def _service_to_endpoint(self, svc: HTTPServiceFinding) -> EndpointFinding:
        parsed = urlparse(svc.url)
        endpoint_type, risk = classify_path(parsed.path)
        params = [
            ParameterFinding(name=name, location="query", value_type=self._infer_type(value), examples=[value] if value else [])
            for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        ]
        return EndpointFinding(
            url=svc.url, method="GET", status_code=svc.status_code,
            content_type=svc.content_type, path=parsed.path or "/",
            normalized_path=parsed.path or "/",
            host=(parsed.hostname or "").lower(),
            technologies=svc.technologies, server=svc.server,
            server_header=svc.server_header,
            content_length=svc.content_length,
            response_time_ms=svc.response_time_ms,
            parameters=params,
            auth_required=svc.status_code in {401, 403},
            endpoint_type=endpoint_type,
            risk_class=risk,
            source="alpha_http",
            baseline_response_hash=svc.response_hash,
            evidence={"headers": svc.headers, "body_preview": svc.body_preview},
            sources=[SourceRef(tool="http_probe", phase="http_browser_intelligence",
                               confidence=0.9)])

    def _dedupe_and_sort(self, eps: list[EndpointFinding]) -> list[EndpointFinding]:
        seen: set[str] = set()
        unique = []
        for ep in eps:
            key = normalize_endpoint_key(ep.url, ep.method)
            if key not in seen:
                seen.add(key)
                unique.append(ep)
        unique.sort(key=lambda e: e.priority_score, reverse=True)
        return unique

    def _summarize(self, endpoints, state, entities) -> ReconRunSummary:
        return ReconRunSummary(
            total_endpoints=len(endpoints),
            total_subdomains=len(state.subdomains),
            total_ips=len(state.ips),
            total_open_ports=sum(len(p) for p in state.open_ports.values()),
            total_js_files=len(state.js_files),
            total_parameters=len(state.parameters),
            total_secrets=len(state.secrets),
            total_vulns=len(state.vulnerability_candidates),
            attack_surface_stats=entities.get_attack_surface_stats(),
        )

    async def _emit_status(self, scan_id, status, data):
        try:
            event = HiveEvent(type=EventType.AGENT_STATUS,
                source=self.agent_name, scan_id=scan_id,
                payload={"agent": "alpha", "phase": status, **data})
            await self.bus.publish(event)
        except Exception:
            pass

    async def _emit_recon_packet(self, scan_id, ep):
        try:
            event = HiveEvent(type=EventType.RECON_PACKET,
                source=self.agent_name, scan_id=scan_id,
                payload=ep.model_dump(mode="json"))
            await self.bus.publish(event)
        except Exception:
            pass

    async def _emit_complete(self, result):
        try:
            event = HiveEvent(type=EventType.RECON_COMPLETE,
                source=self.agent_name, scan_id=result.scan_id,
                payload=result.model_dump(mode="json"))
            await self.bus.publish(event)
        except Exception:
            pass

    def _detect_tech(self, headers: dict[str, str], body: str) -> list[str]:
        tech: set[str] = set()
        server = headers.get("Server") or headers.get("server") or ""
        powered = headers.get("X-Powered-By") or headers.get("x-powered-by") or ""
        for value in [server, powered]:
            if value:
                tech.add(value.split(";", 1)[0].strip())
        lower = (body or "").lower()
        if "swagger" in lower or "openapi" in lower:
            tech.add("OpenAPI")
        if "graphql" in lower:
            tech.add("GraphQL")
        if "wp-content" in lower:
            tech.add("WordPress")
        return sorted(tech)

    def _infer_type(self, value: str) -> str:
        if re.fullmatch(r"[0-9]+", value or ""):
            return "numeric"
        if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", value or ""):
            return "uuid"
        return "string"

    def _hash_body(self, body: str) -> str:
        import hashlib

        return "sha256:" + hashlib.sha256((body or "").encode("utf-8", errors="replace")).hexdigest()


AlphaV6DeepOrchestrator = AlphaOrchestrator
AlphaV6ReconOrchestrator = AlphaOrchestrator
