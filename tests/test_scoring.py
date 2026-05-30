"""
Alpha V6 Test Suite — Scoring Tests.

Tests endpoint scoring taxonomy:
- Base score classification
- Parameter risk boosts
- Authentication state scoring
- Technology risk factors
- CDN/WAF penalties
- Multi-source bonus
"""
import pytest
from backend.agents.alpha_recon.scoring import score_endpoint, score_entity_priority
from backend.agents.alpha_recon.models import EndpointFinding, EndpointParameter


def _make_endpoint(url="/api/v1/users", method="GET", status=200,
                    auth_required=False, source="crawled", technologies=None,
                    params=None, endpoint_type="UNKNOWN"):
    return EndpointFinding(
        url=f"https://example.com{url}",
        method=method,
        status_code=status,
        endpoint_type=endpoint_type,
        source=source,
        auth_required=auth_required,
        technologies=technologies or [],
        parameters=params or [],
        normalized_path=url,
    )


class TestBaseClassification:
    """Endpoint type classification from URL patterns."""

    def test_admin_endpoint(self):
        ep = _make_endpoint("/admin/dashboard")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "ADMIN_ENDPOINT"
        assert scored.priority_score >= 80

    def test_auth_endpoint(self):
        ep = _make_endpoint("/api/v1/login")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "AUTH_ENDPOINT"
        assert scored.priority_score >= 80

    def test_payment_endpoint(self):
        ep = _make_endpoint("/checkout/payment")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "PAYMENT_ENDPOINT"
        assert scored.priority_score >= 80

    def test_graphql_endpoint(self):
        ep = _make_endpoint("/graphql")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "GRAPHQL_ENDPOINT"

    def test_debug_endpoint(self):
        ep = _make_endpoint("/actuator/health")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "DEBUG_ENDPOINT"
        assert scored.priority_score >= 85

    def test_config_endpoint(self):
        ep = _make_endpoint("/.env")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "CONFIG_ENDPOINT"
        assert scored.priority_score >= 80

    def test_static_endpoint(self):
        ep = _make_endpoint("/static/style.css")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "STATIC"
        assert scored.priority_score <= 30

    def test_js_file(self):
        ep = _make_endpoint("/static/app.js")
        scored = score_endpoint(ep)
        assert scored.endpoint_type == "JS_FILE"
        assert scored.priority_score <= 50


class TestParameterRisk:
    """Parameter-based risk boosts."""

    def test_id_param_boost(self):
        ep = _make_endpoint(
            "/api/users",
            params=[EndpointParameter(name="user_id", value_type="numeric")])
        scored = score_endpoint(ep)
        assert scored.priority_score > 60
        assert any("risky_param" in r or "id_param" in r for r in scored.score_reasons)

    def test_file_param_boost(self):
        ep = _make_endpoint(
            "/download",
            params=[EndpointParameter(name="file", value_type="string")])
        scored = score_endpoint(ep)
        assert any("risky_param:file" in r for r in scored.score_reasons)

    def test_url_param_boost(self):
        ep = _make_endpoint(
            "/proxy",
            params=[EndpointParameter(name="url", value_type="string")])
        scored = score_endpoint(ep)
        assert any("risky_param:url" in r for r in scored.score_reasons)

    def test_cmd_param_highest_risk(self):
        ep = _make_endpoint(
            "/execute",
            params=[EndpointParameter(name="cmd", value_type="string")])
        scored = score_endpoint(ep)
        assert any("risky_param:cmd" in r for r in scored.score_reasons)


class TestAuthScoring:
    """Authentication state scoring."""

    def test_no_auth_boost(self):
        ep = _make_endpoint("/api/data", auth_required=False, status=200)
        scored = score_endpoint(ep)
        assert any("no_auth" in r for r in scored.score_reasons)

    def test_auth_required_still_interesting(self):
        ep = _make_endpoint("/api/data", auth_required=True, status=401)
        scored = score_endpoint(ep)
        assert any("auth_required_confirmable" in r for r in scored.score_reasons)


class TestTechnologyRisk:
    """Technology-based risk factors."""

    def test_struts_boost(self):
        ep = _make_endpoint("/app/action", technologies=["Apache Struts"])
        scored = score_endpoint(ep)
        assert any("technology_risk" in r for r in scored.score_reasons)

    def test_phpmyadmin_boost(self):
        ep = _make_endpoint("/pma", technologies=["phpMyAdmin"])
        scored = score_endpoint(ep)
        assert any("technology_risk" in r for r in scored.score_reasons)


class TestWAFPenalty:
    """CDN/WAF detection penalty."""

    def test_cloudflare_penalty(self):
        ep = _make_endpoint("/api/users", technologies=["Cloudflare"])
        scored = score_endpoint(ep)
        assert any("waf_detected" in r for r in scored.score_reasons)
        # Score should be lower than without WAF
        ep_no_waf = _make_endpoint("/api/users")
        scored_no_waf = score_endpoint(ep_no_waf)
        assert scored.priority_score < scored_no_waf.priority_score


class TestSourceReliability:
    """Source-based reliability weighting."""

    def test_openapi_source_boost(self):
        ep = _make_endpoint("/api/users", source="openapi")
        scored = score_endpoint(ep)
        assert any("high_confidence_source:openapi" in r for r in scored.score_reasons)

    def test_historical_source_boost(self):
        ep = _make_endpoint("/api/old", source="historical_wayback")
        scored = score_endpoint(ep)
        assert any("historical_resurfaced" in r for r in scored.score_reasons)


class TestEntityPriority:
    """Generic entity priority scoring."""

    def test_vuln_candidate_highest(self):
        p = score_entity_priority("vulnerability_candidate", 0.95, {})
        assert p > 0.9

    def test_subdomain_moderate(self):
        p = score_entity_priority("subdomain", 0.8, {})
        assert 0.3 <= p <= 0.6

    def test_static_lowest(self):
        p = score_entity_priority("favicon", 0.5, {})
        assert p < 0.1

    def test_confidence_matters(self):
        high = score_entity_priority("secret", 0.95, {})
        low = score_entity_priority("secret", 0.3, {})
        assert high > low
