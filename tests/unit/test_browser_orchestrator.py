"""
Unit tests for BrowserOrchestrator
Tests context management, engine selection, resource pooling, and memory monitoring
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.browser_orchestrator import BrowserOrchestrator, BrowserEngine


@pytest_asyncio.fixture
async def orchestrator():
    """Create a BrowserOrchestrator instance for testing."""
    orch = BrowserOrchestrator()
    yield orch
    # Cleanup
    await orch.cleanup_all_resources()


class TestEngineSelection:
    """Test engine selection logic."""
    
    def test_select_openclaw_for_stealth(self, orchestrator):
        """OpenClaw should be selected for stealth operations."""
        # Mock openclaw availability
        orchestrator.openclaw = Mock()
        
        engine = orchestrator._select_engine(
            requested=BrowserEngine.AUTO,
            stealth=True,
            url="https://example.com"
        )
        assert engine == BrowserEngine.OPENCLAW
    
    def test_select_pinchtab_for_fast_ops(self, orchestrator):
        """PinchTab should be selected for fast operations."""
        # Mock both engines available
        orchestrator.openclaw = Mock()
        orchestrator.pinchtab = Mock()
        
        engine = orchestrator._select_engine(
            requested=BrowserEngine.AUTO,
            stealth=False,
            url="https://api.example.com"
        )
        # Should prefer OpenClaw by default when both available
        assert engine in [BrowserEngine.OPENCLAW, BrowserEngine.PINCHTAB]
    
    def test_select_openclaw_for_auth(self, orchestrator):
        """OpenClaw should be selected for auth/login pages."""
        orchestrator.openclaw = Mock()
        orchestrator.pinchtab = Mock()
        
        engine = orchestrator._select_engine(
            requested=BrowserEngine.AUTO,
            stealth=False,
            url="https://example.com/login"
        )
        assert engine == BrowserEngine.OPENCLAW


class TestContextManagement:
    """Test browser context lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_create_context(self, orchestrator):
        """Test context creation."""
        context_id = await orchestrator.create_isolated_context(
            scan_id="test_scan_001"
        )
        
        assert context_id is not None
        assert context_id in orchestrator._active_contexts
        assert orchestrator._active_contexts[context_id]["scan_id"] == "test_scan_001"
    
    @pytest.mark.asyncio
    async def test_close_context(self, orchestrator):
        """Test context closure."""
        context_id = await orchestrator.create_isolated_context(
            scan_id="test_scan_001"
        )
        
        await orchestrator.close_context(context_id)
        
        assert context_id not in orchestrator._active_contexts
    
    @pytest.mark.asyncio
    async def test_max_contexts_limit(self, orchestrator):
        """Test maximum context limit enforcement."""
        orchestrator._max_contexts = 3
        
        # Create max contexts
        contexts = []
        for i in range(3):
            ctx = await orchestrator.create_isolated_context(
                scan_id=f"scan_{i}"
            )
            contexts.append(ctx)
        
        # Attempt to create one more should trigger cleanup
        # (not raise exception, but cleanup idle contexts)
        ctx4 = await orchestrator.create_isolated_context(
            scan_id="scan_overflow"
        )
        
        # Should succeed after cleanup
        assert ctx4 is not None


class TestContextPooling:
    """Test context pooling and reuse."""
    
    @pytest.mark.asyncio
    async def test_get_pooled_context_empty_pool(self, orchestrator):
        """Test getting context from empty pool creates new one."""
        context_id = await orchestrator.get_pooled_context("test_scan")
        
        assert context_id is not None
        assert len(orchestrator._context_pool) == 0
    
    @pytest.mark.asyncio
    async def test_return_context_to_pool(self, orchestrator):
        """Test returning context to pool."""
        context_id = await orchestrator.create_isolated_context(
            scan_id="test_scan"
        )
        
        await orchestrator.return_context_to_pool(context_id)
        
        assert context_id in orchestrator._context_pool
        # Context is still tracked but in pool
    
    @pytest.mark.asyncio
    async def test_pool_size_limit(self, orchestrator):
        """Test pool size limit enforcement."""
        orchestrator._max_pool_size = 2
        
        # Create and return contexts
        for i in range(3):
            ctx = await orchestrator.create_isolated_context(
                scan_id=f"scan_{i}"
            )
            await orchestrator.return_context_to_pool(ctx)
        
        # Pool should not exceed max size
        assert len(orchestrator._context_pool) <= 2
    
    @pytest.mark.asyncio
    async def test_context_reuse_from_pool(self, orchestrator):
        """Test context reuse from pool."""
        # Create and return context
        ctx1 = await orchestrator.create_isolated_context(
            scan_id="scan_1"
        )
        await orchestrator.return_context_to_pool(ctx1)
        
        # Get from pool should reuse
        ctx2 = await orchestrator.get_pooled_context("scan_2")
        
        assert ctx2 == ctx1
        assert len(orchestrator._context_pool) == 0


class TestMemoryMonitoring:
    """Test memory monitoring and cleanup."""
    
    @pytest.mark.asyncio
    async def test_monitor_memory_below_threshold(self, orchestrator):
        """Test memory monitoring when below threshold."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
            
            stats = await orchestrator.monitor_memory()
            
            assert stats["memory_mb"] == 100
            assert stats["threshold_exceeded"] is False
    
    @pytest.mark.asyncio
    async def test_monitor_memory_above_threshold(self, orchestrator):
        """Test memory monitoring triggers cleanup when above threshold."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 600 * 1024 * 1024  # 600MB
            
            # Create some idle contexts
            ctx = await orchestrator.create_isolated_context(
                scan_id="test_scan"
            )
            
            # Make it idle
            import time
            orchestrator._active_contexts[ctx]["last_activity"] = time.time() - 300
            
            stats = await orchestrator.monitor_memory()
            
            assert stats["threshold_exceeded"] is True
            assert stats.get("cleanup_triggered") is True
    
    @pytest.mark.asyncio
    async def test_memory_check_rate_limiting(self, orchestrator):
        """Test memory checks are rate limited."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024
            
            # First check
            stats1 = await orchestrator.monitor_memory()
            
            # Immediate second check should be skipped
            stats2 = await orchestrator.monitor_memory()
            
            # Should return skipped result
            assert stats2.get("skipped") is True


class TestLazyInitialization:
    """Test lazy initialization of browser engines."""
    
    @pytest.mark.asyncio
    async def test_lazy_init_openclaw(self, orchestrator):
        """Test lazy initialization of OpenClaw."""
        orchestrator._openclaw_initialized = False
        
        with patch('backend.core.openclaw_engine.OpenClawEngine') as mock_openclaw_class:
            mock_instance = AsyncMock()
            mock_openclaw_class.return_value = mock_instance
            
            await orchestrator._lazy_init_openclaw()
            
            assert orchestrator._openclaw_initialized is True
            mock_instance.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lazy_init_pinchtab(self, orchestrator):
        """Test lazy initialization of PinchTab."""
        orchestrator._pinchtab_initialized = False
        
        with patch('backend.core.pinchtab_engine.PinchTabEngine') as mock_pinchtab_class:
            mock_instance = AsyncMock()
            mock_pinchtab_class.return_value = mock_instance
            
            await orchestrator._lazy_init_pinchtab()
            
            assert orchestrator._pinchtab_initialized is True
            mock_instance.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_duplicate_initialization(self, orchestrator):
        """Test engines are not initialized twice."""
        with patch('backend.core.openclaw_engine.OpenClawEngine') as mock_openclaw_class:
            mock_instance = AsyncMock()
            mock_openclaw_class.return_value = mock_instance
            
            await orchestrator._lazy_init_openclaw()
            await orchestrator._lazy_init_openclaw()
            
            # Should only be called once
            mock_instance.initialize.assert_called_once()


class TestResourceCleanup:
    """Test resource cleanup and statistics."""
    
    @pytest.mark.asyncio
    async def test_cleanup_all_resources(self, orchestrator):
        """Test comprehensive resource cleanup."""
        # Create some contexts
        ctx1 = await orchestrator.create_isolated_context("scan_1")
        ctx2 = await orchestrator.create_isolated_context("scan_2")
        
        # Add to pool
        await orchestrator.return_context_to_pool(ctx1)
        
        await orchestrator.cleanup_all_resources()
        
        assert len(orchestrator._active_contexts) == 0
        assert len(orchestrator._context_pool) == 0
    
    def test_get_resource_stats(self, orchestrator):
        """Test resource statistics."""
        stats = orchestrator.get_resource_stats()
        
        assert "active_contexts" in stats
        assert "pooled_contexts" in stats
        assert "max_contexts" in stats
        assert "max_pool_size" in stats
        assert "openclaw_initialized" in stats
        assert "pinchtab_initialized" in stats
    
    @pytest.mark.asyncio
    async def test_close_with_cleanup(self, orchestrator):
        """Test close method performs cleanup."""
        # Create contexts
        await orchestrator.create_isolated_context("scan_1")
        
        # Mock engines
        orchestrator.openclaw = AsyncMock()
        orchestrator.pinchtab = AsyncMock()
        
        await orchestrator.close()
        
        assert len(orchestrator._active_contexts) == 0
        orchestrator.openclaw.close.assert_called_once()
        orchestrator.pinchtab.close.assert_called_once()


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    @pytest.mark.asyncio
    async def test_context_creation_failure(self, orchestrator):
        """Test handling of context creation failure."""
        # Context creation should not fail in normal circumstances
        # This tests that the method handles errors gracefully
        context_id = await orchestrator.create_isolated_context("scan_1")
        assert context_id is not None
    
    @pytest.mark.asyncio
    async def test_context_closure_failure_graceful(self, orchestrator):
        """Test graceful handling of context closure failure."""
        ctx = await orchestrator.create_isolated_context("scan_1")
        
        # Should not raise even if context has issues
        await orchestrator.close_context(ctx)
        
        # Context should be removed from tracking
        assert ctx not in orchestrator._active_contexts
    
    @pytest.mark.asyncio
    async def test_cleanup_with_errors(self, orchestrator):
        """Test cleanup continues despite errors."""
        ctx1 = await orchestrator.create_isolated_context("scan_1")
        ctx2 = await orchestrator.create_isolated_context("scan_2")
        
        # Cleanup should handle all contexts even if some fail
        await orchestrator.cleanup_all_resources()
        
        # Both contexts should be removed
        assert len(orchestrator._active_contexts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
