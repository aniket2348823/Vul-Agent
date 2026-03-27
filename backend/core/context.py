import asyncio
import uuid
from typing import Dict, Any, Set

class ScanContext:
    def __init__(self, scan_id: str = None):
        self.scan_id = scan_id or str(uuid.uuid4())
        
        # 1. State Isolation Barriers (Fixes Invariant 8: Cross-Scan Bleed)
        self.baseline_cache: Dict[str, Any] = {}
        self.diff_cache: Dict[str, Any] = {}
        self.workflow_state: Dict[str, Any] = {}
        
        # 2. Causal Ordering (Fixes Invariant 21)
        self.event_queue = asyncio.Queue()
        
        # 3. Deduplication Window (Fixes Invariant 7)
        self._recent_events: Set[str] = set()
        
        # 4. Cancellation Propagation (Fixes Invariant 24)
        self.is_cancelled: bool = False
