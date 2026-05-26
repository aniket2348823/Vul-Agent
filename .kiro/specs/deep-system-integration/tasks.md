# Implementation Plan: Deep System Integration (HARDENED)

## Overview

This implementation plan integrates the Agent Evolution System with OpenClaw browser automation using production-grade patterns: dependency injection, circuit breakers, event batching, distributed locking, feature flags, and comprehensive testing.

**Key Improvements**:
- Dependency injection (no god objects)
- Circuit breakers for failure isolation
- Event batching to prevent storms
- Distributed locking for race conditions
- Feature flags for gradual rollout
- Property-based testing
- Chaos engineering tests
- Comprehensive observability

## Tasks

- [-] 1. Foundation Infrastructure
  - [x] 1.1 Set up feature flags system
    - Create FeatureFlags dataclass
    - Add environment variable loading
    - Add gradual rollout logic (percentage-based)
    - _Requirements: Backward Compatibility_
  
  - [x] 1.2 Set up OpenTelemetry tracing
    - Configure tracer
    - Add span creation helpers
    - Integrate with Jaeger/Zipkin
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [x] 1.3 Set up Redis for distributed locking
    - Configure Redis client
    - Add connection pooling
    - Add health checks
    - _Requirements: 13.1, 13.2_
  
  - [x] 1.4 Create test infrastructure
    - Set up testcontainers (Redis, Postgres)
    - Create test fixtures
    - Add integration test harness
    - _Requirements: Testing_
  
  - [x] 1.5 Implement IntegrationCoordinator (with feature flags OFF)
    - Create with dependency injection
    - Add circuit breakers
    - Add event batching
    - Add concurrency control (semaphore)
    - Add metrics tracking
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [-]* 1.6 Write unit tests for IntegrationCoordinator
    - Test initialization
    - Test event routing
    - Test circuit breaker behavior
    - Test batch processing
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 2. Checkpoint - Foundation Complete
  - Verify all existing tests pass
  - Verify feature flags work
  - Verify tracing visible
  - Verify integration tests run in CI

- [ ] 3. Browser Learning Engine Extension (with idempotency)
  - [x] 3.1 Implement BrowserLearningExtension class
    - Add Redis client dependency
    - Add idempotency key generation
    - Add distributed locking (acquire/release)
    - Add learning cache
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4_
  
  - [x] 3.2 Implement learn_from_browser_vulnerability method
    - Generate idempotency key from vuln data
    - Acquire distributed lock
    - Check cache for duplicates
    - Extract browser-specific pattern
    - Tag with browser context
    - Store with execution requirements
    - Publish SKILL_EXTRACTED event
    - _Requirements: 1.1, 1.2, 1.3, 1.5_
  
  - [ ]* 3.3 Write property test for idempotency
    - **Property 1: Browser Skill Creation and Tagging**
    - **Property: Idempotency of Vulnerability Learning**
    - Use Hypothesis to generate random vulnerabilities
    - Test learning same vuln twice returns False
    - Test no duplicate skills created
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5**
  
  - [x] 3.4 Implement learn_browser_workflow method
    - Get existing workflow stats from Redis
    - Update stats incrementally
    - Calculate success rate
    - Promote to skill if threshold reached
    - _Requirements: 16.1, 16.6_
  
  - [x] 3.5 Implement get_browser_recommendations method
    - Add LRU cache decorator
    - Query patterns from database
    - Rank by confidence and success rate
    - Return workflows, payloads, framework-specific
    - _Requirements: 2.5, 2.6_
  
  - [ ]* 3.6 Write property test for recommendations
    - **Property 5: Browser-Based Recommendations**
    - Test recommendations are subset of stored patterns
    - Test ranking is correct
    - **Validates: Requirements 2.5, 2.6**
  
  - [x] 3.7 Implement learn_framework_pattern method
    - Deduplicate routes
    - Get existing framework routes from Redis
    - Add only new routes
    - Extract route patterns
    - Store patterns for matching
    - _Requirements: 2.1_
  
  - [ ] 3.8 Enable browser learning for 10% of scans
    - Set ENABLE_BROWSER_LEARNING=true
    - Set BROWSER_LEARNING_ROLLOUT_PCT=10
    - Monitor metrics for 1 week
    - _Requirements: Gradual Rollout_

- [ ] 4. Checkpoint - Learning Engine Complete
  - Verify property tests pass
  - Verify no duplicate skills created
  - Verify cache hit rate > 50%
  - Verify 10% rollout successful

- [ ] 5. Skill Library Extension (with indexing)
  - [x] 5.1 Create BrowserSkill dataclass
    - Add execution_context field
    - Add browser_requirements field
    - Add workflow_steps field
    - Add evidence_requirements field
    - Add version field (semantic versioning)
    - Add deprecated field
    - Add required_capabilities field
    - _Requirements: 1.5, 4.1, 4.2_
  
  - [x] 5.2 Implement BrowserSkillLibraryExtension class
    - Create capability index (Dict[str, Set[str]])
    - Create context index (Dict[str, Set[str]])
    - Create framework index (Dict[str, Set[str]])
    - Create version tracking (Dict[str, List[str]])
    - _Requirements: 4.1, 4.2_
  
  - [x] 5.3 Implement add_browser_skill method
    - Validate version format (semver)
    - Check for duplicates
    - Store skill
    - Update all indexes
    - Track version
    - Tag with "browser_automation"
    - _Requirements: 1.2, 1.3, 1.5_
  
  - [ ]* 5.4 Write property test for skill storage
    - **Property 3: High-Confidence Skill Distribution**
    - **Property 10: Unified Skill Storage**
    - Generate random skills with Hypothesis
    - Test all stored skills are retrievable
    - Test no duplicates created
    - **Validates: Requirements 1.6, 4.1, 4.2**
  
  - [x] 5.5 Implement search_browser_skills method
    - Use indexes for O(1) lookups
    - Filter by context (if provided)
    - Filter by framework (if provided)
    - Filter by capabilities (subset check)
    - Skip deprecated skills
    - Sort by success rate and usage
    - _Requirements: 4.3_
  
  - [ ]* 5.6 Write property test for capability filtering
    - **Property 11: Capability-Based Skill Filtering**
    - Test filtered skills match agent capabilities
    - Test results are subset of all skills
    - Test deprecated skills excluded
    - **Validates: Requirements 4.3**
  
  - [x] 5.7 Implement compose_workflows method
    - Validate all are workflows
    - Validate compatibility
    - Merge workflow steps
    - Merge success conditions
    - Merge browser requirements
    - Create composed skill
    - _Requirements: 16.4_
  
  - [ ]* 5.8 Write property test for workflow composition
    - **Property 55: Workflow Composition**
    - Test composed workflow contains all steps
    - Test composed requirements are union
    - **Validates: Requirements 16.4**
  
  - [x] 5.9 Implement deprecate_skill method
    - Mark skill as deprecated
    - Set deprecation reason
    - Set migration path
    - Log deprecation
    - _Requirements: 4.6_
  
  - [ ] 5.10 Migrate existing skills to new format
    - Export existing skills
    - Add version numbers
    - Add capability requirements
    - Re-import with indexes
    - Verify migration
    - _Requirements: 4.1, 4.2_
  
  - [ ] 5.11 Enable skill library for 25% of scans
    - Set rollout to 25%
    - Monitor skill search latency
    - Monitor index performance
    - _Requirements: Gradual Rollout_

- [ ] 6. Checkpoint - Skill Library Complete
  - Verify property tests pass
  - Verify skill search < 10ms (p99)
  - Verify all skills migrated
  - Verify 25% rollout successful

- [ ] 7. Health Monitor Extension (browser metrics)
  - [x] 7.1 Create BrowserHealthMetrics dataclass
    - Add active_contexts field
    - Add context_memory_mb field
    - Add page_load_time_ms field
    - Add screenshot_time_ms field
    - Add browser_error_rate field
    - _Requirements: 5.1, 6.2, 6.3, 6.4_
  
  - [x] 7.2 Implement report_browser_metrics method
    - Store browser metrics
    - Calculate browser health score
    - Alert if browser operations impact system
    - _Requirements: 6.2, 6.3, 6.6_
  
  - [ ]* 7.3 Write property test for browser health monitoring
    - **Property 15: Browser Metric Tracking**
    - **Property 21: Universal Health Monitoring**
    - Test metrics are tracked correctly
    - Test health score calculation
    - **Validates: Requirements 5.1, 6.1, 6.2, 6.3, 6.4**
  
  - [x] 7.4 Implement get_browser_health method
    - Return browser metrics
    - Include context count and memory
    - _Requirements: 6.2, 6.4_
  
  - [x] 7.5 Implement calculate_browser_health_score method
    - Factor in context count
    - Factor in memory usage
    - Factor in page load times
    - Factor in error rate
    - _Requirements: 6.3_
  
  - [ ]* 7.6 Write property test for health score calculation
    - **Property 22: Browser Health Impact Alerts**
    - Test alerts fire when health drops
    - Test score calculation is consistent
    - **Validates: Requirements 6.6**
  
  - [ ] 7.7 Add browser metrics to dashboard
    - Create browser health panel
    - Add real-time context count
    - Add memory usage graph
    - Add error rate chart
    - _Requirements: 15.1, 15.4_
  
  - [ ] 7.8 Enable health monitoring for 50% of scans
    - Set rollout to 50%
    - Monitor dashboard
    - Verify alerts work
    - _Requirements: Gradual Rollout_

- [ ] 8. Checkpoint - Health Monitor Complete
  - Verify property tests pass
  - Verify metrics visible in dashboard
  - Verify alerts fire correctly
  - Verify 50% rollout successful

- [ ] 9. Self-Healing Engine Extension (browser recovery)
  - [x] 9.1 Implement heal_browser_crash method
    - Detect crash via Health Monitor
    - Restart browser context
    - Restore session state
    - Apply exponential backoff
    - _Requirements: 3.1, 3.2, 3.5_
  
  - [ ]* 9.2 Write property test for browser crash recovery
    - **Property 6: Browser Crash Detection and Recovery**
    - Test crash is detected
    - Test context is restarted
    - Test session state restored
    - **Validates: Requirements 3.1, 3.2, 3.5**
  
  - [x] 9.3 Implement heal_browser_memory method
    - Close idle contexts
    - Clear context pool
    - Trigger garbage collection
    - _Requirements: 3.3, 5.3_
  
  - [ ]* 9.4 Write property test for memory management
    - **Property 7: Browser Memory Management**
    - **Property 17: Memory-Triggered Cleanup**
    - Test idle contexts are closed
    - Test memory is freed
    - **Validates: Requirements 3.3, 5.3**
  
  - [x] 9.5 Implement adapt_browser_strategy method
    - Switch to stealth mode on failures
    - Reduce concurrency
    - Fall back to HTTP
    - _Requirements: 3.4_
  
  - [ ]* 9.6 Write property test for strategy adaptation
    - **Property 8: Browser Strategy Adaptation**
    - Test strategy changes after repeated failures
    - Test fallback to HTTP works
    - **Validates: Requirements 3.4**
  
  - [x] 9.7 Implement browser circuit breaker
    - Track browser target failures
    - Open circuit after threshold
    - Close circuit after timeout
    - _Requirements: 3.6_
  
  - [ ]* 9.8 Write property test for browser circuit breaker
    - **Property 9: Browser Circuit Breaker**
    - Test circuit opens after failures
    - Test circuit closes after timeout
    - **Validates: Requirements 3.6**
  
  - [ ]* 9.9 Write chaos test for resilience
    - **Chaos Test: Coordinator Survives Learning Engine Crash**
    - Inject 50% failure rate into learning engine
    - Send 100 events
    - Verify coordinator still healthy
    - Verify failure rate < 60%
    - **Validates: Resilience**
  
  - [ ] 9.10 Enable self-healing for 75% of scans
    - Set rollout to 75%
    - Monitor recovery success rate
    - Monitor circuit breaker trips
    - _Requirements: Gradual Rollout_

- [ ] 10. Checkpoint - Self-Healing Complete
  - Verify property tests pass
  - Verify chaos tests pass
  - Verify recovery rate > 95%
  - Verify 75% rollout successful

- [ ] 11. Knowledge Graph Extension (HTTP-browser linking)
  - [ ] 11.1 Add browser discovery node types
    - Add BrowserEndpoint node type
    - Add JavaScriptRoute node type
    - Add WebSocketConnection node type
    - _Requirements: 7.1, 7.2_
  
  - [x] 11.2 Implement add_browser_discovery method
    - Create node with source="browser_recon"
    - Link to HTTP equivalent if exists
    - Store discovery metadata
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [ ]* 11.3 Write property test for discovery source tagging
    - **Property 23: Discovery Source Tagging**
    - Test source is tagged correctly
    - Test metadata is stored
    - **Validates: Requirements 7.1, 7.2, 7.5**
  
  - [x] 11.4 Implement link_http_browser_endpoints method
    - Create HTTP_EQUIVALENT relationship
    - Merge metadata
    - Deduplicate discoveries
    - _Requirements: 7.3, 7.4_
  
  - [ ]* 11.5 Write property test for endpoint linking
    - **Property 24: HTTP-Browser Endpoint Linking**
    - Test endpoints are linked correctly
    - Test deduplication works
    - **Validates: Requirements 7.3, 7.4**
  
  - [x] 11.6 Implement get_endpoint_context method
    - Return HTTP discovery data
    - Return browser discovery data
    - Return linked endpoints
    - _Requirements: 7.6_
  
  - [ ]* 11.7 Write property test for unified endpoint context
    - **Property 25: Unified Endpoint Context**
    - Test both HTTP and browser context returned
    - Test linked endpoints included
    - **Validates: Requirements 7.6**
  
  - [ ] 11.8 Enable knowledge graph for 100% of scans
    - Set rollout to 100%
    - Monitor graph queries
    - Monitor deduplication rate
    - _Requirements: Gradual Rollout_

- [ ] 12. Checkpoint - Knowledge Graph Complete
  - Verify property tests pass
  - Verify endpoints are linked
  - Verify deduplication works
  - Verify 100% rollout successful

- [ ] 13. Cross-System Features (routing + forensics)
  - [ ] 13.1 Implement IntelligentRouter class
    - Initialize with learning_engine and browser_orchestrator
    - Set up routing decision logic
    - _Requirements: 17.1, 17.2_
  
  - [ ] 13.2 Implement recommend_method method
    - Query learned patterns
    - Check target characteristics
    - Return HTTP-only, browser-only, or hybrid
    - _Requirements: 17.2, 17.5_
  
  - [ ]* 13.3 Write property test for method recommendation
    - **Property 59: Method Recommendation Based on Patterns**
    - Test recommendations match learned patterns
    - Test HTTP-only recommended when appropriate
    - **Validates: Requirements 17.2, 17.5**
  
  - [ ] 13.4 Implement select_browser_engine method
    - Analyze task complexity
    - Check stealth requirements
    - Return PinchTab or OpenClaw
    - _Requirements: 17.3_
  
  - [ ]* 13.5 Write property test for engine selection
    - **Property 60: Complexity-Based Engine Selection**
    - Test PinchTab selected for simple tasks
    - Test OpenClaw selected for complex tasks
    - **Validates: Requirements 17.3**
  
  - [ ] 13.6 Implement ForensicLearningBridge class
    - Initialize with learning_engine and forensic_collector
    - Set up evidence quality metrics
    - _Requirements: 9.1, 9.2_
  
  - [ ] 13.7 Implement analyze_evidence_quality method
    - Check for required evidence types
    - Calculate quality score
    - Identify gaps
    - _Requirements: 9.2_
  
  - [ ]* 13.8 Write property test for evidence quality
    - **Property 32: Evidence Quality Analysis**
    - Test quality score calculation
    - Test gap identification
    - **Validates: Requirements 9.2**
  
  - [ ] 13.9 Implement learn_evidence_requirements method
    - Track evidence types per vulnerability
    - Calculate value scores
    - Store requirements
    - _Requirements: 9.3_
  
  - [ ]* 13.10 Write property test for evidence learning
    - **Property 33: Evidence Value Learning**
    - Test evidence requirements are learned
    - Test value scores are tracked
    - **Validates: Requirements 9.3**
  
  - [ ] 13.11 Enable routing and forensics for 100%
    - Enable all features
    - Monitor routing decisions
    - Monitor evidence quality
    - _Requirements: Gradual Rollout_

- [ ] 14. Checkpoint - Cross-System Features Complete
  - Verify property tests pass
  - Verify routing improves success rate
  - Verify evidence quality improves
  - Verify 100% rollout successful

- [ ] 15. End-to-End Testing
  - [ ]* 15.1 Write E2E test for complete integrated scan
    - Test full scan with all systems integrated
    - Test HTTP and browser agents collaborate
    - Test learning, healing, and skills all work
    - Test vulnerability → pattern → skill → distribution
    - **Validates: All Requirements**
  
  - [ ]* 15.2 Write E2E test for browser crash recovery
    - Test crash → detection → healing → restoration
    - Verify self-healing works end-to-end
    - **Validates: Requirements 3.1, 3.2, 3.5**
  
  - [ ]* 15.3 Write E2E test for cross-system learning
    - Test HTTP vuln → browser verification → hybrid skill
    - Verify cross-method learning works
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.6**
  
  - [ ]* 15.4 Write chaos test for event storm handling
    - Send 1000 events rapidly
    - Verify system doesn't crash
    - Verify batching works
    - **Validates: Event Batching**

- [ ] 16. Final Checkpoint - All Tests Pass
  - Verify all property tests pass (80 properties)
  - Verify all integration tests pass
  - Verify all E2E tests pass
  - Verify all chaos tests pass
  - Verify performance within 10% of baseline

- [ ] 17. Documentation and Deployment
  - [ ] 17.1 Update API documentation
    - Document new endpoints
    - Document new event types
    - Document integration configuration
  
  - [ ] 17.2 Update architecture documentation
    - Document integration architecture
    - Document event flows
    - Document data models
  
  - [ ] 17.3 Create operational runbooks
    - Daily health check procedures
    - Troubleshooting guides
    - Rollback procedures
    - Skill library maintenance
  
  - [ ] 17.4 Create monitoring dashboards
    - Integration health dashboard
    - Learning performance dashboard
    - Skill library dashboard
    - Browser health dashboard
  
  - [ ] 17.5 Configure alerting rules
    - High failure rate alert
    - Circuit breaker alert
    - Slow skill search alert
    - Browser memory leak alert
  
  - [ ] 17.6 Final deployment to production
    - Deploy with feature flags OFF
    - Enable for 1% (canary)
    - Monitor for 1 week
    - Gradually increase to 100%

## Notes

- Tasks marked with `*` are property-based or chaos tests
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Chaos tests validate resilience under failure
- Gradual rollout ensures safe deployment
- Feature flags enable instant rollback

- [ ] 2. Extend Learning Engine for browser patterns
  - [ ] 2.1 Add learn_from_browser_vulnerability method
    - Extract browser-specific patterns
    - Tag with browser context
    - Store execution requirements
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4_
  
  - [ ]* 2.2 Write property test for browser pattern extraction
    - **Property 1: Browser Skill Creation and Tagging**
    - **Property 4: Discovery Pattern Learning**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5, 2.1, 2.2, 2.3, 2.4**
  
  - [ ] 2.3 Add learn_browser_workflow method
    - Extract workflow patterns
    - Store steps and conditions
    - Track success rates
    - _Requirements: 16.1, 16.6_
  
  - [ ] 2.4 Add get_browser_recommendations method
    - Query browser patterns
    - Return browser workflows and payloads
    - Include framework-specific recommendations
    - _Requirements: 2.5, 2.6_
  
  - [ ]* 2.5 Write property test for browser recommendations
    - **Property 5: Browser-Based Recommendations**
    - **Validates: Requirements 2.5, 2.6**
  
  - [ ] 2.6 Add learn_framework_pattern method
    - Store framework-specific patterns (React, Vue, Angular)
    - Track route structures
    - _Requirements: 2.1_

- [ ] 3. Extend Skill Library for browser skills
  - [ ] 3.1 Add BrowserSkill data model
    - Add execution_context field
    - Add browser_requirements field
    - Add workflow_steps field
    - Add evidence_requirements field
    - _Requirements: 1.5, 4.1, 4.2_
  
  - [ ] 3.2 Add add_browser_skill method
    - Store skill with browser metadata
    - Tag with "browser_automation"
    - Include stealth/session requirements
    - _Requirements: 1.2, 1.3, 1.5_
  
  - [ ]* 3.3 Write property test for browser skill storage
    - **Property 3: High-Confidence Skill Distribution**
    - **Property 10: Unified Skill Storage**
    - **Validates: Requirements 1.6, 4.1, 4.2**
  
  - [ ] 3.4 Add search_browser_skills method
    - Filter by HTTP-only vs browser-required
    - Return skills matching agent capabilities
    - _Requirements: 4.3_
  
  - [ ]* 3.5 Write property test for capability-based filtering
    - **Property 11: Capability-Based Skill Filtering**
    - **Validates: Requirements 4.3**
  
  - [ ] 3.6 Add compose_workflows method
    - Combine multiple workflow skills
    - Merge success conditions
    - _Requirements: 16.4_
  
  - [ ]* 3.7 Write property test for workflow composition
    - **Property 55: Workflow Composition**
    - **Validates: Requirements 16.4**



- [ ] 4. Extend Health Monitor for browser metrics
  - [ ] 4.1 Add BrowserHealthMetrics data model
    - Add active_contexts field
    - Add context_memory_mb field
    - Add page_load_time_ms field
    - Add screenshot_time_ms field
    - Add browser_error_rate field
    - _Requirements: 5.1, 6.2, 6.3, 6.4_
  
  - [ ] 4.2 Add report_browser_metrics method
    - Store browser metrics
    - Calculate browser health score
    - Alert if browser operations impact system
    - _Requirements: 6.2, 6.3, 6.6_
  
  - [ ]* 4.3 Write property test for browser health monitoring
    - **Property 15: Browser Metric Tracking**
    - **Property 21: Universal Health Monitoring**
    - **Validates: Requirements 5.1, 6.1, 6.2, 6.3, 6.4**
  
  - [ ] 4.4 Add get_browser_health method
    - Return browser metrics
    - Include context count and memory
    - _Requirements: 6.2, 6.4_
  
  - [ ] 4.5 Add calculate_browser_health_score method
    - Factor in context count
    - Factor in memory usage
    - Factor in page load times
    - _Requirements: 6.3_
  
  - [ ]* 4.6 Write property test for health score calculation
    - **Property 22: Browser Health Impact Alerts**
    - **Validates: Requirements 6.6**

- [ ] 5. Extend Self-Healing Engine for browser failures
  - [ ] 5.1 Add heal_browser_crash method
    - Detect crash via Health Monitor
    - Restart browser context
    - Restore session state
    - Apply exponential backoff
    - _Requirements: 3.1, 3.2, 3.5_
  
  - [ ]* 5.2 Write property test for browser crash recovery
    - **Property 6: Browser Crash Detection and Recovery**
    - **Validates: Requirements 3.1, 3.2, 3.5**
  
  - [ ] 5.3 Add heal_browser_memory method
    - Close idle contexts
    - Clear context pool
    - Trigger garbage collection
    - _Requirements: 3.3, 5.3_
  
  - [ ]* 5.4 Write property test for memory management
    - **Property 7: Browser Memory Management**
    - **Property 17: Memory-Triggered Cleanup**
    - **Validates: Requirements 3.3, 5.3**
  
  - [ ] 5.5 Add adapt_browser_strategy method
    - Switch to stealth mode on failures
    - Reduce concurrency
    - Fall back to HTTP
    - _Requirements: 3.4_
  
  - [ ]* 5.6 Write property test for strategy adaptation
    - **Property 8: Browser Strategy Adaptation**
    - **Validates: Requirements 3.4**
  
  - [ ] 5.7 Add browser circuit breaker support
    - Track browser target failures
    - Open circuit after threshold
    - _Requirements: 3.6_
  
  - [ ]* 5.8 Write property test for browser circuit breaker
    - **Property 9: Browser Circuit Breaker**
    - **Validates: Requirements 3.6**

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.



- [ ] 7. Extend Knowledge Graph for HTTP-browser linking
  - [ ] 7.1 Add browser discovery node types
    - Add BrowserEndpoint node type
    - Add JavaScriptRoute node type
    - Add WebSocketConnection node type
    - _Requirements: 7.1, 7.2_
  
  - [ ] 7.2 Add add_browser_discovery method
    - Create node with source="browser_recon"
    - Link to HTTP equivalent if exists
    - Store discovery metadata
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [ ]* 7.3 Write property test for discovery source tagging
    - **Property 23: Discovery Source Tagging**
    - **Validates: Requirements 7.1, 7.2, 7.5**
  
  - [ ] 7.4 Add link_http_browser_endpoints method
    - Create HTTP_EQUIVALENT relationship
    - Merge metadata
    - Deduplicate discoveries
    - _Requirements: 7.3, 7.4_
  
  - [ ]* 7.5 Write property test for endpoint linking
    - **Property 24: HTTP-Browser Endpoint Linking**
    - **Validates: Requirements 7.3, 7.4**
  
  - [ ] 7.6 Add get_endpoint_context method
    - Return HTTP discovery data
    - Return browser discovery data
    - Return linked endpoints
    - _Requirements: 7.6_
  
  - [ ]* 7.7 Write property test for unified endpoint context
    - **Property 25: Unified Endpoint Context**
    - **Validates: Requirements 7.6**

- [ ] 8. Implement Forensic-Learning Bridge
  - [ ] 8.1 Create ForensicLearningBridge class
    - Initialize with learning_engine and forensic_collector
    - Set up evidence quality metrics
    - _Requirements: 9.1, 9.2_
  
  - [ ] 8.2 Add analyze_evidence_quality method
    - Check for required evidence types
    - Calculate quality score
    - Identify gaps
    - _Requirements: 9.2_
  
  - [ ]* 8.3 Write property test for evidence quality analysis
    - **Property 32: Evidence Quality Analysis**
    - **Validates: Requirements 9.2**
  
  - [ ] 8.4 Add learn_evidence_requirements method
    - Track evidence types per vulnerability
    - Calculate value scores
    - Store requirements
    - _Requirements: 9.3_
  
  - [ ]* 8.5 Write property test for evidence value learning
    - **Property 33: Evidence Value Learning**
    - **Validates: Requirements 9.3**
  
  - [ ] 8.6 Add adapt_evidence_collection method
    - Query learned requirements
    - Return collection strategy
    - _Requirements: 9.4_
  
  - [ ]* 8.7 Write property test for adaptive evidence collection
    - **Property 34: Evidence Strategy Adaptation**
    - **Validates: Requirements 9.4**



- [ ] 9. Implement Intelligent Router
  - [ ] 9.1 Create IntelligentRouter class
    - Initialize with learning_engine and browser_orchestrator
    - Set up routing decision logic
    - _Requirements: 17.1, 17.2_
  
  - [ ] 9.2 Add recommend_method method
    - Query learned patterns
    - Check target characteristics
    - Return HTTP-only, browser-only, or hybrid recommendation
    - _Requirements: 17.2, 17.5_
  
  - [ ]* 9.3 Write property test for method recommendation
    - **Property 59: Method Recommendation Based on Patterns**
    - **Property 62: HTTP-Only Recommendation**
    - **Validates: Requirements 17.2, 17.5**
  
  - [ ] 9.4 Add select_browser_engine method
    - Analyze task complexity
    - Check stealth requirements
    - Return PinchTab or OpenClaw selection
    - _Requirements: 17.3_
  
  - [ ]* 9.5 Write property test for engine selection
    - **Property 60: Complexity-Based Engine Selection**
    - **Validates: Requirements 17.3**
  
  - [ ] 9.6 Add learn_method_effectiveness method
    - Extract target characteristics
    - Store method effectiveness
    - Update recommendations
    - _Requirements: 17.1, 17.4_
  
  - [ ]* 9.7 Write property test for method effectiveness learning
    - **Property 58: Target Browser Benefit Learning**
    - **Property 61: Method Success Rate Comparison**
    - **Validates: Requirements 17.1, 17.4**

- [x] 10. Implement cross-system learning flows
  - [x] 10.1 Add cross-method recommendation logic
    - HTTP vulnerabilities recommend browser verification
    - Browser exploits recommend HTTP variants
    - _Requirements: 8.1, 8.2_
  
  - [ ]* 10.2 Write property test for cross-method recommendations
    - **Property 26: Cross-Method Recommendations**
    - **Validates: Requirements 8.1, 8.2**
  
  - [x] 10.3 Add cross-context pattern identification
    - Identify patterns that work in both contexts
    - Create hybrid attack skills
    - _Requirements: 8.3, 8.6_
  
  - [ ]* 10.4 Write property test for cross-context patterns
    - **Property 27: Cross-Context Pattern Identification**
    - **Property 30: Collaborative Pattern Skills**
    - **Validates: Requirements 8.3, 8.6**
  
  - [x] 10.5 Add HTTP payload extraction from browser workflows
    - Extract HTTP-equivalent payloads
    - Store as separate skills
    - _Requirements: 8.4_
  
  - [ ]* 10.6 Write property test for payload extraction
    - **Property 28: HTTP Payload Extraction from Browser**
    - **Validates: Requirements 8.4**
  
  - [x] 10.7 Add HTTP-browser correlation tracking
    - Track correlation between HTTP recon and browser exploitation
    - Store correlation patterns
    - _Requirements: 8.5_
  
  - [ ]* 10.8 Write property test for correlation tracking
    - **Property 29: HTTP-Browser Correlation Tracking**
    - **Validates: Requirements 8.5**

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.



- [ ] 12. Implement unified resource management
  - [x] 12.1 Extend NeuroNegotiator for browser resources
    - Add browser context resource type
    - Include memory requirements in bids
    - _Requirements: 12.1, 12.2_
  
  - [ ]* 12.2 Write property test for unified resource bidding
    - **Property 41: Unified Resource Bidding**
    - **Validates: Requirements 12.1, 12.2**
  
  - [x] 12.3 Add HTTP-browser resource balancing
    - Balance resources between agent types
    - Prioritize based on learning value
    - _Requirements: 12.3, 12.4_
  
  - [ ]* 12.4 Write property test for resource balancing
    - **Property 42: HTTP-Browser Resource Balancing**
    - **Property 43: Learning-Value Priority**
    - **Validates: Requirements 12.3, 12.4**
  
  - [x] 12.5 Add healing-triggered reallocation
    - Trigger reallocation on browser failures
    - Use health data for optimization
    - _Requirements: 12.5, 12.6_
  
  - [ ]* 12.6 Write property test for reallocation
    - **Property 44: Healing-Triggered Reallocation**
    - **Property 45: Health-Driven Resource Optimization**
    - **Validates: Requirements 12.5, 12.6**

- [ ] 13. Implement unified error handling
  - [x] 13.1 Extend Self-Healing Engine for unified patterns
    - Apply same recovery patterns to HTTP and browser
    - Use exponential backoff for both
    - Use circuit breakers for both
    - _Requirements: 13.1, 13.2, 13.3_
  
  - [ ]* 13.2 Write property test for unified error handling
    - **Property 46: Unified Error Handling**
    - **Validates: Requirements 13.1, 13.2, 13.3**
  
  - [x] 13.3 Add cross-context learning application
    - Apply HTTP learnings to browser
    - Apply browser learnings to HTTP
    - _Requirements: 13.4, 13.5_
  
  - [ ]* 13.4 Write property test for cross-context learning
    - **Property 47: Cross-Context Learning Application**
    - **Property 48: Unified Failure Learning**
    - **Validates: Requirements 13.4, 13.5**
  
  - [x] 13.5 Add separate recovery tracking
    - Track HTTP recovery separately
    - Track browser recovery separately
    - _Requirements: 13.6_
  
  - [ ]* 13.6 Write property test for recovery tracking
    - **Property 49: Separate Recovery Tracking**
    - **Validates: Requirements 13.6**

- [ ] 14. Implement unified data storage
  - [x] 14.1 Ensure unified storage for all data types
    - Skills stored in same database
    - Patterns stored in same database
    - Health metrics stored in same database
    - Discoveries stored in same graph
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [ ]* 14.2 Write property test for unified storage
    - **Property 50: Unified Data Storage**
    - **Validates: Requirements 14.1, 14.2, 14.3, 14.4**
  
  - [x] 14.3 Add unified query interface
    - Provide unified results across sources
    - Support atomic transactions
    - _Requirements: 14.5, 14.6_
  
  - [ ]* 14.4 Write property test for unified queries
    - **Property 51: Unified Query Results**
    - **Property 52: Atomic Cross-Context Updates**
    - **Validates: Requirements 14.5, 14.6**



- [ ] 15. Implement workflow skill management
  - [x] 15.1 Add workflow skill extraction
    - Extract successful workflows as skills
    - Include steps and success conditions
    - _Requirements: 16.1, 16.2_
  
  - [ ]* 15.2 Write property test for workflow extraction
    - **Property 53: Workflow Skill Extraction**
    - **Validates: Requirements 16.1**
  
  - [x] 15.3 Add workflow metadata storage
    - Store workflow steps
    - Store success conditions
    - Store session requirements
    - Store timing information
    - _Requirements: 16.2, 16.3_
  
  - [ ]* 15.4 Write property test for workflow metadata
    - **Property 54: Workflow Metadata Storage**
    - **Validates: Requirements 16.2, 16.3**
  
  - [x] 15.5 Add adaptive workflow execution
    - Adapt steps based on target responses
    - Track success rates
    - _Requirements: 16.5, 16.6_
  
  - [ ]* 15.6 Write property test for adaptive execution
    - **Property 56: Adaptive Workflow Execution**
    - **Property 57: Workflow Success Rate Tracking**
    - **Validates: Requirements 16.5, 16.6**

- [ ] 16. Implement authentication pattern learning
  - [x] 16.1 Add auth pattern extraction
    - Extract successful auth patterns
    - Store as reusable skills
    - _Requirements: 18.1, 18.2_
  
  - [ ]* 16.2 Write property test for auth pattern extraction
    - **Property 64: Auth Pattern Extraction**
    - **Validates: Requirements 18.1, 18.2**
  
  - [x] 16.3 Add auth pattern reuse
    - Reuse patterns for similar targets
    - Store session state for reuse
    - _Requirements: 18.3, 18.4_
  
  - [ ]* 16.4 Write property test for auth pattern reuse
    - **Property 65: Auth Pattern Reuse**
    - **Property 66: Session State Persistence**
    - **Validates: Requirements 18.3, 18.4**
  
  - [x] 16.5 Add automatic re-authentication
    - Re-authenticate on session expiry
    - Use learned patterns
    - Track auth method effectiveness
    - _Requirements: 18.5, 18.6_
  
  - [ ]* 16.6 Write property test for re-authentication
    - **Property 67: Automatic Re-Authentication**
    - **Property 68: Auth Method Tracking**
    - **Validates: Requirements 18.5, 18.6**

- [ ] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.



- [ ] 18. Implement evidence quality learning
  - [x] 18.1 Add evidence quality analysis
    - Analyze completeness
    - Analyze quality metrics
    - Identify gaps
    - _Requirements: 19.1, 19.2_
  
  - [ ]* 18.2 Write property test for evidence quality
    - **Property 69: Evidence Quality Analysis**
    - **Property 70: Evidence Gap Learning**
    - **Validates: Requirements 19.1, 19.2**
  
  - [x] 18.3 Add adaptive evidence collection
    - Adapt based on learned requirements
    - Store evidence patterns as skills
    - _Requirements: 19.3, 19.4_
  
  - [ ]* 18.4 Write property test for adaptive collection
    - **Property 71: Adaptive Evidence Collection**
    - **Property 72: Evidence Collection Skills**
    - **Validates: Requirements 19.3, 19.4**
  
  - [x] 18.5 Add required evidence enforcement
    - Ensure required evidence collected
    - Track quality over time
    - _Requirements: 19.5, 19.6_
  
  - [ ]* 18.6 Write property test for evidence enforcement
    - **Property 73: Required Evidence Enforcement**
    - **Property 74: Evidence Quality Tracking**
    - **Validates: Requirements 19.5, 19.6**

- [ ] 19. Implement performance optimization
  - [x] 19.1 Add system-wide bottleneck identification
    - Identify bottlenecks across components
    - Optimize resource allocation
    - _Requirements: 20.1, 20.2_
  
  - [ ]* 19.2 Write property test for bottleneck identification
    - **Property 75: System-Wide Bottleneck Identification**
    - **Property 76: Performance-Based Resource Optimization**
    - **Validates: Requirements 20.1, 20.2**
  
  - [x] 19.3 Add learning overhead balancing
    - Balance learning vs scan performance
    - Track end-to-end performance
    - _Requirements: 20.3, 20.5_
  
  - [ ]* 19.4 Write property test for overhead balancing
    - **Property 77: Learning Overhead Balancing**
    - **Property 79: End-to-End Performance Tracking**
    - **Validates: Requirements 20.3, 20.5**
  
  - [x] 19.5 Add HTTP alternative recommendation
    - Recommend HTTP for slow browser operations
    - Adapt operation mix for throughput
    - _Requirements: 20.4, 20.6_
  
  - [ ]* 19.6 Write property test for operation mix adaptation
    - **Property 78: HTTP Alternative Recommendation**
    - **Property 80: Adaptive Operation Mix**
    - **Validates: Requirements 20.4, 20.6**

- [ ] 20. Implement dashboard integration
  - [x] 20.1 Add integration metrics endpoint
    - Expose unified metrics
    - Include skill acquisition rates
    - Include health metrics
    - Include performance metrics
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_
  
  - [x] 20.2 Add real-time monitoring endpoints
    - Active browser contexts
    - Resource usage
    - Evolution progress
    - Self-healing events
    - _Requirements: 15.1, 15.4, 15.5_
  
  - [x] 20.3 Add drill-down endpoints
    - HTTP vs browser metrics
    - Skill type breakdown
    - Agent-specific metrics
    - _Requirements: 15.6_



- [ ] 21. Implement event publishing
  - [x] 21.1 Add SKILL_EXTRACTED event publishing
    - Publish when skills are created
    - Include skill metadata
    - _Requirements: 11.1_
  
  - [x] 21.2 Add AGENT_HEALED event publishing
    - Publish when recovery succeeds
    - Include recovery details
    - _Requirements: 11.2_
  
  - [x] 21.3 Add BROWSER_DISCOVERY event publishing
    - Publish for JavaScript routes
    - Include discovery metadata
    - _Requirements: 11.3_
  
  - [x] 21.4 Add EVIDENCE_COLLECTED event publishing
    - Publish with evidence metadata
    - Include quality metrics
    - _Requirements: 11.4_
  
  - [x] 21.5 Add HEALTH_ALERT event publishing
    - Publish when agents become unhealthy
    - Include health metrics
    - _Requirements: 11.5_
  
  - [ ]* 21.6 Write property test for event publishing
    - **Property 40: Unified Event Publishing**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

- [ ] 22. Integration testing
  - [ ] 22.1 Write integration test for browser vulnerability flow
    - Test browser vuln → pattern → skill → distribution
    - Verify all components interact correctly
    - _Requirements: 1.1, 1.2, 1.3, 1.6_
  
  - [ ] 22.2 Write integration test for browser crash recovery
    - Test crash → detection → healing → restoration
    - Verify self-healing works end-to-end
    - _Requirements: 3.1, 3.2, 3.5_
  
  - [ ] 22.3 Write integration test for cross-system learning
    - Test HTTP vuln → browser verification → hybrid skill
    - Verify cross-method learning works
    - _Requirements: 8.1, 8.2, 8.3, 8.6_
  
  - [ ] 22.4 Write integration test for unified resource management
    - Test resource bidding for HTTP and browser
    - Verify balancing and prioritization
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  
  - [ ] 22.5 Write integration test for forensic learning
    - Test evidence collection → quality analysis → adaptation
    - Verify forensic-learning loop works
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 23. End-to-end testing
  - [ ] 23.1 Write E2E test for complete integrated scan
    - Test full scan with all systems integrated
    - Verify HTTP and browser agents collaborate
    - Verify learning, healing, and skills all work
    - _Requirements: All_

- [ ] 24. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 25. Documentation and deployment
  - [ ] 25.1 Update API documentation
    - Document new endpoints
    - Document new event types
    - Document integration configuration
  
  - [ ] 25.2 Update architecture documentation
    - Document integration architecture
    - Document event flows
    - Document data models
  
  - [ ] 25.3 Create integration guide
    - How to enable/disable integration
    - How to configure integration
    - How to monitor integration
  
  - [ ] 25.4 Update deployment documentation
    - Migration strategy
    - Rollback procedures
    - Configuration examples

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate component interactions
- End-to-end tests validate complete system behavior

