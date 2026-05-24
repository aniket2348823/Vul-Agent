"""
Unit tests for Antigravity V5 Agents
Tests Alpha, Beta, Gamma, Delta, Sigma, Zeta, Kappa, Omega, Prism, and Chi agents
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.hive import EventType, HiveEvent
from backend.core.protocol import JobPacket, AgentID, ModuleConfig, TaskTarget


# ============================================================================
# ALPHA AGENT TESTS
# ============================================================================

class TestAlphaAgent:
    """Test Alpha Agent (Scout - Recon & API Detection)."""
    
    @pytest.fixture
    async def alpha_agent(self):
        """Create Alpha agent instance."""
        from backend.agents.alpha import AlphaAgent
        
        mock_bus = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.publish = AsyncMock()
        mock_bus.get_or_create_context = Mock(return_value=Mock(baseline_cache={}))
        
        agent = AlphaAgent(mock_bus)
        
        # Mock browser
        agent.browser = AsyncMock()
        agent.browser.navigate = AsyncMock(return_value={"success": True})
        agent.browser.detect_framework = AsyncMock(return_value="react")
        agent.browser.extract_endpoints = AsyncMock(return_value=[])
        agent.browser.intercept_network = AsyncMock(return_value=[])
        agent.browser.find_websockets = AsyncMock(return_value=[])
        
        # Mock cortex
        agent.cortex = AsyncMock()
        agent.cortex.classify_target = AsyncMock(return_value={"is_api": False, "tags": []})
        
        yield agent
    
    @pytest.mark.asyncio
    async def test_setup_subscribes_to_events(self, alpha_agent):
        """Test agent subscribes to required events."""
        await alpha_agent.setup()
        
        assert alpha_agent.bus.subscribe.call_count == 2
        # Should subscribe to JOB_ASSIGNED and TARGET_ACQUIRED
        calls = alpha_agent.bus.subscribe.call_args_list
        event_types = [call[0][0] for call in calls]
        assert EventType.JOB_ASSIGNED in event_types
        assert EventType.TARGET_ACQUIRED in event_types
    
    @pytest.mark.asyncio
    async def test_detect_spa_identifies_react(self, alpha_agent):
        """Test SPA detection identifies React apps."""
        alpha_agent.browser.detect_framework = AsyncMock(return_value="react")
        
        is_spa = await alpha_agent._detect_spa("https://example.com")
        
        assert is_spa is True
        alpha_agent.browser.navigate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_spa_identifies_vue(self, alpha_agent):
        """Test SPA detection identifies Vue apps."""
        alpha_agent.browser.detect_framework = AsyncMock(return_value="vue")
        
        is_spa = await alpha_agent._detect_spa("https://example.com")
        
        assert is_spa is True
    
    @pytest.mark.asyncio
    async def test_detect_spa_returns_false_for_non_spa(self, alpha_agent):
        """Test SPA detection returns False for non-SPA sites."""
        alpha_agent.browser.detect_framework = AsyncMock(return_value="none")
        
        is_spa = await alpha_agent._detect_spa("https://example.com")
        
        assert is_spa is False
    
    @pytest.mark.asyncio
    async def test_merge_endpoints_deduplicates(self, alpha_agent):
        """Test endpoint merging removes duplicates."""
        endpoints1 = [
            {"url": "https://api.example.com/users", "method": "GET"},
            {"url": "https://api.example.com/posts", "method": "GET"}
        ]
        endpoints2 = [
            {"url": "https://api.example.com/users", "method": "GET"},  # Duplicate
            {"url": "https://api.example.com/comments", "method": "GET"}
        ]
        
        merged = alpha_agent._merge_endpoints(endpoints1, endpoints2)
        
        assert len(merged) == 3
        urls = [e["url"] for e in merged]
        assert "https://api.example.com/users" in urls
        assert "https://api.example.com/posts" in urls
        assert "https://api.example.com/comments" in urls
    
    @pytest.mark.asyncio
    async def test_handle_job_prevents_infinite_recursion(self, alpha_agent):
        """Test job handler prevents infinite recursion."""
        # Create deep URL that exceeds max depth
        deep_url = "https://example.com/" + "/".join(["a"] * 10)
        
        event = HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="test",
            scan_id="test_scan",
            payload={
                "id": "job_1",
                "priority": 1,
                "target": {"url": deep_url},
                "config": {
                    "module_id": "test_module",
                    "agent_id": "ALPHA",
                    "params": {},
                    "aggression": 1,
                    "session_id": "test_session"
                }
            }
        )
        
        # Should return early without processing
        await alpha_agent.handle_job(event)
        
        # Should not publish any events
        alpha_agent.bus.publish.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_job_detects_api_endpoints(self, alpha_agent):
        """Test job handler detects API endpoints."""
        alpha_agent.cortex.classify_target = AsyncMock(return_value={"is_api": True, "tags": []})
        
        event = HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="test",
            scan_id="test_scan",
            payload={
                "id": "job_1",
                "priority": 1,
                "target": {"url": "https://api.example.com/users"},
                "config": {
                    "module_id": "test_module",
                    "agent_id": "ALPHA",
                    "params": {},
                    "aggression": 1,
                    "session_id": "test_session"
                }
            }
        )
        
        await alpha_agent.handle_job(event)
        
        # Should publish VULN_CANDIDATE event
        calls = alpha_agent.bus.publish.call_args_list
        event_types = [call[0][0].type for call in calls]
        assert EventType.VULN_CANDIDATE in event_types
    
    @pytest.mark.asyncio
    async def test_handle_job_detects_sensitive_paths(self, alpha_agent):
        """Test job handler detects sensitive paths."""
        event = HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="test",
            scan_id="test_scan",
            payload={
                "id": "job_1",
                "priority": 1,
                "target": {"url": "https://example.com/user/profile"},
                "config": {
                    "module_id": "test_module",
                    "agent_id": "ALPHA",
                    "params": {},
                    "aggression": 1,
                    "session_id": "test_session"
                }
            }
        )
        
        await alpha_agent.handle_job(event)
        
        # Should publish TARGET_ACQUIRED event
        calls = alpha_agent.bus.publish.call_args_list
        event_types = [call[0][0].type for call in calls]
        assert EventType.TARGET_ACQUIRED in event_types


# ============================================================================
# BETA AGENT TESTS
# ============================================================================

class TestBetaAgent:
    """Test Beta Agent (CSRF & Session Testing)."""
    
    @pytest.fixture
    async def beta_agent(self):
        """Create Beta agent instance."""
        from backend.agents.beta import BetaAgent
        
        mock_bus = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.publish = AsyncMock()
        
        agent = BetaAgent(mock_bus)
        
        # Mock browser
        agent.browser = AsyncMock()
        agent.browser.navigate = AsyncMock(return_value={"success": True})
        
        # Mock network interceptor
        agent.network_interceptor = AsyncMock()
        agent.network_interceptor.intercept = AsyncMock(return_value=[])
        
        yield agent
    
    @pytest.mark.asyncio
    async def test_csrf_bypass_no_token(self, beta_agent):
        """Test CSRF bypass technique: no token."""
        # Mock successful request without token
        beta_agent.network_interceptor.intercept = AsyncMock(
            return_value=[{"status": 200}]
        )
        
        result = await beta_agent._test_csrf_bypass(
            "https://example.com/api/update",
            method="POST"
        )
        
        assert result["bypassed"] is True
        assert result["technique"] == "no_token"
    
    @pytest.mark.asyncio
    async def test_csrf_bypass_empty_token(self, beta_agent):
        """Test CSRF bypass technique: empty token."""
        # Mock blocked without token, success with empty
        responses = [
            [{"status": 403}],  # No token blocked
            [{"status": 200}]   # Empty token success
        ]
        beta_agent.network_interceptor.intercept = AsyncMock(side_effect=responses)
        
        result = await beta_agent._test_csrf_bypass(
            "https://example.com/api/update",
            method="POST"
        )
        
        assert result["bypassed"] is True
        assert result["technique"] == "empty_token"
    
    @pytest.mark.asyncio
    async def test_csrf_bypass_all_blocked(self, beta_agent):
        """Test CSRF bypass when all techniques blocked."""
        # Mock all requests blocked
        beta_agent.network_interceptor.intercept = AsyncMock(
            return_value=[{"status": 403}]
        )
        
        result = await beta_agent._test_csrf_bypass(
            "https://example.com/api/update",
            method="POST"
        )
        
        assert result["bypassed"] is False
        assert result["technique"] is None


# ============================================================================
# GAMMA AGENT TESTS
# ============================================================================

class TestGammaAgent:
    """Test Gamma Agent (Network Traffic Analysis)."""
    
    @pytest.fixture
    async def gamma_agent(self):
        """Create Gamma agent instance."""
        from backend.agents.gamma import GammaAgent
        
        mock_bus = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.publish = AsyncMock()
        
        agent = GammaAgent(mock_bus)
        
        # Mock network interceptor
        agent.network_interceptor = AsyncMock()
        agent.network_interceptor.capture = AsyncMock(return_value=[])
        
        # Mock forensics
        agent.forensics = AsyncMock()
        agent.forensics.capture_network_logs = AsyncMock()
        
        yield agent
    
    @pytest.mark.asyncio
    async def test_analyze_network_traffic_detects_ssrf(self, gamma_agent):
        """Test network traffic analysis detects SSRF attempts."""
        # Mock network events with SSRF pattern
        network_events = [
            {
                "url": "http://169.254.169.254/latest/meta-data/",
                "method": "GET",
                "status": 200
            }
        ]
        
        gamma_agent.network_interceptor.capture = AsyncMock(return_value=network_events)
        
        result = await gamma_agent._analyze_network_traffic("https://example.com")
        
        assert len(result["suspicious"]) > 0
        assert any("169.254.169.254" in s["url"] for s in result["suspicious"])
    
    @pytest.mark.asyncio
    async def test_analyze_network_traffic_detects_metadata_access(self, gamma_agent):
        """Test detection of cloud metadata access."""
        network_events = [
            {
                "url": "http://metadata.google.internal/",
                "method": "GET",
                "status": 200
            }
        ]
        
        gamma_agent.network_interceptor.capture = AsyncMock(return_value=network_events)
        
        result = await gamma_agent._analyze_network_traffic("https://example.com")
        
        assert len(result["suspicious"]) > 0
        assert any("metadata.google.internal" in s["url"] for s in result["suspicious"])


# ============================================================================
# SIGMA AGENT TESTS
# ============================================================================

class TestSigmaAgent:
    """Test Sigma Agent (DOM Analysis & Payload Generation)."""
    
    @pytest.fixture
    async def sigma_agent(self):
        """Create Sigma agent instance."""
        from backend.agents.sigma import SigmaAgent
        
        mock_bus = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.publish = AsyncMock()
        
        agent = SigmaAgent(mock_bus)
        
        # Mock browser
        agent.browser = AsyncMock()
        agent.browser.navigate = AsyncMock(return_value={"success": True})
        agent.browser.detect_framework = AsyncMock(return_value="react")
        
        yield agent
    
    @pytest.mark.asyncio
    async def test_analyze_dom_structure_detects_framework(self, sigma_agent):
        """Test DOM analysis detects JavaScript framework."""
        result = await sigma_agent._analyze_dom_structure("https://example.com")
        
        assert result["framework"] == "react"
        sigma_agent.browser.navigate.assert_called_once()
        sigma_agent.browser.detect_framework.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_dom_structure_handles_errors(self, sigma_agent):
        """Test DOM analysis handles navigation errors."""
        sigma_agent.browser.navigate = AsyncMock(return_value={"success": False})
        
        result = await sigma_agent._analyze_dom_structure("https://example.com")
        
        assert result["framework"] is None
        assert result["success"] is False


# ============================================================================
# ZETA AGENT TESTS
# ============================================================================

class TestZetaAgent:
    """Test Zeta Agent (Context Management)."""
    
    @pytest.fixture
    async def zeta_agent(self):
        """Create Zeta agent instance."""
        from backend.agents.zeta import ZetaAgent
        
        mock_bus = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.publish = AsyncMock()
        
        agent = ZetaAgent(mock_bus)
        
        # Mock browser orchestrator
        agent.browser_orchestrator = Mock()
        agent.browser_orchestrator._active_contexts = {
            "ctx_1": {
                "scan_id": "scan_1",
                "engine": "openclaw",
                "created_at": 1000,
                "last_activity": 1000
            },
            "ctx_2": {
                "scan_id": "scan_2",
                "engine": "pinchtab",
                "created_at": 2000,
                "last_activity": 2000
            }
        }
        agent.browser_orchestrator.close_context = AsyncMock()
        
        yield agent
    
    @pytest.mark.asyncio
    async def test_get_active_contexts_returns_all(self, zeta_agent):
        """Test getting all active contexts."""
        with patch('time.time', return_value=3000):
            contexts = await zeta_agent._get_active_contexts()
        
        assert len(contexts) == 2
        assert any(c["scan_id"] == "scan_1" for c in contexts)
        assert any(c["scan_id"] == "scan_2" for c in contexts)
    
    @pytest.mark.asyncio
    async def test_close_idle_contexts_closes_old_contexts(self, zeta_agent):
        """Test closing idle contexts."""
        # Make ctx_1 idle (>5 minutes old)
        with patch('time.time', return_value=1000 + 400):  # 400 seconds later
            closed_count = await zeta_agent._close_idle_contexts()
        
        assert closed_count == 1
        zeta_agent.browser_orchestrator.close_context.assert_called_once_with("ctx_1")
    
    @pytest.mark.asyncio
    async def test_close_idle_contexts_keeps_active(self, zeta_agent):
        """Test idle context closure keeps active contexts."""
        # No contexts are idle yet
        with patch('time.time', return_value=1000 + 100):  # 100 seconds later
            closed_count = await zeta_agent._close_idle_contexts()
        
        assert closed_count == 0
        zeta_agent.browser_orchestrator.close_context.assert_not_called()


# ============================================================================
# PRISM AGENT TESTS
# ============================================================================

class TestPrismAgent:
    """Test Prism Agent (HTTP Probing & Iframe Analysis)."""
    
    @pytest.fixture
    async def prism_agent(self):
        """Create Prism agent instance."""
        from backend.agents.prism import PrismAgent
        
        mock_bus = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.publish = AsyncMock()
        
        agent = PrismAgent(mock_bus)
        
        # Mock browser
        agent.browser = AsyncMock()
        agent.browser.navigate = AsyncMock(return_value={"success": True})
        
        yield agent
    
    @pytest.mark.asyncio
    async def test_analyze_iframes_detects_suspicious_patterns(self, prism_agent):
        """Test iframe analysis detects suspicious patterns."""
        # Mock page with suspicious iframe
        prism_agent.browser.navigate = AsyncMock(return_value={
            "success": True,
            "iframes": [
                {"src": "data:text/html,<script>alert(1)</script>"},
                {"src": "https://example.com/normal"}
            ]
        })
        
        result = await prism_agent._analyze_iframes("https://example.com")
        
        assert len(result["suspicious"]) > 0
        assert any("data:text/html" in iframe["src"] for iframe in result["suspicious"])


# ============================================================================
# CHI AGENT TESTS
# ============================================================================

class TestChiAgent:
    """Test Chi Agent (Event Prevention & Clickjacking)."""
    
    @pytest.fixture
    async def chi_agent(self):
        """Create Chi agent instance."""
        from backend.agents.chi import ChiAgent
        
        mock_bus = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.publish = AsyncMock()
        
        agent = ChiAgent(mock_bus)
        
        # Mock forensics
        agent.forensics = AsyncMock()
        agent.forensics.capture_screenshot = AsyncMock()
        
        yield agent
    
    @pytest.mark.asyncio
    async def test_block_event_captures_forensics(self, chi_agent):
        """Test event blocking captures forensic evidence."""
        result = await chi_agent._block_event(
            event_type="click",
            target_selector="#malicious-button",
            scan_id="test_scan"
        )
        
        assert result["blocked"] is True
        chi_agent.forensics.capture_screenshot.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
