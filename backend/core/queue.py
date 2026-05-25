from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Coroutine, Sequence

logger = logging.getLogger(__name__)

class LanePriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass
class ProcessResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    killed: bool
    duration_ms: int

class ProcessRunner:
    """
    Wraps subprocess execution with strict timeouts, no-output watchdogs,
    and aggressive cleanup to prevent zombie processes.
    """
    @staticmethod
    async def run(
        command: str,
        no_output_timeout_ms: int = 30000,
        max_runtime_ms: int = 120000,
    ) -> ProcessResult:
        async def _spawn_shell():
            return await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        return await ProcessRunner._run_spawned(
            _spawn_shell,
            display_command=command,
            no_output_timeout_ms=no_output_timeout_ms,
            max_runtime_ms=max_runtime_ms,
        )

    @staticmethod
    async def run_exec(
        argv: Sequence[str],
        *,
        stdin: str | bytes | None = None,
        cwd: str | os.PathLike[str] | None = None,
        no_output_timeout_ms: int = 30000,
        max_runtime_ms: int = 120000,
    ) -> ProcessResult:
        display_command = " ".join(str(part) for part in argv)

        async def _spawn_exec():
            return await asyncio.create_subprocess_exec(
                *[str(part) for part in argv],
                cwd=str(cwd) if cwd else None,
                stdin=asyncio.subprocess.PIPE if stdin is not None else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        return await ProcessRunner._run_spawned(
            _spawn_exec,
            display_command=display_command,
            stdin=stdin,
            no_output_timeout_ms=no_output_timeout_ms,
            max_runtime_ms=max_runtime_ms,
        )

    @staticmethod
    async def _run_spawned(
        spawn_coro,
        *,
        display_command: str,
        stdin: str | bytes | None = None,
        no_output_timeout_ms: int = 30000,
        max_runtime_ms: int = 120000,
    ) -> ProcessResult:
        from backend.core.task_manager import TaskManager
        
        start_time = time.monotonic()
        task_manager = TaskManager("ProcessRunner")
        
        try:
            proc = await spawn_coro()
        except Exception as e:
            logger.error(f"Failed to start process '{display_command}': {e}")
            return ProcessResult(-1, "", str(e), False, False, 0)

        stdout_chunks = []
        stderr_chunks = []
        timed_out = False
        killed = False
        last_output_at = time.monotonic()

        async def _read_stream(stream, chunks_list):
            nonlocal last_output_at
            while True:
                line = await stream.readline()
                if not line:
                    break
                last_output_at = time.monotonic()
                chunks_list.append(line.decode('utf-8', errors='replace'))

        stdout_task = task_manager.create_task(
            _read_stream(proc.stdout, stdout_chunks),
            name="stdout_reader"
        )
        stderr_task = task_manager.create_task(
            _read_stream(proc.stderr, stderr_chunks),
            name="stderr_reader"
        )

        async def _write_stdin():
            if stdin is None or proc.stdin is None:
                return
            data = stdin.encode("utf-8") if isinstance(stdin, str) else stdin
            proc.stdin.write(data)
            await proc.stdin.drain()
            proc.stdin.close()

        async def _no_output_watchdog():
            nonlocal timed_out, killed
            while proc.returncode is None:
                await asyncio.sleep(0.25)
                if (time.monotonic() - last_output_at) * 1000 > no_output_timeout_ms:
                    timed_out = True
                    killed = True
                    logger.warning(
                        "Process exceeded no_output_timeout_ms (%sms). Killing.",
                        no_output_timeout_ms,
                    )
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                    return

        stdin_task = task_manager.create_task(_write_stdin(), name="stdin_writer")
        watchdog_task = task_manager.create_task(
            _no_output_watchdog(),
            name="watchdog"
        )
        
        try:
            # Wait with max runtime timeout
            await asyncio.wait_for(
                asyncio.gather(proc.wait(), stdout_task, stderr_task, stdin_task),
                timeout=max_runtime_ms / 1000.0
            )
        except asyncio.TimeoutError:
            timed_out = True
            killed = True
            logger.warning(f"Process exceeded max_runtime_ms ({max_runtime_ms}ms). Killing.")
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            
            # Ensure tasks finish
            stdout_task.cancel()
            stderr_task.cancel()
            stdin_task.cancel()
        finally:
            watchdog_task.cancel()
            # Cleanup all tasks
            await task_manager.cancel_all()

        duration_ms = int((time.monotonic() - start_time) * 1000)
        stdout_text = "".join(stdout_chunks)
        stderr_text = "".join(stderr_chunks)

        return ProcessResult(
            exit_code=proc.returncode if not killed else None,
            stdout=stdout_text,
            stderr=stderr_text,
            timed_out=timed_out,
            killed=killed,
            duration_ms=duration_ms
        )

class CommandLane:
    """
    Command Lane throttle manager to balance concurrent executions.
    Prevents host network/OS resource exhaustion by limiting active threads.
    Mirrors OpenClaw's CommandLane in-process queue design.
    """
    def __init__(self, max_concurrent: int = 8):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Telemetry
        self.active_count = 0
        self.waiting_count = 0
        self.total_executed = 0
        self.total_timed_out = 0
        self.total_failed = 0
        
        # Priority Queue for tracking (Actual scheduling done via asyncio.PriorityQueue if needed, 
        # but for simple concurrency limits, Semaphore with tracking is sufficient)

    class _SlotContextManager:
        def __init__(self, lane: CommandLane, priority: LanePriority):
            self.lane = lane
            self.priority = priority

        async def __aenter__(self):
            self.lane.waiting_count += 1
            await self.lane.semaphore.acquire()
            self.lane.waiting_count -= 1
            self.lane.active_count += 1
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.lane.active_count -= 1
            self.lane.total_executed += 1
            if exc_type:
                self.lane.total_failed += 1
            self.lane.semaphore.release()

    def slot(self, priority: LanePriority = LanePriority.NORMAL) -> '_SlotContextManager':
        """
        Context manager to acquire an execution slot.
        """
        return self._SlotContextManager(self, priority)

    @property
    def telemetry(self) -> Dict[str, Any]:
        return {
            "max_concurrent": self.max_concurrent,
            "active_count": self.active_count,
            "waiting_count": self.waiting_count,
            "total_executed": self.total_executed,
            "total_timed_out": self.total_timed_out,
            "total_failed": self.total_failed,
        }

# Global singleton
command_lane = CommandLane(max_concurrent=8)
