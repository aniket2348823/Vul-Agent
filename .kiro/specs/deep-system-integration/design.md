# Design Document: Deep System Integration

## Overview

This design implements the deep integration of three major Antigravity V5 systems:
1. **Agent Evolution System** - Self-improving agents with learning, self-healing, and skill management
2. **OpenClaw Integration** - Browser-based autonomous reconnaissance and exploitation
3. **File Consolidation** - Repository organization (maintenance task, minimal integration)

The goal is to create emergent capabilities where these systems work together seamlessly, producing results greater than the sum of their parts. The integration maintains loose coupling through the EventBus, unified resource management through NeuroNegotiator, and consistent patterns across all components.

## Architecture

### System Integration Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  DEEP SYSTEM INTEGRATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              UNIFIED EVENTBUS LAYER                       │  │
│  │  (All components communicate via events)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────┬─────────────────┬─────────────────────┐  │
│  │  EVOLUTION      │  BROWSER        │  KNOWLEDGE          │  │
│  │  SYSTEM         │  AUTOMATION     │  MANAGEMENT         │  │
│  ├─────────────────┼─────────────────┼─────────────────────┤  │
│  │ Learning Engine │ BrowserOrch     │ Knowledge Graph     │  │
│  │ Skill Library   │ OpenClaw        │ Memory Store        │  │
│  │ Health Monitor  │ PinchTab        │ Pattern Store       │  │
│  │ Self-Healing    │ Forensics       │ Session Manager     │  │
│  └─────────────────┴─────────────────┴─────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         UNIFIED RESOURCE MANAGEMENT                       │  │
│  │         (NeuroNegotiator)                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              HYBRID AGENT LAYER                           │  │
│  │  (All agents have HTTP + Browser capabilities)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Layers


#### Layer 1: EventBus Communication
- All components publish and subscribe to events
- Loose coupling - no direct dependencies
- Event types: SKILL_EXTRACTED, AGENT_HEALED, BROWSER_DISCOVERY, EVIDENCE_COLLECTED, HEALTH_ALERT
- Event routing handled by existing EventBus infrastructure

#### Layer 2: Unified Resource Management
- NeuroNegotiator handles all resource allocation
- Browser contexts bid for resources like HTTP operations
- Memory-aware allocation for browser operations
- Load balancing between HTTP and browser agents

#### Layer 3: Shared Knowledge Stores
- Unified Skill Library (HTTP + browser skills)
- Unified Learning Engine (HTTP + browser patterns)
- Unified Knowledge Graph (HTTP + browser discoveries)
- Unified Health Monitoring (all agent types)

#### Layer 4: Cross-System Intelligence
- Learning from browser discoveries
- Self-healing for browser failures
- Forensic evidence in learning loop
- Performance optimization across systems

## Testing Strategy (PRODUCTION-GRADE)

### Test Infrastructure

#### 1. Property-Based Test Framework
```python
from hypothesis import given, strategies as st, settings, Phase
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import pytest

# Custom strategies for domain objects
@st.composite
def browser_vulnerability_strategy(draw):
    """Generate realistic browser vulnerabilities for property testing"""
    return {
        "url": draw(st.from_regex(r"https?://[a-z]+\.[a-z]{2,3}/[a-z/]*", fullmatch=True)),
        "vuln_type": draw(st.sampled_from(["XSS", "CSRF", "SQLi", "SSRF"])),
        "payload": draw(st.text(min_size=1, max_size=1000)),
        "method": draw(st.sampled_from(["GET", "POST", "PUT", "DELETE"])),
        "framework": draw(st.sampled_from(["React", "Vue", "Angular", None])),
        "stealth_required": draw(st.booleans()),
        "session_required": draw(st.booleans())
    }

@st.composite
def browser_skill_strategy(draw):
    """Generate browser skills for property testing"""
    capabilities = draw(st.sets(
        st.sampled_from(["http", "browser", "stealth", "session"]),
        min_size=1,
        max_size=4
    ))
    
    return BrowserSkill(
        id=draw(st.uuids()).hex,
        name=draw(st.text(min_size=5, max_size=50)),
        execution_context=draw(st.sampled_from(["browser_required", "http_only", "hybrid"])),
        browser_requirements={
            "stealth": draw(st.booleans()),
            "session": draw(st.booleans()),
            "framework": draw(st.sampled_from(["React", "Vue", "Angular", None]))
        },
        version=f"{draw(st.integers(1, 10))}.{draw(st.integers(0, 20))}.{draw(st.integers(0, 50))}",
        required_capabilities=frozenset(capabilities),
        success_rate=draw(st.floats(0.0, 1.0)),
        usage_count=draw(st.integers(0, 10000))
    )

# Stateful testing for integration coordinator
class IntegrationCoordinatorStateMachine(RuleBasedStateMachine):
    """Stateful property testing for integration coordinator"""
    
    def __init__(self):
        super().__init__()
        self.coordinator = None
        self.events_sent = []
        self.skills_created = []
    
    @rule()
    def initialize_coordinator(self):
        """Initialize coordinator"""
        if not self.coordinator:
            self.coordinator = IntegrationCoordinator(
                bus=MockEventBus(),
                learning_engine=MockLearningEngine(),
                skill_library=MockSkillLibrary(),
                health_monitor=MockHealthMonitor(),
                healing_engine=MockHealingEngine(),
                browser_orchestrator=MockBrowserOrchestrator()
            )
    
    @rule(vuln=browser_vulnerability_strategy())
    def send_vulnerability_event(self, vuln):
        """Send vulnerability event"""
        assume(self.coordinator is not None)
        event = Event(type="VULN_CONFIRMED", data=vuln, scan_id="test")
        self.events_sent.append(event)
        asyncio.run(self.coordinator._on_vulnerability(event))
    
    @invariant()
    def events_processed_correctly(self):
        """Invariant: All events should be processed without data loss"""
        if self.coordinator:
            metrics = self.coordinator.get_integration_metrics()
            # No events should be lost
            assert metrics["events_processed"] + metrics["events_failed"] == len(self.events_sent)
    
    @invariant()
    def no_duplicate_skills(self):
        """Invariant: No duplicate skills should be created"""
        skill_ids = [s.id for s in self.skills_created]
        assert len(skill_ids) == len(set(skill_ids))

# Property tests
class TestIntegrationProperties:
    """Property-based tests for integration"""
    
    @given(vuln=browser_vulnerability_strategy())
    @settings(max_examples=100, phases=[Phase.generate, Phase.target])
    def test_idempotency_of_vulnerability_learning(self, vuln):
        """Property: Learning same vulnerability twice should be idempotent"""
        engine = BrowserLearningExtension(redis_client=MockRedis())
        
        # Learn once
        result1 = asyncio.run(engine.learn_from_browser_vulnerability(vuln, "scan1"))
        
        # Learn again with same data
        result2 = asyncio.run(engine.learn_from_browser_vulnerability(vuln, "scan1"))
        
        # Second call should return False (duplicate)
        assert result1 == True
        assert result2 == False
    
    @given(skills=st.lists(browser_skill_strategy(), min_size=1, max_size=100))
    def test_skill_search_returns_subset(self, skills):
        """Property: Skill search should always return subset of stored skills"""
        library = BrowserSkillLibraryExtension()
        
        # Add all skills
        for skill in skills:
            library.add_browser_skill(skill, {})
        
        # Search with random capabilities
        caps = ["http", "browser"]
        results = library.search_browser_skills(caps)
        
        # Results should be subset
        result_ids = {s.id for s in results}
        all_ids = {s.id for s in skills}
        assert result_ids.issubset(all_ids)
    
    @given(
        skills=st.lists(browser_skill_strategy(), min_size=2, max_size=5),
        agent_caps=st.sets(st.sampled_from(["http", "browser", "stealth", "session"]), min_size=1)
    )
    def test_capability_filtering_correctness(self, skills, agent_caps):
        """Property: Filtered skills should match agent capabilities"""
        library = BrowserSkillLibraryExtension()
        
        for skill in skills:
            library.add_browser_skill(skill, {})
        
        results = library.search_browser_skills(list(agent_caps))
        
        # All results should have capabilities subset of agent caps
        for skill in results:
            assert skill.required_capabilities.issubset(agent_caps)
```

#### 2. Integration Test Harness
```python
import pytest
import asyncio
from testcontainers.redis import RedisContainer
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for integration tests"""
    with RedisContainer() as redis:
        yield redis

@pytest.fixture(scope="session")
def postgres_container():
    """Start Postgres container for integration tests"""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture
async def integration_environment(redis_container, postgres_container):
    """Set up complete integration environment"""
    # Initialize all components
    bus = EventBus()
    redis_client = redis.Redis.from_url(redis_container.get_connection_url())
    
    learning_engine = LearningEngine(redis_client=redis_client)
    skill_library = SkillLibrary(db_url=postgres_container.get_connection_url())
    health_monitor = HealthMonitor()
    healing_engine = SelfHealingEngine()
    browser_orchestrator = BrowserOrchestrator()
    
    coordinator = IntegrationCoordinator(
        bus=bus,
        learning_engine=learning_engine,
        skill_library=skill_library,
        health_monitor=health_monitor,
        healing_engine=healing_engine,
        browser_orchestrator=browser_orchestrator
    )
    
    await coordinator.initialize()
    
    yield {
        "coordinator": coordinator,
        "bus": bus,
        "learning_engine": learning_engine,
        "skill_library": skill_library
    }
    
    await coordinator.shutdown()

@pytest.mark.integration
class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    async def test_browser_vulnerability_to_skill_flow(self, integration_environment):
        """Test complete flow: vulnerability → pattern → skill → distribution"""
        env = integration_environment
        
        # 1. Publish vulnerability event
        vuln_data = {
            "url": "https://example.com/api/users",
            "vuln_type": "XSS",
            "payload": "<script>alert(1)</script>",
            "method": "POST",
            "framework": "React"
        }
        
        await env["bus"].publish("VULN_CONFIRMED", vuln_data)
        
        # 2. Wait for processing
        await asyncio.sleep(0.5)
        
        # 3. Verify pattern was learned
        patterns = await env["learning_engine"].get_patterns(vuln_type="XSS")
        assert len(patterns) > 0
        
        # 4. Verify skill was created
        skills = env["skill_library"].search_browser_skills(["browser"])
        assert len(skills) > 0
        assert any(s.browser_requirements.get("framework") == "React" for s in skills)
        
        # 5. Verify skill is queryable by other agents
        recommendations = await env["learning_engine"].get_browser_recommendations(
            "https://example.com/api/users"
        )
        assert len(recommendations["payloads"]) > 0
```

#### 3. Chaos Engineering Tests
```python
import random
from chaos_engineering import inject_failure, inject_latency

@pytest.mark.chaos
class TestChaosEngineering:
    """Chaos engineering tests for resilience"""
    
    async def test_coordinator_survives_learning_engine_crash(self, integration_environment):
        """Test coordinator resilience when learning engine crashes"""
        env = integration_environment
        
        # Inject failure into learning engine
        with inject_failure(env["learning_engine"], failure_rate=0.5):
            # Send 100 events
            for i in range(100):
                await env["bus"].publish("VULN_CONFIRMED", {
                    "url": f"https://example.com/api/{i}",
                    "vuln_type": "XSS",
                    "payload": f"<script>alert({i})</script>",
                    "method": "POST"
                })
            
            await asyncio.sleep(2)
        
        # Verify coordinator is still healthy
        metrics = env["coordinator"].get_integration_metrics()
        assert metrics["events_processed"] > 0
        assert metrics["failure_rate"] < 0.6  # Some failures expected
    
    async def test_event_storm_handling(self, integration_environment):
        """Test system handles event storms gracefully"""
        env = integration_environment
        
        # Send 1000 events rapidly
        tasks = []
        for i in range(1000):
            task = env["bus"].publish("BROWSER_DISCOVERY", {
                "framework": "React",
                "routes": [f"/route/{i}"]
            })
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(5)
        
        # Verify system didn't crash
        metrics = env["coordinator"].get_integration_metrics()
        assert metrics["events_processed"] > 0
        
        # Verify batching worked
        assert metrics["pending_discoveries"] < 100  # Should have been batched
```

### Rollback Strategy

#### Feature Flags Configuration
```python
# config/feature_flags.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout"""
    
    # Integration features
    enable_browser_learning: bool = False  # Start disabled
    enable_cross_system_healing: bool = False
    enable_forensic_learning: bool = False
    enable_intelligent_routing: bool = False
    
    # Rollout percentages (0-100)
    browser_learning_rollout_pct: int = 0
    cross_healing_rollout_pct: int = 0
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_s: int = 60
    
    # Performance limits
    max_concurrent_learning: int = 5
    event_batch_size: int = 10
    event_batch_timeout_ms: int = 1000
    
    @classmethod
    def from_env(cls) -> "FeatureFlags":
        """Load from environment variables"""
        import os
        return cls(
            enable_browser_learning=os.getenv("ENABLE_BROWSER_LEARNING", "false").lower() == "true",
            enable_cross_system_healing=os.getenv("ENABLE_CROSS_HEALING", "false").lower() == "true",
            enable_forensic_learning=os.getenv("ENABLE_FORENSIC_LEARNING", "false").lower() == "true",
            browser_learning_rollout_pct=int(os.getenv("BROWSER_LEARNING_ROLLOUT_PCT", "0")),
            cross_healing_rollout_pct=int(os.getenv("CROSS_HEALING_ROLLOUT_PCT", "0"))
        )
    
    def should_enable_for_scan(self, scan_id: str, feature: str) -> bool:
        """Determine if feature should be enabled for this scan (gradual rollout)"""
        if feature == "browser_learning":
            if not self.enable_browser_learning:
                return False
            # Use scan_id hash for consistent rollout
            return hash(scan_id) % 100 < self.browser_learning_rollout_pct
        
        return False
```

#### Rollback Procedure
```markdown
# Rollback Procedure

## Immediate Rollback (< 5 minutes)

1. **Disable all integration features**:
   ```bash
   export ENABLE_BROWSER_LEARNING=false
   export ENABLE_CROSS_HEALING=false
   export ENABLE_FORENSIC_LEARNING=false
   ```

2. **Restart services**:
   ```bash
   systemctl restart antigravity-backend
   ```

3. **Verify rollback**:
   ```bash
   curl http://localhost:8000/api/integration/metrics
   # Should show all features disabled
   ```

## Gradual Rollback (reduce traffic)

1. **Reduce rollout percentage**:
   ```bash
   export BROWSER_LEARNING_ROLLOUT_PCT=10  # Reduce from 50% to 10%
   ```

2. **Monitor metrics**:
   ```bash
   watch -n 5 'curl -s http://localhost:8000/api/integration/metrics | jq'
   ```

3. **If issues persist, disable completely**

## Data Rollback (if skills corrupted)

1. **Export current skills**:
   ```bash
   python scripts/export_skills.py --output /backup/skills_$(date +%s).json
   ```

2. **Restore from backup**:
   ```bash
   python scripts/restore_skills.py --input /backup/skills_<timestamp>.json
   ```

3. **Verify restoration**:
   ```bash
   python scripts/verify_skills.py
   ```
```

### 1. Integration Coordinator (REDESIGNED)

**Purpose**: Lightweight event router with failure isolation and observability

**Location**: `backend/core/integration_coordinator.py`

**Design Principles**:
- Dependency injection (no magic globals)
- Circuit breakers for failure isolation
- Event batching to prevent storms
- Feature flags for gradual rollout
- Distributed tracing for observability

**Interface**:
```python
from typing import Protocol
from dataclasses import dataclass
import asyncio
from circuitbreaker import circuit
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@dataclass
class IntegrationConfig:
    """Configuration for integration features"""
    enable_browser_learning: bool = True
    enable_cross_system_healing: bool = True
    enable_forensic_learning: bool = True
    event_batch_size: int = 10
    event_batch_timeout_ms: int = 1000
    max_concurrent_learning: int = 5
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_s: int = 60

class LearningEngineProtocol(Protocol):
    """Protocol for learning engine dependency"""
    async def learn_from_browser_vulnerability(self, vuln_data: Dict, scan_id: str) -> None: ...
    async def learn_browser_workflow(self, workflow: Dict, success: bool) -> None: ...

class SkillLibraryProtocol(Protocol):
    """Protocol for skill library dependency"""
    async def add_browser_skill(self, skill: Skill, context_requirements: Dict) -> bool: ...
    async def search_browser_skills(self, agent_capabilities: List[str]) -> List[Skill]: ...

class IntegrationCoordinator:
    """
    Lightweight coordinator that routes events between systems with:
    - Failure isolation via circuit breakers
    - Event batching to prevent storms
    - Distributed tracing for observability
    - Feature flags for gradual rollout
    """
    
    def __init__(
        self,
        bus: EventBus,
        learning_engine: LearningEngineProtocol,
        skill_library: SkillLibraryProtocol,
        health_monitor: HealthMonitor,
        healing_engine: SelfHealingEngine,
        browser_orchestrator: BrowserOrchestrator,
        config: IntegrationConfig = IntegrationConfig()
    ):
        self.bus = bus
        self.learning_engine = learning_engine
        self.skill_library = skill_library
        self.health_monitor = health_monitor
        self.healing_engine = healing_engine
        self.browser_orchestrator = browser_orchestrator
        self.config = config
        
        # Event batching
        self._discovery_batch: List[Dict] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        
        # Concurrency control
        self._learning_semaphore = asyncio.Semaphore(config.max_concurrent_learning)
        
        # Metrics
        self._events_processed = 0
        self._events_failed = 0
        self._circuit_breaker_trips = 0
        
    async def initialize(self) -> None:
        """Initialize integration with health checks"""
        with tracer.start_as_current_span("integration_init"):
            # Subscribe to events
            await self.bus.subscribe("VULN_CONFIRMED", self._on_vulnerability)
            await self.bus.subscribe("BROWSER_DISCOVERY", self._on_discovery)
            await self.bus.subscribe("AGENT_FAILURE", self._on_failure)
            
            # Start batch processor
            self._batch_task = asyncio.create_task(self._process_discovery_batches())
            
            logger.info("Integration coordinator initialized", extra={
                "config": self.config,
                "features_enabled": {
                    "browser_learning": self.config.enable_browser_learning,
                    "cross_healing": self.config.enable_cross_system_healing,
                    "forensic_learning": self.config.enable_forensic_learning
                }
            })
    
    @circuit(failure_threshold=5, recovery_timeout=60, name="browser_vulnerability_learning")
    async def _on_vulnerability(self, event: Event) -> None:
        """Handle vulnerability with circuit breaker and tracing"""
        if not self.config.enable_browser_learning:
            return
            
        with tracer.start_as_current_span("handle_vulnerability") as span:
            span.set_attribute("vuln.type", event.data.get("vuln_type"))
            span.set_attribute("vuln.source", event.data.get("source"))
            
            try:
                async with self._learning_semaphore:  # Limit concurrency
                    await self.learning_engine.learn_from_browser_vulnerability(
                        event.data, 
                        event.scan_id
                    )
                self._events_processed += 1
                span.set_status(trace.Status(trace.StatusCode.OK))
            except Exception as e:
                self._events_failed += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error("Failed to learn from vulnerability", exc_info=e, extra={
                    "event_id": event.id,
                    "scan_id": event.scan_id
                })
                raise  # Let circuit breaker handle it
    
    async def _on_discovery(self, event: Event) -> None:
        """Batch discoveries to prevent event storms"""
        async with self._batch_lock:
            self._discovery_batch.append(event.data)
            
            # Flush if batch is full
            if len(self._discovery_batch) >= self.config.event_batch_size:
                await self._flush_discovery_batch()
    
    async def _process_discovery_batches(self) -> None:
        """Background task to flush batches periodically"""
        while True:
            await asyncio.sleep(self.config.event_batch_timeout_ms / 1000)
            async with self._batch_lock:
                if self._discovery_batch:
                    await self._flush_discovery_batch()
    
    @circuit(failure_threshold=5, recovery_timeout=60, name="discovery_learning")
    async def _flush_discovery_batch(self) -> None:
        """Process batched discoveries"""
        if not self.config.enable_browser_learning or not self._discovery_batch:
            return
            
        batch = self._discovery_batch[:]
        self._discovery_batch.clear()
        
        with tracer.start_as_current_span("flush_discovery_batch") as span:
            span.set_attribute("batch.size", len(batch))
            
            try:
                # Process batch in parallel with concurrency limit
                tasks = [
                    self.learning_engine.learn_framework_pattern(
                        d.get("framework"), 
                        d.get("routes", [])
                    )
                    for d in batch
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                span.set_status(trace.Status(trace.StatusCode.OK))
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                logger.error("Failed to process discovery batch", exc_info=e)
    
    async def shutdown(self) -> None:
        """Graceful shutdown with batch flush"""
        if self._batch_task:
            self._batch_task.cancel()
        
        # Flush remaining batches
        async with self._batch_lock:
            if self._discovery_batch:
                await self._flush_discovery_batch()
        
        logger.info("Integration coordinator shutdown", extra={
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
            "circuit_breaker_trips": self._circuit_breaker_trips
        })
    
    def get_integration_metrics(self) -> Dict:
        """Get metrics with health indicators"""
        return {
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
            "failure_rate": self._events_failed / max(self._events_processed, 1),
            "circuit_breaker_trips": self._circuit_breaker_trips,
            "pending_discoveries": len(self._discovery_batch),
            "features_enabled": {
                "browser_learning": self.config.enable_browser_learning,
                "cross_healing": self.config.enable_cross_system_healing,
                "forensic_learning": self.config.enable_forensic_learning
            }
        }
```



### 2. Browser-Aware Learning Engine Extension (REDESIGNED)

**Purpose**: Extend Learning Engine with idempotency, caching, and conflict resolution

**Location**: `backend/core/learning_engine.py` (extend existing)

**Design Principles**:
- Idempotency keys to prevent duplicate learning
- Distributed locking for conflict resolution
- Caching for performance
- Incremental learning to avoid reprocessing

**New Methods**:
```python
from functools import lru_cache
from hashlib import sha256
import redis
from typing import Optional

class BrowserLearningExtension:
    """Extension for browser-specific learning with production-grade features"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._learning_cache = {}
        
    def _generate_idempotency_key(self, vuln_data: Dict) -> str:
        """Generate idempotency key from vulnerability data"""
        # Use stable fields to create unique key
        key_data = {
            "url": vuln_data.get("url"),
            "vuln_type": vuln_data.get("vuln_type"),
            "payload": vuln_data.get("payload"),
            "method": vuln_data.get("method")
        }
        return f"vuln:{sha256(str(sorted(key_data.items())).encode()).hexdigest()}"
    
    async def learn_from_browser_vulnerability(
        self, 
        vuln_data: Dict, 
        scan_id: str,
        idempotency_key: Optional[str] = None
    ) -> bool:
        """
        Learn from browser-based vulnerability with idempotency
        
        Returns:
            True if learning occurred, False if duplicate
        """
        # Generate or use provided idempotency key
        idem_key = idempotency_key or self._generate_idempotency_key(vuln_data)
        
        # Check if already processed (distributed lock)
        lock_key = f"lock:{idem_key}"
        if not await self._acquire_lock(lock_key, ttl_seconds=300):
            logger.info("Duplicate vulnerability, skipping", extra={"key": idem_key})
            return False
        
        try:
            # Check cache first
            if idem_key in self._learning_cache:
                return False
            
            # Extract browser-specific pattern
            pattern = self._extract_browser_pattern(vuln_data)
            
            # Tag with browser context
            pattern["execution_context"] = "browser_required"
            pattern["browser_requirements"] = {
                "stealth": vuln_data.get("stealth_required", False),
                "session": vuln_data.get("session_required", False),
                "framework": vuln_data.get("framework")
            }
            
            # Store with execution requirements
            await self._store_pattern(pattern, scan_id)
            
            # Cache to prevent reprocessing
            self._learning_cache[idem_key] = True
            
            # Publish skill extracted event
            await self.bus.publish("SKILL_EXTRACTED", {
                "pattern_id": pattern["id"],
                "source": "browser_vulnerability",
                "scan_id": scan_id
            })
            
            return True
            
        finally:
            await self._release_lock(lock_key)
    
    async def _acquire_lock(self, key: str, ttl_seconds: int) -> bool:
        """Acquire distributed lock using Redis"""
        return bool(self.redis.set(key, "1", nx=True, ex=ttl_seconds))
    
    async def _release_lock(self, key: str) -> None:
        """Release distributed lock"""
        self.redis.delete(key)
    
    async def learn_browser_workflow(
        self, 
        workflow: Dict, 
        success: bool,
        workflow_id: Optional[str] = None
    ) -> None:
        """
        Learn from browser workflow execution with incremental updates
        
        Args:
            workflow: Workflow data including steps and conditions
            success: Whether workflow succeeded
            workflow_id: Optional ID for workflow tracking
        """
        wf_id = workflow_id or workflow.get("id")
        
        # Get existing workflow stats
        stats_key = f"workflow:{wf_id}:stats"
        stats = await self._get_workflow_stats(stats_key)
        
        # Update stats incrementally
        stats["total_executions"] += 1
        if success:
            stats["successful_executions"] += 1
        stats["success_rate"] = stats["successful_executions"] / stats["total_executions"]
        
        # Store updated stats
        await self._store_workflow_stats(stats_key, stats)
        
        # If success rate crosses threshold, promote to skill
        if stats["success_rate"] >= 0.7 and stats["total_executions"] >= 3:
            await self._promote_workflow_to_skill(workflow, stats)
    
    @lru_cache(maxsize=1000)
    async def get_browser_recommendations(self, target_url: str) -> Dict:
        """
        Get browser-specific attack recommendations with caching
        
        Cache is invalidated when new skills are learned
        """
        # Query browser patterns from database
        patterns = await self._query_patterns({
            "execution_context": "browser_required",
            "target_similarity": target_url
        })
        
        # Rank by confidence and success rate
        ranked = sorted(
            patterns, 
            key=lambda p: (p["confidence"], p["success_rate"]), 
            reverse=True
        )
        
        return {
            "workflows": [p for p in ranked if p["type"] == "workflow"],
            "payloads": [p for p in ranked if p["type"] == "payload"],
            "framework_specific": self._get_framework_recommendations(target_url)
        }
    
    async def learn_framework_pattern(
        self, 
        framework: str, 
        routes: List[str]
    ) -> None:
        """
        Learn JavaScript framework patterns with deduplication
        
        Args:
            framework: Framework name (React, Vue, Angular, etc.)
            routes: List of routes discovered
        """
        # Deduplicate routes
        unique_routes = set(routes)
        
        # Get existing framework patterns
        pattern_key = f"framework:{framework}:routes"
        existing = await self._get_framework_routes(pattern_key)
        
        # Add only new routes
        new_routes = unique_routes - existing
        if not new_routes:
            return
        
        # Store new routes
        await self._add_framework_routes(pattern_key, new_routes)
        
        # Extract route patterns (e.g., /api/:id/users)
        route_patterns = self._extract_route_patterns(new_routes)
        
        # Store patterns for future matching
        await self._store_route_patterns(framework, route_patterns)
```

### 3. Browser-Aware Skill Library Extension (REDESIGNED)

**Purpose**: Extend Skill Library with indexing, versioning, and capability filtering

**Location**: `backend/core/skill_library.py` (extend existing)

**Design Principles**:
- Indexed queries for O(1) lookups
- Semantic versioning for skills
- Capability-based access control
- Skill deprecation and migration

**New Skill Types**:
- `browser_workflow`: Multi-step browser automation
- `hybrid_attack`: Combined HTTP + browser attack
- `browser_payload`: Browser-specific payload

**New Methods**:
```python
from dataclasses import dataclass, field
from typing import Set, FrozenSet
from datetime import datetime
import semver

@dataclass
class BrowserSkill(Skill):
    """Extended skill for browser operations with versioning"""
    execution_context: str  # "browser_required", "http_only", "hybrid"
    browser_requirements: Dict[str, Any]
    workflow_steps: Optional[List[WorkflowStep]] = None
    session_requirements: Optional[Dict] = None
    evidence_requirements: List[str] = field(default_factory=list)
    
    # Versioning
    version: str = "1.0.0"  # Semantic versioning
    deprecated: bool = False
    deprecation_reason: Optional[str] = None
    migration_path: Optional[str] = None  # ID of replacement skill
    
    # Capability requirements
    required_capabilities: FrozenSet[str] = field(default_factory=frozenset)
    
    # Performance tracking
    avg_execution_time_ms: float = 0.0
    success_rate: float = 0.0
    usage_count: int = 0

class BrowserSkillLibraryExtension:
    """Extension with indexing and capability filtering"""
    
    def __init__(self):
        # Indexes for O(1) lookups
        self._capability_index: Dict[str, Set[str]] = {}  # capability -> skill_ids
        self._context_index: Dict[str, Set[str]] = {}     # context -> skill_ids
        self._framework_index: Dict[str, Set[str]] = {}   # framework -> skill_ids
        
        # Version tracking
        self._skill_versions: Dict[str, List[str]] = {}   # skill_name -> [versions]
        
    def add_browser_skill(
        self, 
        skill: BrowserSkill, 
        context_requirements: Dict
    ) -> bool:
        """
        Add browser skill with indexing and validation
        
        Returns:
            True if added, False if duplicate or invalid
        """
        # Validate version format
        try:
            semver.VersionInfo.parse(skill.version)
        except ValueError:
            raise ValueError(f"Invalid version format: {skill.version}")
        
        # Check for duplicate
        if self._is_duplicate_skill(skill):
            logger.warning("Duplicate skill detected", extra={"skill_id": skill.id})
            return False
        
        # Store skill
        self._skills[skill.id] = skill
        
        # Update indexes
        self._update_capability_index(skill)
        self._update_context_index(skill)
        self._update_framework_index(skill)
        
        # Track version
        skill_name = skill.name
        if skill_name not in self._skill_versions:
            self._skill_versions[skill_name] = []
        self._skill_versions[skill_name].append(skill.version)
        
        # Tag with "browser_automation"
        skill.tags.add("browser_automation")
        
        logger.info("Browser skill added", extra={
            "skill_id": skill.id,
            "version": skill.version,
            "capabilities": list(skill.required_capabilities)
        })
        
        return True
    
    def search_browser_skills(
        self, 
        agent_capabilities: List[str],
        context: Optional[str] = None,
        framework: Optional[str] = None
    ) -> List[BrowserSkill]:
        """
        Search skills with O(1) indexed lookups
        
        Args:
            agent_capabilities: List of agent capabilities (e.g., ["http", "browser", "stealth"])
            context: Optional execution context filter
            framework: Optional framework filter
            
        Returns:
            List of skills matching criteria, sorted by success rate
        """
        capability_set = set(agent_capabilities)
        
        # Start with all skills
        candidate_ids = set(self._skills.keys())
        
        # Filter by context using index
        if context:
            candidate_ids &= self._context_index.get(context, set())
        
        # Filter by framework using index
        if framework:
            candidate_ids &= self._framework_index.get(framework, set())
        
        # Filter by capabilities
        matching_skills = []
        for skill_id in candidate_ids:
            skill = self._skills[skill_id]
            
            # Skip deprecated skills
            if skill.deprecated:
                continue
            
            # Check if agent has required capabilities
            if skill.required_capabilities.issubset(capability_set):
                matching_skills.append(skill)
        
        # Sort by success rate and usage
        return sorted(
            matching_skills,
            key=lambda s: (s.success_rate, s.usage_count),
            reverse=True
        )
    
    def get_workflow_skills(self) -> List[BrowserSkill]:
        """Get all workflow-based skills using index"""
        workflow_ids = self._context_index.get("browser_workflow", set())
        return [self._skills[sid] for sid in workflow_ids if not self._skills[sid].deprecated]
    
    def compose_workflows(self, skill_ids: List[str]) -> BrowserSkill:
        """
        Compose multiple workflow skills into one
        
        Validates compatibility and merges steps
        """
        skills = [self._skills[sid] for sid in skill_ids]
        
        # Validate all are workflows
        if not all(s.execution_context == "browser_workflow" for s in skills):
            raise ValueError("All skills must be workflows")
        
        # Validate compatibility (session requirements, etc.)
        self._validate_workflow_compatibility(skills)
        
        # Merge workflow steps
        combined_steps = []
        for skill in skills:
            combined_steps.extend(skill.workflow_steps)
        
        # Merge success conditions
        combined_conditions = self._merge_success_conditions(skills)
        
        # Create composed skill
        composed = BrowserSkill(
            id=f"composed_{'-'.join(skill_ids)}",
            name=f"Composed: {' + '.join(s.name for s in skills)}",
            execution_context="browser_workflow",
            browser_requirements=self._merge_browser_requirements(skills),
            workflow_steps=combined_steps,
            session_requirements=self._merge_session_requirements(skills),
            evidence_requirements=list(set(sum([s.evidence_requirements for s in skills], []))),
            version="1.0.0",
            required_capabilities=frozenset().union(*[s.required_capabilities for s in skills])
        )
        
        return composed
    
    def deprecate_skill(
        self, 
        skill_id: str, 
        reason: str, 
        replacement_id: Optional[str] = None
    ) -> None:
        """
        Deprecate a skill with migration path
        
        Args:
            skill_id: ID of skill to deprecate
            reason: Reason for deprecation
            replacement_id: Optional ID of replacement skill
        """
        skill = self._skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        skill.deprecated = True
        skill.deprecation_reason = reason
        skill.migration_path = replacement_id
        
        logger.warning("Skill deprecated", extra={
            "skill_id": skill_id,
            "reason": reason,
            "replacement": replacement_id
        })
    
    def get_skill_version_history(self, skill_name: str) -> List[str]:
        """Get all versions of a skill"""
        versions = self._skill_versions.get(skill_name, [])
        return sorted(versions, key=semver.VersionInfo.parse, reverse=True)
    
    def _update_capability_index(self, skill: BrowserSkill) -> None:
        """Update capability index for fast lookups"""
        for cap in skill.required_capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(skill.id)
    
    def _update_context_index(self, skill: BrowserSkill) -> None:
        """Update context index"""
        if skill.execution_context not in self._context_index:
            self._context_index[skill.execution_context] = set()
        self._context_index[skill.execution_context].add(skill.id)
    
    def _update_framework_index(self, skill: BrowserSkill) -> None:
        """Update framework index"""
        framework = skill.browser_requirements.get("framework")
        if framework:
            if framework not in self._framework_index:
                self._framework_index[framework] = set()
            self._framework_index[framework].add(skill.id)
```



### 4. Browser-Aware Health Monitor Extension

**Purpose**: Extend Health Monitor to track browser-specific metrics

**Location**: `backend/core/agent_health_monitor.py` (extend existing)

**New Metrics**:
```python
class BrowserHealthMetrics:
    active_contexts: int
    context_memory_mb: float
    page_load_time_ms: float
    screenshot_time_ms: float
    browser_error_rate: float
    context_creation_time_ms: float
```

**New Methods**:
```python
def report_browser_metrics(self, agent_name: str, metrics: BrowserHealthMetrics):
    """Report browser-specific health metrics"""
    # Store browser metrics
    # Calculate browser health score
    # Alert if browser operations impact system
    
def get_browser_health(self, agent_name: str) -> Dict:
    """Get browser-specific health metrics"""
    # Return browser metrics
    # Include context count and memory
    
def calculate_browser_health_score(self, metrics: BrowserHealthMetrics) -> float:
    """Calculate health score accounting for browser resources"""
    # Factor in context count
    # Factor in memory usage
    # Factor in page load times
```

### 5. Browser-Aware Self-Healing Extension

**Purpose**: Extend Self-Healing Engine for browser failures

**Location**: `backend/core/self_healing_engine.py` (extend existing)

**New Recovery Actions**:
```python
async def heal_browser_crash(self, agent_name: str, context_id: str) -> bool:
    """Heal crashed browser context"""
    # Detect crash via Health Monitor
    # Restart browser context
    # Restore session state
    # Apply exponential backoff
    
async def heal_browser_memory(self, agent_name: str) -> bool:
    """Heal high browser memory usage"""
    # Close idle contexts
    # Clear context pool
    # Trigger garbage collection
    
async def adapt_browser_strategy(self, agent_name: str, reason: str):
    """Adapt browser strategy on repeated failures"""
    # Switch to stealth mode
    # Reduce concurrency
    # Fall back to HTTP
```



### 6. Unified Knowledge Graph Extension

**Purpose**: Extend Knowledge Graph to link HTTP and browser discoveries

**Location**: `backend/core/knowledge_graph.py` (extend existing)

**New Node Types**:
- `BrowserEndpoint`: Endpoint discovered via browser
- `JavaScriptRoute`: Route extracted from JS framework
- `WebSocketConnection`: WebSocket discovered via browser

**New Relationships**:
- `HTTP_EQUIVALENT`: Links browser endpoint to HTTP endpoint
- `DISCOVERED_BY`: Links endpoint to discovery method
- `FRAMEWORK_ROUTE`: Links route to framework

**New Methods**:
```python
def add_browser_discovery(self, endpoint: str, source: str, metadata: Dict):
    """Add browser-discovered endpoint to graph"""
    # Create node with source="browser_recon"
    # Link to HTTP equivalent if exists
    # Store discovery metadata
    
def link_http_browser_endpoints(self, http_url: str, browser_url: str):
    """Link HTTP and browser versions of same endpoint"""
    # Create HTTP_EQUIVALENT relationship
    # Merge metadata
    
def get_endpoint_context(self, endpoint: str) -> Dict:
    """Get both HTTP and browser context for endpoint"""
    # Return HTTP discovery data
    # Return browser discovery data
    # Return linked endpoints
```

### 7. Forensic-Learning Integration

**Purpose**: Feed forensic evidence into learning engine

**Location**: `backend/core/forensic_learning_bridge.py` (new)

**Responsibilities**:
- Analyze forensic evidence quality
- Extract learning patterns from evidence
- Adapt evidence collection based on learning
- Store evidence requirements in skills

**Interface**:
```python
class ForensicLearningBridge:
    def __init__(self, learning_engine, forensic_collector):
        self.learning_engine = learning_engine
        self.forensics = forensic_collector
        
    async def analyze_evidence_quality(self, evidence: Dict) -> Dict:
        """Analyze completeness and quality of evidence"""
        # Check for required evidence types
        # Calculate quality score
        # Identify gaps
        
    async def learn_evidence_requirements(self, vuln_type: str, evidence: Dict):
        """Learn what evidence is valuable for vulnerability type"""
        # Track evidence types per vuln
        # Calculate value scores
        # Store requirements
        
    async def adapt_evidence_collection(self, vuln_type: str) -> Dict:
        """Get evidence collection strategy for vulnerability type"""
        # Query learned requirements
        # Return collection strategy
```



### 8. Intelligent Routing Engine

**Purpose**: Decide between HTTP and browser methods based on learning

**Location**: `backend/core/intelligent_router.py` (new)

**Responsibilities**:
- Learn which targets benefit from browser
- Recommend HTTP vs browser based on patterns
- Select PinchTab vs OpenClaw based on complexity
- Adapt routing based on resources

**Interface**:
```python
class IntelligentRouter:
    def __init__(self, learning_engine, browser_orchestrator):
        self.learning_engine = learning_engine
        self.browser = browser_orchestrator
        
    async def recommend_method(self, target_url: str, scan_context: Dict) -> str:
        """Recommend HTTP-only, browser-only, or hybrid"""
        # Query learned patterns
        # Check target characteristics
        # Return recommendation
        
    async def select_browser_engine(self, task: Dict) -> BrowserEngine:
        """Select PinchTab or OpenClaw for task"""
        # Analyze task complexity
        # Check stealth requirements
        # Return engine selection
        
    async def learn_method_effectiveness(self, target_url: str, method: str, success: bool):
        """Learn which method works for target type"""
        # Extract target characteristics
        # Store method effectiveness
        # Update recommendations
```

## Data Models

### BrowserSkill

```python
@dataclass
class BrowserSkill(Skill):
    """Extended skill for browser operations"""
    execution_context: str  # "browser_required", "http_only", "hybrid"
    browser_requirements: Dict[str, Any]  # stealth, session, framework
    workflow_steps: Optional[List[WorkflowStep]] = None
    session_requirements: Optional[Dict] = None
    evidence_requirements: List[str] = field(default_factory=list)
```

### BrowserPattern

```python
@dataclass
class BrowserPattern(LearningPattern):
    """Extended pattern for browser operations"""
    framework: Optional[str] = None  # React, Vue, Angular
    requires_browser: bool = True
    workflow_complexity: int = 1  # 1-10 scale
    stealth_required: bool = False
```



### IntegrationMetrics

```python
@dataclass
class IntegrationMetrics:
    """Metrics for integrated system"""
    # Skill metrics
    total_skills: int
    browser_skills: int
    http_skills: int
    hybrid_skills: int
    
    # Learning metrics
    browser_patterns: int
    http_patterns: int
    cross_method_patterns: int
    
    # Health metrics
    browser_agent_health: float
    http_agent_health: float
    overall_system_health: float
    
    # Performance metrics
    browser_success_rate: float
    http_success_rate: float
    hybrid_success_rate: float
    
    # Resource metrics
    active_browser_contexts: int
    browser_memory_mb: float
    resource_utilization: float
    
    timestamp: float
```

## Event Flow

### Browser Vulnerability Confirmed

```
1. Browser agent confirms vulnerability
   ↓
2. Publish VULN_CONFIRMED event with browser context
   ↓
3. Learning Engine receives event
   ↓
4. Extract browser-specific pattern
   ↓
5. Skill Extractor creates browser skill
   ↓
6. Publish SKILL_EXTRACTED event
   ↓
7. All browser agents receive new skill
   ↓
8. Forensic Collector analyzes evidence quality
   ↓
9. Learning Engine learns evidence requirements
```

### Browser Context Crash

```
1. Browser context crashes
   ↓
2. Health Monitor detects missing heartbeat
   ↓
3. Publish HEALTH_ALERT event
   ↓
4. Self-Healing Engine receives alert
   ↓
5. Restart browser context with backoff
   ↓
6. Restore session state
   ↓
7. Publish AGENT_HEALED event
   ↓
8. Learning Engine learns failure pattern
```



### Browser Discovery

```
1. Browser agent discovers JavaScript routes
   ↓
2. Publish BROWSER_DISCOVERY event
   ↓
3. Knowledge Graph receives event
   ↓
4. Store with source="browser_recon"
   ↓
5. Link to HTTP equivalent if exists
   ↓
6. Learning Engine extracts framework pattern
   ↓
7. Publish RECON_PACKET for each route
   ↓
8. Other agents receive new endpoints
```

### Cross-System Learning

```
1. HTTP agent finds vulnerability
   ↓
2. Learning Engine recommends browser verification
   ↓
3. Browser agent verifies in real browser
   ↓
4. Forensic evidence collected
   ↓
5. Learning Engine correlates HTTP + browser success
   ↓
6. Create hybrid attack skill
   ↓
7. Skill available to all agents
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Browser Skill Creation and Tagging

*For any* browser-based vulnerability that is confirmed, the system should extract an attack pattern, create a browser-specific skill, and tag it with "browser_automation" including all required browser context metadata.

**Validates: Requirements 1.1, 1.2, 1.3, 1.5**

### Property 2: Payload Generalization

*For any* successful browser payload, the system should generalize it into a reusable template that can match similar payloads with different specific values.

**Validates: Requirements 1.4**

### Property 3: High-Confidence Skill Distribution

*For any* browser skill that reaches high confidence (>0.7), the skill should be queryable and retrievable by all browser-capable agents.

**Validates: Requirements 1.6**

### Property 4: Discovery Pattern Learning

*For any* OpenClaw discovery (JavaScript routes, API endpoints, auth flows, WebSockets), the Learning Engine should create a pattern with the appropriate framework/method metadata.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**



### Property 5: Browser-Based Recommendations

*For any* target URL with learned browser patterns, the Learning Engine should generate recommendations that include browser-based attack vectors when queried.

**Validates: Requirements 2.5, 2.6**

### Property 6: Browser Crash Detection and Recovery

*For any* browser context crash, the Health Monitor should detect it and the Self-Healing Engine should restart the context with exponential backoff and session state restoration.

**Validates: Requirements 3.1, 3.2, 3.5**

### Property 7: Browser Memory Management

*For any* situation where browser memory exceeds thresholds, the Self-Healing Engine should close idle contexts to reduce memory usage.

**Validates: Requirements 3.3**

### Property 8: Browser Strategy Adaptation

*For any* browser operation that times out repeatedly (3+ times), the Self-Healing Engine should adapt the strategy (e.g., switch to stealth mode or reduce concurrency).

**Validates: Requirements 3.4**

### Property 9: Browser Circuit Breaker

*For any* browser target that fails repeatedly (5+ times), the Self-Healing Engine should apply circuit breaker logic to prevent further attempts.

**Validates: Requirements 3.6**

### Property 10: Unified Skill Storage

*For any* skill (HTTP, browser, or hybrid), the Skill Library should store it in the same persistent storage with execution context metadata.

**Validates: Requirements 4.1, 4.2**

### Property 11: Capability-Based Skill Filtering

*For any* agent querying skills, the Skill Library should filter results based on the agent's capabilities (HTTP-only vs browser-capable).

**Validates: Requirements 4.3**

### Property 12: Skill Effectiveness Tracking

*For any* skill used in both HTTP and browser contexts, the Skill Library should track effectiveness separately for each context.

**Validates: Requirements 4.4**

### Property 13: Skill Export Completeness

*For any* browser skill exported, the export should include all browser automation requirements (stealth, session, framework).

**Validates: Requirements 4.5**

### Property 14: Independent Skill Versioning

*For any* skill update, browser-specific skills and HTTP-specific skills should have independent version numbers.

**Validates: Requirements 4.6**



### Property 15: Browser Metric Tracking

*For any* browser operation, the Health Monitor should track browser-specific metrics (memory per context, page load time, screenshot time) and include them in health calculations.

**Validates: Requirements 5.1, 6.2, 6.3, 6.4**

### Property 16: Performance Bottleneck Identification

*For any* browser operation that is slow (>2x expected time), the Learning Engine should identify it as a performance bottleneck.

**Validates: Requirements 5.2**

### Property 17: Memory-Triggered Cleanup

*For any* situation where browser memory usage is high, the Self-Healing Engine should trigger context cleanup.

**Validates: Requirements 5.3**

### Property 18: Target Method Learning

*For any* target scanned with both HTTP and browser methods, the Learning Engine should learn which method is more effective for that target type.

**Validates: Requirements 5.4**

### Property 19: Engine Selection Recommendations

*For any* operation, the system should recommend PinchTab for fast/simple operations and OpenClaw for complex/stealth operations based on learned patterns.

**Validates: Requirements 5.5**

### Property 20: Resource Reallocation on Failure

*For any* browser operation that fails due to insufficient resources, the NeuroNegotiator should reallocate resources.

**Validates: Requirements 5.6**

### Property 21: Universal Health Monitoring

*For any* agent (HTTP or browser), the Health Monitor should track health metrics and calculate health scores.

**Validates: Requirements 6.1**

### Property 22: Browser Health Impact Alerts

*For any* browser operation that causes overall system health to drop below threshold, the Health Monitor should generate an alert.

**Validates: Requirements 6.6**

### Property 23: Discovery Source Tagging

*For any* endpoint discovered, the Knowledge Graph should tag it with the correct source ("http_recon" or "browser_recon") and track which method discovered it first.

**Validates: Requirements 7.1, 7.2, 7.5**

### Property 24: HTTP-Browser Endpoint Linking

*For any* endpoint discovered by both HTTP and browser methods, the Knowledge Graph should link them and deduplicate.

**Validates: Requirements 7.3, 7.4**



### Property 25: Unified Endpoint Context

*For any* endpoint query, the system should provide both HTTP and browser context (discovery method, metadata, linked endpoints).

**Validates: Requirements 7.6**

### Property 26: Cross-Method Recommendations

*For any* vulnerability found via HTTP, the Learning Engine should recommend browser verification, and vice versa.

**Validates: Requirements 8.1, 8.2**

### Property 27: Cross-Context Pattern Identification

*For any* vulnerability confirmed in both HTTP and browser contexts, the Learning Engine should identify it as a cross-context pattern.

**Validates: Requirements 8.3**

### Property 28: HTTP Payload Extraction from Browser

*For any* successful browser workflow, the Learning Engine should extract HTTP-equivalent payloads when possible.

**Validates: Requirements 8.4**

### Property 29: HTTP-Browser Correlation Tracking

*For any* scan that uses HTTP reconnaissance followed by browser exploitation, the system should track the correlation between the two.

**Validates: Requirements 8.5**

### Property 30: Collaborative Pattern Skills

*For any* successful collaboration between agents (HTTP + browser), the system should record the collaborative pattern as a skill.

**Validates: Requirements 8.6**

### Property 31: Comprehensive Evidence Capture

*For any* browser exploit confirmed, the Forensic Collector should capture all evidence types (screenshots, network logs, DOM snapshots).

**Validates: Requirements 9.1**

### Property 32: Evidence Quality Analysis

*For any* evidence collected, the Learning Engine should analyze completeness and quality metrics.

**Validates: Requirements 9.2**

### Property 33: Evidence Value Learning

*For any* vulnerability type, the Learning Engine should learn which evidence types are most valuable based on historical data.

**Validates: Requirements 9.3**

### Property 34: Evidence Strategy Adaptation

*For any* evidence collection failure, the Self-Healing Engine should adapt the evidence capture strategy.

**Validates: Requirements 9.4**

### Property 35: Skill Evidence Requirements

*For any* skill stored, the Skill Library should include evidence requirements, and when the skill is executed, the required evidence should be collected.

**Validates: Requirements 9.5, 9.6**



### Property 36: Separate Attack Method Tracking

*For any* attack (HTTP or browser), the Health Monitor should track success rates separately by method.

**Validates: Requirements 10.1**

### Property 37: Browser Pattern Confidence

*For any* browser-based pattern, the Learning Engine should calculate confidence scores using the same algorithm as HTTP patterns.

**Validates: Requirements 10.2**

### Property 38: Browser Skill Acquisition Tracking

*For any* browser-specific skill acquired, the system should track the acquisition rate separately from HTTP skills.

**Validates: Requirements 10.4**

### Property 39: Browser Performance Improvement Measurement

*For any* browser operation performed over time, the system should measure performance improvement (speed, success rate).

**Validates: Requirements 10.5**

### Property 40: Unified Event Publishing

*For any* significant system event (skill extraction, agent healing, browser discovery, evidence collection, health alert), the responsible component should publish an event to the EventBus.

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

### Property 41: Unified Resource Bidding

*For any* browser context creation, the system should use the NeuroNegotiator bidding system with memory requirements included in the bid.

**Validates: Requirements 12.1, 12.2**

### Property 42: HTTP-Browser Resource Balancing

*For any* resource allocation decision, the NeuroNegotiator should balance resources between HTTP agents and browser agents.

**Validates: Requirements 12.3**

### Property 43: Learning-Value Priority

*For any* resource scarcity situation, the NeuroNegotiator should prioritize operations with higher learning value.

**Validates: Requirements 12.4**

### Property 44: Healing-Triggered Reallocation

*For any* browser operation failure due to resources, the Self-Healing Engine should trigger resource reallocation.

**Validates: Requirements 12.5**

### Property 45: Health-Driven Resource Optimization

*For any* resource allocation decision, the NeuroNegotiator should use resource usage data from the Health Monitor.

**Validates: Requirements 12.6**



### Property 46: Unified Error Handling

*For any* error (HTTP or browser), the Self-Healing Engine should apply the same recovery patterns (exponential backoff, circuit breakers).

**Validates: Requirements 13.1, 13.2, 13.3**

### Property 47: Cross-Context Learning Application

*For any* recovery strategy adapted in one context (HTTP or browser), the system should apply learnings to the other context.

**Validates: Requirements 13.4**

### Property 48: Unified Failure Learning

*For any* failure (HTTP or browser), the Learning Engine should extract failure patterns using the same algorithm.

**Validates: Requirements 13.5**

### Property 49: Separate Recovery Tracking

*For any* recovery action, the system should track success rates separately for HTTP and browser operations.

**Validates: Requirements 13.6**

### Property 50: Unified Data Storage

*For any* data type (skills, patterns, health metrics, discoveries), the system should store HTTP and browser data in the same unified storage.

**Validates: Requirements 14.1, 14.2, 14.3, 14.4**

### Property 51: Unified Query Results

*For any* knowledge store query, the system should provide unified results across all sources (HTTP and browser).

**Validates: Requirements 14.5**

### Property 52: Atomic Cross-Context Updates

*For any* data update affecting both HTTP and browser data, the system should support atomic transactions.

**Validates: Requirements 14.6**

### Property 53: Workflow Skill Extraction

*For any* multi-step browser workflow that succeeds, the Skill Extractor should extract it as a skill with all steps and success conditions.

**Validates: Requirements 16.1**

### Property 54: Workflow Metadata Storage

*For any* workflow skill stored, the Skill Library should include workflow steps, success conditions, session requirements, and timing.

**Validates: Requirements 16.2, 16.3**

### Property 55: Workflow Composition

*For any* set of workflow skills, the Skill Library should support composing them into a single combined workflow.

**Validates: Requirements 16.4**



### Property 56: Adaptive Workflow Execution

*For any* workflow skill executed, the system should adapt steps based on target responses.

**Validates: Requirements 16.5**

### Property 57: Workflow Success Rate Tracking

*For any* workflow pattern, the Learning Engine should track success rates across all executions.

**Validates: Requirements 16.6**

### Property 58: Target Browser Benefit Learning

*For any* target scanned with both HTTP and browser methods, the Learning Engine should learn which targets benefit from browser automation.

**Validates: Requirements 17.1**

### Property 59: Method Recommendation Based on Patterns

*For any* target scan, the system should recommend HTTP vs browser based on learned patterns for similar targets.

**Validates: Requirements 17.2**

### Property 60: Complexity-Based Engine Selection

*For any* browser task, the BrowserOrchestrator should automatically select PinchTab for simple tasks and OpenClaw for complex tasks.

**Validates: Requirements 17.3**

### Property 61: Method Success Rate Comparison

*For any* target type, the Learning Engine should track and compare success rates for HTTP-only vs browser-enhanced scans.

**Validates: Requirements 17.4**

### Property 62: HTTP-Only Recommendation

*For any* target where browser automation adds no value (based on learned patterns), the system should recommend HTTP-only approach.

**Validates: Requirements 17.5**

### Property 63: Adaptive Routing

*For any* routing decision, the system should adapt based on resource availability and target characteristics.

**Validates: Requirements 17.6**

### Property 64: Auth Pattern Extraction

*For any* successful browser authentication, the Learning Engine should extract the auth pattern as a reusable skill.

**Validates: Requirements 18.1, 18.2**

### Property 65: Auth Pattern Reuse

*For any* target similar to one with learned auth patterns, the system should reuse the learned authentication pattern.

**Validates: Requirements 18.3**



### Property 66: Session State Persistence

*For any* browser session, the Hybrid_Session_Manager should store session state for reuse across scans.

**Validates: Requirements 18.4**

### Property 67: Automatic Re-Authentication

*For any* expired session, the Self-Healing Engine should re-authenticate using learned patterns.

**Validates: Requirements 18.5**

### Property 68: Auth Method Tracking

*For any* authentication method used, the Learning Engine should track which methods work for which target types.

**Validates: Requirements 18.6**

### Property 69: Evidence Quality Analysis

*For any* forensic evidence collected, the Learning Engine should analyze completeness and quality.

**Validates: Requirements 19.1**

### Property 70: Evidence Gap Learning

*For any* insufficient evidence, the system should learn what additional evidence is needed.

**Validates: Requirements 19.2**

### Property 71: Adaptive Evidence Collection

*For any* evidence collection operation, the Forensic Collector should adapt based on learned requirements.

**Validates: Requirements 19.3**

### Property 72: Evidence Collection Skills

*For any* evidence collection pattern, the Skill Library should store it as a skill.

**Validates: Requirements 19.4**

### Property 73: Required Evidence Enforcement

*For any* vulnerability reported, the system should ensure all required evidence is collected.

**Validates: Requirements 19.5**

### Property 74: Evidence Quality Tracking

*For any* evidence collected over time, the Learning Engine should track quality metrics.

**Validates: Requirements 19.6**

### Property 75: System-Wide Bottleneck Identification

*For any* performance bottleneck across all system components, the Learning Engine should identify it.

**Validates: Requirements 20.1**

### Property 76: Performance-Based Resource Optimization

*For any* resource allocation decision, the Self-Healing Engine should optimize based on performance metrics.

**Validates: Requirements 20.2**



### Property 77: Learning Overhead Balancing

*For any* system operation, the system should balance learning overhead against scan performance to maintain overall throughput.

**Validates: Requirements 20.3**

### Property 78: HTTP Alternative Recommendation

*For any* slow browser operation, the system should recommend HTTP alternatives.

**Validates: Requirements 20.4**

### Property 79: End-to-End Performance Tracking

*For any* operation, the Health Monitor should track end-to-end performance including learning and browser overhead.

**Validates: Requirements 20.5**

### Property 80: Adaptive Operation Mix

*For any* throughput optimization opportunity, the system should adapt the operation mix (HTTP vs browser) to maximize overall throughput.

**Validates: Requirements 20.6**

## Error Handling

### Browser-Specific Errors

1. **Context Crash**: Restart with exponential backoff, restore session
2. **Memory Exhaustion**: Close idle contexts, clear pool, trigger GC
3. **Timeout**: Retry with increased timeout, fall back to HTTP
4. **Navigation Failure**: Circuit breaker, mark target as problematic
5. **Screenshot Failure**: Continue without screenshot, log warning

### Integration Errors

1. **EventBus Failure**: Queue events locally, retry on reconnect
2. **Storage Failure**: Use in-memory fallback, alert operator
3. **Learning Engine Failure**: Continue without learning, log errors
4. **Resource Allocation Failure**: Graceful degradation, prioritize critical operations

### Recovery Strategies

1. **Exponential Backoff**: 5s, 10s, 30s, 60s, 300s
2. **Circuit Breaker**: Open after 5 failures, half-open after 30s
3. **Graceful Degradation**: Disable non-critical features under load
4. **Fallback Chains**: Browser → HTTP → Skip

## Testing Strategy

### Dual Testing Approach

The testing strategy combines unit tests for specific examples and edge cases with property-based tests for universal properties:

**Unit Tests**:
- Specific integration scenarios
- Edge cases (empty data, null values, boundary conditions)
- Error conditions (crashes, timeouts, failures)
- Component interactions
- Event flow verification

**Property-Based Tests**:
- Universal properties across all inputs
- Comprehensive input coverage through randomization
- Minimum 100 iterations per property test
- Each property test references its design document property



### Property-Based Testing Configuration

**Library**: Use `hypothesis` for Python property-based testing

**Configuration**:
```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=100)  # Minimum 100 iterations
@given(
    vuln_data=st.fixed_dictionaries({
        'type': st.sampled_from(['XSS', 'SQLi', 'CSRF']),
        'url': st.text(min_size=10),
        'payload': st.text(min_size=1),
        'browser_context': st.booleans()
    })
)
def test_property_1_browser_skill_creation(vuln_data):
    """
    Feature: deep-system-integration, Property 1: Browser Skill Creation and Tagging
    
    For any browser-based vulnerability that is confirmed, the system should 
    extract an attack pattern, create a browser-specific skill, and tag it 
    with "browser_automation" including all required browser context metadata.
    """
    # Test implementation
```

### Test Organization

```
tests/
├── unit/
│   ├── test_integration_coordinator.py
│   ├── test_browser_learning.py
│   ├── test_browser_skills.py
│   ├── test_browser_health.py
│   ├── test_browser_healing.py
│   ├── test_knowledge_graph_integration.py
│   ├── test_forensic_learning.py
│   └── test_intelligent_router.py
├── integration/
│   ├── test_browser_evolution_flow.py
│   ├── test_cross_system_learning.py
│   ├── test_unified_resource_management.py
│   └── test_event_flow.py
└── property/
    ├── test_properties_1_10.py
    ├── test_properties_11_20.py
    ├── test_properties_21_30.py
    ├── test_properties_31_40.py
    ├── test_properties_41_50.py
    ├── test_properties_51_60.py
    ├── test_properties_61_70.py
    └── test_properties_71_80.py
```

### Test Coverage Goals

- Unit test coverage: 90%+ for new integration code
- Property test coverage: 100% of correctness properties
- Integration test coverage: All major event flows
- End-to-end test coverage: Complete scan with integrated systems

## Performance Considerations

### Memory Management

- Browser contexts limited to 10 concurrent
- Context pooling with max size of 5
- Automatic cleanup of idle contexts (>5 minutes)
- Memory monitoring every 60 seconds
- Cleanup triggered at 500MB threshold

### CPU Optimization

- Learning overhead < 5% of scan time
- Skill lookup < 10ms
- Health checks < 50ms
- Event publishing async (non-blocking)

### Storage Optimization

- Unified storage reduces duplication
- Indexed queries for fast skill lookup
- Pattern consolidation prevents explosion
- Periodic cleanup of old data



### Scalability

- Support 50+ concurrent agents (HTTP + browser)
- Handle 10,000+ skills in library
- Process 100+ evolution events per second
- Support 20+ concurrent browser contexts
- Scale learning engine to 1000+ patterns

## Configuration

### Environment Variables

```bash
# Integration Configuration
INTEGRATION_ENABLED=true
INTEGRATION_LAZY_INIT=true  # Lazy initialize components

# Browser-Learning Integration
BROWSER_LEARNING_ENABLED=true
BROWSER_SKILL_EXTRACTION=true
BROWSER_PATTERN_CONFIDENCE_THRESHOLD=0.7

# Browser-Healing Integration
BROWSER_HEALING_ENABLED=true
BROWSER_MEMORY_THRESHOLD_MB=500
BROWSER_CONTEXT_IDLE_TIMEOUT=300  # 5 minutes

# Forensic-Learning Integration
FORENSIC_LEARNING_ENABLED=true
EVIDENCE_QUALITY_THRESHOLD=0.8

# Intelligent Routing
INTELLIGENT_ROUTING_ENABLED=true
PREFER_BROWSER_FOR_SPA=true
PREFER_HTTP_FOR_API=true

# Resource Management
UNIFIED_RESOURCE_MANAGEMENT=true
BROWSER_RESOURCE_PRIORITY=0.7
LEARNING_VALUE_WEIGHT=0.3

# Performance
MAX_LEARNING_OVERHEAD_PERCENT=5
MAX_BROWSER_CONTEXTS=10
CONTEXT_POOL_SIZE=5
```

### Settings Integration

```python
class Settings(BaseSettings):
    # Integration
    INTEGRATION_ENABLED: bool = True
    INTEGRATION_LAZY_INIT: bool = True
    
    # Browser-Learning
    BROWSER_LEARNING_ENABLED: bool = True
    BROWSER_SKILL_EXTRACTION: bool = True
    BROWSER_PATTERN_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Browser-Healing
    BROWSER_HEALING_ENABLED: bool = True
    BROWSER_MEMORY_THRESHOLD_MB: int = 500
    BROWSER_CONTEXT_IDLE_TIMEOUT: int = 300
    
    # Forensic-Learning
    FORENSIC_LEARNING_ENABLED: bool = True
    EVIDENCE_QUALITY_THRESHOLD: float = 0.8
    
    # Intelligent Routing
    INTELLIGENT_ROUTING_ENABLED: bool = True
    PREFER_BROWSER_FOR_SPA: bool = True
    PREFER_HTTP_FOR_API: bool = True
    
    # Resource Management
    UNIFIED_RESOURCE_MANAGEMENT: bool = True
    BROWSER_RESOURCE_PRIORITY: float = 0.7
    LEARNING_VALUE_WEIGHT: float = 0.3
    
    # Performance
    MAX_LEARNING_OVERHEAD_PERCENT: int = 5
    MAX_BROWSER_CONTEXTS: int = 10
    CONTEXT_POOL_SIZE: int = 5
```



## Implementation Phases

### Phase 1: Core Integration Infrastructure (Week 1-2)

**Components**:
- IntegrationCoordinator
- Event type extensions
- Configuration setup
- Basic testing framework

**Deliverables**:
- Integration coordinator initialized
- All components can communicate via events
- Configuration loaded and validated
- Unit tests for coordinator

### Phase 2: Browser-Learning Integration (Week 3-4)

**Components**:
- Browser-aware Learning Engine extensions
- Browser-aware Skill Library extensions
- BrowserPattern and BrowserSkill models
- Intelligent Router

**Deliverables**:
- Browser vulnerabilities create patterns
- Browser skills stored and queryable
- Recommendations include browser vectors
- Property tests for learning integration

### Phase 3: Browser-Healing Integration (Week 5-6)

**Components**:
- Browser-aware Health Monitor extensions
- Browser-aware Self-Healing extensions
- Browser crash recovery
- Memory management

**Deliverables**:
- Browser crashes detected and recovered
- Memory thresholds enforced
- Strategy adaptation working
- Property tests for healing integration

### Phase 4: Knowledge Graph Integration (Week 7-8)

**Components**:
- Knowledge Graph extensions
- HTTP-Browser endpoint linking
- Discovery source tracking
- Unified query interface

**Deliverables**:
- HTTP and browser discoveries linked
- Source tagging working
- Unified queries return both contexts
- Property tests for graph integration

### Phase 5: Forensic-Learning Integration (Week 9-10)

**Components**:
- ForensicLearningBridge
- Evidence quality analysis
- Evidence requirement learning
- Adaptive evidence collection

**Deliverables**:
- Evidence quality analyzed
- Requirements learned and stored
- Collection adapts based on learning
- Property tests for forensic integration



### Phase 6: Resource Management Integration (Week 11-12)

**Components**:
- NeuroNegotiator extensions
- Browser resource bidding
- Load balancing
- Priority-based allocation

**Deliverables**:
- Browser contexts bid for resources
- Resources balanced between HTTP and browser
- Learning value affects priority
- Property tests for resource integration

### Phase 7: Dashboard and Monitoring (Week 13-14)

**Components**:
- Dashboard API extensions
- Unified metrics endpoints
- Real-time monitoring
- Visualization support

**Deliverables**:
- Dashboard shows integrated metrics
- Real-time health for all agents
- Skill acquisition rates visible
- Evolution progress tracked

### Phase 8: End-to-End Testing and Optimization (Week 15-16)

**Activities**:
- Complete property test suite
- Integration test suite
- End-to-end test scenarios
- Performance optimization
- Documentation

**Deliverables**:
- All 80 properties tested
- Integration tests passing
- Performance within targets
- Complete documentation

## Success Metrics

### Integration Metrics

1. **Unified Skill Acquisition**: 10+ new skills per 100 scans (HTTP + browser combined)
   - Measurement: Track skill creation rate in Skill Library
   - Target: 10+ skills per 100 scans

2. **Cross-System Recovery**: 95%+ recovery rate for both HTTP and browser failures
   - Measurement: Track recovery success in Self-Healing Engine
   - Target: 95%+ success rate

3. **Performance Optimization**: 25%+ improvement in scan effectiveness
   - Measurement: Compare vulnerability discovery rate before/after integration
   - Target: 25%+ more vulnerabilities found

4. **Knowledge Sharing**: 90%+ of discoveries available to all agents
   - Measurement: Track discovery propagation in Knowledge Graph
   - Target: 90%+ of discoveries accessible

5. **Resource Efficiency**: 30%+ better resource utilization
   - Measurement: Track resource usage in NeuroNegotiator
   - Target: 30%+ reduction in wasted resources

6. **Evolution Speed**: 2x faster learning rate
   - Measurement: Track pattern acquisition rate in Learning Engine
   - Target: 2x more patterns learned per scan

7. **Dashboard Visibility**: 100% of capabilities visible
   - Measurement: Manual verification of dashboard completeness
   - Target: All metrics and capabilities displayed

8. **Forensic Quality**: 40%+ improvement in evidence completeness
   - Measurement: Track evidence completeness scores
   - Target: 40%+ improvement



## Security Considerations

### Skill Validation

- All skills validated before execution
- Browser skills sandboxed in isolated contexts
- Malicious skill injection prevented
- Skill access role-based

### Data Sovereignty

- All data stays local (Sovereign Midnight principle)
- No external API calls
- Session data encrypted at rest
- Forensic evidence tamper-proof

### Resource Limits

- Browser context limits enforced
- Memory thresholds prevent exhaustion
- CPU limits prevent DoS
- Network rate limiting

### Audit Trail

- All skill executions logged
- All learning events logged
- All healing actions logged
- All resource allocations logged

## Monitoring and Observability

### Metrics to Track

**Integration Metrics**:
- Cross-system event flow rate
- Integration coordinator health
- Component initialization time
- Event processing latency

**Learning Metrics**:
- Browser pattern acquisition rate
- HTTP pattern acquisition rate
- Cross-context pattern rate
- Recommendation accuracy

**Healing Metrics**:
- Browser crash recovery rate
- HTTP failure recovery rate
- Memory cleanup frequency
- Strategy adaptation rate

**Resource Metrics**:
- Browser context utilization
- HTTP agent utilization
- Resource allocation efficiency
- Load balance effectiveness

**Performance Metrics**:
- End-to-end scan time
- Learning overhead percentage
- Browser operation overhead
- Overall throughput

### Logging

**Log Levels**:
- DEBUG: Detailed integration flow
- INFO: Major integration events
- WARNING: Performance degradation
- ERROR: Integration failures
- CRITICAL: System-wide issues

**Log Format**:
```
[timestamp] [level] [component] [integration_context] message
```

**Example**:
```
[2026-05-26 10:30:45] [INFO] [IntegrationCoordinator] [browser_vuln] Browser vulnerability confirmed, triggering learning
[2026-05-26 10:30:46] [INFO] [LearningEngine] [browser_vuln] Extracted browser pattern: XSS_React_Component
[2026-05-26 10:30:47] [INFO] [SkillLibrary] [browser_vuln] Created browser skill: skill_browser_xss_001
```



## Migration Strategy

### Backward Compatibility

- Existing HTTP-only agents continue to work
- Existing skills remain valid
- Existing patterns remain valid
- Existing health monitoring continues

### Gradual Rollout

1. **Phase 1**: Enable integration coordinator (no behavior change)
2. **Phase 2**: Enable browser learning (browser skills created)
3. **Phase 3**: Enable browser healing (browser failures recovered)
4. **Phase 4**: Enable knowledge graph integration (discoveries linked)
5. **Phase 5**: Enable forensic learning (evidence quality improves)
6. **Phase 6**: Enable resource management (resources optimized)
7. **Phase 7**: Enable dashboard (visibility improves)

### Rollback Plan

- Feature flags for each integration component
- Disable integration coordinator to revert to standalone systems
- Existing data preserved during rollback
- No data loss on rollback

## Dependencies

### Existing Systems

- Agent Evolution System (implemented)
- OpenClaw Integration (implemented)
- Learning Engine (implemented)
- Skill Library (implemented)
- Health Monitor (implemented)
- Self-Healing Engine (implemented)
- BrowserOrchestrator (implemented)
- Forensic Collector (implemented)
- EventBus (existing)
- NeuroNegotiator (existing)
- Knowledge Graph (existing)

### New Dependencies

- hypothesis (property-based testing library)
- No new external dependencies

## Future Enhancements

### Phase 9: Advanced Learning (Future)

- Genetic algorithms for payload optimization
- Reinforcement learning for strategy selection
- Swarm intelligence for multi-agent coordination
- Meta-learning (learning to learn)

### Phase 10: Advanced Integration (Future)

- Real-time collaborative editing of skills
- Skill marketplace between organizations
- AI-powered skill generation
- Automated skill A/B testing

### Phase 11: Advanced Monitoring (Future)

- Predictive health monitoring
- Anomaly detection for integration issues
- Automated performance tuning
- Self-optimizing resource allocation

## Conclusion

This design provides a comprehensive integration of the Agent Evolution System and OpenClaw Integration, creating emergent capabilities through:

1. **Unified Learning**: Browser and HTTP discoveries feed the same learning engine
2. **Unified Healing**: Browser and HTTP failures handled by the same self-healing system
3. **Unified Skills**: Browser and HTTP techniques stored in the same skill library
4. **Unified Resources**: Browser and HTTP operations managed by the same resource allocator
5. **Unified Knowledge**: Browser and HTTP discoveries stored in the same knowledge graph

The integration maintains loose coupling through events, provides consistent patterns across all components, and creates a system that is greater than the sum of its parts.

