"""
Unit tests for security components
Tests RateLimiter, URLValidator, and CSRFProtection
"""

import pytest
import time
from unittest.mock import Mock, patch
from backend.core.rate_limiter import RateLimiter
from backend.core.url_validator import URLValidator
from backend.core.csrf_protection import CSRFProtection


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a RateLimiter instance."""
        return RateLimiter()
    
    def test_allow_request_within_limit(self, rate_limiter):
        """Test requests within limit are allowed."""
        client_id = "192.168.1.1"
        endpoint = "/api/test"
        
        # First request should be allowed
        allowed, retry_after = rate_limiter.check_rate_limit(client_id, endpoint)
        assert allowed is True
        assert retry_after is None
    
    def test_block_request_over_limit(self, rate_limiter):
        """Test requests over limit are blocked."""
        client_id = "192.168.1.1"
        endpoint = "/api/test"
        
        # Exhaust rate limit (default 60 req/min)
        for _ in range(60):
            rate_limiter.check_rate_limit(client_id, endpoint)
        
        # Next request should be blocked
        allowed, retry_after = rate_limiter.check_rate_limit(client_id, endpoint)
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_different_clients_independent(self, rate_limiter):
        """Test different clients have independent limits."""
        client1 = "192.168.1.1"
        client2 = "192.168.1.2"
        endpoint = "/api/test"
        
        # Exhaust client1's limit
        for _ in range(60):
            rate_limiter.check_rate_limit(client1, endpoint)
        
        # Client2 should still be allowed
        allowed, _ = rate_limiter.check_rate_limit(client2, endpoint)
        assert allowed is True
    
    def test_different_endpoints_independent(self, rate_limiter):
        """Test different endpoints have independent limits."""
        client = "192.168.1.1"
        endpoint1 = "/api/test1"
        endpoint2 = "/api/test2"
        
        # Exhaust endpoint1's limit
        for _ in range(60):
            rate_limiter.check_rate_limit(client, endpoint1)
        
        # endpoint2 should still be allowed
        allowed, _ = rate_limiter.check_rate_limit(client, endpoint2)
        assert allowed is True
    
    def test_custom_endpoint_limits(self, rate_limiter):
        """Test custom limits for specific endpoints."""
        client = "192.168.1.1"
        endpoint = "/api/dashboard/stats"
        
        # Dashboard endpoint has 120 req/min limit
        for _ in range(120):
            allowed, _ = rate_limiter.check_rate_limit(client, endpoint)
            assert allowed is True
        
        # 121st request should be blocked
        allowed, _ = rate_limiter.check_rate_limit(client, endpoint)
        assert allowed is False
    
    def test_token_refill(self, rate_limiter):
        """Test tokens refill over time."""
        client = "192.168.1.1"
        endpoint = "/api/test"
        
        # Use some tokens
        for _ in range(30):
            rate_limiter.check_rate_limit(client, endpoint)
        
        # Wait for refill (mock time)
        with patch('time.time') as mock_time:
            mock_time.return_value = time.time() + 60  # 1 minute later
            
            # Should have refilled
            allowed, _ = rate_limiter.check_rate_limit(client, endpoint)
            assert allowed is True
    
    def test_cleanup_old_buckets(self, rate_limiter):
        """Test cleanup of old buckets."""
        # Create some buckets
        for i in range(10):
            rate_limiter.check_rate_limit(f"192.168.1.{i}", "/api/test")
        
        assert len(rate_limiter._buckets) == 10
        
        # Mock old timestamps
        for key in rate_limiter._buckets:
            rate_limiter._buckets[key]["last_update"] = time.time() - 7200  # 2 hours ago
        
        # Cleanup
        rate_limiter.cleanup_old_buckets()
        
        # Old buckets should be removed
        assert len(rate_limiter._buckets) == 0


class TestURLValidator:
    """Test URLValidator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create a URLValidator instance."""
        return URLValidator()
    
    def test_validate_allowed_url(self, validator):
        """Test validation of allowed URLs."""
        valid, reason = validator.validate_url("http://localhost:8080/test")
        assert valid is True
        assert reason is None
    
    def test_block_aws_metadata(self, validator):
        """Test blocking AWS metadata endpoint."""
        valid, reason = validator.validate_url("http://169.254.169.254/latest/meta-data/")
        assert valid is False
        assert "cloud metadata" in reason.lower()
    
    def test_block_gcp_metadata(self, validator):
        """Test blocking GCP metadata endpoint."""
        valid, reason = validator.validate_url("http://metadata.google.internal/")
        assert valid is False
        assert "cloud metadata" in reason.lower()
    
    def test_block_azure_metadata(self, validator):
        """Test blocking Azure metadata endpoint."""
        valid, reason = validator.validate_url("http://metadata.azure.com/")
        assert valid is False
        assert "cloud metadata" in reason.lower()
    
    def test_block_file_protocol(self, validator):
        """Test blocking file:// protocol."""
        valid, reason = validator.validate_url("file:///etc/passwd")
        assert valid is False
        assert "dangerous protocol" in reason.lower()
    
    def test_block_ftp_protocol(self, validator):
        """Test blocking ftp:// protocol."""
        valid, reason = validator.validate_url("ftp://example.com/file.txt")
        assert valid is False
        assert "dangerous protocol" in reason.lower()
    
    def test_block_gopher_protocol(self, validator):
        """Test blocking gopher:// protocol."""
        valid, reason = validator.validate_url("gopher://example.com/")
        assert valid is False
        assert "dangerous protocol" in reason.lower()
    
    def test_block_injection_characters(self, validator):
        """Test blocking URLs with injection characters."""
        urls = [
            "http://example.com/test?param=value;rm -rf /",
            "http://example.com/test|whoami",
            "http://example.com/test`id`",
        ]
        
        for url in urls:
            valid, reason = validator.validate_url(url)
            assert valid is False
            assert "injection" in reason.lower()
    
    def test_allow_localhost(self, validator):
        """Test allowing localhost URLs."""
        urls = [
            "http://localhost:8080/",
            "http://127.0.0.1:3000/",
            "http://0.0.0.0:5000/",
        ]
        
        for url in urls:
            valid, reason = validator.validate_url(url)
            assert valid is True
    
    def test_allow_private_ips(self, validator):
        """Test allowing private IP ranges."""
        urls = [
            "http://192.168.1.1/",
            "http://10.0.0.1/",
            "http://172.16.0.1/",
        ]
        
        for url in urls:
            valid, reason = validator.validate_url(url)
            assert valid is True
    
    def test_allow_test_domains(self, validator):
        """Test allowing .test domains."""
        valid, reason = validator.validate_url("http://example.test/")
        assert valid is True
    
    def test_custom_allowed_hosts(self):
        """Test custom allowed hosts."""
        validator = URLValidator(allowed_hosts=["example.com", "test.com"])
        
        valid, _ = validator.validate_url("http://example.com/")
        assert valid is True
        
        valid, _ = validator.validate_url("http://test.com/")
        assert valid is True
        
        valid, _ = validator.validate_url("http://other.com/")
        assert valid is False
    
    def test_invalid_url_format(self, validator):
        """Test handling of invalid URL format."""
        valid, reason = validator.validate_url("not-a-url")
        assert valid is False
        assert "invalid" in reason.lower()


class TestCSRFProtection:
    """Test CSRFProtection functionality."""
    
    @pytest.fixture
    def csrf(self):
        """Create a CSRFProtection instance."""
        return CSRFProtection()
    
    def test_generate_token(self, csrf):
        """Test CSRF token generation."""
        session_id = "test_session_123"
        token = csrf.generate_token(session_id)
        
        assert token is not None
        assert len(token) == 64  # 32 bytes hex = 64 chars
        assert session_id in csrf._tokens
    
    def test_validate_valid_token(self, csrf):
        """Test validation of valid token."""
        session_id = "test_session_123"
        token = csrf.generate_token(session_id)
        
        valid = csrf.validate_token(session_id, token)
        assert valid is True
    
    def test_validate_invalid_token(self, csrf):
        """Test validation of invalid token."""
        session_id = "test_session_123"
        csrf.generate_token(session_id)
        
        valid = csrf.validate_token(session_id, "invalid_token")
        assert valid is False
    
    def test_validate_wrong_session(self, csrf):
        """Test validation with wrong session ID."""
        session_id1 = "session_1"
        session_id2 = "session_2"
        
        token = csrf.generate_token(session_id1)
        
        valid = csrf.validate_token(session_id2, token)
        assert valid is False
    
    def test_token_consumption(self, csrf):
        """Test token is consumed after use."""
        session_id = "test_session_123"
        token = csrf.generate_token(session_id)
        
        # First validation should succeed
        valid1 = csrf.validate_token(session_id, token, consume=True)
        assert valid1 is True
        
        # Second validation should fail (token consumed)
        valid2 = csrf.validate_token(session_id, token, consume=True)
        assert valid2 is False
    
    def test_token_expiry(self, csrf):
        """Test token expiry."""
        session_id = "test_session_123"
        token = csrf.generate_token(session_id)
        
        # Mock expired token
        csrf._tokens[session_id][token] = time.time() - 7200  # 2 hours ago
        
        valid = csrf.validate_token(session_id, token)
        assert valid is False
    
    def test_cleanup_expired_tokens(self, csrf):
        """Test cleanup of expired tokens."""
        # Generate some tokens
        for i in range(5):
            csrf.generate_token(f"session_{i}")
        
        # Mock expired timestamps
        for session_id in csrf._tokens:
            for token in csrf._tokens[session_id]:
                csrf._tokens[session_id][token] = time.time() - 7200
        
        # Cleanup
        csrf.cleanup_expired_tokens()
        
        # All tokens should be removed
        assert len(csrf._tokens) == 0
    
    def test_multiple_tokens_per_session(self, csrf):
        """Test multiple tokens for same session."""
        session_id = "test_session_123"
        
        token1 = csrf.generate_token(session_id)
        token2 = csrf.generate_token(session_id)
        
        assert token1 != token2
        
        # Both should be valid
        assert csrf.validate_token(session_id, token1) is True
        assert csrf.validate_token(session_id, token2) is True
    
    def test_token_uniqueness(self, csrf):
        """Test tokens are unique."""
        session_id = "test_session_123"
        
        tokens = set()
        for _ in range(100):
            token = csrf.generate_token(session_id)
            tokens.add(token)
        
        # All tokens should be unique
        assert len(tokens) == 100
    
    def test_custom_expiry_time(self):
        """Test custom token expiry time."""
        csrf = CSRFProtection(token_expiry=60)  # 1 minute
        
        session_id = "test_session_123"
        token = csrf.generate_token(session_id)
        
        # Mock token just expired
        csrf._tokens[session_id][token] = time.time() - 61
        
        valid = csrf.validate_token(session_id, token)
        assert valid is False


class TestSecurityIntegration:
    """Test integration between security components."""
    
    def test_rate_limiter_with_csrf(self):
        """Test rate limiter doesn't interfere with CSRF."""
        rate_limiter = RateLimiter()
        csrf = CSRFProtection()
        
        client_id = "192.168.1.1"
        session_id = "test_session"
        
        # Generate CSRF token
        token = csrf.generate_token(session_id)
        
        # Check rate limit
        allowed, _ = rate_limiter.check_rate_limit(client_id, "/api/test")
        
        # Both should work independently
        assert allowed is True
        assert csrf.validate_token(session_id, token) is True
    
    def test_url_validator_with_rate_limiter(self):
        """Test URL validator works with rate limiter."""
        validator = URLValidator()
        rate_limiter = RateLimiter()
        
        url = "http://localhost:8080/test"
        client_id = "192.168.1.1"
        
        # Validate URL
        valid, _ = validator.validate_url(url)
        
        # Check rate limit
        allowed, _ = rate_limiter.check_rate_limit(client_id, "/api/test")
        
        # Both should pass
        assert valid is True
        assert allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
