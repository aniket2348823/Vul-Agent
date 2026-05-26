# ═══════════════════════════════════════════════════════════════════════════════
# ANTIGRAVITY V6 :: PHASE GATE — LIFECYCLE STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════
# PURPOSE: Enforces strict sequential execution of scan phases
#          Prevents agents from executing out of order
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import logging
from enum import Enum
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger("PhaseGate")


class ScanPhase(str, Enum):
    """Scan lifecycle phases in strict sequential order"""
    PLANNING = "PLANNING"
    RECONNAISSANCE = "RECONNAISSANCE"
    ASSESSMENT = "ASSESSMENT"
    EXPLOITATION = "EXPLOITATION"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"


class PhaseGate:
    """
    State machine that enforces proper scan phase sequencing.
    Agents must wait for prerequisite phases to complete before executing.
    """
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.current_phase = ScanPhase.PLANNING
        self.phase_events: Dict[ScanPhase, asyncio.Event] = {
            phase: asyncio.Event() for phase in ScanPhase
        }
        self.phase_start_times: Dict[ScanPhase, Optional[datetime]] = {
            phase: None for phase in ScanPhase
        }
        self.phase_end_times: Dict[ScanPhase, Optional[datetime]] = {
            phase: None for phase in ScanPhase
        }
        
        # Planning phase starts immediately
        self.phase_events[ScanPhase.PLANNING].set()
        self.phase_start_times[ScanPhase.PLANNING] = datetime.now()
        
        logger.info(f"[{scan_id}] PhaseGate initialized - Starting in PLANNING phase")
    
    async def advance_to(self, next_phase: ScanPhase) -> bool:
        """
        Advance to the next phase if prerequisites are met.
        Returns True if advancement succeeded, False otherwise.
        """
        # Get phase order
        phases = list(ScanPhase)
        current_idx = phases.index(self.current_phase)
        next_idx = phases.index(next_phase)
        
        # Can only advance forward sequentially
        if next_idx != current_idx + 1:
            logger.warning(
                f"[{self.scan_id}] Cannot advance from {self.current_phase} to {next_phase} "
                f"(must be sequential)"
            )
            return False
        
        # Mark current phase as complete
        self.phase_end_times[self.current_phase] = datetime.now()
        duration = (
            self.phase_end_times[self.current_phase] - 
            self.phase_start_times[self.current_phase]
        ).total_seconds()
        
        logger.info(
            f"[{self.scan_id}] Phase {self.current_phase} completed in {duration:.1f}s"
        )
        
        # Advance to next phase
        self.current_phase = next_phase
        self.phase_start_times[next_phase] = datetime.now()
        self.phase_events[next_phase].set()
        
        logger.info(f"[{self.scan_id}] Advanced to phase: {next_phase}")
        return True
    
    async def wait_for_phase(self, phase: ScanPhase, timeout: Optional[float] = None):
        """
        Block until the specified phase is reached.
        Raises asyncio.TimeoutError if timeout is exceeded.
        """
        if timeout:
            await asyncio.wait_for(
                self.phase_events[phase].wait(),
                timeout=timeout
            )
        else:
            await self.phase_events[phase].wait()
    
    def is_phase_active(self, phase: ScanPhase) -> bool:
        """Check if a specific phase is currently active"""
        return self.current_phase == phase
    
    def is_phase_complete(self, phase: ScanPhase) -> bool:
        """Check if a specific phase has completed"""
        return self.phase_events[phase].is_set() and self.phase_end_times[phase] is not None
    
    def get_phase_duration(self, phase: ScanPhase) -> Optional[float]:
        """Get the duration of a completed phase in seconds"""
        if not self.is_phase_complete(phase):
            return None
        
        start = self.phase_start_times[phase]
        end = self.phase_end_times[phase]
        
        if start and end:
            return (end - start).total_seconds()
        return None
    
    def get_telemetry(self) -> dict:
        """Get phase gate telemetry for reporting"""
        return {
            "scan_id": self.scan_id,
            "current_phase": self.current_phase,
            "phase_durations": {
                phase.value: self.get_phase_duration(phase)
                for phase in ScanPhase
                if self.get_phase_duration(phase) is not None
            },
            "phases_completed": [
                phase.value for phase in ScanPhase
                if self.is_phase_complete(phase)
            ]
        }
