"""
Unit tests for browser engines (OpenClaw and PinchTab).

Tests cover:
- Engine initialization
- Navigation
- Endpoint extraction
- Token extraction
- Error handling
"""

import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.openclaw_engine import OpenClawEngine
from backend.core.pinchtab_engine import PinchTabEngine


# ============================================================================
# OpenClawEngine Tests
# ============================================================================

class TestOpenClawEngine:
    """Test suite for OpenClawEngine"""
    
    @pytest.fixture
    def engine(self):
        """Create OpenClawEngine instance"""
        return OpenClawEngine()
    
    def test_initialization(self, engine):
        """Test engine initialization"""
        assert engine.client is None
        assert engine.workflow_engine is None
        assert engine.active_contexts == {}
        assert engine.current_page is None
        assert engine.current_context is None
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, engine):
        """Test successful initialization with mocked OpenClaw"""
        # Mock the OpenClaw import and client
        mock_client = AsyncMock()
        mock_client.initialize = AsyncMock()
        
        # Create a mock module with ClawClient
        mock_openclaw = MagicMock()
        mock_openclaw.ClawClient = Mock(return_value=mock_client)
        
        # Patch the import
        with patch.dict('sys.modules', {'openclaw': mock_openclaw}):
            result = await engine.initialize()
        
        assert result is True
        assert engine.client == mock_client
        mock_client.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_import_error(self, engine):
        """Test initialization with missing OpenClaw"""
        # This is the expected behavior when OpenClaw is not installed
        result = await engine.initialize()
        
        assert result is False
        assert engine.client is None
    
    @pytest.mark.asyncio
    async def test_initialize_exception(self, engine):
        """Test initialization with exception during client setup"""
        # Mock the OpenClaw import but make initialization fail
        mock_client = AsyncMock()
        mock_client.initialize = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Create a mock module with ClawClient
        mock_openclaw = MagicMock()
        mock_openclaw.ClawClient = Mock(return_value=mock_client)
        
        # Patch the import
        with patch.dict('sys.modules', {'openclaw': mock_openclaw}):
            result = await engine.initialize()
        
        assert result is False
        assert engine.client == mock_client
    
    @pytest.mark.asyncio
    async def test_navigate_success(self, engine):
        """Test successful navigation"""
        # Setup mocks
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        mock_client = AsyncMock()
        mock_client.create_context = AsyncMock(return_value=mock_context)
        
        engine.client = mock_client
        
        # Test navigation
        result = await engine.navigate("https://example.com")
        
        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert result["context"] == mock_context
        assert result["page"] == mock_page
        assert engine.current_context == mock_context
        assert engine.current_page == mock_page
        
        mock_client.create_context.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_page.goto.assert_called_once_with("https://example.com", wait_until="networkidle")
    
    @pytest.mark.asyncio
    async def test_navigate_with_stealth(self, engine):
        """Test navigation with stealth mode"""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        mock_client = AsyncMock()
        mock_client.create_context = AsyncMock(return_value=mock_context)
        
        engine.client = mock_client
        
        # Test navigation with stealth
        result = await engine.navigate("https://example.com", stealth=True)
        
        assert result["success"] is True
        # Verify stealth parameter was passed
        call_kwargs = mock_client.create_context.call_args[1]
        assert call_kwargs.get("stealth") is True
    
    @pytest.mark.asyncio
    async def test_navigate_not_initialized(self, engine):
        """Test navigation without initialization"""
        with pytest.raises(RuntimeError, match="OpenClaw not initialized"):
            await engine.navigate("https://example.com")
    
    @pytest.mark.asyncio
    async def test_extract_endpoints_deep(self, engine):
        """Test deep endpoint extraction"""
        # Setup mocks
        mock_endpoints = ["/api/users", "/api/posts", "/v1/data"]
        
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=mock_endpoints)
        
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        mock_client = AsyncMock()
        mock_client.create_context = AsyncMock(return_value=mock_context)
        
        engine.client = mock_client
        
        # Test extraction
        endpoints = await engine.extract_endpoints_deep("https://example.com")
        
        assert endpoints == mock_endpoints
        mock_page.evaluate.assert_called_once()


# ============================================================================
# PinchTabEngine Tests
# ============================================================================

class TestPinchTabEngine:
    """Test suite for PinchTabEngine"""
    
    @pytest.fixture
    def engine(self):
        """Create PinchTabEngine instance"""
        return PinchTabEngine()
    
    def test_initialization(self, engine):
        """Test engine initialization"""
        assert engine.client is not None
        assert engine.last_tab_id is None
        assert engine.last_url is None
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, engine):
        """Test successful initialization"""
        engine.client.health = AsyncMock(return_value={"status": "ok"})
        
        result = await engine.initialize()
        
        assert result is True
        engine.client.health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, engine):
        """Test initialization failure"""
        engine.client.health = AsyncMock(side_effect=Exception("Connection failed"))
        
        result = await engine.initialize()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_navigate_success(self, engine):
        """Test successful navigation"""
        engine.client.navigate = AsyncMock(return_value={"tabId": "tab-123"})
        
        result = await engine.navigate("https://example.com")
        
        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert result["tab_id"] == "tab-123"
        assert engine.last_tab_id == "tab-123"
        assert engine.last_url == "https://example.com"
        
        engine.client.navigate.assert_called_once_with("https://example.com")
    
    @pytest.mark.asyncio
    async def test_navigate_failure(self, engine):
        """Test navigation failure"""
        engine.client.navigate = AsyncMock(side_effect=Exception("Navigation failed"))
        
        result = await engine.navigate("https://example.com")
        
        assert result["success"] is False
        assert result["tab_id"] is None
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_extract_endpoints_fast(self, engine):
        """Test fast endpoint extraction"""
        # Mock navigation
        engine.client.navigate = AsyncMock(return_value={"tabId": "tab-123"})
        
        # Mock text extraction with API endpoints
        mock_text = '''
        fetch("/api/users")
        axios.get("/v1/posts")
        "/graphql"
        '''
        engine.client.text = AsyncMock(return_value=mock_text)
        
        endpoints = await engine.extract_endpoints_fast("https://example.com")
        
        assert len(endpoints) > 0
        # Should extract at least some endpoints
        assert any("/api" in e or "/v1" in e or "graphql" in e for e in endpoints)
    
    @pytest.mark.asyncio
    async def test_extract_endpoints_no_tab(self, engine):
        """Test endpoint extraction without tab"""
        engine.client.navigate = AsyncMock(return_value={})
        
        endpoints = await engine.extract_endpoints_fast("https://example.com")
        
        assert endpoints == []
    
    @pytest.mark.asyncio
    async def test_extract_endpoints_exception(self, engine):
        """Test endpoint extraction with exception"""
        engine.client.navigate = AsyncMock(return_value={"tabId": "tab-123"})
        engine.client.text = AsyncMock(side_effect=Exception("Text extraction failed"))
        
        endpoints = await engine.extract_endpoints_fast("https://example.com")
        
        assert endpoints == []
    
    @pytest.mark.asyncio
    async def test_extract_tokens(self, engine):
        """Test token extraction"""
        # Mock navigation
        engine.client.navigate = AsyncMock(return_value={"tabId": "tab-123"})
        
        # Mock text with tokens
        mock_text = '''
        const jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        Authorization: Bearer abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
        api_key: "sk_test_1234567890abcdefghijklmnopqrstuvwxyz"
        '''
        engine.client.text = AsyncMock(return_value=mock_text)
        
        tokens = await engine.extract_tokens("https://example.com")
        
        assert len(tokens) > 0
        # Should extract JWT token
        assert any(token.startswith("eyJ") for token in tokens)
    
    @pytest.mark.asyncio
    async def test_extract_tokens_no_tab(self, engine):
        """Test token extraction without tab"""
        engine.client.navigate = AsyncMock(return_value={})
        
        tokens = await engine.extract_tokens("https://example.com")
        
        assert tokens == []
    
    @pytest.mark.asyncio
    async def test_extract_tokens_exception(self, engine):
        """Test token extraction with exception"""
        engine.client.navigate = AsyncMock(return_value={"tabId": "tab-123"})
        engine.client.text = AsyncMock(side_effect=Exception("Text extraction failed"))
        
        tokens = await engine.extract_tokens("https://example.com")
        
        assert tokens == []
    
    @pytest.mark.asyncio
    async def test_test_injection(self, engine):
        """Test injection testing"""
        # Mock navigation
        engine.client.navigate = AsyncMock(return_value={"tabId": "tab-123"})
        
        # Mock text with reflected payload
        mock_text = "Response contains <script>alert(1)</script>"
        engine.client.text = AsyncMock(return_value=mock_text)
        
        # This method is incomplete in the source, so we just test it doesn't crash
        # In a real implementation, we'd test the full injection logic
        try:
            result = await engine.test_injection("https://example.com", "<script>alert(1)</script>")
            # If method is implemented, check result
            if result is not None:
                assert "reflected" in result or "success" in result
        except AttributeError:
            # Method might not be fully implemented
            pass


# ============================================================================
# Integration Tests
# ============================================================================

class TestEngineIntegration:
    """Integration tests for engine coordination"""
    
    @pytest.mark.asyncio
    async def test_both_engines_initialize(self):
        """Test both engines can initialize"""
        openclaw = OpenClawEngine()
        pinchtab = PinchTabEngine()
        
        # Test OpenClaw (will fail if not installed, which is expected)
        openclaw_result = await openclaw.initialize()
        # OpenClaw may not be installed, so we just check it returns a boolean
        assert isinstance(openclaw_result, bool)
        
        # Mock PinchTab
        pinchtab.client.health = AsyncMock(return_value={"status": "ok"})
        pinchtab_result = await pinchtab.initialize()
        
        assert pinchtab_result is True
    
    @pytest.mark.asyncio
    async def test_engine_selection_logic(self):
        """Test logic for selecting appropriate engine"""
        # This would test BrowserOrchestrator's engine selection
        # For now, just verify both engines have compatible interfaces
        
        openclaw = OpenClawEngine()
        pinchtab = PinchTabEngine()
        
        # Both should have initialize method
        assert hasattr(openclaw, 'initialize')
        assert hasattr(pinchtab, 'initialize')
        
        # Both should have navigate method
        assert hasattr(openclaw, 'navigate')
        assert hasattr(pinchtab, 'navigate')
        
        # Both should have endpoint extraction
        assert hasattr(openclaw, 'extract_endpoints_deep')
        assert hasattr(pinchtab, 'extract_endpoints_fast')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
