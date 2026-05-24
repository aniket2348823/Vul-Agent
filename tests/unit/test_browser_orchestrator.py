"""
Unit tests for BrowserOrchestrator
Tests context management, engine selection, resource pooling, and memory monitoring
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.browser_orchestrator import BrowserOrchestrator, BrowserEngine


@pytest.fixture
async def orchestrator():
    """Create a BrowserOrchestrator instance for testing."""
    orch = BrowserOrchestrator()
    yield orch
    # Cleanup
    await orch.cleanup_all_resources()


@pytest.fixture
def mock_openclaw():
    """Mock OpenClawEngine."""
    mock = AsyncMock()
    mock.initialize = AsyncMock()
    mock.navigate = AsyncMock(return_value={"success": True})
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_pinchtab():
    """Mock PinchTabEngine."""
    mock = AsyncMock()
    mock.initialize = AsyncMock()
    mock.navigate = AsyncMock(return_value={"success": True})
    mock.close = AsyncMock()
    return mock


class TestEngineSelection:
    """Test engine selection logic."""
    
    def test_select_openclaw_for_stealth(self, orchestrator):
        """OpenClaw should be selected for stealth operations."""
        engine = orchestrator._select_engine(
            url="https://example.com",
            operation="navigate",
            stealth=True
        )
        assert engine == BrowserEngine.OPENCLAW
    
    def test_select_pinchtab_for_fast_ops(self, orchestrator):
        """PinchTab should be selected for fast operations."""
        engine = orchestrator._select_engine(
            url="https://api.example.com",
            operation="extract_tokens",
            stealth=False
        )
        assert engine == BrowserEngine.PINCHTAB
    
    def test_select_openclaw_for_spa(self, orchestrator):
        """OpenClaw should be selected for SPA applications."""
        engine = orchestrator._select_engine(
            url="https://app.example.com",
            operation="navigate",
            stealth=False,
            is_spa=True
        )
        assert engine == BrowserEngine.OPENCLAW


class TestContextManagement:
    """Test browser context lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_create_context(self, orchestrator, mock_openclaw):
        """Test context creation."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            context_id = await orchestrator.create_context(
                scan_id="test_scan_001",
                engine=BrowserEngine.OPENCLAW
            )
            
            assert context_id is not None
            assert context_id in orchestrator._active_contexts
            assert orchestrator._active_contexts[context_id]["scan_id"] == "test_scan_001"
    
    @pytest.mark.asyncio
    async def test_close_context(self, orchestrator, mock_openclaw):
        """Test context closure."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            context_id = await orchestrator.create_context(
                scan_id="test_scan_001",
                engine=BrowserEngine.OPENCLAW
            )
            
            await orchestrator.close_context(context_id)
            
            assert context_id not in orchestrator._active_contexts
    
    @pytest.mark.asyncio
    async def test_max_contexts_limit(self, orchestrator, mock_openclaw):
        """Test maximum context limit enforcement."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            orchestrator._max_contexts = 3
            
            # Create max contexts
            contexts = []
            for i in range(3):
                ctx = await orchestrator.create_context(
                    scan_id=f"scan_{i}",
                    engine=BrowserEngine.OPENCLAW
                )
                contexts.append(ctx)
            
            # Attempt to create one more should fail
            with pytest.raises(Exception, match="Maximum context limit"):
                await orchestrator.create_context(
                    scan_id="scan_overflow",
                    engine=BrowserEngine.OPENCLAW
                )


class TestContextPooling:
    """Test context pooling and reuse."""
    
    @pytest.mark.asyncio
    async def test_get_pooled_context_empty_pool(self, orchestrator, mock_openclaw):
        """Test getting context from empty pool creates new one."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            context_id = await orchestrator.get_pooled_context("test_scan")
            
            assert context_id is not None
            assert len(orchestrator._context_pool) == 0
    
    @pytest.mark.asyncio
    async def test_return_context_to_pool(self, orchestrator, mock_openclaw):
        """Test returning context to pool."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            context_id = await orchestrator.create_context(
                scan_id="test_scan",
                engine=BrowserEngine.OPENCLAW
            )
            
            await orchestrator.return_context_to_pool(context_id)
            
            assert context_id in orchestrator._context_pool
            assert context_id not in orchestrator._active_contexts
    
    @pytest.mark.asyncio
    async def test_pool_size_limit(self, orchestrator, mock_openclaw):
        """Test pool size limit enforcement."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            orchestrator._max_pool_size = 2
            
            # Create and return contexts
            for i in range(3):
                ctx = await orchestrator.create_context(
                    scan_id=f"scan_{i}",
                    engine=BrowserEngine.OPENCLAW
                )
                await orchestrator.return_context_to_pool(ctx)
            
            # Pool should not exceed max size
            assert len(orchestrator._context_pool) <= 2
    
    @pytest.mark.asyncio
    async def test_context_reuse_from_pool(self, orchestrator, mock_openclaw):
        """Test context reuse from pool."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            # Create and return context
            ctx1 = await orchestrator.create_context(
                scan_id="scan_1",
                engine=BrowserEngine.OPENCLAW
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
            assert stats["cleanup_triggered"] is False
    
    @pytest.mark.asyncio
    async def test_monitor_memory_above_threshold(self, orchestrator, mock_openclaw):
        """Test memory monitoring triggers cleanup when above threshold."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 600 * 1024 * 1024  # 600MB
            
            with patch.object(orchestrator, 'openclaw', mock_openclaw):
                # Create some idle contexts
                ctx = await orchestrator.create_context(
                    scan_id="test_scan",
                    engine=BrowserEngine.OPENCLAW
                )
                
                # Make it idle
                import time
                orchestrator._active_contexts[ctx]["last_activity"] = time.time() - 300
                
                stats = await orchestrator.monitor_memory()
                
                assert stats["threshold_exceeded"] is True
                assert stats["cleanup_triggered"] is True
    
    @pytest.mark.asyncio
    async def test_memory_check_rate_limiting(self, orchestrator):
        """Test memory checks are rate limited."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024
            
            # First check
            stats1 = await orchestrator.monitor_memory()
            
            # Immediate second check should be skipped
            stats2 = await orchestrator.monitor_memory()
            
            # Should return cached result
            assert stats1 == stats2


class TestLazyInitialization:
    """Test lazy initialization of browser engines."""
    
    @pytest.mark.asyncio
    async def test_lazy_init_openclaw(self, orchestrator, mock_openclaw):
        """Test lazy initialization of OpenClaw."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            orchestrator._openclaw_initialized = False
            
            await orchestrator._lazy_init_openclaw()
            
            assert orchestrator._openclaw_initialized is True
            mock_openclaw.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lazy_init_pinchtab(self, orchestrator, mock_pinchtab):
        """Test lazy initialization of PinchTab."""
        with patch.object(orchestrator, 'pinchtab', mock_pinchtab):
            orchestrator._pinchtab_initialized = False
            
            await orchestrator._lazy_init_pinchtab()
            
            assert orchestrator._pinchtab_initialized is True
            mock_pinchtab.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_duplicate_initialization(self, orchestrator, mock_openclaw):
        """Test engines are not initialized twice."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            await orchestrator._lazy_init_openclaw()
            await orchestrator._lazy_init_openclaw()
            
            # Should only be called once
            mock_openclaw.initialize.assert_called_once()


class TestResourceCleanup:
    """Test resource cleanup and statistics."""
    
    @pytest.mark.asyncio
    async def test_cleanup_all_resources(self, orchestrator, mock_openclaw):
        """Test comprehensive resource cleanup."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            # Create some contexts
            ctx1 = await orchestrator.create_context("scan_1", BrowserEngine.OPENCLAW)
            ctx2 = await orchestrator.create_context("scan_2", BrowserEngine.OPENCLAW)
            
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
    async def test_close_with_cleanup(self, orchestrator, mock_openclaw, mock_pinchtab):
        """Test close method performs cleanup."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            with patch.object(orchestrator, 'pinchtab', mock_pinchtab):
                # Create contexts
                await orchestrator.create_context("scan_1", BrowserEngine.OPENCLAW)
                
                await orchestrator.close()
                
                assert len(orchestrator._active_contexts) == 0
                mock_openclaw.close.assert_called_once()
                mock_pinchtab.close.assert_called_once()


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    @pytest.mark.asyncio
    async def test_context_creation_failure(self, orchestrator, mock_openclaw):
        """Test handling of context creation failure."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            mock_openclaw.create_context = AsyncMock(side_effect=Exception("Creation failed"))
            
            with pytest.raises(Exception, match="Creation failed"):
                await orchestrator.create_context("scan_1", BrowserEngine.OPENCLAW)
    
    @pytest.mark.asyncio
    async def test_context_closure_failure_graceful(self, orchestrator, mock_openclaw):
        """Test graceful handling of context closure failure."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            ctx = await orchestrator.create_context("scan_1", BrowserEngine.OPENCLAW)
            
            mock_openclaw.close_context = AsyncMock(side_effect=Exception("Close failed"))
            
            # Should not raise, but log error
            await orchestrator.close_context(ctx)
            
            # Context should still be removed from tracking
            assert ctx not in orchestrator._active_contexts
    
    @pytest.mark.asyncio
    async def test_cleanup_with_errors(self, orchestrator, mock_openclaw):
        """Test cleanup continues despite errors."""
        with patch.object(orchestrator, 'openclaw', mock_openclaw):
            ctx1 = await orchestrator.create_context("scan_1", BrowserEngine.OPENCLAW)
            ctx2 = await orchestrator.create_context("scan_2", BrowserEngine.OPENCLAW)
            
            # Make first context fail to close
            close_calls = [Exception("Close failed"), None]
            mock_openclaw.close_context = AsyncMock(side_effect=close_calls)
            
            await orchestrator.cleanup_all_resources()
            
            # Both contexts should be removed despite error
            assert len(orchestrator._active_contexts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
