"""
Surgical upgrade script: adds missing OpenClaw infrastructure imports
and ScanContext logging to all agents that still need them.
"""
import re
import os

agents_dir = "backend/agents"

# What each agent is MISSING (True = needs adding)
UPGRADES = {
    "alpha.py":        {"queue": True,  "boundary": False, "ctx": False},
    "beta.py":         {"queue": False, "boundary": False, "ctx": True},
    "chi.py":          {"queue": True,  "boundary": False, "ctx": True},
    "delta.py":        {"queue": False, "boundary": False, "ctx": True},
    "gamma.py":        {"queue": True,  "boundary": False, "ctx": True},
    "kappa.py":        {"queue": True,  "boundary": False, "ctx": True},
    "lambda_agent.py": {"queue": True,  "boundary": True,  "ctx": True},
    "sigma.py":        {"queue": False, "boundary": False, "ctx": True},
    "zeta.py":         {"queue": False, "boundary": True,  "ctx": True},
}


def find_last_backend_import(lines):
    idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("from backend."):
            idx = i
    return idx


def upgrade_file(fname, needs):
    path = os.path.join(agents_dir, fname)
    if not os.path.exists(path):
        return f"SKIP {fname}: not found"

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    changes = []

    # 1. Add command_lane import
    if needs["queue"] and "command_lane" not in content:
        lines = content.split("\n")
        idx = find_last_backend_import(lines)
        if idx >= 0:
            lines.insert(idx + 1, "from backend.core.queue import command_lane")
            content = "\n".join(lines)
            changes.append("+queue")

    # 2. Add content_boundary import
    if needs["boundary"] and "content_boundary" not in content:
        lines = content.split("\n")
        idx = find_last_backend_import(lines)
        if idx >= 0:
            lines.insert(idx + 1, "from backend.core.content_boundary import content_boundary")
            content = "\n".join(lines)
            changes.append("+boundary")

    # 3. Add ScanContext logging to first handler
    if needs["ctx"] and "get_or_create_context" not in content:
        pattern = r"(payload\s*=\s*event\.payload)"
        match = re.search(pattern, content)
        if match:
            indent = "        "
            ctx_block = (
                match.group(1) + "\n"
                + indent + "# ScanContext: record event for transcript causality\n"
                + indent + 'if hasattr(self.bus, "get_or_create_context"):\n'
                + indent + '    _ctx = self.bus.get_or_create_context(getattr(event, "scan_id", "GLOBAL"))\n'
                + indent + "    _ctx.append_event(event)"
            )
            content = content[: match.start()] + ctx_block + content[match.end() :]
            changes.append("+ctx")

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"OK   {fname}: {' '.join(changes)}"
    else:
        return f"SKIP {fname}: already complete"


for fname, needs in UPGRADES.items():
    print(upgrade_file(fname, needs))
