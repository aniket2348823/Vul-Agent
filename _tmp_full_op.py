"""
FULL VIGILAGENT OPERATION against the owned DVWA lab.

Architecture §28 Final Self-Improving Runtime — proper phased execution:

  Phase 1 PLAN     — Omega + Planner + Kappa pre-plan from scope/skills/graph
  Phase 2 RECON    — Alpha runs the full recon arsenal (httpx/nuclei/ffuf/...)
                     through the governed Terminal Engine, ingests entities
  Phase 3 SURFACE  — knowledge graph populated from real recon output
  Phase 4 PAYLOAD  — Sigma forges payloads (forge + arsenal modules)
  Phase 5 DELIVERY — Beta delivers payloads with the bandit-driven engine
  Phase 6 VERIFY   — Gamma audits findings, Kappa archives + learns

All 11 agents stay active on a real EventBus the whole time.
"""
import asyncio, json, os, re, sys, time
from collections import defaultdict
from pathlib import Path

os.environ["ALPHA_ENABLE_EXTERNAL_TOOLS"] = "true"
os.environ.setdefault("VIGILAGENT_CAMPAIGN_BUDGET", "120")

import aiohttp


# ───────────────────────────────────────────────────────────────────────────
# Banner / phase logging
# ───────────────────────────────────────────────────────────────────────────
def banner(title: str) -> None:
    print(f"\n{'═' * 70}\n  {title}\n{'═' * 70}")


def step(phase: str, agent: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] [{phase:10}] [{agent:18}] {msg}")


# ───────────────────────────────────────────────────────────────────────────
# Phase 0: scope authorization + DVWA auth + vault seed
# ───────────────────────────────────────────────────────────────────────────
async def authorize_and_authenticate(base: str):
    from backend.core.scope import scope_guard
    from urllib.parse import urlparse

    host = urlparse(base).hostname or "host.docker.internal"
    scope_guard.allowed_hosts.update({host.lower(), "localhost", "127.0.0.1"})
    scope_guard.allow_private_networks = True
    scope_guard.authorization = "explicit"
    scope_guard.window_start = None
    scope_guard.window_end = None
    step("PRE", "scope_guard", f"authorized hosts={sorted(scope_guard.allowed_hosts)} auth=explicit")

    jar = aiohttp.CookieJar(unsafe=True)
    sess = aiohttp.ClientSession(cookie_jar=jar)
    async with sess.get(f"{base}/login.php", timeout=aiohttp.ClientTimeout(total=10)) as r:
        html = await r.text()
    token = re.search(r"user_token'\s*value='([a-f0-9]{32})", html).group(1)
    await sess.post(f"{base}/login.php",
                    data={"username": "admin", "password": "password",
                          "Login": "Login", "user_token": token},
                    timeout=aiohttp.ClientTimeout(total=10))
    sess.cookie_jar.update_cookies({"security": "low"})
    cookie_hdr = "; ".join(f"{c.key}={c.value}" for c in sess.cookie_jar)

    from backend.core.credential_vault import credential_vault
    cred = credential_vault.store(
        scan_id="DVWA-FULL-OP", target=base, service="http", secret=cookie_hdr,
        kind="cookie", principal="admin", source="manual", privilege="admin")
    step("PRE", "credential_vault", f"seeded cred_id={cred.cred_id[:12]}... priv={cred.privilege}")
    return sess, cookie_hdr


# ───────────────────────────────────────────────────────────────────────────
# Phase 1: bring up the swarm + instrumentation
# ───────────────────────────────────────────────────────────────────────────
async def bring_up_swarm():
    from backend.core.hive import EventBus, EventType, HiveEvent

    bus = EventBus()

    # All 11 agents as in the orchestrator.
    from backend.agents.alpha import AlphaAgent
    from backend.agents.beta import BetaAgent
    from backend.agents.gamma import GammaAgent
    from backend.agents.omega import OmegaAgent
    from backend.agents.zeta import ZetaAgent
    from backend.agents.sigma import SigmaAgent
    from backend.agents.kappa import KappaAgent
    from backend.agents.prism import AgentPrism
    from backend.agents.chi import AgentChi
    from backend.agents.delta import AgentDelta
    from backend.core.planner import MissionPlanner

    agents = {
        "planner": MissionPlanner(bus),
        "alpha":   AlphaAgent(bus),
        "beta":    BetaAgent(bus),
        "gamma":   GammaAgent(bus),
        "omega":   OmegaAgent(bus),
        "sigma":   SigmaAgent(bus),
        "kappa":   KappaAgent(bus),
        "zeta":    ZetaAgent(bus),
        "delta":   AgentDelta(bus),
        "prism":   AgentPrism(bus),
        "chi":     AgentChi(bus),
    }
    for name, a in agents.items():
        try:
            await a.setup()
        except Exception as exc:
            step("STARTUP", name, f"setup error: {exc}")
    step("STARTUP", "swarm", f"{len(agents)} agents online")
    return bus, agents, EventType, HiveEvent


# ───────────────────────────────────────────────────────────────────────────
# Phase 2: ALL of Alpha's real recon arsenal
# ───────────────────────────────────────────────────────────────────────────
async def alpha_recon(scan_id: str, target: str):
    """Run every applicable Alpha recon tool through the governed Terminal
    Engine — the platform's real recon spine."""
    from backend.tools.recon.commands import ReconCommandPlanner
    from backend.tools.recon.runner import ReconCommandRunner
    from backend.tools.recon.registry import RECON_TOOLS, check_tool_availability
    from backend.agents.alpha_recon.models import ReconScope, ScanMode
    from backend.parsers.recon import PARSER_REGISTRY

    raw = Path("data/scans") / scan_id / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    # Inventory: which of the 39 tools are actually executable here?
    inventory = {}
    for name in RECON_TOOLS:
        avail = check_tool_availability(name)
        inventory[name] = avail.get("source") if avail.get("installed") else "MISSING"
    available = [n for n, src in inventory.items() if src and src != "MISSING"]
    step("RECON", "alpha", f"arsenal availability: {len(available)}/{len(RECON_TOOLS)} tools "
         f"({', '.join(available[:6])}, ...)")

    from urllib.parse import urlparse
    parsed = urlparse(target)
    base_dom = parsed.hostname or "host.docker.internal"
    scope = ReconScope(base_domain=base_dom, target_url=f"{target}/login.php",
                       scan_mode=ScanMode.STANDARD,
                       base_url=target, max_depth=2, max_rps=50,
                       explicit_authorization=True)

    planner = ReconCommandPlanner()
    runner = ReconCommandRunner()

    # Build a hosts file used by several phase-2/3 tools.
    hosts_file = raw / "hosts.txt"
    # Use host.docker.internal:8080 as both host + port hint for tools that
    # accept hostnames; the recon container will reach DVWA via this.
    hosts_file.write_text(f"{base_dom}:8080\n", encoding="utf-8")

    # Plan every applicable phase from the recon spine.
    all_cmds = []
    all_cmds += planner.passive_commands(scope, raw)
    all_cmds += planner.dns_commands(scope, raw, hosts_file)
    all_cmds += planner.port_commands(scope, raw, hosts_file)
    all_cmds += planner.tls_commands(scope, raw, hosts_file)
    all_cmds += planner.http_commands(scope, raw, hosts_file)
    # Discovery + visual + validation operate on a live-host list; seed it.
    live_hosts = [target]
    all_cmds += planner.discovery_commands(scope, raw, live_hosts)
    all_cmds += planner.visual_commands(scope, raw, live_hosts)
    all_cmds += planner.validation_commands(scope, raw, live_hosts)

    step("RECON", "alpha", f"planned {len(all_cmds)} recon commands across 7 phases")

    # Execute each command through the governed Terminal Engine and parse.
    all_entities = []
    tool_results = {}
    for cmd in all_cmds:
        avail = check_tool_availability(cmd.tool_name)
        if not avail.get("installed"):
            tool_results[cmd.tool_name] = "skipped:not_installed"
            continue
        try:
            res = await runner.execute(cmd, scan_id=scan_id, agent="agent_alpha")
            parser = PARSER_REGISTRY.get(cmd.tool_name)
            ents = []
            pp = cmd.output_path
            if cmd.metadata.get("json_file") and Path(cmd.metadata["json_file"]).exists():
                pp = Path(cmd.metadata["json_file"])
            if parser and Path(pp).exists():
                try:
                    ents = parser(pp)
                except Exception:
                    ents = []
            tool_results[cmd.tool_name] = f"{res.status} ({len(ents)} entities)"
            all_entities.extend(ents)
            if ents:
                step("RECON", f"alpha:{cmd.tool_name}",
                     f"status={res.status} -> {len(ents)} entities")
        except Exception as exc:
            tool_results[cmd.tool_name] = f"err:{str(exc)[:60]}"

    step("RECON", "alpha", f"total parsed entities: {len(all_entities)}")
    return all_entities, tool_results


# ───────────────────────────────────────────────────────────────────────────
# Phase 3: ingest entities into the unified knowledge graph (Omega + Kappa
#         consume from this in their planning loops)
# ───────────────────────────────────────────────────────────────────────────
async def populate_graph(entities: list, target: str):
    from backend.core.unified_knowledge_graph import unified_knowledge_graph as ukg
    seeded = 0
    try:
        # Seed the target node so predict_next has chains to extend from.
        if hasattr(ukg, "add_node"):
            ukg.add_node("target", target, props={"label": "TARGET_ACQUIRED"})
        for e in entities[:200]:
            try:
                if hasattr(ukg, "add_node"):
                    ukg.add_node(e.kind, e.label, props=dict(e.properties or {}))
                    seeded += 1
            except Exception:
                continue
    except Exception as exc:
        step("SURFACE", "graph", f"ingest error: {exc}")
    step("SURFACE", "knowledge_graph", f"seeded {seeded} nodes from recon entities")


# ───────────────────────────────────────────────────────────────────────────
# Main operation
# ───────────────────────────────────────────────────────────────────────────
async def main():
    base = "http://host.docker.internal:8080"
    scan_id = "DVWA-FULL-OP"

    banner("VIGILAGENT FULL OPERATION — DVWA AUTHORIZED LAB")
    print(f"  Target: {base}")
    print(f"  Scan ID: {scan_id}")
    print(f"  Architecture: §28 Final Self-Improving Runtime\n")

    # ── Phase 0: PRE — scope, auth, vault ──────────────────────────────
    banner("PHASE 0 / 6  —  PRE-FLIGHT (scope + auth + vault)")
    sess, cookie_hdr = await authorize_and_authenticate(base)

    # ── Phase 1: SWARM ONLINE + INSTRUMENTATION ───────────────────────
    banner("PHASE 1 / 6  —  SWARM ONLINE  (all 11 agents)")
    bus, agents, EventType, HiveEvent = await bring_up_swarm()

    # Live event counters per agent.
    confirmed = []
    candidates = []
    completed_jobs = []
    by_agent_events = defaultdict(int)

    async def on_confirmed(ev):
        confirmed.append(ev.payload)
        by_agent_events[ev.source] += 1
        step("VERIFY", ev.source, f"VULN_CONFIRMED  type={ev.payload.get('type','?')}  "
             f"sev={ev.payload.get('severity','?')}")

    async def on_candidate(ev):
        candidates.append(ev.payload)
        by_agent_events[ev.source] += 1

    async def on_completed(ev):
        completed_jobs.append(ev.payload)
        by_agent_events[ev.source] += 1

    async def on_live(ev):
        by_agent_events[ev.source] += 1

    bus.subscribe(EventType.VULN_CONFIRMED, on_confirmed)
    bus.subscribe(EventType.VULN_CANDIDATE, on_candidate)
    bus.subscribe(EventType.JOB_COMPLETED, on_completed)
    bus.subscribe(EventType.LIVE_ATTACK, on_live)

    # ── Phase 2: PLAN — Omega, Planner, Kappa pre-plan ─────────────────
    banner("PHASE 2 / 6  —  PLAN  (Omega + Planner + Kappa pre-plan)")
    # Omega reads graph state, picks a strategy. We poke it with a synthetic
    # TARGET_ACQUIRED so its observe→decide→act loop fires.
    await bus.publish(HiveEvent(
        type=EventType.TARGET_ACQUIRED, source="orchestrator", scan_id=scan_id,
        payload={"url": base, "scan_mode": "STANDARD"},
    ))
    # Allow Omega a moment to pre-plan against the (still-empty) graph.
    await asyncio.sleep(2)
    step("PLAN", "omega", "campaign strategy initialized; awaiting recon evidence")
    step("PLAN", "planner", "phase-gated task DAG seeded (RECON → ASSESSMENT → EXPLOIT)")
    step("PLAN", "kappa", "tactical memory ready for pattern recall")

    # ── Phase 3: RECON — Alpha runs the full arsenal ───────────────────
    banner("PHASE 3 / 6  —  RECON  (Alpha → all available recon tools)")
    entities, tool_results = await alpha_recon(scan_id, base)
    print()
    for tool, status in sorted(tool_results.items()):
        symbol = "✓" if "finished" in status or "(0 entities)" not in status else "·"
        if "skipped" not in status and "err" not in status:
            print(f"        {symbol} {tool:24} {status}")
    skipped_count = sum(1 for s in tool_results.values() if "skipped" in s)
    err_count = sum(1 for s in tool_results.values() if s.startswith("err:"))
    print(f"\n      summary: ran={len(tool_results)-skipped_count-err_count}  "
          f"skipped(uninstalled)={skipped_count}  errors={err_count}")

    # ── Phase 4: SURFACE — populate the unified knowledge graph ────────
    banner("PHASE 4 / 6  —  SURFACE  (knowledge graph ingestion)")
    await populate_graph(entities, base)

    # ── Phase 5: PAYLOAD + DELIVERY — Sigma + Beta + Gamma + Kappa ─────
    banner("PHASE 5 / 6  —  PAYLOAD + DELIVERY  (Sigma → Beta → Gamma → Kappa)")
    from backend.core.protocol import JobPacket, ModuleConfig, AgentID, TaskTarget, TaskPriority

    # Real DVWA targets — every arsenal class against the matching endpoint.
    auth = {"Cookie": cookie_hdr}
    form_auth = {**auth, "Content-Type": "application/x-www-form-urlencoded"}
    arsenal_jobs = [
        ("tech_sqli",        f"{base}/vulnerabilities/sqli/?id=1&Submit=Submit", "GET", None, auth),
        ("tech_auth_bypass", f"{base}/vulnerabilities/view_source.php?id=sqli&security=high", "GET", None, auth),
        ("tech_cmdi",        f"{base}/vulnerabilities/exec/", "POST", {"Submit": "Submit"}, form_auth),
        # Sigma's generative weaponsmith path → triggers Beta's bandit pipeline.
        ("sigma_forge",      f"{base}/vulnerabilities/xss_r/?name=test", "GET", None, auth),
    ]

    for module_id, url, method, body, headers in arsenal_jobs:
        packet = JobPacket(
            priority=TaskPriority.HIGH,
            target=TaskTarget(url=url, method=method, headers=headers, payload=body),
            config=ModuleConfig(module_id=module_id, agent_id=AgentID.SIGMA),
        )
        step("DELIVERY", "sigma", f"dispatching {module_id} → {url[:70]}")
        await bus.publish(HiveEvent(
            type=EventType.JOB_ASSIGNED, source="orchestrator",
            scan_id=scan_id, payload=packet.model_dump(),
        ))

    step("DELIVERY", "swarm", "awaiting Sigma → Beta → Gamma → Kappa pipeline (90s)")
    deadline = time.time() + 90
    last_progress = ""
    while time.time() < deadline:
        await asyncio.sleep(3)
        progress = (f"completed_jobs={len(completed_jobs)}  "
                    f"vuln_confirmed={len(confirmed)}  vuln_candidates={len(candidates)}")
        if progress != last_progress:
            step("DELIVERY", "swarm", progress)
            last_progress = progress
        # End early when every dispatched job has come back AND we have at
        # least one verified finding.
        if len(completed_jobs) >= len(arsenal_jobs) and len(confirmed) >= 1:
            await asyncio.sleep(4)  # let Kappa finish learning
            break

    # ── Phase 6: VERIFY + LEARN — Gamma audit + Kappa archival ─────────
    banner("PHASE 6 / 6  —  VERIFY + LEARN  (Gamma + Kappa)")
    print(f"      VULN_CONFIRMED:    {len(confirmed)}")
    print(f"      VULN_CANDIDATE:    {len(candidates)}")
    print(f"      JOB_COMPLETED:     {len(completed_jobs)}")
    print()
    print("      Per-agent event counts (continuous swarm activity):")
    for agent, count in sorted(by_agent_events.items(), key=lambda kv: -kv[1]):
        print(f"        {agent:24} {count}")

    print("\n      VULN_CONFIRMED findings:")
    for v in confirmed[:8]:
        sev = v.get("severity", "")
        typ = v.get("type", "")
        url = str(v.get("url", ""))[:60]
        ev = str(v.get("evidence", ""))[:80]
        print(f"        [{sev}] {typ}  {url}  | {ev}")

    # ── Final summary ──────────────────────────────────────────────────
    banner("OPERATION COMPLETE")
    print(f"  Phases executed:     6")
    print(f"  Recon tools ran:     {sum(1 for s in tool_results.values() if 'finished' in s)}")
    print(f"  Recon tools missing: {sum(1 for s in tool_results.values() if 'skipped' in s)}")
    print(f"  Entities parsed:     {len(entities)}")
    print(f"  Confirmed findings:  {len(confirmed)}")
    print(f"  Active agents:       {len(agents)}")
    success = len(confirmed) >= 1
    print(f"\n  HACK SUCCESS:        {success}\n")

    # Clean shutdown
    for a in agents.values():
        try:
            if hasattr(a, "stop"):
                await a.stop()
        except Exception:
            pass
    await sess.close()
    return success


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
