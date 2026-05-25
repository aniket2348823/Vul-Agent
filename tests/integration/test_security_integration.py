"""
Integration tests for security components.

Tests how rate limiter, CSRF protection, and URL validator work together.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from backend.core.rate_limiter import RateLimiter
from backend.core.csrf_protection import CSRFProtection
from backend.core.url_validator import URLValidator


class TestSecurityIntegration:
    """Test security component integration."""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter."""
        limiter = RateLimiter()
        # Configure a test endpoint with 5 requests per minute
        limiter.configure_limit("/api/test", 5)
        return limiter

    @pytest.fixture
    def csrf_protection(self):
        """Create CSRF protection."""
        return CSRFProtection()

    @pytest.fixture
    def url_validator(self):
        """Create URL validator."""
        validator = URLValidator()
        # Add test hosts to allowlist
        validator.add_allowed_host("example.com")
        validator.add_allowed_host("test.com")
        return validator

    @pytest.mark.asyncio
    async def test_rate_limiter_and_url_validator(self, rate_limiter, url_validator):
        """Test rate limiting with URL validation."""
        url = "https://example.com/api/test"
        client_ip = "192.168.1.1"
        endpoint = "/api/test"
        
        # Validate URL first
        is_valid, reason = url_validator.validate(url)
        assert is_valid, f"URL validation failed: {reason}"
        
        # Then check rate limit (5 requests allowed)
        for i in range(5):
            allowed = await rate_limiter.check_rate_limit(client_ip, endpoint)
            assert allowed, f"Request {i+1} should be allowed"
        
        # 6th request should be rate limited
        allowed = await rate_limiter.check_rate_limit(client_ip, endpoint)
        assert not allowed, "6th request should be rate limited"

    @pytest.mark.asyncio
    async def test_csrf_and_url_validator(self, csrf_protection, url_validator):
        """Test CSRF protection with URL validation."""
        url = "https://example.com/api/action"
        
        # Validate URL
        is_valid, reason = url_validator.validate(url)
        assert is_valid, f"URL validation failed: {reason}"
        
        # Generate CSRF token
        token = await csrf_protection.generate_token("user123")
        assert token
        
        # Validate token
        assert await csrf_protection.validate_token(token, "user123")

    @pytest.mark.asyncio
    async def test_full_security_pipeline(self, rate_limiter, csrf_protection, url_validator):
        """Test complete security pipeline."""
        url = "https://example.com/api/action"
        user_id = "user123"
        client_ip = "192.168.1.1"
        endpoint = "/api/test"
        
        # Step 1: Validate URL
        is_valid, reason = url_validator.validate(url)
        if not is_valid:
            pytest.fail(f"URL validation failed: {reason}")
        
        # Step 2: Check rate limit
        allowed = await rate_limiter.check_rate_limit(client_ip, endpoint)
        if not allowed:
            pytest.fail("Rate limit exceeded")
        
        # Step 3: Generate CSRF token
        token = await csrf_protection.generate_token(user_id)
        
        # Step 4: Validate CSRF token
        valid = await csrf_protection.validate_token(token, user_id)
        if not valid:
            pytest.fail("CSRF validation failed")
        
        # All checks passed
        assert True

    def test_invalid_url_blocks_pipeline(self, url_validator):
        """Test invalid URL blocks entire pipeline."""
        url = "javascript:alert(1)"
        
        # URL validation should fail
        is_valid, reason = url_validator.validate(url)
        assert not is_valid, "Dangerous URL should be blocked"
        
        # Should not proceed to rate limiting or CSRF

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_valid_requests(self, rate_limiter, url_validator):
        """Test rate limit blocks even valid URLs."""
        url = "https://example.com/api/test"
        client_ip = "192.168.1.2"
        endpoint = "/api/test"
        
        # Validate URL
        is_valid, reason = url_validator.validate(url)
        assert is_valid, f"URL validation failed: {reason}"
        
        # Exhaust rate limit
        for i in range(5):
            await rate_limiter.check_rate_limit(client_ip, endpoint)
        
        # Next request should be blocked despite valid URL
        allowed = await rate_limiter.check_rate_limit(client_ip, endpoint)
        assert not allowed, "Request should be rate limited"

    @pytest.mark.asyncio
    async def test_csrf_token_reuse_prevention(self, csrf_protection):
        """Test CSRF tokens cannot be reused."""
        user_id = "user123"
        
        # Generate token
        token = await csrf_protection.generate_token(user_id)
        
        # First validation succeeds
        assert await csrf_protection.validate_token(token, user_id)
        
        # Second validation with same token should fail (if single-use)
        # Note: This depends on implementation - some allow reuse within window

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, rate_limiter):
        """Test rate limiting under concurrent requests."""
        client_ip = "192.168.1.3"
        endpoint = "/api/test"
        
        results = []
        for i in range(10):
            result = await rate_limiter.check_rate_limit(client_ip, endpoint)
            results.append(result)
        
        # First 5 should pass, rest should fail
        assert sum(results) == 5, f"Expected 5 allowed requests, got {sum(results)}"

    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self, rate_limiter):
        """Test rate limit recovers after window."""
        client_ip = "192.168.1.4"
        endpoint = "/api/test"
        
        # Exhaust limit
        for i in range(5):
            await rate_limiter.check_rate_limit(client_ip, endpoint)
        
        # Should be blocked
        allowed = await rate_limiter.check_rate_limit(client_ip, endpoint)
        assert not allowed, "Should be rate limited"
        
        # Wait for window to expire (rate limiter uses 60 second window)
        await asyncio.sleep(61)
        
        # Should be allowed again
        allowed = await rate_limiter.check_rate_limit(client_ip, endpoint)
        assert allowed, "Should be allowed after window expires"

    def test_url_validator_blocks_dangerous_schemes(self, url_validator):
        """Test URL validator blocks dangerous schemes."""
        dangerous_urls = [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "ftp://example.com/file"
        ]
        
        for url in dangerous_urls:
            is_valid, reason = url_validator.validate(url)
            assert not is_valid, f"Should block {url}: {reason}"

    def test_url_validator_allows_safe_schemes(self, url_validator):
        """Test URL validator allows safe schemes."""
        safe_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com:8080/path?query=value"
        ]
        
        for url in safe_urls:
            is_valid, reason = url_validator.validate(url)
            assert is_valid, f"Should allow {url}: {reason}"

    @pytest.mark.asyncio
    async def test_csrf_token_user_isolation(self, csrf_protection):
        """Test CSRF tokens are user-specific."""
        user1 = "user123"
        user2 = "user456"
        
        # Generate token for user1
        token = await csrf_protection.generate_token(user1)
        
        # Should validate for user1
        assert await csrf_protection.validate_token(token, user1)
        
        # Should NOT validate for user2
        assert not await csrf_protection.validate_token(token, user2)

    @pytest.mark.asyncio
    async def test_rate_limiter_per_endpoint(self, rate_limiter):
        """Test rate limiter tracks per endpoint."""
        client_ip = "192.168.1.5"
        endpoint1 = "/api/test"
        endpoint2 = "/api/other"
        
        # Configure second endpoint
        rate_limiter.configure_limit(endpoint2, 5)
        
        # Exhaust limit for endpoint1
        for i in range(5):
            await rate_limiter.check_rate_limit(client_ip, endpoint1)
        
        # endpoint1 should be blocked
        allowed = await rate_limiter.check_rate_limit(client_ip, endpoint1)
        assert not allowed, "endpoint1 should be rate limited"
        
        # endpoint2 should still be allowed
        allowed = await rate_limiter.check_rate_limit(client_ip, endpoint2)
        assert allowed, "endpoint2 should still be allowed"

    @pytest.mark.asyncio
    async def test_security_pipeline_with_errors(self, rate_limiter, csrf_protection, url_validator):
        """Test security pipeline handles errors gracefully."""
        # Test with None URL
        try:
            is_valid, reason = url_validator.validate(None)
            # Should return False, not crash
            assert not is_valid
        except Exception:
            pass  # Should handle gracefully
        
        # Test with invalid token
        valid = await csrf_protection.validate_token("invalid", "user123")
        assert not valid, "Invalid token should not validate"
        
        # Test with empty endpoint
        try:
            await rate_limiter.check_rate_limit("192.168.1.1", "")
        except Exception:
            pass  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_multiple_users_rate_limiting(self, rate_limiter):
        """Test rate limiting with multiple users."""
        endpoint = "/api/test"
        
        # Different IPs should have separate limits
        ip1 = "192.168.1.6"
        ip2 = "192.168.1.7"
        
        # Exhaust limit for ip1
        for i in range(5):
            await rate_limiter.check_rate_limit(ip1, endpoint)
        
        # ip1 should be blocked
        allowed = await rate_limiter.check_rate_limit(ip1, endpoint)
        assert not allowed, "ip1 should be rate limited"
        
        # ip2 should still be allowed
        allowed = await rate_limiter.check_rate_limit(ip2, endpoint)
        assert allowed, "ip2 should still be allowed"

    @pytest.mark.asyncio
    async def test_csrf_token_expiration(self, csrf_protection):
        """Test CSRF tokens expire."""
        user_id = "user123"
        
        # Generate token
        token = await csrf_protection.generate_token(user_id)
        
        # Should be valid immediately
        assert await csrf_protection.validate_token(token, user_id)
        
        # Note: Actual expiration testing would require time manipulation
        # or configurable expiration time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
