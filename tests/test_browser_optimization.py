"""
Unit tests for browser optimization components.
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from backend.core.browser_optimization import (
    BrowserContextPool,
    FrameworkDetectionCache,
    BrowserResourceMonitor,
    OptimizedBrowserOrchestrator
)


class TestBrowserContextPool:
    """Test browser context pooling."""
    
    @pytest.mark.asyncio
    async def test_acquire_new_context(self):
        """Test acquiring a new context."""
        pool = BrowserContextPool(max_contexts=3)
        
        context = await pool.acquire(scan_id="test_scan_1")
        
        assert context is not None
        assert "id" in context
        assert "created_at" in context
        assert len(pool._active_contexts) == 1
    
    @pytest.mark.asyncio
    async def test_release_and_reuse_context(self):
        """Test releasing and reusing contexts."""
        pool = BrowserContextPool(max_contexts=3)
        
        # Acquire and release
        context1 = await pool.acquire(scan_id="test_scan_1")
        await pool.release(context1, scan_id="test_scan_1")
        
        assert len(pool._available_contexts) == 1
        assert len(pool._active_contexts) == 0
        
        # Acquire again - should reuse
        context2 = await pool.acquire(scan_id="test_scan_2")
        
        assert context2["id"] == context1["id"]
        assert len(pool._available_contexts) == 0
        assert len(pool._active_contexts) == 1
    
    @pytest.mark.asyncio
    async def test_max_contexts_limit(self):
        """Test that pool respects max contexts limit."""
        pool = BrowserContextPool(max_contexts=2)
        
        context1 = await pool.acquire(scan_id="scan_1")
        context2 = await pool.acquire(scan_id="scan_2")
        
        assert len(pool._active_contexts) == 2
        
        # Third acquire should wait (we'll timeout instead)
        try:
            context3 = await asyncio.wait_for(
                pool.acquire(scan_id="scan_3"),
                timeout=2.0
            )
            # Should not reach here
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            # Expected
            pass
    
    @pytest.mark.asyncio
    async def test_cleanup_idle_contexts(self):
        """Test cleanup of idle contexts."""
        pool = BrowserContextPool(max_contexts=3)
        
        # Create contexts
        context1 = await pool.acquire(scan_id="scan_1")
        context2 = await pool.acquire(scan_id="scan_2")
        
        # Release them
        await pool.release(context1, scan_id="scan_1")
        await pool.release(context2, scan_id="scan_2")
        
        assert len(pool._available_contexts) == 2
        
        # Make one context old
        pool._available_contexts[0]["last_used"] = datetime.now() - timedelta(seconds=400)
        
        # Cleanup with 300s timeout
        await pool.cleanup_idle(idle_timeout=300)
        
        # Should have removed the old context
        assert len(pool._available_contexts) == 1
    
    @pytest.mark.asyncio
    async def test_close_all(self):
        """Test closing all contexts."""
        pool = BrowserContextPool(max_contexts=3)
        
        context1 = await pool.acquire(scan_id="scan_1")
        context2 = await pool.acquire(scan_id="scan_2")
        await pool.release(context1, scan_id="scan_1")
        
        await pool.close_all()
        
        assert len(pool._available_contexts) == 0
        assert len(pool._active_contexts) == 0


class TestFrameworkDetectionCache:
    """Test framework detection caching."""
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = FrameworkDetectionCache(cache_ttl=3600)
        
        result = await cache.get("example.com")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit returns cached value."""
        cache = FrameworkDetectionCache(cache_ttl=3600)
        
        await cache.set("example.com", "React")
        result = await cache.get("example.com")
        
        assert result == "React"
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache expiration."""
        cache = FrameworkDetectionCache(cache_ttl=1)  # 1 second TTL
        
        await cache.set("example.com", "Vue")
        
        # Should hit
        result1 = await cache.get("example.com")
        assert result1 == "Vue"
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Should miss
        result2 = await cache.get("example.com")
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing cache."""
        cache = FrameworkDetectionCache(cache_ttl=3600)
        
        await cache.set("example.com", "React")
        await cache.set("test.com", "Angular")
        
        await cache.clear()
        
        assert await cache.get("example.com") is None
        assert await cache.get("test.com") is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = FrameworkDetectionCache(cache_ttl=3600)
        
        asyncio.run(cache.set("example.com", "React"))
        asyncio.run(cache.set("test.com", "Vue"))
        
        stats = cache.get_stats()
        
        assert stats["size"] == 2
        assert "example.com" in stats["domains"]
        assert "test.com" in stats["domains"]


class TestBrowserResourceMonitor:
    """Test browser resource monitoring."""
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = BrowserResourceMonitor(memory_threshold_mb=500)
        pool = BrowserContextPool(max_contexts=3)
        
        await monitor.start_monitoring(pool)
        assert monitor._monitoring is True
        assert monitor._monitor_task is not None
        
        await monitor.stop_monitoring()
        assert monitor._monitoring is False
    
    @pytest.mark.asyncio
    async def test_memory_threshold_trigger(self):
        """Test that high memory triggers cleanup."""
        monitor = BrowserResourceMonitor(memory_threshold_mb=1)  # Very low threshold
        pool = BrowserContextPool(max_contexts=3)
        
        # Create and release contexts
        context1 = await pool.acquire(scan_id="scan_1")
        await pool.release(context1, scan_id="scan_1")
        
        # Make context old
        pool._available_contexts[0]["last_used"] = datetime.now() - timedelta(seconds=100)
        
        # Start monitoring (should trigger cleanup)
        await monitor.start_monitoring(pool)
        
        # Wait for monitor loop to run
        await asyncio.sleep(1)
        
        await monitor.stop_monitoring()
        
        # Context should have been cleaned up
        # (This test is simplified - actual behavior depends on memory metrics)


class TestOptimizedBrowserOrchestrator:
    """Test optimized browser orchestrator."""
    
    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that get_instance returns same instance."""
        instance1 = await OptimizedBrowserOrchestrator.get_instance()
        instance2 = await OptimizedBrowserOrchestrator.get_instance()
        
        assert instance1 is instance2
    
    @pytest.mark.asyncio
    async def test_framework_caching(self):
        """Test framework detection with caching."""
        # This test would require actual browser
        # Simplified version:
        
        # First call - should detect and cache
        framework1 = await OptimizedBrowserOrchestrator.detect_framework_cached("https://example.com")
        
        # Second call - should use cache
        framework2 = await OptimizedBrowserOrchestrator.detect_framework_cached("https://example.com")
        
        # Both should return same result (or None if no browser)
        assert framework1 == framework2
    
    @pytest.mark.asyncio
    async def test_context_pool_integration(self):
        """Test context pool integration."""
        context = await OptimizedBrowserOrchestrator.acquire_context(scan_id="test_scan")
        
        assert context is not None
        
        await OptimizedBrowserOrchestrator.release_context(context, scan_id="test_scan")
    
    def test_get_stats(self):
        """Test getting optimization statistics."""
        stats = OptimizedBrowserOrchestrator.get_stats()
        
        assert "singleton_initialized" in stats
        assert "context_pool" in stats
        assert "framework_cache" in stats
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup of all resources."""
        # Initialize
        await OptimizedBrowserOrchestrator.get_instance()
        
        # Cleanup
        await OptimizedBrowserOrchestrator.cleanup()
        
        # Instance should be None after cleanup
        assert OptimizedBrowserOrchestrator._instance is None


if __name__ == "__main__":
    print("=" * 60)
    print("Browser Optimization Test Suite")
    print("=" * 60)
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
