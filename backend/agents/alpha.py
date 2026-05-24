import asyncio
import aiohttp
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, ModuleConfig, TaskTarget
from backend.core.config import settings
from backend.core.content_boundary import content_boundary
from backend.core.proxy import network_interceptor
from backend.agents.alpha_v6 import AlphaOrchestrator

# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine
from backend.core.queue import command_lane

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
        self.alpha_recon = AlphaOrchestrator(bus, agent_name=self.name)

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
        
        if getattr(settings, "ALPHA_ENABLE_V6", True):
            try:
                mode = event.payload.get("scan_mode") or event.payload.get("mode") or getattr(settings, "ALPHA_DEFAULT_MODE", "STANDARD")
                await self.alpha_recon.run(target_url, scan_id=event.scan_id, mode=mode)
                return
            except Exception as exc:
                print(f"[{self.name}] Alpha V6 recon failed: {exc}")

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
