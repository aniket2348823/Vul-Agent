import asyncio
import logging
from datetime import datetime
from backend.core.hive import EventBus, EventType, HiveEvent
from backend.core.protocol import ModuleConfig, AgentID, TaskPriority, TaskTarget
# NeuroNegotiator removed - dead code cleanup V6
from backend.core.state import stats_db_manager
from backend.core.config import settings
from backend.api.socket_manager import manager

# Import Agents
from backend.agents.alpha import AlphaAgent
from backend.agents.beta import BetaAgent
from backend.agents.gamma import GammaAgent
from backend.agents.omega import OmegaAgent
from backend.agents.zeta import ZetaAgent
from backend.agents.sigma import SigmaAgent
from backend.agents.kappa import KappaAgent 
# V6 AGENTS
from backend.agents.sentinel import AgentTheta # Agent Theta (The Sentinel)
from backend.agents.inspector import AgentIota # Agent Iota (The Inspector)

# recorder removed - unused import cleanup V6
from backend.core.reporting import ReportGenerator # The Voice
# Hybrid AI Engine for campaign strategy
from backend.ai.cortex import CortexEngine
from backend.core.planner import MissionPlanner

logger = logging.getLogger("HiveOrchestrator")
ai_cortex = CortexEngine()

class HiveOrchestrator:
    # Global Registry for API Access (Nervous System)
    active_agents = {}

    @staticmethod
    async def bootstrap_hive(target_config, scan_id=None):
        """
        Initializes the Antigravity V5 Singularity.
        """
        start_time = datetime.now()
        if not scan_id:
             scan_id = f"HIVE-V5-{int(start_time.timestamp())}"

        # 0. Register Scan (Idempotent Check)
        # Check if already registered by attack.py
        existing = next((s for s in stats_db_manager.get_stats()["scans"] if s["id"] == scan_id), None)
        if not existing:
            scan_record = {
                "id": scan_id,
                "status": "Initializing",
                "name": target_config['url'],
                "scope": target_config['url'],
                "modules": ["Singularity V5"],
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": []
            }
            try:
                stats_db_manager.register_scan(scan_record)
            except Exception:
                pass # DB might be locked
        else:
             # Just update status if needed
             for s in stats_db_manager.get_stats()["scans"]:
                 if s["id"] == scan_id:
                     s["status"] = "Running"
                     break
             stats_db_manager._save()
            
        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Initializing"}})

        # 1. Create Nervous System
        bus = EventBus()
        
        # --- REPORTING LINK ---
        scan_events = []
        async def event_listener(event: HiveEvent):
            scan_events.append(event.model_dump())
            
            # REAL-TIME DASHBOARD SYNC
            if event.type == EventType.VULN_CONFIRMED:
                # Update global stats immediately
                real_payload = event.payload
                if 'payload' in real_payload and isinstance(real_payload['payload'], dict):
                     pass

                severity = real_payload.get('severity', 'High')
                # Passing normalized signature data to StateManager for robust deduplication
                sig_data = {
                    "url": str(real_payload.get('url', '')).strip().lower(),
                    "type": str(real_payload.get('type', '')).upper(),
                    "data": str(real_payload.get('data', real_payload.get('payload', '')))
                }
                stats_db_manager.record_finding(scan_id, severity, sig_data)
                
                # Broadcast authoritative stats to UI
                current_stats = stats_db_manager.get_stats()
                await manager.broadcast({
                    "type": "VULN_UPDATE", 
                    "payload": {
                        "metrics": {
                            "vulnerabilities": current_stats["vulnerabilities"],
                            "critical": current_stats["critical"],
                            "active_scans": current_stats["active_scans"], 
                            "total_scans": current_stats["total_scans"]
                        },
                        "graph_data": current_stats["history"]
                    }
                })

                # V6: Persist Threat Metrics
                threat_type = real_payload.get("type", "Unknown Threat")
                risk_score = real_payload.get("data", {}).get("risk_score", 0)
                stats_db_manager.record_threat(threat_type, risk_score)

                # Broadcast LIVE THREAT LOG (New Feature)
                await manager.broadcast({
                    "type": "LIVE_THREAT_LOG",
                    "payload": {
                        "agent": event.source,
                        "threat_type": threat_type,
                        "url": real_payload.get("url", "Unknown Source"),
                        "severity": severity,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "risk_score": risk_score
                    }
                })
                
            elif event.type == EventType.VULN_CANDIDATE:
                real_payload = event.payload
                threat_type = real_payload.get("tag", "Anomaly Target")
                await manager.broadcast({
                    "type": "LIVE_THREAT_LOG",
                    "payload": {
                        "agent": event.source,
                        "threat_type": f"[RECON] {threat_type}",
                        "url": real_payload.get("url", "Unknown Source"),
                        "severity": "INFO",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "risk_score": 0
                    }
                })

            elif event.type == EventType.LIVE_ATTACK:
                # Compute a dynamic severity based on keywords in the action/arsenal
                action_str = (event.payload.get("action", "") + event.payload.get("arsenal", "")).lower()
                if any(k in action_str for k in ["inject", "sqli", "xss", "bypass", "exploit", "crack"]):
                    attack_severity = "HIGH"
                    attack_risk = 75
                elif any(k in action_str for k in ["fuzz", "mutation", "brute", "payload"]):
                    attack_severity = "MEDIUM"
                    attack_risk = 50
                else:
                    attack_severity = "LOW"
                    attack_risk = 25

                await manager.broadcast({
                    "type": "LIVE_ATTACK_FEED",
                    "payload": {
                        "agent": event.source,
                        "url": event.payload.get("url", "N/A"),
                        "arsenal": event.payload.get("arsenal", "General"),
                        "action": event.payload.get("action", "Processing"),
                        "payload": event.payload.get("payload", "N/A"),
                        "severity": attack_severity,
                        "risk_score": attack_risk,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })

            elif event.type == EventType.RECON_PACKET:
                await manager.broadcast({
                    "type": "RECON_PACKET",
                    "payload": {
                        "url": event.payload.get("url", "Unknown"),
                        "severity": event.payload.get("severity", "INFO"),
                        "risk_score": event.payload.get("risk_score", 10),
                        "source": event.source,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })

            elif event.type == EventType.JOB_ASSIGNED:
                # Broadcast job dispatch as a visual event for the dashboard
                target_data = event.payload.get("target", {})
                config_data = event.payload.get("config", {})
                job_url = target_data.get("url", "System Process") if isinstance(target_data, dict) else "System Process"
                job_module = config_data.get("module_id", "Unknown") if isinstance(config_data, dict) else "Unknown"
                await manager.broadcast({
                    "type": "JOB_ASSIGNED",
                    "payload": {
                        "source": event.source,
                        "url": job_url,
                        "module": job_module,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })

        # Subscribe Recorder to Everything for maximum fidelity
        for etype in EventType:
            bus.subscribe(etype, event_listener)
        # ----------------------

        # 2. Spawn Agents (Singularity V5)
        # All agents now inherit from Hive BaseAgent and take `bus`
        scout = AlphaAgent(bus)
        breaker = BetaAgent(bus)
        analyst = GammaAgent(bus)
        strategist = OmegaAgent(bus)
        governor = ZetaAgent(bus)
        
        # AWAKENING: The Smith and The Librarian
        sigma = SigmaAgent(bus)
        kappa = KappaAgent(bus) 
        
        # AWAKENING: The Sentinel and The Inspector (Purple Team Expansion)
        sentinel = AgentTheta(bus)
        inspector = AgentIota(bus) 
        
        # AWAKENING: The Mission Planner (V6 Strategic Heart)
        planner = MissionPlanner(bus)

        # 4. Wake Up the Hive
        # DATA WIRING: Pass Mission Profile
        mission_profile = {
            "modules": target_config.get("modules", []),
            "filters": target_config.get("filters", []),
            "scope": target_config.get("url", "")
        }
        
        # MODULE-BASED AGENT ROUTING
        # Core agents always run — these provide essential cross-cutting services
        # Alpha: Recon, Kappa: Memory, Planner: Strategy, Theta: Defense, Iota: Defense
        # Gamma: Forensic Audit, Omega: Campaign Strategy, Zeta: Governance/Throttle
        core_agents = [scout, kappa, planner, sentinel, inspector, analyst, strategist, governor]
        
        # Offensive agents mapped to modules (Beta + Sigma are attack-specific)
        module_agent_map = {
            "The Tycoon": [breaker, sigma],
            "The Escalator": [breaker, sigma],
            "The Skipper": [breaker, sigma],
            "Doppelganger (IDOR)": [breaker, sigma],
            "Chronomancer": [breaker, sigma],
            "SQL Injection Probe": [breaker, sigma],
            "JWT Token Cracker": [breaker, sigma],
            "API Fuzzer (REST)": [breaker, sigma],
            "Auth Bypass Tester": [breaker, sigma],
        }
        
        selected_modules = target_config.get("modules", [])
        
        if selected_modules:
            # Build unique set of agents from selected modules
            offensive_agents_set = set()
            for mod in selected_modules:
                for agent in module_agent_map.get(mod, []):
                    offensive_agents_set.add(agent)
            agents = core_agents + list(offensive_agents_set)
        else:
            # No modules selected = run everything (backward compatibility)
            agents = [scout, breaker, analyst, strategist, governor, sigma, kappa, sentinel, inspector, planner]
        
        for agent in agents:
            agent.mission_config = mission_profile # Inject Config
            await agent.start()
            
        # Register in Global State
        HiveOrchestrator.active_agents["THETA"] = sentinel
        HiveOrchestrator.active_agents["IOTA"] = inspector
        HiveOrchestrator.active_agents["OMEGA"] = strategist
        HiveOrchestrator.active_agents["ALPHA"] = scout
        HiveOrchestrator.active_agents["BETA"] = breaker
        HiveOrchestrator.active_agents["GAMMA"] = analyst
        HiveOrchestrator.active_agents["ZETA"] = governor
        HiveOrchestrator.active_agents["SIGMA"] = sigma
        HiveOrchestrator.active_agents["KAPPA"] = kappa
        HiveOrchestrator.active_agents["PLANNER"] = planner
        
        # HYBRID AI: Log campaign strategy
        strategy_name = "Dynamic Multi-Core Heuristics"
        logger.info(f"AI Campaign Strategy: {strategy_name}")
            
        await manager.broadcast({"type": "GI5_LOG", "payload": f"SINGULARITY V6 ONLINE. AI Strategy: {strategy_name}."})
        # CRITICAL FIX: Include target_url in SCAN_UPDATE so Dashboard can filter
        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Running", "target_url": target_config['url']}})

        # 5. Seed the Mission — PUBLISH WITH SCAN_ID FOR CONTEXT ISOLATION
        await bus.publish(HiveEvent(
            type=EventType.TARGET_ACQUIRED,
            source="Orchestrator",
            scan_id=scan_id,
            payload={"url": target_config['url'], "tech_stack": ["Unknown"]} 
        ))
        
        # [V6 REAL-TIME FIX] Dispatch selected modules concurrently!
        module_mapper = {
            "The Tycoon": "logic_tycoon",
            "The Escalator": "logic_escalator",
            "The Skipper": "logic_skipper",
            "Doppelganger (IDOR)": "logic_doppelganger",
            "Chronomancer": "logic_chronomancer",
            "SQL Injection Probe": "tech_sqli",
            "JWT Token Cracker": "tech_jwt",
            "API Fuzzer (REST)": "tech_fuzzer",
            "Auth Bypass Tester": "tech_auth_bypass"
        }
        
        from backend.core.protocol import JobPacket, TaskTarget, ModuleConfig, TaskPriority
        from backend.core.protocol import AgentID
        
        for ui_module_name in selected_modules:
            internal_id = module_mapper.get(ui_module_name)
            if not internal_id: continue
            
            packet = JobPacket(
                priority=TaskPriority.HIGH,
                target=TaskTarget(url=target_config['url']),
                config=ModuleConfig(
                    module_id=internal_id,
                    agent_id=AgentID.SIGMA
                )
            )
            
            await bus.publish(HiveEvent(
                type=EventType.JOB_ASSIGNED,
                source="Orchestrator",
                scan_id=scan_id,
                payload=packet.model_dump()
            ))

        # [V6 REAL-TIME FIX] Always force an AI Generative Assault payload to feed BetaAgent
        ai_packet = JobPacket(
            priority=TaskPriority.NORMAL,
            target=TaskTarget(url=target_config['url']),
            config=ModuleConfig(
                module_id="sigma_generative_blast",
                agent_id=AgentID.SIGMA
            )
        )
        await bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="Orchestrator",
            scan_id=scan_id,
            payload=ai_packet.model_dump()
        ))

        # [V6 REAL-TIME FIX] Also dispatch a direct Beta assault job to ensure real-time attacks
        beta_assault_packet = JobPacket(
            priority=TaskPriority.HIGH,
            target=TaskTarget(url=target_config['url']),
            config=ModuleConfig(
                module_id="beta_direct_assault",
                agent_id=AgentID.BETA,
                aggression=8
            )
        )
        await bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED,
            source="Orchestrator",
            scan_id=scan_id,
            payload=beta_assault_packet.model_dump()
        ))

        await manager.broadcast({"type": "GI5_LOG", "payload": "HYPER-MIND ONLINE. Parallel Overdrive Active."})

        # 6. Run Duration (Custom duration from config or default)
        duration_val = target_config.get('duration')
        scan_duration = int(duration_val) if duration_val is not None else settings.SCAN_TIMEOUT
        scan_duration = max(scan_duration, 1) # Ensure at least 1s
        try:
            await asyncio.sleep(scan_duration)
        except asyncio.CancelledError:
            pass
        finally:
            await manager.broadcast({"type": "GI5_LOG", "payload": "Hyper-Mind: Mission Complete. Shutting down."})
            for agent in agents:
                try:
                    await asyncio.wait_for(agent.stop(), timeout=5.0)
                except Exception as e:
                    logger.error(f"Failed to stop agent {agent.name}: {e}")
            
            # --- V6 GRACE PERIOD ---
            await asyncio.sleep(1.0)
            
            # --- SCAN ISOLATION: UNSUBSCRIBE LISTENERS ---
            for etype in EventType:
                bus.unsubscribe(etype, event_listener)
            
            # Clear registry
            HiveOrchestrator.active_agents.clear()
            print(f"[Orchestrator] Scan {scan_id} Cleaned Up. Listeners detached.")
            
            # --- GENERATE GOD MODE REPORT ---
            try:
                items_found = [e for e in scan_events if e.get('type') in (EventType.VULN_CONFIRMED, "VULN_CONFIRMED")]
                stats_db_manager.complete_scan(scan_id, items_found, scan_duration)
                await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Finalizing"}})
            except Exception as e:
                logger.error(f"Failed to record complete_scan (Finalizing): {e}")

            try:
                async def generate_and_mark_ready():
                    try:
                        report_gen = ReportGenerator()
                        print(f"[Orchestrator] Starting AI report generation for scan {scan_id}...")
                        
                        end_time = datetime.now()
                        requested_concurrency = target_config.get('velocity', len(agents))
                        
                        # Get REAL AI telemetry from CortexEngine
                        cortex_telemetry = ai_cortex.get_telemetry()
                        real_ai_calls = cortex_telemetry.get("llm_calls", 0)
                        real_avg_latency = cortex_telemetry.get("avg_llm_latency", 0.0)
                        real_cb_trips = cortex_telemetry.get("circuit_breaker_trips", 0)
                        
                        total_attack_events = sum(1 for e in scan_events if e.get('type') in (EventType.LIVE_ATTACK, "LIVE_ATTACK"))
                        avg_request_latency = round((scan_duration / max(total_attack_events, 1)) * 1000, 1)
                        
                        telemetry = {
                            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "duration": f"{scan_duration}s",
                            "total_requests": len(scan_events),
                            "avg_latency_ms": avg_request_latency,
                            "peak_concurrency": requested_concurrency,
                            "ai_calls": real_ai_calls,
                            "llm_avg_latency": f"{real_avg_latency:.1f}" if real_avg_latency else "N/A",
                            "circuit_breaker_activations": real_cb_trips,
                        }
                        
                        await asyncio.wait_for(
                            report_gen.generate_report(scan_id, scan_events, target_config['url'], telemetry=telemetry, manager=manager),
                            timeout=900.0
                        )
                        
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                        
                        stats_db_manager.flush_immediate()
                        print(f"[Orchestrator] AI Report for {scan_id} is now READY and SYNCED with UI.")
                    except asyncio.TimeoutError:
                        print(f"[Orchestrator] Report generation TIMED OUT for {scan_id}. Forcing ready.")
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                                
                        stats_db_manager.flush_immediate()
                    except Exception as ge:
                        print(f"[Orchestrator] Background Report Async Task Error: {ge}")
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                                
                        stats_db_manager.flush_immediate()
                        import traceback
                        traceback.print_exc()

                asyncio.create_task(generate_and_mark_ready())
                await manager.broadcast({"type": "GI5_LOG", "payload": f"FORENSIC REPORT GENERATION INITIATED FOR {scan_id}"})
            except Exception as e:
                logger.error(f"Report Background Gen Trigger Failed: {e}")

            await manager.broadcast({"type": "GI5_LOG", "payload": f"SCAN FINISHED. AI FINALIZING FORENSIC DATA FOR {scan_id}..."})
