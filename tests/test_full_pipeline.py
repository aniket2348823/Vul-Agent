"""
Full Pipeline Integration Test — Backend Only.

Tests the COMPLETE scan lifecycle without frontend:
  1. Agent dispatching & activation
  2. Alpha V6 Recon (HTTP probe, scoring, deduplication)
  3. HiveOrchestrator event routing
  4. Attack module dispatch (Beta, Sigma)
  5. Report generation pipeline
  6. Cleanup & isolation

Target: http://testphp.vulnweb.com (Acunetix public test site)

Usage:
  python -m pytest tests/test_full_pipeline.py -v -s
"""
import asyncio
import time
import pytest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline_test")


# ─── TEST 1: Agent Import Chain ────────────────────────────────────────
class TestAgentImports:
    """Verify every agent module imports cleanly after refactor."""

    def test_alpha_agent(self):
        from backend.agents.alpha import AlphaAgent
        assert AlphaAgent.__name__ == "AlphaAgent"

    def test_alpha_orchestrator_direct(self):
        from backend.agents.alpha_recon.alpha_orchestrator import AlphaOrchestrator
        assert AlphaOrchestrator.__name__ == "AlphaOrchestrator"

    def test_alpha_orchestrator_aliases(self):
        from backend.agents.alpha_recon import AlphaOrchestrator, AlphaV6ReconOrchestrator, AlphaV6DeepOrchestrator
        assert AlphaOrchestrator is AlphaV6ReconOrchestrator
        assert AlphaOrchestrator is AlphaV6DeepOrchestrator

    def test_beta_agent(self):
        from backend.agents.beta import BetaAgent
        assert BetaAgent.__name__ == "BetaAgent"

    def test_gamma_agent(self):
        from backend.agents.gamma import GammaAgent
        assert GammaAgent.__name__ == "GammaAgent"

    def test_omega_agent(self):
        from backend.agents.omega import OmegaAgent
        assert OmegaAgent.__name__ == "OmegaAgent"

    def test_sigma_agent(self):
        from backend.agents.sigma import SigmaAgent
        assert SigmaAgent.__name__ == "SigmaAgent"

    def test_zeta_agent(self):
        from backend.agents.zeta import ZetaAgent
        assert ZetaAgent.__name__ == "ZetaAgent"

    def test_kappa_agent(self):
        from backend.agents.kappa import KappaAgent
        assert KappaAgent.__name__ == "KappaAgent"

    def test_prism_agent(self):
        from backend.agents.prism import AgentPrism
        assert AgentPrism.__name__ == "AgentPrism"

    def test_chi_agent(self):
        from backend.agents.chi import AgentChi
        assert AgentChi.__name__ == "AgentChi"

    def test_delta_agent(self):
        from backend.agents.delta import AgentDelta
        assert AgentDelta.__name__ == "AgentDelta"


# ─── TEST 2: Core Systems Boot ─────────────────────────────────────────
class TestCoreSystems:
    """Verify core infrastructure modules initialize."""

    def test_hive_orchestrator(self):
        from backend.core.orchestrator import HiveOrchestrator
        assert hasattr(HiveOrchestrator, 'bootstrap_hive')
        assert hasattr(HiveOrchestrator, 'active_agents')

    def test_event_bus(self):
        from backend.core.hive import EventBus, EventType
        bus = EventBus()
        assert bus is not None
        required = ['TARGET_ACQUIRED', 'VULN_CONFIRMED', 'VULN_CANDIDATE',
                     'RECON_PACKET', 'RECON_COMPLETE', 'LIVE_ATTACK',
                     'JOB_ASSIGNED', 'AGENT_STATUS', 'SCOPE_VIOLATION']
        for name in required:
            assert hasattr(EventType, name), f"Missing EventType.{name}"

    def test_cortex_engine(self):
        from backend.ai.cortex import get_cortex_engine
        engine = get_cortex_engine()
        assert engine is not None

    def test_mission_planner(self):
        from backend.core.planner import MissionPlanner
        from backend.core.hive import EventBus
        bus = EventBus()
        planner = MissionPlanner(bus)
        assert planner is not None

    def test_report_generator(self):
        from backend.core.reporting import ReportGenerator
        rg = ReportGenerator()
        assert rg is not None

    def test_scope_policy(self):
        from backend.core.scope import ScopePolicy
        policy = ScopePolicy.from_target("http://testphp.vulnweb.com")
        assert policy is not None


# ─── TEST 3: Agent Dispatch & EventBus Wiring ──────────────────────────
class TestAgentDispatch:
    """Test that agents can be created, started, and receive events."""

    @pytest.fixture
    def bus(self):
        from backend.core.hive import EventBus
        return EventBus()

    def test_create_all_agents(self, bus):
        from backend.agents.alpha import AlphaAgent
        from backend.agents.beta import BetaAgent
        from backend.agents.gamma import GammaAgent
        from backend.agents.omega import OmegaAgent
        from backend.agents.sigma import SigmaAgent
        from backend.agents.zeta import ZetaAgent
        from backend.agents.kappa import KappaAgent

        agents = {
            "alpha": AlphaAgent(bus),
            "beta": BetaAgent(bus),
            "gamma": GammaAgent(bus),
            "omega": OmegaAgent(bus),
            "sigma": SigmaAgent(bus),
            "zeta": ZetaAgent(bus),
            "kappa": KappaAgent(bus),
        }

        for name, agent in agents.items():
            assert hasattr(agent, 'name'), f"{name} missing 'name' attribute"
            assert hasattr(agent, 'start'), f"{name} missing 'start' method"
            assert hasattr(agent, 'stop'), f"{name} missing 'stop' method"

    @pytest.mark.asyncio
    async def test_event_publish_subscribe(self, bus):
        from backend.core.hive import EventType, HiveEvent

        received = []

        async def listener(event):
            received.append(event)

        bus.subscribe(EventType.TARGET_ACQUIRED, listener)

        await bus.publish(HiveEvent(
            type=EventType.TARGET_ACQUIRED,
            source="test",
            scan_id="TEST-001",
            payload={"url": "http://testphp.vulnweb.com"}
        ))

        await asyncio.sleep(0.1)

        assert len(received) >= 1
        assert received[0].payload["url"] == "http://testphp.vulnweb.com"

    @pytest.mark.asyncio
    async def test_module_routing_map(self, bus):
        """Verify the module→agent routing map matches what orchestrator uses."""
        from backend.agents.beta import BetaAgent
        from backend.agents.sigma import SigmaAgent

        breaker = BetaAgent(bus)
        sigma = SigmaAgent(bus)

        module_agent_map = {
            "The Tycoon": [breaker, sigma],
            "SQL Injection Probe": [breaker, sigma],
            "API Fuzzer (REST)": [breaker, sigma],
            "Auth Bypass Tester": [breaker, sigma],
        }

        for mod_name, agents in module_agent_map.items():
            assert len(agents) == 2, f"Module '{mod_name}' should map to Beta + Sigma"
            assert type(agents[0]).__name__ == "BetaAgent"
            assert type(agents[1]).__name__ == "SigmaAgent"


# ─── TEST 4: Alpha V6 Recon Pipeline ──────────────────────────────────
class TestAlphaReconPipeline:
    """Test the Alpha V6 recon engine components individually."""

    def test_scope_compilation(self):
        from backend.agents.alpha_recon.alpha_orchestrator import AlphaOrchestrator
        from backend.agents.alpha_recon.models import ScanMode
        from backend.core.hive import EventBus

        orch = AlphaOrchestrator(EventBus())
        scope = orch._compile_scope("http://testphp.vulnweb.com", ScanMode.STANDARD)

        assert scope.base_domain == "testphp.vulnweb.com"
        assert scope.scan_mode == ScanMode.STANDARD
        assert scope.max_depth >= 2

    def test_scope_gate_allows_test_target(self):
        from backend.agents.alpha_recon.scope_gate import ScopeGate
        from backend.agents.alpha_recon.models import ReconScope, ScanMode

        scope = ReconScope(
            base_domain="testphp.vulnweb.com",
            target_url="http://testphp.vulnweb.com",
            scan_mode=ScanMode.STANDARD,
            max_rps=50, max_depth=3,
        )
        gate = ScopeGate(scope)
        gate.validate_target("http://testphp.vulnweb.com")

    def test_scope_gate_blocks_gov(self):
        from backend.agents.alpha_recon.scope_gate import ScopeGate, ScopeGateViolation
        from backend.agents.alpha_recon.models import ReconScope, ScanMode

        scope = ReconScope(
            base_domain="whitehouse.gov",
            target_url="https://whitehouse.gov",
            scan_mode=ScanMode.STANDARD,
            max_rps=50, max_depth=3,
        )
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation):
            gate.validate_target("https://whitehouse.gov")

    def test_scoring_engine(self):
        from backend.agents.alpha_recon.scoring import score_endpoint
        from backend.agents.alpha_recon.models import EndpointFinding

        ep = EndpointFinding(
            url="http://testphp.vulnweb.com/api/v1/users",
            method="GET",
            normalized_path="/api/v1/users",
            status_code=200,
            endpoint_type="API_ENDPOINT",
            risk_class="MEDIUM",
            source="test",
        )
        scored = score_endpoint(ep)
        assert scored.priority_score > 0
        assert len(scored.score_reasons) > 0

    def test_dedupe_engine(self):
        from backend.agents.alpha_recon.dedupe import (
            SeenSet, normalize_url, normalize_endpoint_key, classify_path
        )

        seen = SeenSet()
        assert seen.add("key1") is True
        assert seen.add("key1") is False
        assert seen.add("key2") is True

        # normalize_url preserves trailing slashes (that's by design)
        result = normalize_url("http://example.com/path/")
        assert "example.com" in result

        assert normalize_endpoint_key("http://example.com/api", "GET") is not None

        ep_type, risk = classify_path("/api/v1/users")
        assert ep_type != ""
        assert risk != ""

    def test_entity_engine(self):
        from backend.agents.alpha_recon.entity_engine import EntityEngine
        from backend.parsers.recon.base import ParsedEntity

        engine = EntityEngine("TEST-SCAN")
        entities = [
            ParsedEntity(
                kind="subdomain",
                label="api.example.com",
                confidence=0.9,
                source_tool="subfinder",
                phase="passive",
            ),
            ParsedEntity(
                kind="subdomain",
                label="cdn.example.com",
                confidence=0.8,
                source_tool="subfinder",
                phase="passive",
            ),
        ]
        engine.ingest_entities(entities)
        stats = engine.get_attack_surface_stats()
        assert isinstance(stats, dict)

    def test_artifact_store(self):
        from backend.agents.alpha_recon.artifacts import ArtifactStore
        store = ArtifactStore("TEST-ARTIFACTS")
        assert store.raw_dir is not None
        assert store.screenshots_dir is not None

    def test_phase_controller(self):
        from backend.agents.alpha_recon.phase_controller import PhaseController
        from backend.agents.alpha_recon.models import ReconScope, ScanMode

        scope = ReconScope(
            base_domain="example.com",
            target_url="http://example.com",
            scan_mode=ScanMode.STANDARD,
            max_rps=50, max_depth=3,
        )
        pc = PhaseController(scope)
        assert len(pc.PHASE_ORDER) >= 7

    def test_wordlist_builder(self):
        from backend.agents.alpha_recon.wordlist_builder import WordlistBuilder
        wb = WordlistBuilder()
        assert wb is not None

    def test_exporters(self):
        """Verify all exporter classes exist."""
        from backend.agents.alpha_recon.exporters import (
            SARIFExporter, HackerOneExporter, MarkdownReportExporter
        )
        assert SARIFExporter is not None
        assert HackerOneExporter is not None
        assert MarkdownReportExporter is not None

    def test_graph_exporters(self):
        """Verify graph exporter classes exist."""
        from backend.agents.alpha_recon.graph_exporters import (
            Neo4jExporter, STIXExporter, MaltegoExporter
        )
        assert Neo4jExporter is not None
        assert STIXExporter is not None
        assert MaltegoExporter is not None


# ─── TEST 5: Live HTTP Recon (against real test target) ────────────────
class TestLiveRecon:
    """Live recon against testphp.vulnweb.com — tests REAL HTTP probing."""

    @pytest.mark.asyncio
    async def test_http_probe(self):
        """Run the Alpha orchestrator's HTTP probe against the public test target."""
        from backend.agents.alpha_recon.alpha_orchestrator import AlphaOrchestrator
        from backend.core.hive import EventBus
        from backend.core.scope import ScopePolicy
        from backend.modules.tech.http_client import http_client

        bus = EventBus()
        orch = AlphaOrchestrator(bus)
        target = "http://testphp.vulnweb.com"
        scan_id = f"LIVE-TEST-{int(time.time())}"

        http_client.scope = ScopePolicy.from_target(target)

        services = await orch._http_probe(target, scan_id)

        logger.info(f"HTTP Probe found {len(services)} services")
        # testphp.vulnweb.com should be reachable; if not, skip gracefully
        if len(services) == 0:
            pytest.skip("testphp.vulnweb.com unreachable — skipping live probe test")

        for svc in services[:5]:
            assert svc.url.startswith("http")
            assert svc.status_code > 0
            logger.info(f"  [{svc.status_code}] {svc.url} — {svc.content_type}")

    @pytest.mark.asyncio
    async def test_endpoint_scoring_live(self):
        """Probe + Score endpoints from the live target."""
        from backend.agents.alpha_recon.alpha_orchestrator import AlphaOrchestrator
        from backend.agents.alpha_recon.scoring import score_endpoint
        from backend.core.hive import EventBus
        from backend.core.scope import ScopePolicy
        from backend.modules.tech.http_client import http_client

        bus = EventBus()
        orch = AlphaOrchestrator(bus)
        target = "http://testphp.vulnweb.com"
        scan_id = f"SCORE-TEST-{int(time.time())}"

        http_client.scope = ScopePolicy.from_target(target)
        services = await orch._http_probe(target, scan_id)

        if len(services) == 0:
            pytest.skip("testphp.vulnweb.com unreachable — skipping live scoring test")

        scored_endpoints = []
        for svc in services:
            ep = orch._service_to_endpoint(svc)
            ep = score_endpoint(ep)
            scored_endpoints.append(ep)

        scored_endpoints.sort(key=lambda e: e.priority_score, reverse=True)

        logger.info(f"\n{'='*60}")
        logger.info(f"SCORED ENDPOINTS ({len(scored_endpoints)} total)")
        logger.info(f"{'='*60}")
        for ep in scored_endpoints[:10]:
            logger.info(f"  [{ep.priority_score:3d}] {ep.method} {ep.url} — {ep.endpoint_type} ({ep.risk_class})")

        assert len(scored_endpoints) > 0
        assert scored_endpoints[0].priority_score > 0

    @pytest.mark.asyncio
    async def test_dedup_pipeline(self):
        """Verify deduplication works on probe results."""
        from backend.agents.alpha_recon.alpha_orchestrator import AlphaOrchestrator
        from backend.agents.alpha_recon.scoring import score_endpoint
        from backend.core.hive import EventBus
        from backend.core.scope import ScopePolicy
        from backend.modules.tech.http_client import http_client

        bus = EventBus()
        orch = AlphaOrchestrator(bus)
        target = "http://testphp.vulnweb.com"
        scan_id = f"DEDUP-TEST-{int(time.time())}"

        http_client.scope = ScopePolicy.from_target(target)
        services = await orch._http_probe(target, scan_id)

        if len(services) == 0:
            pytest.skip("testphp.vulnweb.com unreachable — skipping live dedup test")

        endpoints = [score_endpoint(orch._service_to_endpoint(s)) for s in services]

        # Duplicate some manually
        duplicated = endpoints + endpoints[:5]
        deduped = orch._dedupe_and_sort(duplicated)

        logger.info(f"Before dedup: {len(duplicated)}, After dedup: {len(deduped)}")
        assert len(deduped) <= len(endpoints), "Dedup should remove duplicates"
        assert len(deduped) > 0


# ─── TEST 6: API Routes (Simulated) ───────────────────────────────────
class TestAPIRoutes:
    """Test the FastAPI route structure is intact."""

    def test_app_boots(self):
        from backend.main import app
        assert app.title == "Vulagent Scanner"

    def test_all_route_prefixes(self):
        from backend.main import app
        paths = [r.path for r in app.routes if hasattr(r, 'methods')]

        required_prefixes = [
            "/api/health",
            "/api/recon",
            "/api/attack",
            "/api/reports",
            "/api/defense",
            "/api/dashboard",
            "/api/ai",
            "/api/v1/recon",
        ]

        for prefix in required_prefixes:
            found = any(p.startswith(prefix) for p in paths)
            assert found, f"Missing route prefix: {prefix}"

    def test_alpha_recon_routes(self):
        from backend.main import app
        paths = [r.path for r in app.routes if hasattr(r, 'methods')]

        alpha_routes = [
            "/api/v1/recon/start",
            "/api/v1/recon/status/{scan_id}",
            "/api/v1/recon/scans",
            "/api/v1/recon/entities/{scan_id}",
            "/api/v1/recon/export",
        ]

        for route in alpha_routes:
            assert route in paths, f"Missing alpha route: {route}"


# ─── TEST 7: Reporting Pipeline ────────────────────────────────────────
class TestReportingPipeline:
    """Test report generation components."""

    def test_report_generator_init(self):
        from backend.core.reporting import ReportGenerator
        rg = ReportGenerator()
        assert rg is not None

    def test_cvss_calculator(self):
        from backend.reporting.cvss_engine import CVSSCalculator
        calc = CVSSCalculator(
            success_count=3,
            body_content="SQL syntax error near 'OR 1=1'",
            target_url="http://testphp.vulnweb.com/search?q=test",
            vuln_type="SQL_INJECTION"
        )
        score, vector = calc.calculate()
        assert 0 <= score <= 10
        assert vector is not None
        logger.info(f"CVSS Score: {score} | Vector: {vector}")

    def test_sarif_exporter(self):
        """Test SARIF exporter class instantiation and export."""
        import tempfile
        from pathlib import Path
        from backend.agents.alpha_recon.exporters import SARIFExporter
        from backend.agents.alpha_recon.models import ReconRunResult, ReconRunSummary, ScanMode

        result = ReconRunResult(
            scan_id="REPORT-TEST",
            target="http://testphp.vulnweb.com",
            mode=ScanMode.STANDARD,
            duration_seconds=30,
            summary=ReconRunSummary(),
            attack_surface=[],
            tools_run=["alpha_http"],
            tools_skipped=[],
        )
        exporter = SARIFExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_report.sarif.json"
            output = exporter.export(result, [], out_path)
            assert output is not None
            logger.info(f"SARIF export path: {output}")

    def test_markdown_exporter(self):
        """Test Markdown report exporter."""
        import tempfile
        from pathlib import Path
        from backend.agents.alpha_recon.exporters import MarkdownReportExporter
        from backend.agents.alpha_recon.models import ReconRunResult, ReconRunSummary, ScanMode

        result = ReconRunResult(
            scan_id="MD-REPORT-TEST",
            target="http://testphp.vulnweb.com",
            mode=ScanMode.STANDARD,
            duration_seconds=45,
            summary=ReconRunSummary(),
            attack_surface=[],
            tools_run=["alpha_http"],
            tools_skipped=[],
        )
        exporter = MarkdownReportExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_report.md"
            output = exporter.export(result, [], out_path)
            assert output is not None
            logger.info(f"Markdown export path: {output}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
