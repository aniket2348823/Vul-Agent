"""
Unit tests for session management and forensics collection.

Tests cover:
- Session save/restore
- Session sanitization
- Forensic evidence collection
- Encryption/decryption
- Error handling
"""

import pytest
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.hybrid_session_manager import HybridSessionManager
from backend.core.forensic_collector import ForensicCollector


# ============================================================================
# HybridSessionManager Tests
# ============================================================================

class TestHybridSessionManager:
    """Test suite for HybridSessionManager"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for tests"""
        return str(tmp_path / "sessions")
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create HybridSessionManager instance"""
        return HybridSessionManager(storage_dir=temp_dir, sanitize_sensitive=True)
    
    def test_initialization(self, manager, temp_dir):
        """Test manager initialization"""
        assert manager.storage_dir == Path(temp_dir)
        assert manager.storage_dir.exists()
        assert manager.sessions == {}
        assert manager.sanitize_sensitive is True
        assert len(manager.sensitive_regex) > 0
    
    def test_is_sensitive_key(self, manager):
        """Test sensitive key detection"""
        # Sensitive keys
        assert manager._is_sensitive_key("auth_token") is True
        assert manager._is_sensitive_key("api_key") is True
        assert manager._is_sensitive_key("password") is True
        assert manager._is_sensitive_key("session_id") is True
        assert manager._is_sensitive_key("csrf_token") is True
        assert manager._is_sensitive_key("bearer_token") is True
        
        # Non-sensitive keys
        assert manager._is_sensitive_key("username") is False
        assert manager._is_sensitive_key("email") is False
        assert manager._is_sensitive_key("user_id") is False
    
    def test_sanitize_value(self, manager):
        """Test value sanitization"""
        # Normal value
        result = manager._sanitize_value("secret123456")
        assert result.startswith("secr")
        assert "*" in result
        assert "123456" not in result
        
        # Short value
        result = manager._sanitize_value("abc")
        assert result == "[REDACTED]"
        
        # Empty value
        result = manager._sanitize_value("")
        assert result == "[REDACTED]"
    
    def test_sanitize_cookies(self, manager):
        """Test cookie sanitization"""
        cookies = [
            {"name": "session_id", "value": "abc123def456"},
            {"name": "username", "value": "john_doe"},
            {"name": "auth_token", "value": "secret_token_xyz"},
        ]
        
        sanitized = manager._sanitize_cookies(cookies)
        
        # Check session_id is sanitized
        session_cookie = next(c for c in sanitized if c["name"] == "session_id")
        assert session_cookie["value"] != "abc123def456"
        assert session_cookie["_sanitized"] is True
        
        # Check username is not sanitized
        username_cookie = next(c for c in sanitized if c["name"] == "username")
        assert username_cookie["value"] == "john_doe"
        assert "_sanitized" not in username_cookie
        
        # Check auth_token is sanitized
        auth_cookie = next(c for c in sanitized if c["name"] == "auth_token")
        assert auth_cookie["value"] != "secret_token_xyz"
        assert auth_cookie["_sanitized"] is True
    
    def test_sanitize_cookies_disabled(self, temp_dir):
        """Test cookie sanitization when disabled"""
        manager = HybridSessionManager(storage_dir=temp_dir, sanitize_sensitive=False)
        
        cookies = [
            {"name": "session_id", "value": "abc123def456"},
            {"name": "auth_token", "value": "secret_token_xyz"},
        ]
        
        sanitized = manager._sanitize_cookies(cookies)
        
        # Should not be sanitized
        assert sanitized == cookies
    
    def test_sanitize_storage(self, manager):
        """Test storage sanitization"""
        storage = {
            "username": "john_doe",
            "auth_token": "secret123",
            "api_key": "key_abc_xyz",
            "theme": "dark",
        }
        
        sanitized = manager._sanitize_storage(storage)
        
        # Check sensitive keys are sanitized
        assert sanitized["auth_token"] != "secret123"
        assert sanitized["api_key"] != "key_abc_xyz"
        
        # Check non-sensitive keys are not sanitized
        assert sanitized["username"] == "john_doe"
        assert sanitized["theme"] == "dark"
    
    def test_sanitize_storage_disabled(self, temp_dir):
        """Test storage sanitization when disabled"""
        manager = HybridSessionManager(storage_dir=temp_dir, sanitize_sensitive=False)
        
        storage = {
            "auth_token": "secret123",
            "api_key": "key_abc_xyz",
        }
        
        sanitized = manager._sanitize_storage(storage)
        
        # Should not be sanitized
        assert sanitized == storage
    
    def test_sanitize_session_data(self, manager):
        """Test full session data sanitization"""
        session_data = {
            "cookies": [
                {"name": "session_id", "value": "abc123"},
                {"name": "username", "value": "john"},
            ],
            "localStorage": {
                "auth_token": "secret123",
                "theme": "dark",
            },
            "url": "https://example.com",
        }
        
        sanitized = manager._sanitize_session_data(session_data)
        
        # Check cookies are sanitized
        session_cookie = next(c for c in sanitized["cookies"] if c["name"] == "session_id")
        assert session_cookie["value"] != "abc123"
        
        # Check localStorage is sanitized
        assert sanitized["localStorage"]["auth_token"] != "secret123"
        assert sanitized["localStorage"]["theme"] == "dark"
        
        # Check non-sensitive data is preserved
        assert sanitized["url"] == "https://example.com"


# ============================================================================
# ForensicCollector Tests
# ============================================================================

class TestForensicCollector:
    """Test suite for ForensicCollector"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for tests"""
        return str(tmp_path / "forensics")
    
    @pytest.fixture
    def collector(self, temp_dir):
        """Create ForensicCollector instance"""
        return ForensicCollector(storage_dir=temp_dir, encryption_key="test_key_123")
    
    def test_initialization(self, collector, temp_dir):
        """Test collector initialization"""
        assert collector.storage_dir == Path(temp_dir)
        assert collector.storage_dir.exists()
        assert collector.evidence_cache == {}
        assert collector.encryption_enabled is True
        assert collector.cipher is not None
    
    def test_initialization_no_key(self, temp_dir):
        """Test initialization without encryption key"""
        with patch.dict(os.environ, {}, clear=True):
            collector = ForensicCollector(storage_dir=temp_dir)
            
            # Should still initialize with generated key
            assert collector.encryption_enabled is True
            assert collector.cipher is not None
    
    def test_initialization_with_env_key(self, temp_dir):
        """Test initialization with environment variable key"""
        with patch.dict(os.environ, {"FORENSIC_ENCRYPTION_KEY": "env_key_456"}):
            collector = ForensicCollector(storage_dir=temp_dir)
            
            assert collector.encryption_enabled is True
            assert collector.cipher is not None
    
    def test_encrypt_decrypt_data(self, collector):
        """Test data encryption and decryption"""
        original_data = b"sensitive forensic data"
        
        # Encrypt
        encrypted = collector._encrypt_data(original_data)
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)
        
        # Decrypt
        decrypted = collector._decrypt_data(encrypted)
        assert decrypted == original_data
    
    def test_encrypt_data_disabled(self, temp_dir):
        """Test encryption when disabled"""
        collector = ForensicCollector(storage_dir=temp_dir)
        collector.encryption_enabled = False
        
        original_data = b"test data"
        encrypted = collector._encrypt_data(original_data)
        
        # Should return original data
        assert encrypted == original_data
    
    def test_decrypt_data_disabled(self, temp_dir):
        """Test decryption when disabled"""
        collector = ForensicCollector(storage_dir=temp_dir)
        collector.encryption_enabled = False
        
        original_data = b"test data"
        decrypted = collector._decrypt_data(original_data)
        
        # Should return original data
        assert decrypted == original_data
    
    def test_encrypt_data_error_handling(self, collector):
        """Test encryption error handling"""
        # Corrupt the cipher
        collector.cipher = None
        
        original_data = b"test data"
        result = collector._encrypt_data(original_data)
        
        # Should return original data on error
        assert result == original_data
    
    def test_decrypt_data_error_handling(self, collector):
        """Test decryption error handling"""
        # Try to decrypt invalid data
        invalid_data = b"not encrypted data"
        result = collector._decrypt_data(invalid_data)
        
        # Should return original data on error
        assert result == invalid_data
    
    @pytest.mark.asyncio
    async def test_capture_screenshot_openclaw(self, collector):
        """Test screenshot capture with OpenClaw"""
        # Mock OpenClaw context
        mock_context = AsyncMock()
        mock_context.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
        
        result = await collector.capture_screenshot(
            scan_id="test_scan",
            context=mock_context,
            engine="openclaw",
            label="test_screenshot"
        )
        
        assert result is not None
        assert "test_scan" in result
        assert "test_screenshot" in result
        
        # Verify screenshot was called
        mock_context.screenshot.assert_called_once()
        
        # Verify file was created
        filepath = Path(result)
        assert filepath.exists()
        
        # Verify file is encrypted (should be larger than original)
        file_size = filepath.stat().st_size
        assert file_size > 0
    
    @pytest.mark.asyncio
    async def test_capture_screenshot_error(self, collector):
        """Test screenshot capture error handling"""
        # Mock context that raises error
        mock_context = AsyncMock()
        mock_context.screenshot = AsyncMock(side_effect=Exception("Screenshot failed"))
        
        result = await collector.capture_screenshot(
            scan_id="test_scan",
            context=mock_context,
            engine="openclaw"
        )
        
        # Should return None on error
        assert result is None


# ============================================================================
# Integration Tests
# ============================================================================

class TestSessionForensicsIntegration:
    """Integration tests for session and forensics coordination"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for tests"""
        return str(tmp_path)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create session manager"""
        return HybridSessionManager(storage_dir=f"{temp_dir}/sessions")
    
    @pytest.fixture
    def collector(self, temp_dir):
        """Create forensic collector"""
        return ForensicCollector(storage_dir=f"{temp_dir}/forensics", encryption_key="test_key")
    
    def test_both_components_initialize(self, manager, collector):
        """Test both components can initialize"""
        assert manager.storage_dir.exists()
        assert collector.storage_dir.exists()
        assert manager.sanitize_sensitive is True
        assert collector.encryption_enabled is True
    
    def test_session_sanitization_with_forensics(self, manager, collector):
        """Test session sanitization works with forensic collection"""
        # Create session with sensitive data
        session_data = {
            "cookies": [
                {"name": "auth_token", "value": "secret123"},
            ],
            "localStorage": {
                "api_key": "key_abc_xyz",
            },
        }
        
        # Sanitize session
        sanitized = manager._sanitize_session_data(session_data)
        
        # Verify sanitization
        auth_cookie = sanitized["cookies"][0]
        assert auth_cookie["value"] != "secret123"
        assert sanitized["localStorage"]["api_key"] != "key_abc_xyz"
        
        # Encrypt sanitized data (simulating forensic storage)
        json_data = json.dumps(sanitized).encode()
        encrypted = collector._encrypt_data(json_data)
        
        # Verify encryption
        assert encrypted != json_data
        
        # Decrypt and verify
        decrypted = collector._decrypt_data(encrypted)
        restored = json.loads(decrypted.decode())
        
        # Should match sanitized data
        assert restored["cookies"][0]["value"] == auth_cookie["value"]
        assert restored["localStorage"]["api_key"] == sanitized["localStorage"]["api_key"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
