import asyncio
import aiohttp
from backend.core.hive import EventType, HiveEvent
from backend.core.browser_agent import BrowserEnabledAgent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, ModuleConfig, TaskTarget
from backend.core.config import settings
from backend.core.content_boundary import content_boundary
from backend.core.proxy import network_interceptor
from backend.agents.alpha_v6 import AlphaOrchestrator

# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.queue import command_lane

class AlphaAgent(BrowserEnabledAgent):
    """
    AGENT ALPHA: THE SCOUT
    Role: Real-time Recon & API Detection with Hybrid Browser Capabilities.
    Now performs HTTP + Browser reconnaissance against targets.
    
    Browser Capabilities:
    - Deep SPA endpoint discovery (React/Vue/Angular)
    - JavaScript route extraction
    - Framework detection
    - Network interception (XHR/Fetch)
    - WebSocket discovery
    """
    def __init__(self, bus):
        super().__init__("agent_alpha", bus)
        # Hybrid AI Engine for intelligent classification
        self.cortex = get_cortex_engine()
        self.MAX_CRAWL_DEPTH = 5
        self._session = None
        self.alpha_recon = AlphaOrchestrator(bus, agent_name=self.name)
        
        # Browser Integration inherited from BrowserEnabledAgent
        # self.browser, self.session_manager, self.forensics available via properties

    async def setup(self):
        # Listen for assigned jobs
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)
        # Listen for target acquired to do direct recon
        self.bus.subscribe(EventType.TARGET_ACQUIRED, self.handle_target_acquired)

    async def handle_target_acquired(self, event: HiveEvent):
        """React to new targets by performing real HTTP + Browser recon."""
        target_url = event.payload.get("url")
        if not target_url:
            return

        if event.source == "Orchestrator" and getattr(settings, "ALPHA_RECON_VIA_PLANNER", True):
            print(f"[{self.name}] Target received; waiting for Mission Planner recon assignment.")
            return
        
        print(f"[{self.name}] TARGET ACQUIRED: {target_url}. Initiating hybrid recon...")
        
        # Broadcast recon start
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            payload={"url": target_url, "arsenal": "Hybrid Recon Engine", "action": "Initiating HTTP + Browser Recon", "payload": "N/A"}
        ))
        
        # Check if this is a SPA that needs browser-based recon
        is_spa = await self._detect_spa(target_url)
        
        if is_spa:
            print(f"[{self.name}] SPA DETECTED: {target_url}. Engaging browser-based reconnaissance...")
            await self._browser_recon(target_url, event.scan_id)
        
        if getattr(settings, "ALPHA_ENABLE_V6", True):
            try:
                mode = event.payload.get("scan_mode") or event.payload.get("mode") or getattr(settings, "ALPHA_DEFAULT_MODE", "STANDARD")
                await self.alpha_recon.run(target_url, scan_id=event.scan_id, mode=mode)
                return
            except Exception as exc:
                print(f"[{self.name}] Alpha V6 recon failed: {exc}")
    
    async def _detect_spa(self, url: str) -> bool:
        """Detect if target is a Single Page Application."""
        try:
            # Quick heuristic: check for common SPA frameworks
            result = await self.browser.navigate(url, stealth=False, wait_for="networkidle")
            
            if not result.get("success"):
                return False
            
            # Check for framework indicators
            framework = await self.browser.detect_framework(url)
            framework_name = str(framework or "").lower()
            
            is_spa = framework_name in ["react", "vue", "angular", "svelte"]
            
            if is_spa:
                print(f"[{self.name}] Framework detected: {framework_name.upper()}")
            
            return is_spa
            
        except Exception as e:
            if "No browser engines available" in str(e):
                print(f"[{self.name}] SPA detection skipped: browser engines unavailable; continuing Alpha V6 HTTP recon.")
            else:
                print(f"[{self.name}] SPA detection failed: {e}")
            return False
    
    async def _browser_recon(self, url: str, scan_id: str):
        """Perform deep browser-based reconnaissance on SPA."""
        try:
            print(f"[{self.name}] Starting browser reconnaissance on {url}")
            
            # 1. Extract endpoints using deep mode (JavaScript analysis)
            endpoints = await self.browser.extract_endpoints(url, deep=True)
            
            print(f"[{self.name}] Discovered {len(endpoints)} endpoints via browser analysis")
            
            # 2. Intercept network traffic
            network_events = await self._intercept_network(url)
            
            # 3. Find WebSockets
            websockets = await self._find_websockets(url)
            
            # 4. Extract JS routes
            js_routes = await self._extract_js_routes(url)
            
            # 5. Merge all discovered endpoints
            all_endpoints = self._merge_endpoints(endpoints, network_events, js_routes, websockets)
            
            print(f"[{self.name}] Total unique endpoints discovered: {len(all_endpoints)}")
            
            # 6. Publish findings
            for endpoint in all_endpoints:
                await self.bus.publish(HiveEvent(
                    type=EventType.RECON_PACKET,
                    source=self.name,
                    scan_id=scan_id,
                    payload={
                        "url": endpoint.get("url"),
                        "method": endpoint.get("method", "GET"),
                        "source": endpoint.get("source", "browser"),
                        "severity": "INFO",
                        "risk_score": 10
                    }
                ))
            
            # 7. Capture forensic evidence
            await self.forensics.capture_screenshot(
                scan_id=scan_id,
                context=None,  # Would need actual page context
                engine="openclaw",
                label="spa_recon"
            )
            
        except Exception as e:
            print(f"[{self.name}] Browser recon failed: {e}")
    
    async def _extract_js_routes(self, url: str) -> list:
        """Extract routes from JavaScript router (React Router, Vue Router, etc.)."""
        try:
            # Use OpenClaw to execute JS and extract routes
            result = await self.browser.navigate(url, stealth=False, wait_for="networkidle")
            
            if not result.get("success"):
                return []
            
            # Detect framework first
            framework = await self.browser.detect_framework(url)
            
            routes = []
            
            if framework == "React":
                # Extract React Router routes
                react_routes = await self.browser.openclaw.current_page.evaluate("""() => {
                    const routes = [];
                    // Check for React Router v6
                    if (window.__REACT_ROUTER__) {
                        const router = window.__REACT_ROUTER__;
                        if (router.routes) {
                            router.routes.forEach(r => {
                                if (r.path) routes.push({url: r.path, method: "GET", source: "react_router"});
                            });
                        }
                    }
                    // Check for older versions via DOM
                    document.querySelectorAll('[data-route]').forEach(el => {
                        const path = el.getAttribute('data-route');
                        if (path) routes.push({url: path, method: "GET", source: "react_dom"});
                    });
                    return routes;
                }""")
                routes.extend(react_routes)
                
            elif framework == "Vue":
                # Extract Vue Router routes
                vue_routes = await self.browser.openclaw.current_page.evaluate("""() => {
                    const routes = [];
                    if (window.$router && window.$router.options) {
                        const routerRoutes = window.$router.options.routes || [];
                        routerRoutes.forEach(r => {
                            if (r.path) routes.push({url: r.path, method: "GET", source: "vue_router"});
                        });
                    }
                    return routes;
                }""")
                routes.extend(vue_routes)
                
            elif framework == "Angular":
                # Extract Angular routes
                angular_routes = await self.browser.openclaw.current_page.evaluate("""() => {
                    const routes = [];
                    if (window.ng && window.ng.probe) {
                        // Angular route extraction
                        const allRoutes = window.ng.probe.getAllRoutes?.() || [];
                        allRoutes.forEach(r => {
                            if (r.path) routes.push({url: r.path, method: "GET", source: "angular_router"});
                        });
                    }
                    return routes;
                }""")
                routes.extend(angular_routes)
            
            print(f"[{self.name}] Extracted {len(routes)} routes from {framework} router")
            return routes
            
        except Exception as e:
            print(f"[{self.name}] JS route extraction failed: {e}")
            return []
    
    async def _intercept_network(self, url: str) -> list:
        """Intercept XHR/Fetch requests to discover API endpoints."""
        try:
            # Use OpenClaw's network interception
            network_events = await self.browser.intercept_network(url)
            
            # Transform to standard format
            endpoints = []
            for event in network_events:
                endpoints.append({
                    "url": event.get("url"),
                    "method": event.get("method", "GET"),
                    "source": "network_intercept",
                    "headers": event.get("headers", {})
                })
            
            print(f"[{self.name}] Intercepted {len(endpoints)} network requests")
            return endpoints
            
        except Exception as e:
            print(f"[{self.name}] Network interception failed: {e}")
            return []
    
    async def _find_websockets(self, url: str) -> list:
        """Discover WebSocket connections."""
        try:
            # Use OpenClaw to monitor WebSocket connections
            ws_urls = await self.browser.find_websockets(url)
            
            # Transform to standard format
            websockets = []
            for ws_url in ws_urls:
                websockets.append({
                    "url": ws_url,
                    "method": "WS",
                    "source": "websocket_monitor"
                })
            
            print(f"[{self.name}] Discovered {len(websockets)} WebSocket connections")
            return websockets
            
        except Exception as e:
            print(f"[{self.name}] WebSocket discovery failed: {e}")
            return []
    
    async def _merge_endpoints(self, *endpoint_lists) -> list:
        """Merge and deduplicate endpoints from multiple sources."""
        seen = set()
        merged = []
        
        for endpoint_list in endpoint_lists:
            for endpoint in endpoint_list:
                url = endpoint.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    merged.append(endpoint)
        
        return merged

    async def handle_job(self, event: HiveEvent):
        """
        Process incoming job.
        """
        payload = event.payload
        try:
            packet = JobPacket(**payload)
        except Exception as e:
            print(f"[{self.name}] Error parsing job: {e}")
            return

        # Am I the target?
        if packet.config.agent_id != AgentID.ALPHA:
            return

        if packet.config.module_id == "alpha_v6_recon":
            params = packet.config.params or {}
            mode = (
                params.get("scan_mode")
                or params.get("mode")
                or getattr(settings, "ALPHA_DEFAULT_MODE", "STANDARD")
            )
            print(f"[{self.name}] Planner assigned Alpha V6 recon on {packet.target.url} (mode={mode}).")
            try:
                await self.alpha_recon.run(packet.target.url, scan_id=event.scan_id, mode=mode)
                await self.bus.publish(HiveEvent(
                    type=EventType.JOB_COMPLETED,
                    source=self.name,
                    scan_id=event.scan_id,
                    payload={"job_id": packet.id, "status": "SUCCESS", "module_id": packet.config.module_id}
                ))
            except Exception as exc:
                print(f"[{self.name}] Planner-assigned Alpha V6 recon failed: {exc}")
                await self.bus.publish(HiveEvent(
                    type=EventType.JOB_COMPLETED,
                    source=self.name,
                    scan_id=event.scan_id,
                    payload={
                        "job_id": packet.id,
                        "status": "FAILED",
                        "module_id": packet.config.module_id,
                        "error": str(exc)[:300],
                    }
                ))
            return

        # ELE-ST FIX 1: Infinite Recursion Deadlock Prevention
        url_lower = packet.target.url.lower()
        from urllib.parse import urlparse
        path = urlparse(url_lower).path
        depth = len([p for p in path.split('/') if p])
        
        if depth > self.MAX_CRAWL_DEPTH:
            print(f"[{self.name}] [STOP] MAX_CRAWL_DEPTH ({self.MAX_CRAWL_DEPTH}) exceeded for {url_lower}. Dropping.")
            return
            
        ctx = self.bus.get_or_create_context(event.scan_id)
        if "visited_urls" not in ctx.baseline_cache:
            ctx.baseline_cache["visited_urls"] = set()
            
        if url_lower in ctx.baseline_cache["visited_urls"]:
            return
            
        ctx.baseline_cache["visited_urls"].add(url_lower)

        print(f"[{self.name}] Received Job {packet.id} ({packet.config.module_id})")
        
        # 1. HYBRID AI: Intelligent Target Classification
        classification = await self.cortex.classify_target(packet.target.url)
        is_api = classification.get("is_api", False)
        
        # Fallback: Hardcoded indicators still checked
        api_indicators = ["/api", "/v1", "graphql", "swagger"]
        if any(ind in url_lower for ind in api_indicators):
            is_api = True
        
        # HYBRID: Flag typosquatting domains at recon stage
        if "TYPOSQUATTING" in classification.get("tags", []):
            print(f"[{self.name}]: TYPOSQUATTING DOMAIN DETECTED by GI5. Flagging as HIGH PRIORITY.")
        
        # PROTOCAL AWARENESS: Force scan for local files
        if url_lower.startswith("file:///"):
            is_api = True
            print(f"[{self.name}]: LOCAL FILE DETECTED. Forcing Singularity V5 Analysis.")
        
        if is_api:
            print(f"[{self.name}]: API/Local Target DETECTED. Dispatching Handover.")
            
            # [NEW] Publish RECON_PACKET so dashboard shows active finding
            await self.bus.publish(HiveEvent(
                type=EventType.RECON_PACKET,
                source=self.name,
                payload={
                    "url": packet.target.url,
                    "severity": "INFO",
                    "risk_score": 10
                }
            ))
            
            # BROADCAST SCAN PROGRESS
            await self.bus.publish(HiveEvent(
                type=EventType.LIVE_ATTACK,
                source=self.name,
                payload={
                    "url": packet.target.url,
                    "arsenal": "Recon Engine",
                    "action": "Mapping API endpoint structure",
                    "payload": "N/A (Structural discovery)"
                }
            ))
            
            # Real implementation: Publish a VULN_CANDIDATE event that Beta listens to
            await self.bus.publish(HiveEvent(
                type=EventType.VULN_CANDIDATE,
                source=self.name,
                payload={"url": packet.target.url, "tag": "API"}
            ))

        # Cyber-Organism Protocol: Target Acquisition
        # DATA WIRING: Respect "filters" from Mission Config
        filters = getattr(self, "mission_config", {}).get("filters", [])
        
        # Default sensitive paths
        sensitive_paths = ["/order", "/user", "/account", "/profile"]
        
        # Extend sensitivity based on filters
        if "Financial Logic" in filters:
            sensitive_paths.extend(["/pay", "/wallet", "/invoice", "/cart"])
        if "Auth & Session" in filters:
            sensitive_paths.extend(["/login", "/token", "/oauth", "/sso"])
        if "PII Data" in filters:
            sensitive_paths.extend(["/me", "/settings", "/export", "/gdpr"])

        if any(p in packet.target.url.lower() for p in sensitive_paths):
            print(f"[{self.name}]: [TARGET] Priority Target Acquired ({filters}). Tagging for Doppelganger.")
            
            await self.bus.publish(HiveEvent(
                type=EventType.TARGET_ACQUIRED,
                source=self.name,
                payload={"url": packet.target.url, "method": "POST"}
            ))
            await self.bus.publish(HiveEvent(
                type=EventType.VULN_CANDIDATE,
                source=self.name,
                payload={"url": packet.target.url, "tag": "DOPPELGANGER_CANDIDATE"}
            ))

        # 2. Execute Module via Sigma
        print(f"[{self.name}] Delegating {packet.config.module_id} to SIGMA Orchestrator on {packet.target.url}")
        
        sigma_job = JobPacket(
            priority=packet.priority,
            target=packet.target,
            config=ModuleConfig(
                module_id=packet.config.module_id, 
                agent_id=AgentID.SIGMA, 
                params=packet.config.params,
                aggression=packet.config.aggression,
                session_id=packet.config.session_id
            )
        )
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source=self.name,
            payload=sigma_job.model_dump()
        ))
