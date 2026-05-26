"""
Pytest fixtures for integration testing.

This module provides test fixtures for integration tests including:
- Test containers (Redis, Postgres)
- Mock components
- Integration environment setup
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Try to import testcontainers, but make it optional
try:
    from testcontainers.redis import RedisContainer
    from testcontainers.postgres import PostgresContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for integration tests"""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")
    
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def postgres_container():
    """Start Postgres container for integration tests"""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")
    
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture
async def redis_client(redis_container):
    """Create Redis client for testing"""
    try:
        import redis.asyncio as aioredis
    except ImportError:
        pytest.skip("redis not available")
    
    client = aioredis.from_url(
        redis_container.get_connection_url(),
        decode_responses=True
    )
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
def mock_event_bus():
    """Create mock EventBus for testing"""
    bus = Mock()
    bus.publish = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    return bus


@pytest.fixture
def mock_learning_engine():
    """Create mock LearningEngine for testing"""
    engine = Mock()
    engine.learn_from_browser_vulnerability = AsyncMock()
    engine.learn_browser_workflow = AsyncMock()
    engine.get_browser_recommendations = AsyncMock(return_value={
        "workflows": [],
        "payloads": [],
        "framework_specific": []
    })
    engine.learn_framework_pattern = AsyncMock()
    return engine


@pytest.fixture
def mock_skill_library():
    """Create mock SkillLibrary for testing"""
    library = Mock()
    library.add_browser_skill = AsyncMock(return_value=True)
    library.search_browser_skills = Mock(return_value=[])
    library.get_workflow_skills = Mock(return_value=[])
    library.compose_workflows = Mock()
    return library


@pytest.fixture
def mock_health_monitor():
    """Create mock HealthMonitor for testing"""
    monitor = Mock()
    monitor.report_browser_metrics = Mock()
    monitor.get_browser_health = Mock(return_value={
        "active_contexts": 0,
        "context_memory_mb": 0.0,
        "health_score": 1.0
    })
    monitor.calculate_browser_health_score = Mock(return_value=1.0)
    return monitor


@pytest.fixture
def mock_healing_engine():
    """Create mock SelfHealingEngine for testing"""
    engine = Mock()
    engine.heal_browser_crash = AsyncMock(return_value=True)
    engine.heal_browser_memory = AsyncMock(return_value=True)
    engine.adapt_browser_strategy = AsyncMock()
    return engine


@pytest.fixture
def mock_browser_orchestrator():
    """Create mock BrowserOrchestrator for testing"""
    orchestrator = Mock()
    orchestrator.create_context = AsyncMock()
    orchestrator.close_context = AsyncMock()
    orchestrator.get_active_contexts = Mock(return_value=[])
    return orchestrator


@pytest.fixture
async def integration_environment(
    mock_event_bus,
    mock_learning_engine,
    mock_skill_library,
    mock_health_monitor,
    mock_healing_engine,
    mock_browser_orchestrator
):
    """
    Set up complete integration environment with all components.
    
    This fixture provides a fully configured integration environment
    with mock components for testing.
    """
    from backend.core.integration_config import IntegrationConfig
    
    config = IntegrationConfig(
        enable_browser_learning=True,
        enable_cross_system_healing=True,
        enable_forensic_learning=True,
        event_batch_size=5,
        event_batch_timeout_ms=100
    )
    
    env = {
        "config": config,
        "bus": mock_event_bus,
        "learning_engine": mock_learning_engine,
        "skill_library": mock_skill_library,
        "health_monitor": mock_health_monitor,
        "healing_engine": mock_healing_engine,
        "browser_orchestrator": mock_browser_orchestrator
    }
    
    yield env


@pytest.fixture
def sample_vulnerability():
    """Sample vulnerability data for testing"""
    return {
        "url": "https://example.com/api/users",
        "vuln_type": "XSS",
        "payload": "<script>alert(1)</script>",
        "method": "POST",
        "framework": "React",
        "stealth_required": False,
        "session_required": False,
        "confidence": 0.95
    }


@pytest.fixture
def sample_browser_skill():
    """Sample browser skill for testing"""
    from backend.core.skill_library import BrowserSkill
    
    return BrowserSkill(
        id="test-skill-001",
        name="XSS via POST parameter",
        execution_context="browser_required",
        browser_requirements={
            "stealth": False,
            "session": False,
            "framework": "React"
        },
        workflow_steps=None,
        session_requirements=None,
        evidence_requirements=["screenshot", "dom_snapshot"],
        version="1.0.0",
        deprecated=False,
        required_capabilities=frozenset(["browser", "http"]),
        success_rate=0.85,
        usage_count=10
    )


@pytest.fixture
def sample_workflow():
    """Sample browser workflow for testing"""
    return {
        "id": "workflow-001",
        "name": "Multi-step XSS exploitation",
        "steps": [
            {"action": "navigate", "url": "https://example.com/login"},
            {"action": "fill", "selector": "#username", "value": "admin"},
            {"action": "fill", "selector": "#password", "value": "password"},
            {"action": "click", "selector": "#submit"},
            {"action": "inject_payload", "selector": "#comment", "payload": "<script>alert(1)</script>"}
        ],
        "success_conditions": [
            {"type": "alert_present"},
            {"type": "dom_modified"}
        ]
    }
