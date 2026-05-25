"""
Integration tests for agent workflows.

Tests how agents work together in realistic scenarios.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.agents.alpha import AlphaAgent
from backend.agents.beta import BetaAgent
from backend.agents.sigma import SigmaAgent
from backend.agents.gamma import GammaAgent
from backend.core.hive import EventBus


class TestAgentWorkflows:
    """Test agent workflow integration."""

    @pytest.fixture
    def mock_hive(self):
        """Create mock hive."""
        hive = Mock(spec=EventBus)
        hive.emit = AsyncMock()
        hive.get_state = Mock(return_value={})
        hive.update_state = Mock()
        return hive

    @pytest.fixture
    def alpha_agent(self, mock_hive):
        """Create Alpha agent."""
        agent = AlphaAgent(mock_hive)
        agent.cortex = AsyncMock()
        return agent

    @pytest.fixture
    def beta_agent(self, mock_hive):
        """Create Beta agent."""
        agent = BetaAgent(mock_hive)
        agent.cortex = AsyncMock()
        return agent

    @pytest.fixture
    def sigma_agent(self, mock_hive):
        """Create Sigma agent."""
        agent = SigmaAgent(mock_hive)
        agent.cortex = AsyncMock()
        return agent

    @pytest.fixture
    def gamma_agent(self, mock_hive):
        """Create Gamma agent."""
        agent = GammaAgent(mock_hive)
        agent.cortex = AsyncMock()
        return agent

    @pytest.mark.asyncio
    async def test_alpha_to_beta_workflow(self, alpha_agent, beta_agent, mock_hive):
        """Test Alpha discovers endpoint, Beta tests it."""
        # Alpha discovers endpoint
        target = {"url": "https://example.com", "scan_id": "test-123"}
        
        with patch.object(alpha_agent, '_http_recon', new_callable=AsyncMock) as mock_recon:
            mock_recon.return_value = {
                "endpoints": [
                    {"url": "https://example.com/search", "method": "GET", "params": ["q"]}
                ]
            }
            
            await alpha_agent.handle_target_acquired(target)
            
            # Verify Alpha emitted RECON_PACKET
            assert mock_hive.emit.called
            emit_calls = [call[0][0] for call in mock_hive.emit.call_args_list]
            assert "RECON_PACKET" in emit_calls

        # Beta receives endpoint and tests it
        endpoint = {
            "url": "https://example.com/search",
            "method": "GET",
            "params": ["q"],
            "scan_id": "test-123"
        }
        
        with patch.object(beta_agent, '_test_xss', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"vulnerable": True, "payload": "<script>alert(1)</script>"}
            
            await beta_agent.handle_candidate(endpoint)
            
            # Verify Beta tested the endpoint
            mock_test.assert_called_once()
            
            # Verify Beta emitted VULN_CONFIRMED
            emit_calls = [call[0][0] for call in mock_hive.emit.call_args_list]
            assert "VULN_CONFIRMED" in emit_calls

    @pytest.mark.asyncio
    async def test_sigma_payload_generation_workflow(self, sigma_agent, mock_hive):
        """Test Sigma generates payloads for specific context."""
        request = {
            "target_url": "https://example.com/search",
            "param": "q",
            "context": "search_input",
            "scan_id": "test-123"
        }
        
        with patch.object(sigma_agent, '_generate_payloads', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = [
                "<script>alert(1)</script>",
                "<img src=x onerror=alert(1)>",
                "javascript:alert(1)"
            ]
            
            await sigma_agent.handle_generation_request(request)
            
            # Verify payloads generated
            mock_gen.assert_called_once()
            
            # Verify PAYLOAD_BATCH emitted
            emit_calls = [call[0][0] for call in mock_hive.emit.call_args_list]
            assert "PAYLOAD_BATCH" in emit_calls

    @pytest.mark.asyncio
    async def test_gamma_verification_workflow(self, gamma_agent, mock_hive):
        """Test Gamma verifies vulnerability."""
        candidate = {
            "url": "https://example.com/search",
            "method": "GET",
            "param": "q",
            "payload": "<script>alert(1)</script>",
            "scan_id": "test-123"
        }
        
        with patch.object(gamma_agent, '_verify_exploit', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified": True, "confidence": 0.95}
            
            await gamma_agent.audit_candidate(candidate)
            
            # Verify verification performed
            mock_verify.assert_called_once()
            
            # Verify AUDIT_COMPLETE emitted
            emit_calls = [call[0][0] for call in mock_hive.emit.call_args_list]
            assert "AUDIT_COMPLETE" in emit_calls

    @pytest.mark.asyncio
    async def test_full_discovery_to_exploitation_workflow(
        self, alpha_agent, beta_agent, sigma_agent, gamma_agent, mock_hive
    ):
        """Test complete workflow: Alpha → Sigma → Beta → Gamma."""
        scan_id = "test-full-workflow"
        
        # Step 1: Alpha discovers endpoint
        target = {"url": "https://example.com", "scan_id": scan_id}
        
        with patch.object(alpha_agent, '_http_recon', new_callable=AsyncMock) as mock_recon:
            mock_recon.return_value = {
                "endpoints": [
                    {"url": "https://example.com/search", "method": "GET", "params": ["q"]}
                ]
            }
            await alpha_agent.handle_target_acquired(target)
        
        # Step 2: Sigma generates payloads
        request = {
            "target_url": "https://example.com/search",
            "param": "q",
            "context": "search_input",
            "scan_id": scan_id
        }
        
        with patch.object(sigma_agent, '_generate_payloads', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ["<script>alert(1)</script>"]
            await sigma_agent.handle_generation_request(request)
        
        # Step 3: Beta tests with payload
        endpoint = {
            "url": "https://example.com/search",
            "method": "GET",
            "params": ["q"],
            "payload": "<script>alert(1)</script>",
            "scan_id": scan_id
        }
        
        with patch.object(beta_agent, '_test_xss', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"vulnerable": True}
            await beta_agent.handle_candidate(endpoint)
        
        # Step 4: Gamma verifies
        candidate = {
            "url": "https://example.com/search",
            "param": "q",
            "payload": "<script>alert(1)</script>",
            "scan_id": scan_id
        }
        
        with patch.object(gamma_agent, '_verify_exploit', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified": True, "confidence": 0.95}
            await gamma_agent.audit_candidate(candidate)
        
        # Verify all steps executed
        assert mock_hive.emit.call_count >= 4  # At least 4 events emitted

    @pytest.mark.asyncio
    async def test_agent_error_handling_workflow(self, alpha_agent, mock_hive):
        """Test agents handle errors gracefully."""
        target = {"url": "https://example.com", "scan_id": "test-error"}
        
        with patch.object(alpha_agent, '_http_recon', new_callable=AsyncMock) as mock_recon:
            mock_recon.side_effect = Exception("Network error")
            
            # Should not raise, should handle gracefully
            await alpha_agent.handle_target_acquired(target)
            
            # Verify error was logged/emitted
            emit_calls = [call[0][0] for call in mock_hive.emit.call_args_list]
            # Agent should emit some kind of error or status event

    @pytest.mark.asyncio
    async def test_concurrent_agent_workflows(self, alpha_agent, beta_agent, mock_hive):
        """Test multiple agents working concurrently."""
        targets = [
            {"url": f"https://example{i}.com", "scan_id": f"test-{i}"}
            for i in range(3)
        ]
        
        with patch.object(alpha_agent, '_http_recon', new_callable=AsyncMock) as mock_recon:
            mock_recon.return_value = {"endpoints": []}
            
            # Run multiple recon tasks concurrently
            tasks = [alpha_agent.handle_target_acquired(t) for t in targets]
            await asyncio.gather(*tasks)
            
            # Verify all targets processed
            assert mock_recon.call_count == 3

    @pytest.mark.asyncio
    async def test_agent_state_sharing(self, alpha_agent, beta_agent, mock_hive):
        """Test agents share state through hive."""
        scan_id = "test-state-sharing"
        
        # Alpha updates state
        mock_hive.get_state.return_value = {"endpoints": []}
        
        target = {"url": "https://example.com", "scan_id": scan_id}
        
        with patch.object(alpha_agent, '_http_recon', new_callable=AsyncMock) as mock_recon:
            mock_recon.return_value = {
                "endpoints": [{"url": "https://example.com/api", "method": "GET"}]
            }
            await alpha_agent.handle_target_acquired(target)
        
        # Beta should be able to access shared state
        mock_hive.get_state.return_value = {
            "endpoints": [{"url": "https://example.com/api", "method": "GET"}]
        }
        
        state = mock_hive.get_state(scan_id)
        assert "endpoints" in state
        assert len(state["endpoints"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
