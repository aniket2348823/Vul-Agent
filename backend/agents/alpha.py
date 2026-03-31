import asyncio
import aiohttp
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, ModuleConfig, TaskTarget

# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

class AlphaAgent(BaseAgent):
    """
    AGENT ALPHA: THE SCOUT
    Role: Real-time Recon & API Detection.
    Now performs actual HTTP reconnaissance against targets.
    """
    def __init__(self, bus):
        super().__init__("agent_alpha", bus)
        # Hybrid AI Engine for intelligent classification
        self.cortex = get_cortex_engine()
        self.MAX_CRAWL_DEPTH = 5
        self._session = None

    async def setup(self):
        # Listen for assigned jobs
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)
        # Listen for target acquired to do direct recon
        self.bus.subscribe(EventType.TARGET_ACQUIRED, self.handle_target_acquired)

    async def handle_target_acquired(self, event: HiveEvent):
        """React to new targets by performing real HTTP recon."""
        target_url = event.payload.get("url")
        if not target_url:
            return
        
        print(f"[{self.name}] TARGET ACQUIRED: {target_url}. Initiating real-time HTTP recon...")
        
        # Broadcast recon start
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            payload={"url": target_url, "arsenal": "Recon Engine", "action": "Initiating HTTP Recon", "payload": "N/A"}
        ))
        
        # Perform real HTTP recon
        await self._real_http_recon(target_url, event.scan_id)

    async def _real_http_recon(self, target_url: str, scan_id: str = None):
        """Perform real HTTP requests to discover the target's structure and endpoints."""
        import time
        from datetime import datetime
        from backend.api.socket_manager import publish_request_event
        
        # Common paths to probe for API discovery
        common_paths = [
            "", "/api", "/api/v1", "/api/v2", "/api/health", "/api/status",
            "/swagger", "/docs", "/openapi.json", "/api-docs",
            "/graphql", "/admin", "/login", "/auth", "/token",
            "/users", "/user", "/account", "/profile", "/settings",
            "/orders", "/order", "/cart", "/payment", "/checkout",
            "/products", "/items", "/search", "/export",
            "/robots.txt", "/sitemap.xml", "/.env", "/config",
            "/wp-admin", "/wp-login.php", "/.git/config"
        ]
        
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(timeout=timeout)
            
            # Probe the main URL first
            await self._probe_url(self._session, target_url, "Main Target", scan_id=scan_id)
            
            # Parse base URL for path probing
            from urllib.parse import urlparse
            parsed = urlparse(target_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Probe common paths concurrently in batches of 5
            for i in range(0, len(common_paths), 5):
                batch = common_paths[i:i+5]
                tasks = []
                for path in batch:
                    full_url = base_url + path
                    tasks.append(self._probe_url(self._session, full_url, f"Path Discovery: {path}", scan_id=scan_id))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.1)  # Small delay between batches
                
        except Exception as e:
            print(f"[{self.name}] HTTP Recon Error: {e}")

    async def _probe_url(self, session, url: str, context: str = "", scan_id: str = None):
        """Probe a single URL and publish results."""
        import time
        from datetime import datetime
        from backend.api.socket_manager import publish_request_event
        
        start_t = time.time()
        try:
            async with session.get(url, allow_redirects=True) as resp:
                text = await resp.text()
                status = resp.status
                latency = int((time.time() - start_t) * 1000)
                
                # Classify the response
                result = "OK" if status == 200 else f"HTTP {status}"
                anomaly = False
                severity = "INFO"
                
                if status == 200:
                    text_lower = text.lower()
                    # Check for interesting content
                    if any(k in text_lower for k in ["api", "endpoint", "swagger", "openapi"]):
                        severity = "MEDIUM"
                        result = "API DISCOVERED"
                        anomaly = True
                    if any(k in text_lower for k in ["password", "secret", "token", "key", "credential"]):
                        severity = "HIGH"
                        result = "SENSITIVE DATA"
                        anomaly = True
                    if any(k in text_lower for k in ["error", "stack trace", "debug", "exception"]):
                        severity = "MEDIUM"
                        result = "INFO LEAK"
                        anomaly = True
                
                # Broadcast RECON_PACKET for dashboard
                await self.bus.publish(HiveEvent(
                    type=EventType.RECON_PACKET,
                    source=self.name,
                    payload={
                        "url": url,
                        "severity": severity,
                        "risk_score": {"INFO": 10, "LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 95}.get(severity, 10)
                    }
                ))
                
                # Broadcast live attack feed
                await self.bus.publish(HiveEvent(
                    type=EventType.LIVE_ATTACK,
                    source=self.name,
                    payload={
                        "url": url,
                        "arsenal": "Recon Engine",
                        "action": f"{context}: HTTP {status}",
                        "payload": f"Response: {len(text)} bytes, {latency}ms"
                    }
                ))
                
                # Publish request event for telemetry
                try:
                    await publish_request_event({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "method": "GET",
                        "endpoint": url[-40:] if len(url) > 40 else url,
                        "payload": "RECON",
                        "status": status,
                        "latency": latency,
                        "result": result,
                        "anomaly": anomaly
                    }, scan_id=scan_id)
                except Exception:
                    pass
                
                # If interesting, publish as VULN_CANDIDATE
                if anomaly:
                    await self.bus.publish(HiveEvent(
                        type=EventType.VULN_CANDIDATE,
                        source=self.name,
                        payload={"url": url, "tag": "API", "description": text[:500], "status": status}
                    ))
                    
                return status, text
        except asyncio.TimeoutError:
            return 0, ""
        except Exception as e:
            return 0, ""

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
