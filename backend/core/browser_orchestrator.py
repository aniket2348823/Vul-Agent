"""
BrowserOrchestrator: Unified browser automation interface.

This module provides a single API that intelligently routes between:
- OpenClaw: Deep automation, multi-step workflows, stealth mode
- PinchTab: Fast DOM scraping, token extraction, lightweight operations

All agents use this unified interface for browser capabilities.
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Union
import asyncio
from pathlib import Path

from backend.core.config import settings


class BrowserEngine(Enum):
    """Browser engine selection"""
    OPENCLAW = "openclaw"      # Deep automation, workflows, stealth
    PINCHTAB = "pinchtab"      # Fast scraping, token extraction
    AUTO = "auto"              # Intelligent selection


class BrowserOrchestrator:
    """
    Unified browser interface that routes between OpenClaw and PinchTab.
    Provides a single API for all agents to use browser capabilities.
    
    Usage:
        browser = BrowserOrchestrator()
        await browser.initialize()
        
        # Auto-select engine
        await browser.navigate("https://example.com")
        
        # Force specific engine
        await browser.navigate("https://example.com", engine=BrowserEngine.OPENCLAW)
    """
    
    def __init__(self):
        self.openclaw = None
        self.pinchtab = None
        self.session_manager = None
        self.forensics = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize both browser engines"""
        if self._initialized:
            return
            
        print("[BrowserOrchestrator] Initializing hybrid browser stack...")
        
        # Initialize OpenClaw if enabled
        if getattr(settings, "OPENCLAW_ENABLED", True):
            try:
                from backend.core.openclaw_engine import OpenClawEngine
                self.openclaw = OpenClawEngine()
                await self.openclaw.initialize()
                print("[BrowserOrchestrator] ✓ OpenClaw initialized")
            except Exception as e:
                print(f"[BrowserOrchestrator] ✗ OpenClaw initialization failed: {e}")
                self.openclaw = None
                
        # Initialize PinchTab if enabled
        if getattr(settings, "PINCHTAB_ENABLED", True):
            try:
                from backend.core.pinchtab_engine import PinchTabEngine
                self.pinchtab = PinchTabEngine()
                await self.pinchtab.initialize()
                print("[BrowserOrchestrator] ✓ PinchTab initialized")
            except Exception as e:
                print(f"[BrowserOrchestrator] ✗ PinchTab initialization failed: {e}")
                self.pinchtab = None
                
        # Initialize session manager
        from backend.core.hybrid_session_manager import HybridSessionManager
        self.session_manager = HybridSessionManager()
        
        # Initialize forensics collector
        from backend.core.forensic_collector import ForensicCollector
        self.forensics = ForensicCollector()
        
        self._initialized = True
        print("[BrowserOrchestrator] Hybrid browser stack ready")
        
    async def navigate(self, url: str, engine: BrowserEngine = BrowserEngine.AUTO,
                      stealth: bool = False, wait_for: str = "networkidle",
                      scan_id: Optional[str] = None):
        """
        Navigate to URL using best engine for the task.
        
        Args:
            url: Target URL
            engine: Browser engine to use (AUTO, OPENCLAW, PINCHTAB)
            stealth: Enable stealth mode (human-like behavior)
            wait_for: Wait condition (networkidle, load, domcontentloaded)
            scan_id: Scan ID for session management
            
        Returns:
            Navigation result with context/page references
            
        AUTO mode logic:
        - Use PinchTab for: Simple DOM scraping, token extraction, fast recon
        - Use OpenClaw for: Complex workflows, stealth mode, multi-step attacks
        """
        await self._ensure_initialized()
        
        selected_engine = self._select_engine(engine, stealth, url)
        
        print(f"[BrowserOrchestrator] Navigating to {url} via {selected_engine.value}")
        
        if selected_engine == BrowserEngine.PINCHTAB and self.pinchtab:
            return await self.pinchtab.navigate(url)
        elif selected_engine == BrowserEngine.OPENCLAW and self.openclaw:
            return await self.openclaw.navigate(url, stealth=stealth, wait_for=wait_for)
        else:
            # Fallback
            if self.openclaw:
                return await self.openclaw.navigate(url, stealth=stealth, wait_for=wait_for)
            elif self.pinchtab:
                return await self.pinchtab.navigate(url)
            else:
                raise RuntimeError("No browser engines available")
                
    async def extract_endpoints(self, url: str, deep: bool = False, scan_id: Optional[str] = None):
        """
        Extract API endpoints from page.
        
        Args:
            url: Target URL
            deep: Use deep analysis (OpenClaw) vs fast extraction (PinchTab)
            scan_id: Scan ID for tracking
            
        Returns:
            List of discovered endpoints
        """
        await self._ensure_initialized()
        
        if deep and self.openclaw:
            print(f"[BrowserOrchestrator] Deep endpoint extraction on {url}")
            return await self.openclaw.extract_endpoints_deep(url)
        elif self.pinchtab:
            print(f"[BrowserOrchestrator] Fast endpoint extraction on {url}")
            return await self.pinchtab.extract_endpoints_fast(url)
        else:
            return []
            
    async def execute_workflow(self, workflow: Dict, scan_id: str):
        """
        Execute multi-step workflow (OpenClaw only).
        
        Args:
            workflow: Workflow definition with steps
            scan_id: Scan ID for tracking
            
        Returns:
            Workflow execution results
        """
        await self._ensure_initialized()
        
        if not self.openclaw:
            raise RuntimeError("OpenClaw required for workflow execution")
            
        print(f"[BrowserOrchestrator] Executing workflow: {workflow.get('name', 'unnamed')}")
        return await self.openclaw.execute_workflow(workflow, scan_id)
        
    async def extract_tokens(self, url: str, scan_id: Optional[str] = None):
        """
        Extract auth tokens (PinchTab optimized).
        
        Args:
            url: Target URL
            scan_id: Scan ID for tracking
            
        Returns:
            List of extracted tokens (JWT, Bearer, etc.)
        """
        await self._ensure_initialized()
        
        if self.pinchtab:
            print(f"[BrowserOrchestrator] Extracting tokens from {url}")
            return await self.pinchtab.extract_tokens(url)
        elif self.openclaw:
            # Fallback to OpenClaw
            return await self.openclaw.extract_tokens(url)
        else:
            return []
            
    async def test_payload(self, url: str, payload: str, method: str = "GET",
                          scan_id: Optional[str] = None):
        """
        Test payload in browser context.
        Auto-selects engine based on payload type.
        
        Args:
            url: Target URL
            payload: Attack payload to test
            method: HTTP method
            scan_id: Scan ID for tracking
            
        Returns:
            Test results with exploitation indicators
        """
        await self._ensure_initialized()
        
        # XSS payloads need real browser execution
        if any(x in payload.lower() for x in ["<script", "onerror", "onclick", "onload", "alert"]):
            if self.openclaw:
                print(f"[BrowserOrchestrator] Testing XSS payload in OpenClaw")
                return await self.openclaw.test_xss_payload(url, payload)
                
        # Simple injection can use fast mode
        if self.pinchtab:
            print(f"[BrowserOrchestrator] Testing injection in PinchTab")
            return await self.pinchtab.test_injection(url, payload, method)
        elif self.openclaw:
            return await self.openclaw.test_xss_payload(url, payload)
        else:
            return {"tested": False, "error": "No engines available"}
            
    async def detect_framework(self, url: str):
        """Detect JavaScript framework (React/Vue/Angular)"""
        await self._ensure_initialized()
        
        if self.openclaw:
            return await self.openclaw.detect_framework(url)
        return None
        
    async def intercept_network(self, url: str):
        """Intercept network requests (XHR/Fetch)"""
        await self._ensure_initialized()
        
        if self.openclaw:
            return await self.openclaw.intercept_network(url)
        return []
        
    async def find_websockets(self, url: str):
        """Find WebSocket connections"""
        await self._ensure_initialized()
        
        if self.openclaw:
            return await self.openclaw.find_websockets(url)
        return []
        
    async def capture_screenshot(self, scan_id: str, label: str = "screenshot"):
        """Capture screenshot for forensic evidence"""
        await self._ensure_initialized()
        
        if self.openclaw:
            return await self.openclaw.capture_screenshot(scan_id, label)
        return None
        
    async def capture_dom(self, scan_id: str, label: str = "dom"):
        """Capture DOM snapshot"""
        await self._ensure_initialized()
        
        if self.openclaw:
            return await self.openclaw.capture_dom(scan_id, label)
        return None
        
    async def get_network_log(self):
        """Get network request log"""
        await self._ensure_initialized()
        
        if self.openclaw:
            return await self.openclaw.get_network_log()
        return []
        
    async def analyze_dom(self, url: str):
        """Analyze DOM structure (forms, inputs, etc.)"""
        await self._ensure_initialized()
        
        if self.pinchtab:
            return await self.pinchtab.analyze_dom(url)
        return {}
        
    async def get_page_text(self):
        """Get page text content"""
        await self._ensure_initialized()
        
        if self.pinchtab:
            return await self.pinchtab.get_page_text()
        elif self.openclaw:
            return await self.openclaw.get_page_text()
        return ""
        
    def _select_engine(self, requested: BrowserEngine, stealth: bool, url: str) -> BrowserEngine:
        """
        Intelligent engine selection based on requirements.
        
        Selection logic:
        - If specific engine requested, use it (if available)
        - If stealth mode, prefer OpenClaw
        - If auth/login URL, prefer OpenClaw (needs session handling)
        - Otherwise, prefer PinchTab for speed
        """
        # Honor explicit request
        if requested != BrowserEngine.AUTO:
            if requested == BrowserEngine.OPENCLAW and self.openclaw:
                return BrowserEngine.OPENCLAW
            elif requested == BrowserEngine.PINCHTAB and self.pinchtab:
                return BrowserEngine.PINCHTAB
                
        # Auto-selection logic
        if stealth:
            return BrowserEngine.OPENCLAW if self.openclaw else BrowserEngine.PINCHTAB
            
        # Auth/login pages need OpenClaw for session management
        if any(keyword in url.lower() for keyword in ["login", "auth", "signin", "oauth"]):
            return BrowserEngine.OPENCLAW if self.openclaw else BrowserEngine.PINCHTAB
            
        # Check user preference
        prefer_speed = getattr(settings, "BROWSER_PREFER_SPEED", False)
        if prefer_speed and self.pinchtab:
            return BrowserEngine.PINCHTAB
            
        # Default: prefer OpenClaw for depth, fallback to PinchTab
        if self.openclaw:
            return BrowserEngine.OPENCLAW
        elif self.pinchtab:
            return BrowserEngine.PINCHTAB
        else:
            return BrowserEngine.OPENCLAW  # Will fail gracefully
            
    async def _ensure_initialized(self):
        """Ensure orchestrator is initialized"""
        if not self._initialized:
            await self.initialize()
            
    async def close(self):
        """Cleanup and close all browser engines"""
        print("[BrowserOrchestrator] Closing browser engines...")
        
        if self.openclaw:
            await self.openclaw.close()
            
        if self.pinchtab:
            await self.pinchtab.close()
            
        self._initialized = False
        print("[BrowserOrchestrator] Closed")


# Global instance for easy access
_browser_orchestrator = None


def get_browser_orchestrator() -> BrowserOrchestrator:
    """Get global BrowserOrchestrator instance"""
    global _browser_orchestrator
    if _browser_orchestrator is None:
        _browser_orchestrator = BrowserOrchestrator()
    return _browser_orchestrator
