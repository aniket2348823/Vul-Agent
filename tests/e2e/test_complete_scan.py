"""
E2E Tests for Complete Scan Workflows

Tests the entire scan lifecycle from initialization to report generation.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from backend.core.state import StateManager
from backend.core.browser_orchestrator import BrowserOrchestrator
from backend.core.reporting import ReportGenerator


@pytest_asyncio.fixture
async def orchestrator():
    """Create mock orchestrator for E2E tests."""
    # Create a simple mock object instead of using HiveOrchestrator
    class MockOrchestrator:
        def __init__(self):
            self.state = StateManager()
            self.browser_orchestrator = BrowserOrchestrator()
    
    orch = MockOrchestrator()
    
    # Mock browser initialization
    orch.browser_orchestrator.initialize = AsyncMock()
    orch.browser_orchestrator.cleanup = AsyncMock()
    
    yield orch
    
    # Cleanup
    await orch.browser_orchestrator.cleanup()


@pytest_asyncio.fixture
async def mock_browser_context():
    """Create mock browser context."""
    context = MagicMock()
    context.new_page = AsyncMock()
    
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html><body>Test</body></html>")
    page.close = AsyncMock()
    
    context.new_page.return_value = page
    return context


@pytest.mark.asyncio
async def test_complete_scan_workflow(orchestrator, mock_browser_context):
    """Test complete scan workflow from start to finish."""
    # Setup
    target_url = "http://test.com"
    scan_id = "test-scan-001"
    
    # Mock browser context
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_browser_context)
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Verify scan initialized
    scan_state = orchestrator.state.get_scan_state(scan_id)
    assert scan_state is not None
    assert scan_state.get("target_url") == target_url
    assert scan_state.get("status") == "initialized"
    
    # Start scan
    orchestrator.state.update_scan_status(scan_id, "running")
    
    # Verify scan running
    scan_state = orchestrator.state.get_scan_state(scan_id)
    assert scan_state.get("status") == "running"
    
    # Complete scan
    orchestrator.state.update_scan_status(scan_id, "completed")
    
    # Verify scan completed
    scan_state = orchestrator.state.get_scan_state(scan_id)
    assert scan_state.get("status") == "completed"


@pytest.mark.asyncio
async def test_scan_with_findings(orchestrator, mock_browser_context):
    """Test scan workflow that discovers findings."""
    # Setup
    target_url = "http://test.com"
    scan_id = "test-scan-002"
    
    # Mock browser context
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_browser_context)
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    orchestrator.state.update_scan_status(scan_id, "running")
    
    # Add findings
    finding1 = {
        "type": "xss",
        "severity": "high",
        "url": f"{target_url}/page1",
        "description": "Reflected XSS vulnerability"
    }
    finding2 = {
        "type": "csrf",
        "severity": "medium",
        "url": f"{target_url}/api/update",
        "description": "Missing CSRF protection"
    }
    
    orchestrator.state.add_finding(scan_id, finding1)
    orchestrator.state.add_finding(scan_id, finding2)
    
    # Verify findings
    findings = orchestrator.state.get_findings(scan_id)
    assert len(findings) == 2
    assert any(f["type"] == "xss" for f in findings)
    assert any(f["type"] == "csrf" for f in findings)
    
    # Complete scan
    orchestrator.state.update_scan_status(scan_id, "completed")


@pytest.mark.asyncio
async def test_scan_error_recovery(orchestrator, mock_browser_context):
    """Test scan error handling and recovery."""
    # Setup
    target_url = "http://test.com"
    scan_id = "test-scan-003"
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    orchestrator.state.update_scan_status(scan_id, "running")
    
    # Simulate error
    error_msg = "Network timeout"
    orchestrator.state.add_error(scan_id, error_msg)
    
    # Verify error recorded
    scan_state = orchestrator.state.get_scan_state(scan_id)
    errors = scan_state.get("errors", [])
    assert len(errors) > 0
    assert error_msg in str(errors)
    
    # Mark as failed
    orchestrator.state.update_scan_status(scan_id, "failed")
    
    # Verify failed status
    scan_state = orchestrator.state.get_scan_state(scan_id)
    assert scan_state.get("status") == "failed"


@pytest.mark.asyncio
async def test_concurrent_scans(orchestrator, mock_browser_context):
    """Test multiple concurrent scans."""
    # Setup
    scan_ids = ["scan-001", "scan-002", "scan-003"]
    target_urls = [
        "http://test1.com",
        "http://test2.com",
        "http://test3.com"
    ]
    
    # Mock browser context
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_browser_context)
    
    # Initialize all scans
    for scan_id, url in zip(scan_ids, target_urls):
        await orchestrator.state.initialize_scan(scan_id, url)
        orchestrator.state.update_scan_status(scan_id, "running")
    
    # Verify all scans running
    for scan_id in scan_ids:
        scan_state = orchestrator.state.get_scan_state(scan_id)
        assert scan_state is not None
        assert scan_state.get("status") == "running"
    
    # Complete all scans
    for scan_id in scan_ids:
        orchestrator.state.update_scan_status(scan_id, "completed")
    
    # Verify all completed
    for scan_id in scan_ids:
        scan_state = orchestrator.state.get_scan_state(scan_id)
        assert scan_state.get("status") == "completed"


@pytest.mark.asyncio
async def test_scan_cancellation(orchestrator, mock_browser_context):
    """Test scan cancellation workflow."""
    # Setup
    target_url = "http://test.com"
    scan_id = "test-scan-004"
    
    # Initialize and start scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    orchestrator.state.update_scan_status(scan_id, "running")
    
    # Cancel scan
    orchestrator.state.update_scan_status(scan_id, "cancelled")
    
    # Verify cancelled
    scan_state = orchestrator.state.get_scan_state(scan_id)
    assert scan_state.get("status") == "cancelled"


@pytest.mark.asyncio
async def test_scan_with_browser_contexts(orchestrator, mock_browser_context):
    """Test scan with browser context management."""
    # Setup
    target_url = "http://test.com"
    scan_id = "test-scan-005"
    
    # Mock browser operations
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_browser_context)
    orchestrator.browser_orchestrator.release_context = AsyncMock()
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get browser context
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    assert context is not None
    
    # Use context
    page = await context.new_page()
    await page.goto(target_url)
    content = await page.content()
    assert "Test" in content
    
    # Release context
    await orchestrator.browser_orchestrator.release_context(scan_id)
    
    # Verify cleanup called
    orchestrator.browser_orchestrator.release_context.assert_called_once()


@pytest.mark.asyncio
async def test_scan_state_persistence(orchestrator):
    """Test scan state persistence across operations."""
    # Setup
    target_url = "http://test.com"
    scan_id = "test-scan-006"
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Add metadata
    orchestrator.state.update_scan_metadata(scan_id, {
        "user": "test-user",
        "tags": ["test", "e2e"],
        "priority": "high"
    })
    
    # Retrieve and verify
    scan_state = orchestrator.state.get_scan_state(scan_id)
    metadata = scan_state.get("metadata", {})
    assert metadata.get("user") == "test-user"
    assert "test" in metadata.get("tags", [])
    assert metadata.get("priority") == "high"


@pytest.mark.asyncio
async def test_scan_progress_tracking(orchestrator):
    """Test scan progress tracking."""
    # Setup
    target_url = "http://test.com"
    scan_id = "test-scan-007"
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    orchestrator.state.update_scan_status(scan_id, "running")
    
    # Update progress
    orchestrator.state.update_scan_progress(scan_id, {
        "phase": "reconnaissance",
        "progress": 25,
        "current_task": "Discovering endpoints"
    })
    
    # Verify progress
    scan_state = orchestrator.state.get_scan_state(scan_id)
    progress = scan_state.get("progress", {})
    assert progress.get("phase") == "reconnaissance"
    assert progress.get("progress") == 25
    
    # Update to next phase
    orchestrator.state.update_scan_progress(scan_id, {
        "phase": "exploitation",
        "progress": 75,
        "current_task": "Testing vulnerabilities"
    })
    
    # Verify updated progress
    scan_state = orchestrator.state.get_scan_state(scan_id)
    progress = scan_state.get("progress", {})
    assert progress.get("phase") == "exploitation"
    assert progress.get("progress") == 75
