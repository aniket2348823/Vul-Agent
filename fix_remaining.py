"""Fix delta.py and sigma.py: add ScanContext logging."""
import re

NL = "\n"
INDENT = "        "

CTX_LINES = [
    NL,
    INDENT + "# ScanContext: record event for transcript causality" + NL,
    INDENT + "if hasattr(self.bus, 'get_or_create_context'):" + NL,
    INDENT + "    _ctx = self.bus.get_or_create_context(getattr(event, 'scan_id', 'GLOBAL'))" + NL,
    INDENT + "    _ctx.append_event(event)",
]
CTX_SUFFIX = "".join(CTX_LINES)


def inject_ctx(filepath, pattern_str):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "get_or_create_context" in content:
        print(f"SKIP {filepath}: already has ctx")
        return

    match = re.search(pattern_str, content)
    if not match:
        print(f"WARN {filepath}: no pattern found")
        return

    replacement = match.group(0) + CTX_SUFFIX
    content = content[: match.start()] + replacement + content[match.end() :]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK   {filepath}: +ctx")


# delta.py uses: packet_dict = event.payload
inject_ctx("backend/agents/delta.py", r"packet_dict\s*=\s*event\.payload")

# sigma.py uses: packet_dict = event.payload
inject_ctx("backend/agents/sigma.py", r"packet_dict\s*=\s*event\.payload")

# lambda_agent.py - standalone class, add queue+boundary imports only
import os
lpath = "backend/agents/lambda_agent.py"
with open(lpath, "r", encoding="utf-8") as f:
    content = f.read()

changed = False
if "command_lane" not in content:
    content = "from backend.core.queue import command_lane" + NL + content
    changed = True
if "content_boundary" not in content:
    content = "from backend.core.content_boundary import content_boundary" + NL + content
    changed = True

if changed:
    with open(lpath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK   {lpath}: +queue +boundary")
else:
    print(f"SKIP {lpath}: already complete")
