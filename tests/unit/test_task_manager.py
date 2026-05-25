"""
Unit tests for TaskManager
Tests async task tracking, error handling, and cleanup
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from backend.core.task_manager import TaskManager


@pytest.fixture
def task_manager():
    """Create a TaskManager instance for testing."""
    return TaskManager("TestComponent")


class TestTaskCreation:
    """Test task creation and tracking."""
    
    @pytest.mark.asyncio
    async def test_create_task_basic(self, task_manager):
        """Test basic task creation."""
        async def simple_task():
            await asyncio.sleep(0.01)
            return "done"
        
        task = task_manager.create_task(simple_task(), name="simple")
        
        assert task is not None
        assert len(task_manager._tasks) == 1
        
        result = await task
        assert result == "done"
    
    @pytest.mark.asyncio
    async def test_create_task_with_name(self, task_manager):
        """Test task creation with custom name."""
        async def named_task():
            await asyncio.sleep(0.01)
        
        task = task_manager.create_task(named_task(), name="custom_name")
        
        assert task.get_name() == "custom_name"
    
    @pytest.mark.asyncio
    async def test_create_task_auto_name(self, task_manager):
        """Test task creation with auto-generated name."""
        async def auto_task():
            await asyncio.sleep(0.01)
        
        task = task_manager.create_task(auto_task())
        
        # Should have auto-generated name (Python uses "Task-N" format)
        assert task.get_name().startswith("Task-") or "task" in task.get_name().lower()
    
    @pytest.mark.asyncio
    async def test_multiple_tasks(self, task_manager):
        """Test creating multiple tasks."""
        async def task_func(n):
            await asyncio.sleep(0.01)
            return n
        
        tasks = []
        for i in range(5):
            task = task_manager.create_task(task_func(i), name=f"task_{i}")
            tasks.append(task)
        
        assert len(task_manager._tasks) == 5
        
        results = await asyncio.gather(*tasks)
        assert results == [0, 1, 2, 3, 4]


class TestErrorHandling:
    """Test error handling and logging."""
    
    @pytest.mark.asyncio
    async def test_task_exception_logged(self, task_manager):
        """Test that task exceptions are logged."""
        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Task failed")
        
        with patch('logging.Logger.error') as mock_log:
            task = task_manager.create_task(failing_task(), name="failing")
            
            # Wait for task to complete
            try:
                await task
            except ValueError:
                pass
            
            # Give time for error callback
            await asyncio.sleep(0.05)
            
            # Error should be logged
            mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_task_exception_not_swallowed(self, task_manager):
        """Test that task exceptions are not swallowed."""
        async def failing_task():
            raise RuntimeError("Critical error")
        
        task = task_manager.create_task(failing_task(), name="critical")
        
        with pytest.raises(RuntimeError, match="Critical error"):
            await task
    
    @pytest.mark.asyncio
    async def test_multiple_task_failures(self, task_manager):
        """Test handling multiple task failures."""
        async def failing_task(n):
            await asyncio.sleep(0.01)
            raise ValueError(f"Task {n} failed")
        
        tasks = []
        for i in range(3):
            task = task_manager.create_task(failing_task(i), name=f"fail_{i}")
            tasks.append(task)
        
        # All tasks should fail independently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert all(isinstance(r, ValueError) for r in results)


class TestTaskCleanup:
    """Test task cleanup and cancellation."""
    
    @pytest.mark.asyncio
    async def test_cancel_all_tasks(self, task_manager):
        """Test cancelling all tasks."""
        async def long_task():
            await asyncio.sleep(10)
        
        # Create multiple long-running tasks
        for i in range(3):
            task_manager.create_task(long_task(), name=f"long_{i}")
        
        assert len(task_manager._tasks) == 3
        
        # Cancel all
        await task_manager.cancel_all()
        
        # All tasks should be cancelled
        assert len(task_manager._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_cancel_specific_task(self, task_manager):
        """Test cancelling a specific task."""
        async def long_task():
            await asyncio.sleep(10)
        
        task1 = task_manager.create_task(long_task(), name="task1")
        task2 = task_manager.create_task(long_task(), name="task2")
        
        # Cancel task1
        task1.cancel()
        
        # Wait a bit
        await asyncio.sleep(0.01)
        
        # task1 should be cancelled, task2 should still be running
        assert task1.cancelled()
        assert not task2.cancelled()
        
        # Cleanup
        await task_manager.cancel_all()
    
    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks(self, task_manager):
        """Test that completed tasks are cleaned up."""
        async def quick_task():
            await asyncio.sleep(0.01)
        
        task = task_manager.create_task(quick_task(), name="quick")
        
        await task
        
        # Give time for cleanup callback
        await asyncio.sleep(0.05)
        
        # Task should be removed from tracking
        assert len(task_manager._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_cancel_all_idempotent(self, task_manager):
        """Test that cancel_all can be called multiple times."""
        async def task_func():
            await asyncio.sleep(0.1)
        
        task_manager.create_task(task_func(), name="task1")
        
        # Cancel multiple times
        await task_manager.cancel_all()
        await task_manager.cancel_all()
        await task_manager.cancel_all()
        
        # Should not raise errors
        assert len(task_manager._tasks) == 0


class TestTaskTracking:
    """Test task tracking and monitoring."""
    
    @pytest.mark.asyncio
    async def test_task_count(self, task_manager):
        """Test tracking task count."""
        async def task_func():
            await asyncio.sleep(0.1)
        
        assert len(task_manager._tasks) == 0
        
        task1 = task_manager.create_task(task_func(), name="task1")
        assert len(task_manager._tasks) == 1
        
        task2 = task_manager.create_task(task_func(), name="task2")
        assert len(task_manager._tasks) == 2
        
        # Cleanup
        await task_manager.cancel_all()
    
    @pytest.mark.asyncio
    async def test_task_removal_on_completion(self, task_manager):
        """Test tasks are removed when completed."""
        async def quick_task():
            await asyncio.sleep(0.01)
        
        task = task_manager.create_task(quick_task(), name="quick")
        
        assert len(task_manager._tasks) == 1
        
        await task
        await asyncio.sleep(0.05)  # Wait for cleanup
        
        assert len(task_manager._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_task_removal_on_cancellation(self, task_manager):
        """Test tasks are removed when cancelled."""
        async def long_task():
            await asyncio.sleep(10)
        
        task = task_manager.create_task(long_task(), name="long")
        
        assert len(task_manager._tasks) == 1
        
        await task_manager.cancel_all()
        
        assert len(task_manager._tasks) == 0


class TestCleanupCallbacks:
    """Test cleanup callback functionality (via done_callback)."""
    
    @pytest.mark.asyncio
    async def test_cleanup_callback_on_completion(self, task_manager):
        """Test cleanup callback is called on task completion."""
        # TaskManager uses add_done_callback internally for cleanup
        # We test that tasks are properly removed from tracking
        async def task_with_cleanup():
            await asyncio.sleep(0.01)
        
        task = task_manager.create_task(
            task_with_cleanup(),
            name="cleanup_test"
        )
        
        assert len(task_manager._tasks) == 1
        
        await task
        await asyncio.sleep(0.05)  # Wait for cleanup callback
        
        # Task should be removed from tracking after completion
        assert len(task_manager._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_callback_on_error(self, task_manager):
        """Test cleanup callback is called even on error."""
        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Task failed")
        
        task = task_manager.create_task(
            failing_task(),
            name="failing_cleanup"
        )
        
        assert len(task_manager._tasks) == 1
        
        try:
            await task
        except ValueError:
            pass
        
        await asyncio.sleep(0.05)  # Wait for cleanup callback
        
        # Task should be removed from tracking even after error
        assert len(task_manager._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_callback_on_cancellation(self, task_manager):
        """Test cleanup callback is called on cancellation."""
        async def long_task():
            await asyncio.sleep(10)
        
        task = task_manager.create_task(
            long_task(),
            name="cancel_cleanup"
        )
        
        assert len(task_manager._tasks) == 1
        
        await task_manager.cancel_all()
        await asyncio.sleep(0.05)  # Wait for cleanup callback
        
        # Task should be removed from tracking after cancellation
        assert len(task_manager._tasks) == 0


class TestConcurrency:
    """Test concurrent task operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, task_manager):
        """Test creating tasks concurrently."""
        async def task_func(n):
            await asyncio.sleep(0.01)
            return n
        
        # Create tasks concurrently
        tasks = [
            task_manager.create_task(task_func(i), name=f"concurrent_{i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert results == list(range(10))
    
    @pytest.mark.asyncio
    async def test_concurrent_cancellation(self, task_manager):
        """Test cancelling tasks while others are running."""
        async def task_func(n):
            await asyncio.sleep(0.1)
            return n
        
        # Create multiple tasks
        for i in range(5):
            task_manager.create_task(task_func(i), name=f"task_{i}")
        
        # Cancel while running
        await task_manager.cancel_all()
        
        assert len(task_manager._tasks) == 0


class TestComponentNaming:
    """Test component naming in logs."""
    
    @pytest.mark.asyncio
    async def test_component_name_in_logs(self):
        """Test component name appears in error logs."""
        manager = TaskManager("MyComponent")
        
        async def failing_task():
            raise ValueError("Test error")
        
        # Patch the logger for the specific component
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Create new manager to use mocked logger
            manager = TaskManager("MyComponent")
            
            task = manager.create_task(failing_task(), name="test")
            
            try:
                await task
            except ValueError:
                pass
            
            await asyncio.sleep(0.05)
            
            # Logger should be created with component name
            mock_get_logger.assert_called_with("TaskManager.MyComponent")
            
            # Error should be logged
            assert mock_logger.error.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
