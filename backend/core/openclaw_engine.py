"""
OpenClawEngine: Deep browser automation using OpenClaw.

Provides advanced capabilities:
- Multi-step workflows
- Stealth mode (human-like behavior)
- Deep JavaScript analysis
- Network interception
- Session management
"""

import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from backend.core.config import settings


class OpenClawEngine:
    """Deep browser automation using OpenClaw framework"""
    
    def __init__(self):
        self.client = None
        self.workflow_engine = None
        self.active_contexts = {}
        self.current_page = None
        self.current_context = None
        
    async def initialize(self):
        """Initialize OpenClaw client"""
        try:
            # Import OpenClaw
            from openclaw import ClawClient
            
            self.client = ClawClient()
            await self.client.initialize()
            
            print("[OpenClawEngine] OpenClaw client initialized")
            return True
        except ImportError:
            print("[OpenClawEngine] OpenClaw not installed. Install with: pip install openclaw")
            return False
        except Exception as e:
            print(f"[OpenClawEngine] Initialization failed: {e}")
            return False
            
    async def navigate(self, url: str, stealth: bool = False, wait_for: str = "networkidle"):
        """
        Navigate to URL with OpenClaw.
        
        Args:
            url: Target URL
            stealth: Enable stealth mode (human-like behavior)
            wait_for: Wait condition (networkidle, load, domcontentloaded)
            
        Returns:
            Navigation result with context and page
        """
        if not self.client:
            raise RuntimeError("OpenClaw not initialized")
            
        # Create browser context
        context = await self.client.create_context(
            headless=getattr(settings, "OPENCLAW_HEADLESS", True),
            stealth=stealth or getattr(settings, "OPENCLAW_STEALTH_MODE", False)
        )
        
        # Create new page
        page = await context.new_page()
        
        # Navigate
        await page.goto(url, wait_until=wait_for)
        
        # Store references
        self.current_context = context
        self.current_page = page
        
        return {
            "context": context,
            "page": page,
            "url": url,
            "success": True
        }
        
    async def extract_endpoints_deep(self, url: str) -> List[str]:
        """
        Deep endpoint extraction with JavaScript analysis.
        
        Extracts endpoints from:
        - window.location
        - fetch() calls
        - XMLHttpRequest
        - React Router
        - Vue Router
        - Angular routes
        """
        result = await self.navigate(url)
        page = result["page"]
        
        # Install network interceptors and extract endpoints
        endpoints = await page.evaluate("""() => {
            const endpoints = new Set();
            
            // Intercept fetch
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                if (args[0]) endpoints.add(args[0].toString());
                return originalFetch.apply(this, args);
            };
            
            // Intercept XHR
            const originalOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url) {
                if (url) endpoints.add(url.toString());
                return originalOpen.apply(this, arguments);
            };
            
            // Extract from React Router
            if (window.__REACT_ROUTER__) {
                const routes = window.__REACT_ROUTER__.routes || [];
                routes.forEach(r => {
                    if (r.path) endpoints.add(r.path);
                });
            }
            
            // Extract from Vue Router
            if (window.$router && window.$router.options) {
                const routes = window.$router.options.routes || [];
                routes.forEach(r => {
                    if (r.path) endpoints.add(r.path);
                });
            }
            
            // Extract from Angular
            if (window.ng && window.ng.probe) {
                // Angular route extraction logic
            }
            
            // Extract from href attributes
            const links = document.querySelectorAll('a[href]');
            links.forEach(link => {
                const href = link.getAttribute('href');
                if (href && (href.startsWith('/') || href.startsWith('http'))) {
                    endpoints.add(href);
                }
            });
            
            // Extract from script tags (API endpoints in JS)
            const scripts = document.querySelectorAll('script');
            scripts.forEach(script => {
                const content = script.textContent || '';
                // Match API-like patterns
                const apiMatches = content.match(/['"](/api/[^'"]+)['"]/g) || [];
                apiMatches.forEach(match => {
                    endpoints.add(match.replace(/['"]/g, ''));
                });
            });
            
            return Array.from(endpoints);
        }""")
        
        return endpoints
        
    async def execute_workflow(self, workflow: Dict, scan_id: str):
        """
        Execute multi-step workflow.
        
        Workflow format:
        {
            "name": "Login and Exploit",
            "steps": [
                {"action": "navigate", "url": "https://example.com/login"},
                {"action": "fill", "selector": "#username", "value": "admin"},
                {"action": "fill", "selector": "#password", "value": "password"},
                {"action": "click", "selector": "#submit"},
                {"action": "wait", "condition": "networkidle"},
                {"action": "navigate", "url": "https://example.com/admin"},
                {"action": "extract", "selector": ".secret-data"}
            ]
        }
        """
        if not self.current_page:
            raise RuntimeError("No active page. Call navigate() first.")
            
        page = self.current_page
        results = []
        
        for step in workflow.get("steps", []):
            action = step.get("action")
            
            try:
                if action == "navigate":
                    await page.goto(step["url"])
                    results.append({"step": action, "success": True})
                    
                elif action == "fill":
                    await page.fill(step["selector"], step["value"])
                    results.append({"step": action, "selector": step["selector"], "success": True})
                    
                elif action == "click":
                    await page.click(step["selector"])
                    results.append({"step": action, "selector": step["selector"], "success": True})
                    
                elif action == "wait":
                    condition = step.get("condition", "networkidle")
                    if condition == "networkidle":
                        await page.wait_for_load_state("networkidle")
                    else:
                        await asyncio.sleep(step.get("duration", 1))
                    results.append({"step": action, "success": True})
                    
                elif action == "extract":
                    data = await page.query_selector(step["selector"])
                    text = await data.text_content() if data else None
                    results.append({"step": action, "selector": step["selector"], "data": text, "success": True})
                    
            except Exception as e:
                results.append({"step": action, "success": False, "error": str(e)})
                if not step.get("continue_on_error", False):
                    break
                    
        return {"workflow": workflow["name"], "results": results}
        
    async def test_xss_payload(self, url: str, payload: str):
        """
        Test XSS payload in real browser context.
        
        Returns indicators of exploitation:
        - alert_triggered: Did alert() fire?
        - dom_modified: Was DOM modified?
        - console_errors: Any console errors?
        """
        result = await self.navigate(url)
        page = result["page"]
        
        # Install alert detector
        await page.evaluate("""() => {
            window.alertFired = false;
            window.originalAlert = window.alert;
            window.alert = function() {
                window.alertFired = true;
                return window.originalAlert.apply(this, arguments);
            };
        }""")
        
        # Get baseline DOM
        dom_before = await page.content()
        
        # Inject payload
        try:
            await page.evaluate(f"document.body.innerHTML += `{payload}`")
        except Exception as e:
            # Payload might have caused error (good sign)
            pass
            
        # Check if alert fired
        alert_fired = await page.evaluate("window.alertFired || false")
        
        # Check DOM modification
        dom_after = await page.content()
        dom_modified = dom_before != dom_after and payload in dom_after
        
        # Check console errors
        console_errors = []  # Would need to set up console listener
        
        return {
            "alert_triggered": alert_fired,
            "dom_modified": dom_modified,
            "console_errors": console_errors,
            "exploited": alert_fired or dom_modified,
            "payload": payload
        }
        
    async def detect_framework(self, url: str) -> Optional[str]:
        """Detect JavaScript framework"""
        result = await self.navigate(url)
        page = result["page"]
        
        framework = await page.evaluate("""() => {
            if (window.React || document.querySelector('[data-reactroot]')) return 'React';
            if (window.Vue || document.querySelector('[data-v-]')) return 'Vue';
            if (window.angular || document.querySelector('[ng-app]')) return 'Angular';
            if (window.Ember) return 'Ember';
            if (window.Backbone) return 'Backbone';
            return null;
        }""")
        
        return framework
        
    async def intercept_network(self, url: str) -> List[Dict]:
        """Intercept and log network requests"""
        result = await self.navigate(url)
        page = result["page"]
        
        requests = []
        
        # Set up request listener
        async def handle_request(request):
            requests.append({
                "url": request.url,
                "method": request.method,
                "headers": request.headers,
                "post_data": request.post_data
            })
            
        page.on("request", handle_request)
        
        # Wait for network activity
        await page.wait_for_load_state("networkidle")
        
        return requests
        
    async def find_websockets(self, url: str) -> List[str]:
        """Find WebSocket connections"""
        result = await self.navigate(url)
        page = result["page"]
        
        websockets = await page.evaluate("""() => {
            const ws = [];
            const originalWebSocket = window.WebSocket;
            window.WebSocket = function(url) {
                ws.push(url);
                return new originalWebSocket(url);
            };
            return ws;
        }""")
        
        return websockets
        
    async def extract_tokens(self, url: str) -> List[str]:
        """Extract auth tokens from page"""
        result = await self.navigate(url)
        page = result["page"]
        
        # Get page content
        content = await page.content()
        
        # Extract JWT tokens
        import re
        jwt_pattern = r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
        tokens = re.findall(jwt_pattern, content)
        
        # Extract from localStorage
        local_storage = await page.evaluate("() => Object.entries(localStorage)")
        for key, value in local_storage:
            if 'token' in key.lower() or 'auth' in key.lower():
                tokens.append(value)
                
        return list(set(tokens))
        
    async def capture_screenshot(self, scan_id: str, label: str) -> Path:
        """Capture screenshot"""
        if not self.current_page:
            return None
            
        screenshot_dir = Path("reports/forensics")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scan_id}_{label}_{timestamp}.png"
        filepath = screenshot_dir / filename
        
        await self.current_page.screenshot(path=str(filepath), full_page=True)
        return filepath
        
    async def capture_dom(self, scan_id: str, label: str) -> Path:
        """Capture DOM snapshot"""
        if not self.current_page:
            return None
            
        dom_dir = Path("reports/forensics")
        dom_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scan_id}_{label}_{timestamp}.html"
        filepath = dom_dir / filename
        
        content = await self.current_page.content()
        filepath.write_text(content, encoding="utf-8")
        return filepath
        
    async def get_network_log(self) -> List[Dict]:
        """Get network request log"""
        # Would need to set up network listener during navigation
        return []
        
    async def get_page_text(self) -> str:
        """Get page text content"""
        if not self.current_page:
            return ""
            
        return await self.current_page.text_content("body")
        
    async def close(self):
        """Close all contexts and cleanup"""
        if self.current_context:
            await self.current_context.close()
            self.current_context = None
            self.current_page = None
            
        for context in self.active_contexts.values():
            try:
                await context.close()
            except:
                pass
                
        self.active_contexts.clear()
