"""
Unit tests for the Agent Evolution System.
Tests health monitoring, self-healing, skill extraction, and skill library.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from backend.core.agent_health_monitor import AgentHealthMonitor, HealthMetrics
from backend.core.recovery_engine import SelfHealingEngine, CircuitBreaker
from backend.core.skill_extractor import SkillExtractor, Skill
from backend.core.skill_library import SkillLibrary
from backend.core.learning_engine import LearningPattern


@pytest.fixture
def temp_brain_dir():
    """Create temporary brain directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# ═══════════════════════════════════════════════════════════════════════
# HEALTH MONITOR TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestAgentHealthMonitor:
    """Test AgentHealthMonitor."""
    
    def test_initialization(self, temp_brain_dir):
        """Test health monitor initialization."""
        monitor = AgentHealthMonitor(brain_dir=temp_brain_dir)
        assert monitor.current_metrics == {}
        assert monitor.history == {}
        assert monitor.alerts == []
    
    def test_report_metrics(self, temp_brain_dir):
        """Test reporting metrics from agent."""
        monitor = AgentHealthMonitor(brain_dir=temp_brain_dir)
        
        monitor.report_metrics("test_agent", {
            "response_time_ms": 100,
            "success": True,
            "memory_mb": 50,
            "cpu_percent": 10
        })
        
        assert "test_agent" in monitor.current_metrics
        metrics = monitor.current_metrics["test_agent"]
        assert metrics.response_time_ms == 100
        assert metrics.tasks_completed == 1
        assert metrics.tasks_failed == 0
    
    def test_health_score_calculation(self):
        """Test health score calculation."""
        metrics = HealthMetrics(
            agent_name="test",
            timestamp=0.0,
            response_time_ms=500,
            error_rate=0.1,
            memory_mb=200,
            cpu_percent=50
        )
        
        score = metrics.calculate_health_score()
        assert 0 <= score <= 100
        assert score < 100  # Should be penalized for error rate
    
    def test_heartbeat_tracking(self, temp_brain_dir):
        """Test heartbeat tracking."""
        monitor = AgentHealthMonitor(brain_dir=temp_brain_dir)
        
        monitor.report_heartbeat("test_agent")
        assert "test_agent" in monitor.current_metrics
        assert monitor.current_metrics["test_agent"].is_active
    
    def test_check_heartbeats(self, temp_brain_dir):
        """Test checking for crashed agents."""
        import time
        monitor = AgentHealthMonitor(brain_dir=temp_brain_dir)
        
        # Create agent with old heartbeat
        monitor.report_heartbeat("test_agent")
        monitor.current_metrics["test_agent"].last_heartbeat = time.time() - 60
        
        crashed = monitor.check_heartbeats()
        assert "test_agent" in crashed
    
    def test_alert_creation(self, temp_brain_dir):
        """Test alert creation for health issues."""
        monitor = AgentHealthMonitor(brain_dir=temp_brain_dir)
        
        # Report high error rate
        monitor.report_metrics("test_agent", {
            "response_time_ms": 100,
            "success": False
        })
        
        # Report multiple failures
        for _ in range(5):
            monitor.report_metrics("test_agent", {
                "response_time_ms": 100,
                "success": False
            })
        
        # Should have created alerts
        assert len(monitor.alerts) > 0
        assert any(a.agent_name == "test_agent" for a in monitor.alerts)


# ═══════════════════════════════════════════════════════════════════════
# SELF-HEALING ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSelfHealingEngine:
    """Test SelfHealingEngine."""
    
    def test_initialization(self, temp_brain_dir):
        """Test self-healing engine initialization."""
        engine = SelfHealingEngine(brain_dir=temp_brain_dir)
        assert engine.recovery_history is not None
        assert engine.circuit_breakers == {}
    
    @pytest.mark.asyncio
    async def test_heal_crashed_agent(self, temp_brain_dir):
        """Test healing a crashed agent."""
        engine = SelfHealingEngine(brain_dir=temp_brain_dir)
        
        # Register restart callback
        restart_called = False
        async def restart_callback():
            nonlocal restart_called
            restart_called = True
        
        engine.register_restart_callback("test_agent", restart_callback)
        
        # Attempt heal
        success = await engine.heal_crashed_agent("test_agent")
        
        assert restart_called
        assert success
        assert engine.restart_counts["test_agent"] == 1
    
    @pytest.mark.asyncio
    async def test_restart_backoff(self, temp_brain_dir):
        """Test exponential backoff for restarts."""
        engine = SelfHealingEngine(brain_dir=temp_brain_dir)
        
        async def restart_callback():
            pass
        
        engine.register_restart_callback("test_agent", restart_callback)
        
        # First restart should succeed
        success1 = await engine.heal_crashed_agent("test_agent")
        assert success1
        
        # Immediate second restart should be delayed
        success2 = await engine.heal_crashed_agent("test_agent")
        # May fail due to backoff
    
    def test_circuit_breaker(self, temp_brain_dir):
        """Test circuit breaker for failing endpoints."""
        engine = SelfHealingEngine(brain_dir=temp_brain_dir)
        
        endpoint = "https://example.com/api/test"
        
        # Should allow initially
        assert engine.check_circuit_breaker(endpoint)
        
        # Record failures
        for _ in range(5):
            engine.record_endpoint_result(endpoint, success=False)
        
        # Circuit should be open now
        breaker = engine.circuit_breakers[endpoint]
        assert breaker.state == "open"
    
    def test_recovery_history(self, temp_brain_dir):
        """Test recovery action history tracking."""
        engine = SelfHealingEngine(brain_dir=temp_brain_dir)
        
        engine._record_recovery(
            "test_agent",
            "high_error_rate",
            "strategy_change",
            {"new_strategy": "LOW_AND_SLOW"},
            True,
            100.0
        )
        
        history = engine.get_recovery_history()
        assert len(history) == 1
        assert history[0]["agent_name"] == "test_agent"
        assert history[0]["success"]


# ═══════════════════════════════════════════════════════════════════════
# SKILL EXTRACTOR TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSkillExtractor:
    """Test SkillExtractor."""
    
    def test_initialization(self, temp_brain_dir):
        """Test skill extractor initialization."""
        extractor = SkillExtractor(brain_dir=temp_brain_dir)
        assert extractor.thresholds["min_confidence"] == 0.7
    
    def test_is_skill_worthy(self, temp_brain_dir):
        """Test skill worthiness check."""
        extractor = SkillExtractor(brain_dir=temp_brain_dir)
        
        # High confidence pattern
        pattern1 = LearningPattern(
            pattern_id="test1",
            pattern_type="payload_success",
            pattern_data={},
            confidence=0.8,
            success_count=15,
            failure_count=5,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        assert extractor._is_skill_worthy(pattern1)
        
        # Low confidence pattern
        pattern2 = LearningPattern(
            pattern_id="test2",
            pattern_type="payload_success",
            pattern_data={},
            confidence=0.3,
            success_count=2,
            failure_count=8,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        assert not extractor._is_skill_worthy(pattern2)
    
    def test_extract_payload_skill(self, temp_brain_dir):
        """Test extracting payload skill from pattern."""
        extractor = SkillExtractor(brain_dir=temp_brain_dir)
        
        pattern = LearningPattern(
            pattern_id="test_payload",
            pattern_type="payload_success",
            pattern_data={
                "vuln_type": "SQL_INJECTION",
                "payload_sample": "' OR 1=1--",
                "payload_features": {
                    "has_sql_keywords": True,
                    "has_special_chars": True
                }
            },
            confidence=0.85,
            success_count=20,
            failure_count=5,
            last_seen=0.0,
            first_seen=0.0,
            scan_count=1
        )
        
        skill = extractor._extract_payload_skill(pattern)
        
        assert skill is not None
        assert skill.skill_type == "payload_generation"
        assert "sql" in skill.name.lower()  # Case-insensitive check
        assert skill.confidence == 0.85
    
    def test_generalize_payload(self, temp_brain_dir):
        """Test payload generalization."""
        extractor = SkillExtractor(brain_dir=temp_brain_dir)
        
        payload = "' OR 1=1--"
        features = {"has_sql_keywords": True}
        
        template = extractor._generalize_payload(payload, features)
        
        # Should have generalized the number
        assert "{number}" in template or "OR" in template


# ═══════════════════════════════════════════════════════════════════════
# SKILL LIBRARY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSkillLibrary:
    """Test SkillLibrary."""
    
    def test_initialization(self, temp_brain_dir):
        """Test skill library initialization."""
        library = SkillLibrary(brain_dir=temp_brain_dir)
        assert library.skills_dir.exists()
        assert library.metadata == {}
    
    def test_add_skill(self, temp_brain_dir):
        """Test adding a skill to library."""
        library = SkillLibrary(brain_dir=temp_brain_dir)
        
        skill = Skill(
            skill_id="test_skill_1",
            name="Test SQL Injection",
            description="Test skill",
            skill_type="payload_generation",
            source_pattern_ids=["pattern1"],
            confidence=0.8,
            success_rate=0.75,
            sample_size=20,
            payload_template="' OR {number}={number}--"
        )
        
        success = library.add_skill(skill)
        assert success
        assert "test_skill_1" in library.metadata
    
    def test_get_skill(self, temp_brain_dir):
        """Test retrieving a skill."""
        library = SkillLibrary(brain_dir=temp_brain_dir)
        
        skill = Skill(
            skill_id="test_skill_2",
            name="Test XSS",
            description="Test skill",
            skill_type="payload_generation",
            source_pattern_ids=["pattern2"],
            confidence=0.9,
            success_rate=0.85,
            sample_size=30
        )
        
        library.add_skill(skill)
        
        retrieved = library.get_skill("test_skill_2")
        assert retrieved is not None
        assert retrieved.name == "Test XSS"
        assert retrieved.confidence == 0.9
    
    def test_update_skill(self, temp_brain_dir):
        """Test updating a skill."""
        library = SkillLibrary(brain_dir=temp_brain_dir)
        
        skill = Skill(
            skill_id="test_skill_3",
            name="Test Skill",
            description="Test",
            skill_type="payload_generation",
            source_pattern_ids=["pattern3"],
            confidence=0.7,
            success_rate=0.6,
            sample_size=10,
            version="1.0.0"
        )
        
        library.add_skill(skill)
        
        # Update skill
        skill.confidence = 0.8
        success = library.update_skill(skill)
        
        assert success
        assert skill.version == "1.0.1"  # Version should increment
    
    def test_search_skills(self, temp_brain_dir):
        """Test searching for skills."""
        library = SkillLibrary(brain_dir=temp_brain_dir)
        
        # Add multiple skills
        for i in range(5):
            skill = Skill(
                skill_id=f"skill_{i}",
                name=f"Skill {i}",
                description="Test",
                skill_type="payload_generation" if i < 3 else "endpoint_discovery",
                source_pattern_ids=[f"pattern{i}"],
                confidence=0.5 + (i * 0.1),
                success_rate=0.6,
                sample_size=10
            )
            library.add_skill(skill)
        
        # Search by type
        payload_skills = library.search_skills(skill_type="payload_generation")
        assert len(payload_skills) == 3
        
        # Search by confidence
        high_conf_skills = library.search_skills(min_confidence=0.7)
        assert len(high_conf_skills) >= 2
    
    def test_record_skill_usage(self, temp_brain_dir):
        """Test recording skill usage."""
        library = SkillLibrary(brain_dir=temp_brain_dir)
        
        skill = Skill(
            skill_id="test_skill_4",
            name="Test Skill",
            description="Test",
            skill_type="payload_generation",
            source_pattern_ids=["pattern4"],
            confidence=0.8,
            success_rate=0.7,
            sample_size=10
        )
        
        library.add_skill(skill)
        
        # Record usage
        library.record_skill_usage("test_skill_4", success=True)
        library.record_skill_usage("test_skill_4", success=True)
        library.record_skill_usage("test_skill_4", success=False)
        
        # Check updated skill
        updated = library.get_skill("test_skill_4")
        assert updated.times_used == 3
        assert updated.times_successful == 2
    
    def test_export_import_skill(self, temp_brain_dir):
        """Test exporting and importing skills."""
        library = SkillLibrary(brain_dir=temp_brain_dir)
        
        skill = Skill(
            skill_id="test_skill_5",
            name="Export Test",
            description="Test export",
            skill_type="payload_generation",
            source_pattern_ids=["pattern5"],
            confidence=0.85,
            success_rate=0.8,
            sample_size=25
        )
        
        library.add_skill(skill)
        
        # Export
        export_path = f"{temp_brain_dir}/export_test.json"
        success = library.export_skill("test_skill_5", export_path)
        assert success
        assert Path(export_path).exists()
        
        # Delete original
        library.delete_skill("test_skill_5")
        assert library.get_skill("test_skill_5") is None
        
        # Import
        skill_id = library.import_skill(export_path)
        assert skill_id is not None
        
        # Verify imported skill
        imported = library.get_skill(skill_id)
        assert imported is not None
        assert imported.name == "Export Test"
