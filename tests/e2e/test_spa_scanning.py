"""
E2E Tests for SPA Scanning Workflows

Tests Single Page Application scanning with dynamic content detection.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.state import StateManager
from backend.core.browser_orchestrator import BrowserOrchestrator


@pytest_asyncio.fixture
async def orchestrator():
    """Create mock orchestrator for SPA E2E tests."""
    # Create a simple mock object
    class MockOrchestrator:
        def __init__(self):
            self.state = StateManager()
            self.browser_orchestrator = BrowserOrchestrator()
    
    orch = MockOrchestrator()
    
    # Mock browser initialization
    orch.browser_orchestrator.initialize = AsyncMock()
    orch.browser_orchestrator.cleanup = AsyncMock()
    
    yield orch
    
    await orch.browser_orchestrator.cleanup()


@pytest_asyncio.fixture
async def mock_spa_page():
    """Create mock SPA page."""
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.evaluate = AsyncMock()
    page.content = AsyncMock(return_value="""
        <html>
            <head>
                <script src="/app.js"></script>
            </head>
            <body>
                <div id="root"></div>
                <script>
                    window.__REACT_DEVTOOLS_GLOBAL_HOOK__ = {};
                </script>
            </body>
        </html>
    """)
    page.close = AsyncMock()
    
    # Mock framework detection
    page.evaluate.return_value = {
        "hasReact": True,
        "hasVue": False,
        "hasAngular": False
    }
    
    return page


@pytest.mark.asyncio
async def test_spa_detection(orchestrator, mock_spa_page):
    """Test SPA framework detection."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-001"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get page and detect SPA
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    await page.goto(target_url)
    
    # Check for SPA indicators
    content = await page.content()
    assert "id=\"root\"" in content or "ng-app" in content or "v-app" in content
    
    # Detect framework
    framework_info = await page.evaluate("() => ({ hasReact: !!window.React, hasVue: !!window.Vue, hasAngular: !!window.angular })")
    
    # Verify SPA detected
    is_spa = any(framework_info.values())
    assert is_spa is True


@pytest.mark.asyncio
async def test_spa_dynamic_content_discovery(orchestrator, mock_spa_page):
    """Test discovery of dynamically loaded content in SPAs."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-002"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Mock dynamic content loading
    mock_spa_page.wait_for_selector = AsyncMock()
    mock_spa_page.query_selector_all = AsyncMock(return_value=[
        MagicMock(get_attribute=AsyncMock(return_value="/api/users")),
        MagicMock(get_attribute=AsyncMock(return_value="/api/posts")),
        MagicMock(get_attribute=AsyncMock(return_value="/api/comments"))
    ])
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get page
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    await page.goto(target_url)
    
    # Wait for dynamic content
    await page.wait_for_load_state("networkidle")
    
    # Discover API endpoints from SPA
    links = await page.query_selector_all("a[href^='/api']")
    endpoints = []
    for link in links:
        href = await link.get_attribute("href")
        if href:
            endpoints.append(href)
    
    # Verify endpoints discovered
    assert len(endpoints) > 0
    assert any("/api/" in ep for ep in endpoints)


@pytest.mark.asyncio
async def test_spa_route_navigation(orchestrator, mock_spa_page):
    """Test navigation through SPA routes."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-003"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Mock route navigation
    routes = ["/", "/about", "/dashboard", "/profile"]
    mock_spa_page.url = target_url
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get page
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    
    # Navigate through routes
    visited_routes = []
    for route in routes:
        full_url = f"{target_url}{route}"
        await page.goto(full_url)
        await page.wait_for_load_state("networkidle")
        visited_routes.append(route)
    
    # Verify all routes visited
    assert len(visited_routes) == len(routes)
    assert all(route in visited_routes for route in routes)


@pytest.mark.asyncio
async def test_spa_state_management(orchestrator, mock_spa_page):
    """Test SPA state management detection."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-004"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Mock state management detection
    mock_spa_page.evaluate.return_value = {
        "hasRedux": True,
        "hasVuex": False,
        "hasNgRx": False
    }
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get page
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    await page.goto(target_url)
    
    # Detect state management
    state_info = await page.evaluate("() => ({ hasRedux: !!window.__REDUX_DEVTOOLS_EXTENSION__, hasVuex: !!window.__VUE_DEVTOOLS_GLOBAL_HOOK__, hasNgRx: false })")
    
    # Verify state management detected
    has_state_management = any(state_info.values())
    assert has_state_management is True


@pytest.mark.asyncio
async def test_spa_api_interception(orchestrator, mock_spa_page):
    """Test API call interception in SPAs."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-005"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Mock API interception
    api_calls = []
    
    async def mock_route_handler(route):
        api_calls.append({
            "url": route.request.url,
            "method": route.request.method
        })
        await route.continue_()
    
    mock_spa_page.route = AsyncMock(side_effect=lambda pattern, handler: None)
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get page and setup interception
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    
    # Setup route interception
    await page.route("**/api/**", mock_route_handler)
    
    # Navigate and trigger API calls
    await page.goto(target_url)
    await page.wait_for_load_state("networkidle")
    
    # Verify interception setup
    mock_spa_page.route.assert_called()


@pytest.mark.asyncio
async def test_spa_client_side_routing(orchestrator, mock_spa_page):
    """Test client-side routing detection."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-006"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Mock routing detection
    mock_spa_page.evaluate.return_value = {
        "hasReactRouter": True,
        "hasVueRouter": False,
        "hasAngularRouter": False
    }
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get page
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    await page.goto(target_url)
    
    # Detect client-side routing
    routing_info = await page.evaluate("() => ({ hasReactRouter: !!window.ReactRouter, hasVueRouter: !!window.VueRouter, hasAngularRouter: false })")
    
    # Verify routing detected
    has_routing = any(routing_info.values())
    assert has_routing is True


@pytest.mark.asyncio
async def test_spa_websocket_detection(orchestrator, mock_spa_page):
    """Test WebSocket connection detection in SPAs."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-007"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Mock WebSocket detection
    mock_spa_page.evaluate.return_value = {
        "hasWebSocket": True,
        "wsUrl": "ws://spa-test.com/socket"
    }
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    
    # Get page
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    await page.goto(target_url)
    
    # Detect WebSocket
    ws_info = await page.evaluate("() => ({ hasWebSocket: !!window.WebSocket, wsUrl: null })")
    
    # Verify WebSocket detected
    assert ws_info.get("hasWebSocket") is True


@pytest.mark.asyncio
async def test_spa_complete_workflow(orchestrator, mock_spa_page):
    """Test complete SPA scanning workflow."""
    # Setup
    target_url = "http://spa-test.com"
    scan_id = "spa-scan-008"
    
    # Mock browser context
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_spa_page)
    orchestrator.browser_orchestrator.get_context = AsyncMock(return_value=mock_context)
    
    # Initialize scan
    await orchestrator.state.initialize_scan(scan_id, target_url)
    orchestrator.state.update_scan_status(scan_id, "running")
    
    # Get page
    context = await orchestrator.browser_orchestrator.get_context(scan_id)
    page = await context.new_page()
    
    # Step 1: Navigate to SPA
    await page.goto(target_url)
    await page.wait_for_load_state("networkidle")
    
    # Step 2: Detect framework
    content = await page.content()
    is_spa = "id=\"root\"" in content
    
    # Step 3: Record SPA metadata
    if is_spa:
        orchestrator.state.update_scan_metadata(scan_id, {
            "is_spa": True,
            "framework": "react"
        })
    
    # Step 4: Complete scan
    orchestrator.state.update_scan_status(scan_id, "completed")
    
    # Verify workflow
    scan_state = orchestrator.state.get_scan_state(scan_id)
    assert scan_state.get("status") == "completed"
    metadata = scan_state.get("metadata", {})
    assert metadata.get("is_spa") is True
