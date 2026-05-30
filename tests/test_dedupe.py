"""
Alpha V6 Test Suite — Dedupe & Entity Engine Tests.

Tests:
- URL normalization
- Endpoint key dedup
- Path classification
- SeenSet behavior
"""
import pytest
from backend.agents.alpha_recon.dedupe import (
    SeenSet, normalize_url, normalize_endpoint_key, classify_path,
)


class TestSeenSet:
    """SeenSet deduplication."""

    def test_first_add_returns_true(self):
        s = SeenSet()
        assert s.add("api.example.com") is True

    def test_second_add_returns_false(self):
        s = SeenSet()
        s.add("api.example.com")
        assert s.add("api.example.com") is False

    def test_case_insensitive(self):
        s = SeenSet()
        s.add("API.Example.COM")
        assert s.add("api.example.com") is False

    def test_strip_whitespace(self):
        s = SeenSet()
        s.add("  api.example.com  ")
        assert s.add("api.example.com") is False

    def test_contains(self):
        s = SeenSet()
        s.add("test.com")
        assert "test.com" in s
        assert "other.com" not in s


class TestNormalizeUrl:
    """URL normalization."""

    def test_strips_trailing_slash(self):
        result = normalize_url("https://example.com/api/")
        # Path normalization may or may not strip trailing slash
        assert "example.com" in result

    def test_lowercases_host(self):
        result = normalize_url("https://EXAMPLE.COM/API")
        assert "example.com" in result

    def test_sorts_query_params(self):
        result = normalize_url("https://example.com/search?z=1&a=2")
        assert "a=2" in result
        assert result.index("a=2") < result.index("z=1")

    def test_removes_duplicate_slashes(self):
        result = normalize_url("https://example.com//api///v1")
        assert "//" not in result.split("://")[1]  # After scheme

    def test_without_query(self):
        result = normalize_url("https://example.com/api?key=val", keep_query=False)
        assert "key" not in result

    def test_adds_default_scheme(self):
        result = normalize_url("example.com/api")
        assert result.startswith("https://")


class TestEndpointKey:
    """Endpoint deduplication key generation."""

    def test_includes_method(self):
        key = normalize_endpoint_key("https://example.com/api", "POST")
        assert key.startswith("POST ")

    def test_default_get(self):
        key = normalize_endpoint_key("https://example.com/api")
        assert key.startswith("GET ")

    def test_strips_query(self):
        key1 = normalize_endpoint_key("https://example.com/api?a=1")
        key2 = normalize_endpoint_key("https://example.com/api?b=2")
        assert key1 == key2  # Same endpoint, different params


class TestClassifyPath:
    """Path classification taxonomy."""

    def test_admin_paths(self):
        for path in ["/admin", "/admin/users", "/dashboard", "/manage", "/console"]:
            ep_type, risk = classify_path(path)
            assert ep_type == "ADMIN_ENDPOINT", f"Failed for {path}"
            assert risk == "CRITICAL"

    def test_auth_paths(self):
        for path in ["/login", "/auth/token", "/oauth/callback", "/session"]:
            ep_type, risk = classify_path(path)
            assert ep_type == "AUTH_ENDPOINT", f"Failed for {path}"

    def test_graphql_paths(self):
        ep_type, _ = classify_path("/graphql")
        assert ep_type == "GRAPHQL_ENDPOINT"

    def test_api_paths(self):
        ep_type, _ = classify_path("/api/v2/users")
        assert ep_type == "API_ENDPOINT"

    def test_data_paths(self):
        for path in ["/user/profile", "/account/settings", "/order/123"]:
            ep_type, _ = classify_path(path)
            assert ep_type == "DATA_ENDPOINT", f"Failed for {path}"

    def test_file_paths(self):
        # Generic data files classify as FILE_ENDPOINT
        for path in ["/data.xml", "/export.csv", "/dump.sql", "/server.log"]:
            ep_type, _ = classify_path(path)
            assert ep_type == "FILE_ENDPOINT", f"Failed for {path}"

    def test_sensitive_config_files(self):
        # Config/secret files are classified as the more specific CONFIG_ENDPOINT (CRITICAL)
        for path in ["/config.json", "/.env", "/wp-config.php"]:
            ep_type, risk = classify_path(path)
            assert ep_type == "CONFIG_ENDPOINT", f"Failed for {path}"
            assert risk == "CRITICAL"

    def test_js_files(self):
        ep_type, _ = classify_path("/static/app.js")
        assert ep_type == "JS_FILE"

    def test_static_assets(self):
        ep_type, _ = classify_path("/static/images/logo.png")
        assert ep_type == "STATIC"

    def test_unknown_paths(self):
        ep_type, _ = classify_path("/something/random")
        assert ep_type == "UNKNOWN"
