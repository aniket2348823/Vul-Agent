"""
Alpha V6 Test Suite — Event Schema Tests.

Tests that all event schemas validate correctly and reject invalid data.
"""
import pytest
import time
from backend.agents.alpha_recon.event_schemas import (
    PhaseStartedEvent, PhaseCompletedEvent,
    ToolStartedEvent, ToolCompletedEvent, ToolSkippedEvent,
    EntityDiscoveredEvent, VulnCandidateEvent, SecretFoundEvent,
    ScopeViolationEvent, ApprovalRequiredEvent, ApprovalResponseEvent,
    ReconStartedEvent, ReconPacketEvent, ReconCompleteEvent,
    OOBInteractionEvent, validate_event, EVENT_SCHEMAS,
)


class TestEventCreation:
    """All events can be constructed with required fields."""

    def test_phase_started(self):
        e = PhaseStartedEvent(scan_id="s1", phase="passive_intelligence",
                               phase_index=0, total_phases=7)
        assert e.event_type == "RECON_PHASE_STARTED"
        assert e.scan_id == "s1"
        assert e.timestamp > 0

    def test_phase_completed(self):
        e = PhaseCompletedEvent(scan_id="s1", phase="passive_intelligence",
                                 entities_found=42, tools_run=3, duration_ms=5000)
        assert e.entities_found == 42

    def test_tool_started(self):
        e = ToolStartedEvent(scan_id="s1", tool_name="subfinder",
                              phase="passive_intelligence")
        assert e.event_type == "RECON_TOOL_STARTED"

    def test_tool_completed(self):
        e = ToolCompletedEvent(scan_id="s1", tool_name="subfinder",
                                phase="passive_intelligence", status="finished",
                                exit_code=0, duration_ms=12000, output_bytes=8192)
        assert e.status == "finished"

    def test_tool_skipped(self):
        e = ToolSkippedEvent(scan_id="s1", tool_name="amass",
                              phase="passive_intelligence",
                              reason="not_installed")
        assert e.reason == "not_installed"

    def test_entity_discovered(self):
        e = EntityDiscoveredEvent(scan_id="s1", kind="subdomain",
                                   label="api.example.com", confidence=0.95,
                                   source_tool="subfinder")
        assert e.kind == "subdomain"

    def test_vuln_candidate(self):
        e = VulnCandidateEvent(scan_id="s1", name="Log4Shell",
                                severity="critical",
                                target="https://example.com/api",
                                confidence=0.98)
        assert e.severity == "critical"

    def test_secret_found(self):
        e = SecretFoundEvent(scan_id="s1", secret_type="aws_key",
                              redacted_value="AKIA****XXXX")
        assert e.event_type == "RECON_SECRET_FOUND"

    def test_scope_violation(self):
        e = ScopeViolationEvent(scan_id="s1", target="https://evil.com",
                                 reason="out_of_scope")
        assert e.target == "https://evil.com"

    def test_approval_required(self):
        e = ApprovalRequiredEvent(scan_id="s1", approval_id="ap_1",
                                   phase="directory_discovery",
                                   tools=["feroxbuster", "ffuf"])
        assert len(e.tools) == 2

    def test_recon_started(self):
        e = ReconStartedEvent(scan_id="s1", target="https://example.com",
                               mode="STANDARD")
        assert e.event_type == "RECON_STARTED"

    def test_recon_packet(self):
        e = ReconPacketEvent(scan_id="s1", phase="passive_intelligence",
                              subdomains=["a.example.com", "b.example.com"])
        assert len(e.subdomains) == 2

    def test_recon_complete(self):
        e = ReconCompleteEvent(scan_id="s1", target="https://example.com",
                                mode="STANDARD", duration_seconds=120.5,
                                total_subdomains=42, total_endpoints=150)
        assert e.total_subdomains == 42

    def test_oob_interaction(self):
        e = OOBInteractionEvent(scan_id="s1", protocol="dns",
                                 remote_address="1.2.3.4")
        assert e.severity == "high"


class TestEventValidation:
    """Validate events through the registry."""

    def test_validate_known_event(self):
        event = validate_event("RECON_PHASE_STARTED", {
            "scan_id": "s1", "phase": "passive_intelligence"})
        assert event.event_type == "RECON_PHASE_STARTED"

    def test_validate_unknown_event_raises(self):
        with pytest.raises(ValueError, match="Unknown event type"):
            validate_event("INVALID_EVENT", {"scan_id": "s1"})

    def test_all_event_types_registered(self):
        assert len(EVENT_SCHEMAS) == 15


class TestEventSerialization:
    """Events serialize to dict/JSON correctly."""

    def test_model_dump(self):
        e = ToolCompletedEvent(scan_id="s1", tool_name="httpx",
                                phase="http_probing", status="finished")
        d = e.model_dump()
        assert d["event_type"] == "RECON_TOOL_COMPLETED"
        assert d["scan_id"] == "s1"
        assert isinstance(d["timestamp"], float)
