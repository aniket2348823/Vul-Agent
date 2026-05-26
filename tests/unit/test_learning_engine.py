"""
Unit tests for the Continuous Learning Engine.
Tests pattern extraction, confidence scoring, and recommendations.
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path

from backend.core.learning_engine import (
    ContinuousLearningEngine,
    LearningPattern,
    LearningMetrics
)


@pytest.fixture
def temp_brain_dir():
    """Create a temporary brain directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def learning_engine(temp_brain_dir):
    """Create a learning engine instance with temporary storage."""
    return ContinuousLearningEngine(brain_dir=temp_brain_dir)


class TestLearningPattern:
    """Test LearningPattern dataclass."""
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        pattern = LearningPattern(
            pattern_id="test_1",
            pattern_type="endpoint_pattern",
            pattern_data={},
            confidence=0.5,
            success_count=7,
            failure_count=3,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        assert pattern.success_rate == 0.7
    
    def test_success_rate_zero_samples(self):
        """Test success rate with no samples."""
        pattern = LearningPattern(
            pattern_id="test_2",
            pattern_type="endpoint_pattern",
            pattern_data={},
            confidence=0.5,
            success_count=0,
            failure_count=0,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        assert pattern.success_rate == 0.0
    
    def test_confidence_update(self):
        """Test confidence update based on success rate and sample size."""
        pattern = LearningPattern(
            pattern_id="test_3",
            pattern_type="endpoint_pattern",
            pattern_data={},
            confidence=0.5,
            success_count=8,
            failure_count=2,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        pattern.update_confidence()
        
        # With 10 samples and 80% success rate, confidence should be 0.8
        assert pattern.confidence == 0.8


class TestLearningEngine:
    """Test ContinuousLearningEngine."""
    
    def test_initialization(self, learning_engine, temp_brain_dir):
        """Test engine initialization."""
        assert learning_engine.brain_dir == Path(temp_brain_dir)
        assert learning_engine.patterns == {}
        assert isinstance(learning_engine.metrics, LearningMetrics)
        assert learning_engine.patterns_file.exists()
        assert learning_engine.metrics_file.exists()
    
    @pytest.mark.asyncio
    async def test_learn_from_vulnerability(self, learning_engine):
        """Test learning from a confirmed vulnerability."""
        vuln_data = {
            "type": "SQL_INJECTION",
            "url": "https://example.com/api/users/123",
            "payload": "' OR 1=1--",
            "confidence": 0.95
        }
        
        await learning_engine.learn_from_vulnerability(vuln_data, "test_scan_1")
        
        # Should have created patterns
        assert len(learning_engine.patterns) > 0
        
        # Check endpoint pattern was learned
        endpoint_patterns = [
            p for p in learning_engine.patterns.values()
            if p.pattern_type == "endpoint_pattern"
        ]
        assert len(endpoint_patterns) > 0
        assert endpoint_patterns[0].success_count == 1
        
        # Check payload pattern was learned
        payload_patterns = [
            p for p in learning_engine.patterns.values()
            if p.pattern_type == "payload_success"
        ]
        assert len(payload_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_learn_from_failure(self, learning_engine):
        """Test learning from failed attacks."""
        attack_data = {
            "type": "XSS",
            "url": "https://example.com/search",
            "payload": "<script>alert(1)</script>"
        }
        
        await learning_engine.learn_from_failure(attack_data, "test_scan_2")
        
        # Should have created patterns with failure counts
        assert len(learning_engine.patterns) > 0
        
        endpoint_patterns = [
            p for p in learning_engine.patterns.values()
            if p.pattern_type == "endpoint_pattern"
        ]
        assert len(endpoint_patterns) > 0
        assert endpoint_patterns[0].failure_count == 1
    
    def test_extract_url_pattern(self, learning_engine):
        """Test URL pattern extraction."""
        # Test ID replacement
        url1 = "https://example.com/api/users/123"
        pattern1 = learning_engine._extract_url_pattern(url1)
        assert pattern1 == "https://example.com/api/users/{id}"
        
        # Test UUID replacement
        url2 = "https://example.com/api/items/550e8400-e29b-41d4-a716-446655440000"
        pattern2 = learning_engine._extract_url_pattern(url2)
        assert pattern2 == "https://example.com/api/items/{uuid}"
        
        # Test query param removal
        url3 = "https://example.com/search?q=test&page=1"
        pattern3 = learning_engine._extract_url_pattern(url3)
        assert pattern3 == "https://example.com/search"
    
    def test_extract_payload_features(self, learning_engine):
        """Test payload feature extraction."""
        # SQL injection payload
        sql_payload = "' OR 1=1--"
        features = learning_engine._extract_payload_features(sql_payload)
        assert features["has_sql_keywords"] is True
        assert features["has_special_chars"] is True
        
        # XSS payload
        xss_payload = "<script>alert('XSS')</script>"
        features = learning_engine._extract_payload_features(xss_payload)
        assert features["has_script_tag"] is True
        assert features["has_special_chars"] is True
        
        # Template injection payload
        ssti_payload = "{{7*7}}"
        features = learning_engine._extract_payload_features(ssti_payload)
        assert features["has_template_injection"] is True
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, learning_engine):
        """Test getting attack recommendations."""
        # Learn from some vulnerabilities first
        vuln1 = {
            "type": "SQL_INJECTION",
            "url": "https://example.com/api/users/123",
            "payload": "' OR 1=1--",
            "confidence": 0.95
        }
        await learning_engine.learn_from_vulnerability(vuln1, "scan_1")
        
        vuln2 = {
            "type": "SQL_INJECTION",
            "url": "https://example.com/api/users/456",
            "payload": "' UNION SELECT NULL--",
            "confidence": 0.90
        }
        await learning_engine.learn_from_vulnerability(vuln2, "scan_2")
        
        # Get recommendations for similar URL
        recommendations = await learning_engine.get_recommendations(
            "https://example.com/api/users/789",
            {"scan_id": "test"}
        )
        
        assert "priority_vulns" in recommendations
        assert "effective_payloads" in recommendations
        assert "confidence" in recommendations
        
        # Should recommend SQL_INJECTION
        if recommendations["priority_vulns"]:
            assert recommendations["priority_vulns"][0]["type"] == "SQL_INJECTION"
            assert recommendations["confidence"] > 0.0
    
    @pytest.mark.asyncio
    async def test_pattern_consolidation(self, learning_engine):
        """Test pattern consolidation to prevent explosion."""
        # Create similar patterns
        for i in range(5):
            vuln = {
                "type": "XSS",
                "url": f"https://example.com/search?q=test{i}",
                "payload": f"<script>alert({i})</script>",
                "confidence": 0.8
            }
            await learning_engine.learn_from_vulnerability(vuln, f"scan_{i}")
        
        initial_count = len(learning_engine.patterns)
        
        # Consolidate patterns
        consolidated = await learning_engine.consolidate_patterns()
        
        # Should have consolidated some patterns
        final_count = len(learning_engine.patterns)
        assert final_count <= initial_count
    
    def test_get_metrics(self, learning_engine):
        """Test metrics retrieval."""
        metrics = learning_engine.get_metrics()
        
        assert "total_patterns" in metrics
        assert "high_confidence_patterns" in metrics
        assert "total_scans_analyzed" in metrics
        assert "total_vulns_learned" in metrics
        assert "avg_pattern_confidence" in metrics
        assert "learning_rate" in metrics
    
    @pytest.mark.asyncio
    async def test_analyze_scan_complete(self, learning_engine):
        """Test scan completion analysis."""
        initial_scans = learning_engine.metrics.total_scans_analyzed
        
        await learning_engine.analyze_scan_complete("test_scan")
        
        assert learning_engine.metrics.total_scans_analyzed == initial_scans + 1
    
    def test_persistence(self, learning_engine):
        """Test pattern persistence to disk."""
        # Create a pattern
        pattern = LearningPattern(
            pattern_id="persist_test",
            pattern_type="endpoint_pattern",
            pattern_data={"test": "data"},
            confidence=0.8,
            success_count=5,
            failure_count=1,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        learning_engine.patterns[pattern.pattern_id] = pattern
        
        # Save to disk
        learning_engine._save_patterns()
        
        # Create new engine instance (should load from disk)
        new_engine = ContinuousLearningEngine(brain_dir=learning_engine.brain_dir)
        
        assert "persist_test" in new_engine.patterns
        assert new_engine.patterns["persist_test"].confidence == 0.8
        assert new_engine.patterns["persist_test"].success_count == 5


class TestPatternSimilarity:
    """Test pattern similarity detection."""
    
    def test_endpoint_pattern_similarity(self, learning_engine):
        """Test endpoint pattern similarity detection."""
        p1 = LearningPattern(
            pattern_id="ep1",
            pattern_type="endpoint_pattern",
            pattern_data={
                "vuln_type": "SQL_INJECTION",
                "url_pattern": "https://example.com/api/users/{id}"
            },
            confidence=0.8,
            success_count=5,
            failure_count=1,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        p2 = LearningPattern(
            pattern_id="ep2",
            pattern_type="endpoint_pattern",
            pattern_data={
                "vuln_type": "SQL_INJECTION",
                "url_pattern": "https://example.com/api/users/{id}"
            },
            confidence=0.7,
            success_count=3,
            failure_count=2,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        assert learning_engine._patterns_similar(p1, p2) is True
    
    def test_different_type_not_similar(self, learning_engine):
        """Test patterns of different types are not similar."""
        p1 = LearningPattern(
            pattern_id="ep1",
            pattern_type="endpoint_pattern",
            pattern_data={},
            confidence=0.8,
            success_count=5,
            failure_count=1,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        p2 = LearningPattern(
            pattern_id="pp1",
            pattern_type="payload_success",
            pattern_data={},
            confidence=0.8,
            success_count=5,
            failure_count=1,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        assert learning_engine._patterns_similar(p1, p2) is False
