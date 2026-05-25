"""
Integration tests for browser engine coordination.

Tests OpenClaw and PinchTab engine coordination and fallback.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.browser_orchestrator import BrowserOrchestrator, BrowserEngine
from backend.core.openclaw_engine import OpenClawEngine
from backend.core.pinchtab_engine import PinchTabEngine


class TestEngineCoordination:
    """Test browser engine coordination."""

    @pytest.fixture
    def mock_openclaw(self):
        """Create mock OpenClaw engine."""
        engine = Mock(spec=OpenClawEngine)
        engine.initialize = AsyncMock()
        engine.navigate = AsyncMock(return_value={"success": True, "url": "https://example.com"})
        engine.extract_endpoints_deep = AsyncMock(return_value=[])
        engine.test_xss_payload = AsyncMock(return_value={"vulnerable": False})
        engine.cleanup = AsyncMock()
        return engine

    @pytest.fixture
    def mock_pinchtab(self):
        """Create mock PinchTab engine."""
        engine = Mock(spec=PinchTabEngine)
        engine.initialize = AsyncMock()
        engine.navigate = AsyncMock(return_value={"success": True, "url": "https://example.com"})
        engine.extract_endpoints_fast = AsyncMock(return_value=[])
        engine.extract_tokens = AsyncMock(return_value=[])
        engine.cleanup = AsyncMock()
        return engine

    @pytest.fixture
    def orchestrator(self, mock_openclaw, mock_pinchtab):
        """Create orchestrator with mocked engines."""
        orch = BrowserOrchestrator()
        orch.openclaw = mock_openclaw
        orch.pinchtab = mock_pinchtab
        return orch

    @pytest.mark.asyncio
    async def test_auto_engine_selection_stealth(self, orchestrator, mock_openclaw):
        """Test auto-selection chooses OpenClaw for stealth."""
        result = await orchestrator.navigate("https://example.com", stealth=True)
        
        # Should use OpenClaw for stealth
        mock_openclaw.navigate.assert_called_once()
        assert result["success"]

    @pytest.mark.asyncio
    async def test_auto_engine_selection_fast(self, orchestrator, mock_pinchtab):
        """Test auto-selection chooses PinchTab for fast operations."""
        result = await orchestrator.extract_endpoints("https://example.com", deep=False)
        
        # Should use PinchTab for fast extraction
        mock_pinchtab.extract_endpoints_fast.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_engine_selection(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test explicit engine selection."""
        # Force OpenClaw
        result = await orchestrator.navigate(
            "https://example.com",
            engine=BrowserEngine.OPENCLAW
        )
        mock_openclaw.navigate.assert_called_once()
        mock_pinchtab.navigate.assert_not_called()
        
        # Reset mocks
        mock_openclaw.reset_mock()
        mock_pinchtab.reset_mock()
        
        # Force PinchTab
        result = await orchestrator.navigate(
            "https://example.com",
            engine=BrowserEngine.PINCHTAB
        )
        mock_pinchtab.navigate.assert_called_once()
        mock_openclaw.navigate.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_openclaw_to_pinchtab(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test fallback from OpenClaw to PinchTab on failure."""
        # OpenClaw fails
        mock_openclaw.navigate.side_effect = Exception("OpenClaw error")
        
        result = await orchestrator.navigate("https://example.com", stealth=True)
        
        # Should try OpenClaw first, then fallback to PinchTab
        mock_openclaw.navigate.assert_called_once()
        mock_pinchtab.navigate.assert_called_once()
        assert result["success"]

    @pytest.mark.asyncio
    async def test_fallback_pinchtab_to_openclaw(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test fallback from PinchTab to OpenClaw on failure."""
        # PinchTab fails
        mock_pinchtab.navigate.side_effect = Exception("PinchTab error")
        
        result = await orchestrator.navigate("https://example.com", stealth=False)
        
        # Should try PinchTab first, then fallback to OpenClaw
        mock_pinchtab.navigate.assert_called_once()
        mock_openclaw.navigate.assert_called_once()
        assert result["success"]

    @pytest.mark.asyncio
    async def test_both_engines_fail(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test behavior when both engines fail."""
        # Both fail
        mock_openclaw.navigate.side_effect = Exception("OpenClaw error")
        mock_pinchtab.navigate.side_effect = Exception("PinchTab error")
        
        with pytest.raises(Exception):
            await orchestrator.navigate("https://example.com")

    @pytest.mark.asyncio
    async def test_deep_extraction_uses_openclaw(self, orchestrator, mock_openclaw):
        """Test deep extraction uses OpenClaw."""
        await orchestrator.extract_endpoints("https://example.com", deep=True)
        
        mock_openclaw.extract_endpoints_deep.assert_called_once()

    @pytest.mark.asyncio
    async def test_fast_extraction_uses_pinchtab(self, orchestrator, mock_pinchtab):
        """Test fast extraction uses PinchTab."""
        await orchestrator.extract_endpoints("https://example.com", deep=False)
        
        mock_pinchtab.extract_endpoints_fast.assert_called_once()

    @pytest.mark.asyncio
    async def test_xss_testing_uses_openclaw(self, orchestrator, mock_openclaw):
        """Test XSS testing uses OpenClaw for real browser."""
        await orchestrator.test_payload(
            "https://example.com/search",
            "<script>alert(1)</script>",
            "q"
        )
        
        mock_openclaw.test_xss_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_extraction_uses_pinchtab(self, orchestrator, mock_pinchtab):
        """Test token extraction uses PinchTab for speed."""
        await orchestrator.extract_tokens("https://example.com")
        
        mock_pinchtab.extract_tokens.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_engine_operations(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test concurrent operations on different engines."""
        import asyncio
        
        # Run operations concurrently
        tasks = [
            orchestrator.navigate("https://example1.com", engine=BrowserEngine.OPENCLAW),
            orchestrator.navigate("https://example2.com", engine=BrowserEngine.PINCHTAB),
            orchestrator.extract_endpoints("https://example3.com", deep=True),
            orchestrator.extract_tokens("https://example4.com")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == 4
        assert all(r.get("success") or isinstance(r, list) for r in results)

    @pytest.mark.asyncio
    async def test_engine_initialization(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test engines are initialized on first use."""
        await orchestrator.navigate("https://example.com", engine=BrowserEngine.OPENCLAW)
        
        # OpenClaw should be initialized
        mock_openclaw.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_engine_cleanup(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test engines are cleaned up properly."""
        await orchestrator.navigate("https://example.com", engine=BrowserEngine.OPENCLAW)
        await orchestrator.cleanup()
        
        # Both engines should be cleaned up
        mock_openclaw.cleanup.assert_called_once()
        mock_pinchtab.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_engine_state_isolation(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test engines maintain separate state."""
        # Navigate with OpenClaw
        await orchestrator.navigate("https://example1.com", engine=BrowserEngine.OPENCLAW)
        
        # Navigate with PinchTab
        await orchestrator.navigate("https://example2.com", engine=BrowserEngine.PINCHTAB)
        
        # Each engine should have been called independently
        assert mock_openclaw.navigate.call_count == 1
        assert mock_pinchtab.navigate.call_count == 1
        
        # Verify different URLs
        openclaw_url = mock_openclaw.navigate.call_args[0][0]
        pinchtab_url = mock_pinchtab.navigate.call_args[0][0]
        assert openclaw_url != pinchtab_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
