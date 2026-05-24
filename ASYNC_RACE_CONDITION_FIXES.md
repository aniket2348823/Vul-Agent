# Async Race Condition Fixes

**Date:** May 24, 2026  
**Priority:** CRITICAL  
**Issues:** 15 fire-and-forget async tasks  
**Estimated Time:** 6-8 hours

---

## Problem

Multiple `asyncio.create_task()` calls throughout the codebase create "fire-and-forget" tasks that:
1. **Don't track completion** - No way to know when they finish
2. **Don't handle errors** - Exceptions are silently swallowed
3. **Don't cleanup** - Can leak resources and cause race conditions
4. **Don't cancel properly** - May continue running after parent stops

---

## Solution Pattern

### Before (Fire-and-Forget)
```python
# BAD: Task created but never tracked
asyncio.create_task(some_coroutine())
```

### After (Tracked with Cleanup)
```python
# GOOD: Task tracked and cleaned up properly
task = asyncio.create_task(some_coroutine())
self._tasks.add(task)
task.add_done_callback(lambda t: self._tasks.discard(t))
task.add_done_callback(self._handle_task_error)
```

---

## Files to Fix

### 1. backend/core/orchestrator.py (5 instances)
- Line 217: `asyncio.create_task(master.start())`
- Line 222: `asyncio.create_task(worker.start())`
- Line 229: `asyncio.create_task(HiveOrchestrator._cluster_telemetry_loop(...))`
- Line 554: `asyncio.create_task(agent_watchdog(agents))`
- Line 872: `asyncio.create_task(generate_and_mark_ready())`

**Status:** Lines 554 and 872 already have proper tracking! ✅  
**Action:** Fix lines 217, 222, 229

### 2. backend/core/hive.py (3 instances)
- Line 73: `asyncio.create_task(self._scan_event_loop(ctx))`
- Line 142: `asyncio.create_task(self._safe_execute(handler, event))`
- Line 268: `asyncio.create_task(self._listen_loop())`
- Line 368: `asyncio.create_task(self.lifecycle())`

**Status:** Lines 73 and 368 have tracking! ✅  
**Action:** Fix lines 142 and 268

### 3. backend/core/queue.py (4 instances)
- Line 112: `asyncio.create_task(_read_stream(proc.stdout, ...))`
- Line 113: `asyncio.create_task(_read_stream(proc.stderr, ...))`
- Line 140: `asyncio.create_task(_write_stdin())`
- Line 141: `asyncio.create_task(_no_output_watchdog())`

**Action:** Add task tracking to ProcessRunner

### 4. backend/agents/prism.py (1 instance)
- Line 78: `asyncio.create_task(self._subscribe_to_results())`

**Action:** Add task tracking to AgentPrism

### 5. backend/agents/chi.py (1 instance)
- Line 81: `asyncio.create_task(self._audit_cluster_payloads())`

**Action:** Add task tracking to AgentChi

### 6. backend/api/socket_manager.py (2 instances)
- Line 136: `asyncio.create_task(self._process_batch_queue())`
- Line 138: `asyncio.create_task(self._track_rps())`

**Action:** Add task tracking to SocketManager

### 7. backend/core/cluster/worker.py (2 instances)
- Line 43: `asyncio.create_task(self.send_heartbeat())`
- Line 52: `asyncio.create_task(self.execute_task(task))`

**Action:** Add task tracking to WorkerNode

### 8. backend/core/cluster/master.py (1 instance)
- Line 32: `asyncio.create_task(self.monitor_workers())`

**Action:** Add task tracking to MasterNode

### 9. backend/core/browser_optimization.py (1 instance)
- Line 184: `asyncio.create_task(self._monitor_loop(context_pool))`

**Action:** Add task tracking to BrowserResourceMonitor

### 10. backend/main.py (3 instances)
- Line 203: `asyncio.create_task(self.start_master())`
- Line 208: `asyncio.create_task(self.start_worker(wid))`

**Action:** Add task tracking to main startup

---

## Implementation Plan

### Phase 1: Add Task Tracking Infrastructure (1 hour)
1. Create `TaskManager` utility class
2. Add error handling callback
3. Add cleanup callback

### Phase 2: Fix Core Components (2 hours)
1. Fix orchestrator.py
2. Fix hive.py
3. Fix queue.py

### Phase 3: Fix Agents (1 hour)
1. Fix prism.py
2. Fix chi.py

### Phase 4: Fix Infrastructure (2 hours)
1. Fix socket_manager.py
2. Fix cluster components
3. Fix browser_optimization.py
4. Fix main.py

### Phase 5: Testing & Verification (1 hour)
1. Run syntax checks
2. Test task cleanup
3. Verify no resource leaks

---

## Task Manager Utility

```python
class TaskManager:
    """Manages async tasks with proper tracking and cleanup."""
    
    def __init__(self, name: str = "TaskManager"):
        self.name = name
        self._tasks: set[asyncio.Task] = set()
        self._logger = logging.getLogger(name)
    
    def create_task(self, coro, name: str = None) -> asyncio.Task:
        """Create a tracked task with automatic cleanup."""
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        
        def cleanup(t: asyncio.Task):
            self._tasks.discard(t)
            if t.cancelled():
                return
            if exc := t.exception():
                self._logger.error(f"Task {name or 'unnamed'} failed: {exc}")
        
        task.add_done_callback(cleanup)
        return task
    
    async def cancel_all(self):
        """Cancel all tracked tasks."""
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self._tasks.clear()
    
    def __len__(self):
        return len(self._tasks)
```

---

## Success Criteria

- [ ] All `asyncio.create_task()` calls are tracked
- [ ] All tasks have error handling
- [ ] All tasks can be cancelled cleanly
- [ ] No resource leaks
- [ ] No silent failures
- [ ] Proper cleanup on shutdown

---

## Testing Checklist

- [ ] Start scan - verify tasks created
- [ ] Stop scan - verify tasks cancelled
- [ ] Task error - verify logged properly
- [ ] Memory check - no leaks
- [ ] Stress test - 100 concurrent scans

---

## Next Steps

1. Create TaskManager utility
2. Fix orchestrator.py (highest priority)
3. Fix hive.py
4. Fix remaining files
5. Test thoroughly
