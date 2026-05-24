import os
import re

def modify_file(filepath, callback):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = callback(content)
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Modified {filepath}")
    else:
        print(f"No changes for {filepath}")

# 1. Alpha
def modify_alpha(c):
    # Remove _real_http_recon and _probe_url
    c = re.sub(
        r'print\(f"\[\{self\.name\}\] Alpha V6 recon failed, falling back to legacy HTTP recon: \{exc\}"\)\s*# Legacy fallback: preserve the existing shallow HTTP recon path\.\s*await self\._real_http_recon\(target_url, event\.scan_id\).*?async def handle_job',
        r'print(f"[{self.name}] Alpha V6 recon failed: {exc}")\n\n    async def handle_job',
        c, flags=re.DOTALL
    )
    # Ensure transcript logging in handle_target_acquired
    if "ctx = self.bus.get_or_create_context(event.scan_id)" not in c:
        c = c.replace('target_url = event.payload.get("url")', 'target_url = event.payload.get("url")\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)')
    return c
modify_file("backend/agents/alpha.py", modify_alpha)

# 2. Sigma
def modify_sigma(c):
    if "from backend.core.queue import command_lane, LanePriority" not in c:
        c = c.replace("from backend.core.proxy import network_interceptor", "from backend.core.proxy import network_interceptor\nfrom backend.core.queue import command_lane, LanePriority")
    
    # Replace aiohttp in _fetch
    if "async with aiohttp.ClientSession" in c:
        c = re.sub(
            r'async with aiohttp\.ClientSession\(\) as session:\s*async with session\.get\(target\.url.*?\)\s*as response:\s*body = await response\.text\(\)',
            r"async with command_lane.slot(LanePriority.HIGH):\n            response = await network_interceptor.fetch('GET', target.url, timeout=15)\n            body = response.body\n            body = content_boundary.wrap_http_response(response.status, response.headers, body, target.url)",
            c, flags=re.DOTALL
        )
    # Transcript logging in handle_generation_request
    if "ctx = self.bus.get_or_create_context(event.scan_id)" not in c and "def handle_generation_request" in c:
        c = re.sub(r'(packet = JobPacket\(\*\*payload\))', r'\1\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)', c)

    # Sanitize generated payloads
    if "final_payloads = [" not in c and "final_payloads" in c:
        c = re.sub(r'(final_payloads = list\(payload_set\))', r'\1\n        final_payloads = [content_boundary.sanitize_control_tokens(p) for p in final_payloads]', c)
    return c
modify_file("backend/agents/sigma.py", modify_sigma)

# 3. Beta
def modify_beta(c):
    if "from backend.core.queue import command_lane, LanePriority" not in c:
        c = c.replace("from backend.core.proxy import network_interceptor", "from backend.core.proxy import network_interceptor\nfrom backend.core.queue import command_lane, LanePriority")
    if "from backend.core.sandbox import TempWorkspace" not in c:
        c = c.replace("from backend.core.proxy import network_interceptor", "from backend.core.proxy import network_interceptor\nfrom backend.core.sandbox import TempWorkspace")
    
    # Wrap execute real attack
    if "async with aiohttp.ClientSession" in c and "def _execute_real_attack" in c:
        c = re.sub(
            r'async with aiohttp\.ClientSession\(timeout=aiohttp\.ClientTimeout\(total=10\)\) as session:\s*try:\s*start_time = time\.time\(\)\s*async with session\.request\(method, target\.url.*?as response:',
            r"async with command_lane.slot(LanePriority.CRITICAL):\n            try:\n                import time\n                start_time = time.time()\n                response = await network_interceptor.fetch(method, target.url, headers=headers, body=payload, timeout=10)",
            c, flags=re.DOTALL
        )
        c = re.sub(r'resp_text = await response\.text\(\)', r'resp_text = response.body', c)
        c = re.sub(r'status_code = response\.status', r'status_code = response.status', c)
        
    # Transcript logging
    if "ctx = self.bus.get_or_create_context" not in c and "def handle_sigma_payloads" in c:
        c = re.sub(r'(packet = ResultPacket\(\*\*event\.payload\))', r'\1\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)', c)
        
    # Sanitize mutation
    if "mutated = content_boundary.sanitize_control_tokens" not in c and "def waf_mutate" in c:
        c = re.sub(r'if mutated and mutated != payload:', r'if mutated and mutated != payload:\n            mutated = content_boundary.sanitize_control_tokens(mutated)', c)
    return c
modify_file("backend/agents/beta.py", modify_beta)

# 4. Omega
def modify_omega(c):
    if "from backend.core.queue import command_lane" not in c:
        c = c.replace("from backend.core.context import ScanContext", "from backend.core.context import ScanContext\nfrom backend.core.queue import command_lane\nfrom backend.core.content_boundary import content_boundary")
    
    # Transcript logging in initiate_campaign
    if "ctx = self.bus.get_or_create_context" not in c and "def initiate_campaign" in c:
        c = re.sub(
            r'(await self\.bus\.publish\(HiveEvent\(\s*type=EventType\.LOG,\s*source=self\.name,\s*scan_id=scan_id,\s*payload=\{"message": f"Omega campaign initiated.*?\}\s*\)\))',
            r'\1\n        ctx = self.bus.get_or_create_context(scan_id)\n        ctx.append_event(HiveEvent(type=EventType.LOG, source=self.name, scan_id=scan_id, payload={"message": f"Omega campaign initiated: strategy={strategy_name}, target={target_url}"}))',
            c, flags=re.DOTALL
        )

    # CommandLane telemetry check
    if "telemetry = command_lane.telemetry" not in c and "def dispatch_job" in c:
        c = re.sub(
            r'def dispatch_job\(self, packet: JobPacket, scan_id: str = None\):\s*async def _dispatch\(\):',
            r'def dispatch_job(self, packet: JobPacket, scan_id: str = None):\n        async def _dispatch():\n            telemetry = command_lane.telemetry\n            if telemetry["waiting_count"] > 20:\n                print(f"[{self.name}] CommandLane saturated (waiting={telemetry[\'waiting_count\']}). Deferring dispatch.")\n                await asyncio.sleep(1.0)',
            c
        )
    return c
modify_file("backend/agents/omega.py", modify_omega)

# 5. Gamma
def modify_gamma(c):
    if "from backend.core.content_boundary import content_boundary" not in c:
        c = c.replace("import collections", "import collections\nfrom backend.core.content_boundary import content_boundary")
    
    if "def handle_result" in c and "ctx = self.bus.get_or_create_context" not in c:
        c = re.sub(r'(packet = ResultPacket\(\*\*event\.payload\))', r'\1\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)', c)
        
    return c
modify_file("backend/agents/gamma.py", modify_gamma)

# 6. Kappa
def modify_kappa(c):
    if "from backend.core.content_boundary import content_boundary" not in c:
        c = c.replace("import json", "import json\nfrom backend.core.content_boundary import content_boundary")
    
    if "def handle_confirmed" in c and "ctx = self.bus.get_or_create_context" not in c:
        c = re.sub(r'(payload = event\.payload)', r'\1\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)', c)
        
    if "def recall_tactics" in c and "sanitized_hits =" not in c:
        c = re.sub(r'return semantic_hits', r'sanitized_hits = []\n        for hit in semantic_hits:\n            if isinstance(hit, dict) and "payload" in hit:\n                hit["payload"] = content_boundary.sanitize_control_tokens(str(hit["payload"]))\n            sanitized_hits.append(hit)\n        return sanitized_hits', c)
    return c
modify_file("backend/agents/kappa.py", modify_kappa)

# 7. Chi
def modify_chi(c):
    if "from backend.core.content_boundary import content_boundary" not in c:
        c = c.replace("import json", "import json\nfrom backend.core.content_boundary import content_boundary")
    
    if "def handle_intercept" in c and "ctx = self.bus.get_or_create_context" not in c:
        c = re.sub(r'(payload = event\.payload)', r'\1\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)', c)
    return c
modify_file("backend/agents/chi.py", modify_chi)

# 8. Prism
def modify_prism(c):
    if "from backend.core.content_boundary import content_boundary" not in c:
        c = c.replace("import json", "import json\nfrom backend.core.content_boundary import content_boundary")
    
    if "def handle_dom_event" in c and "ctx = self.bus.get_or_create_context" not in c:
        c = re.sub(r'(payload = event\.payload)', r'\1\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)', c)
    return c
modify_file("backend/agents/prism.py", modify_prism)

# 9. Delta
def modify_delta(c):
    if "from backend.core.queue import command_lane" not in c:
        c = c.replace("import os", "import os\nfrom backend.core.queue import command_lane, LanePriority\nfrom backend.core.content_boundary import content_boundary")
    
    if "def handle_hybrid_request" in c and "ctx = self.bus.get_or_create_context" not in c:
        c = re.sub(r'(payload = event\.payload)', r'\1\n        ctx = self.bus.get_or_create_context(event.scan_id)\n        ctx.append_event(event)', c)
    return c
modify_file("backend/agents/delta.py", modify_delta)
