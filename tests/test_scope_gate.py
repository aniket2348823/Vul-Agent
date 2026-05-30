"""
Alpha V6 Test Suite — Scope Gate Tests.

Tests for:
- .gov/.mil/.edu TLD blocking
- Private network blocking
- Explicit authorization requirement
- In-scope URL filtering
- Wildcard subdomain matching
"""
import pytest
from backend.agents.alpha_v6.scope_gate import ScopeGate, ScopeGateViolation
from backend.agents.alpha_v6.models import ReconScope, ScanMode


def _make_scope(base_domain="example.com", mode=ScanMode.PASSIVE_ONLY,
                explicit_auth=False, allowed_hosts=None,
                denied_hosts=None, allowed_suffixes=None):
    return ReconScope(
        base_domain=base_domain,
        allowed_hosts=allowed_hosts or [],
        allowed_host_suffixes=allowed_suffixes or [],
        denied_hosts=denied_hosts or [],
        scan_mode=mode,
        max_rps=50,
        max_depth=3,
        explicit_authorization=explicit_auth,
    )


class TestGovMilBlocking:
    """Restricted TLD blocking."""

    def test_blocks_gov_domain(self):
        scope = _make_scope(base_domain="whitehouse.gov")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="restricted_tld"):
            gate.validate_target("https://whitehouse.gov")

    def test_blocks_mil_domain(self):
        scope = _make_scope(base_domain="army.mil")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="restricted_tld"):
            gate.validate_target("https://army.mil/portal")

    def test_blocks_edu_domain(self):
        scope = _make_scope(base_domain="mit.edu")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="restricted_tld"):
            gate.validate_target("https://mit.edu")

    def test_blocks_gov_uk(self):
        scope = _make_scope(base_domain="example.gov.uk")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="restricted_tld"):
            gate.validate_target("https://example.gov.uk")

    def test_allows_gov_with_explicit_auth(self):
        scope = _make_scope(base_domain="bugbounty.gov", explicit_auth=True)
        gate = ScopeGate(scope)
        gate.validate_target("https://bugbounty.gov")  # Should not raise

    def test_allows_regular_com(self):
        scope = _make_scope(base_domain="example.com")
        gate = ScopeGate(scope)
        gate.validate_target("https://example.com")  # Should not raise


class TestPrivateNetworkBlocking:
    """Private network protection."""

    def test_blocks_localhost(self):
        scope = _make_scope(base_domain="localhost")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="private_network"):
            gate.validate_target("http://localhost:8080")

    def test_blocks_127(self):
        scope = _make_scope(base_domain="127.0.0.1")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="private_network"):
            gate.validate_target("http://127.0.0.1")

    def test_blocks_192_168(self):
        scope = _make_scope(base_domain="192.168.1.1")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="private_network"):
            gate.validate_target("http://192.168.1.1")

    def test_blocks_10_x(self):
        scope = _make_scope(base_domain="10.0.0.5")
        gate = ScopeGate(scope)
        with pytest.raises(ScopeGateViolation, match="private_network"):
            gate.validate_target("http://10.0.0.5:3000")


class TestScopeFiltering:
    """In-scope URL filtering."""

    def test_base_domain_in_scope(self):
        scope = _make_scope(base_domain="example.com")
        gate = ScopeGate(scope)
        assert gate.is_in_scope("https://example.com/api/v1")

    def test_subdomain_in_scope(self):
        scope = _make_scope(base_domain="example.com")
        gate = ScopeGate(scope)
        assert gate.is_in_scope("https://api.example.com/users")
        assert gate.is_in_scope("https://staging.api.example.com")

    def test_different_domain_out_of_scope(self):
        scope = _make_scope(base_domain="example.com")
        gate = ScopeGate(scope)
        assert not gate.is_in_scope("https://evil.com/api")
        assert not gate.is_in_scope("https://notexample.com")

    def test_denied_hosts(self):
        scope = _make_scope(base_domain="example.com",
                            denied_hosts=["cdn.example.com"])
        gate = ScopeGate(scope)
        assert not gate.is_in_scope("https://cdn.example.com/asset.js")
        assert gate.is_in_scope("https://api.example.com")

    def test_allowed_hosts(self):
        scope = _make_scope(base_domain="example.com",
                            allowed_hosts=["partner.org"])
        gate = ScopeGate(scope)
        assert gate.is_in_scope("https://partner.org/api")
        assert gate.is_in_scope("https://example.com")

    def test_filter_in_scope(self):
        scope = _make_scope(base_domain="target.com")
        gate = ScopeGate(scope)
        urls = [
            "https://target.com/login",
            "https://api.target.com/users",
            "https://evil.com/steal",
            "https://cdn.target.com/main.js",
        ]
        filtered = gate.filter_in_scope(urls)
        assert len(filtered) == 3
        assert "https://evil.com/steal" not in filtered

    def test_metadata_ip_blocked(self):
        scope = _make_scope(base_domain="example.com")
        gate = ScopeGate(scope)
        assert not gate.is_in_scope("http://169.254.169.254/latest/meta-data")

    def test_empty_host_blocked(self):
        scope = _make_scope(base_domain="example.com")
        gate = ScopeGate(scope)
        assert not gate.is_in_scope("")
        assert not gate.is_in_scope("not-a-url")
