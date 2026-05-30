"""Alpha Unified Recon Tool Registry — Full 39-Tool Matrix (Architecture §7, §5.1.1).

Alpha is the recon commander. It runs the full real-tool recon pipeline across
all 7 phases. Binaries resolve from PATH first, then the project-local recon bin
(tools/recon_bin), then ALPHA_TOOL_ROOT (D:\\projects), Go bin, and pip Scripts.

The §7 document lists the primary 25-tool baseline; this registry extends it to
the full 39-tool arsenal the user requires Alpha to drive (adds assetfinder,
github-subdomains, puredns, cdncheck, masscan, testssl, httprobe, whatweb,
wafw00f, gospider, arjun, paramspider, aquatone, dalfox).
"""
from __future__ import annotations
import shutil
from pathlib import Path
from backend.core.config import settings


RECON_TOOLS = {
    # ── Phase 1: Passive Intelligence ──────────────────────────────────────
    "subfinder":        {"phase": "passive_intelligence",    "binary": "subfinder",         "modes": ["PASSIVE_ONLY", "STANDARD", "AGGRESSIVE"]},
    "amass":            {"phase": "passive_intelligence",    "binary": "amass",             "modes": ["PASSIVE_ONLY", "STANDARD", "AGGRESSIVE"]},
    "assetfinder":      {"phase": "passive_intelligence",    "binary": "assetfinder",       "modes": ["PASSIVE_ONLY", "STANDARD", "AGGRESSIVE"]},
    "github-subdomains":{"phase": "passive_intelligence",    "binary": "github-subdomains", "modes": ["PASSIVE_ONLY", "STANDARD", "AGGRESSIVE"]},
    "gau":              {"phase": "passive_intelligence",    "binary": "gau",               "modes": ["PASSIVE_ONLY", "STANDARD", "AGGRESSIVE"]},
    "waybackurls":      {"phase": "passive_intelligence",    "binary": "waybackurls",       "modes": ["PASSIVE_ONLY", "STANDARD", "AGGRESSIVE"]},
    "cloudlist":        {"phase": "passive_intelligence",    "binary": "cloudlist",         "modes": ["STANDARD", "AGGRESSIVE"]},
    "spiderfoot":       {"phase": "passive_intelligence",    "binary": "python",            "modes": ["AGGRESSIVE"]},
    # ── Phase 2: DNS & Infrastructure ──────────────────────────────────────
    "dnsx":         {"phase": "dns_infrastructure",      "binary": "dnsx",         "modes": ["STANDARD", "AGGRESSIVE"]},
    "shuffledns":   {"phase": "dns_infrastructure",      "binary": "shuffledns",   "modes": ["AGGRESSIVE"]},
    "puredns":      {"phase": "dns_infrastructure",      "binary": "puredns",      "modes": ["AGGRESSIVE"]},
    "cdncheck":     {"phase": "dns_infrastructure",      "binary": "cdncheck",     "modes": ["STANDARD", "AGGRESSIVE"]},
    "naabu":        {"phase": "dns_infrastructure",      "binary": "naabu",        "modes": ["STANDARD", "AGGRESSIVE"]},
    "masscan":      {"phase": "dns_infrastructure",      "binary": "masscan",      "modes": ["AGGRESSIVE"]},
    "nmap":         {"phase": "dns_infrastructure",      "binary": "nmap",         "modes": ["AGGRESSIVE"]},
    "tlsx":         {"phase": "dns_infrastructure",      "binary": "tlsx",         "modes": ["STANDARD", "AGGRESSIVE"]},
    "testssl":      {"phase": "dns_infrastructure",      "binary": "testssl.sh",   "modes": ["AGGRESSIVE"]},
    # ── Phase 3: HTTP & Browser Intelligence ───────────────────────────────
    "httpx":        {"phase": "http_browser_intelligence","binary": "httpx",       "modes": ["STANDARD", "AGGRESSIVE"]},
    "httprobe":     {"phase": "http_browser_intelligence","binary": "httprobe",    "modes": ["STANDARD", "AGGRESSIVE"]},
    "whatweb":      {"phase": "http_browser_intelligence","binary": "whatweb",     "modes": ["STANDARD", "AGGRESSIVE"]},
    "wafw00f":      {"phase": "http_browser_intelligence","binary": "wafw00f",     "modes": ["STANDARD", "AGGRESSIVE"]},
    "katana":       {"phase": "http_browser_intelligence","binary": "katana",      "modes": ["STANDARD", "AGGRESSIVE"]},
    "gospider":     {"phase": "http_browser_intelligence","binary": "gospider",    "modes": ["STANDARD", "AGGRESSIVE"]},
    "hakrawler":    {"phase": "http_browser_intelligence","binary": "hakrawler",   "modes": ["STANDARD", "AGGRESSIVE"]},
    "linkfinder":   {"phase": "http_browser_intelligence","binary": "python",      "modes": ["STANDARD", "AGGRESSIVE"]},
    "secretfinder": {"phase": "http_browser_intelligence","binary": "python",      "modes": ["STANDARD", "AGGRESSIVE"]},
    "arjun":        {"phase": "http_browser_intelligence","binary": "arjun",       "modes": ["STANDARD", "AGGRESSIVE"]},
    "paramspider":  {"phase": "http_browser_intelligence","binary": "python",      "modes": ["STANDARD", "AGGRESSIVE"]},
    # ── Phase 4: Directory & Route Discovery ───────────────────────────────
    "feroxbuster":  {"phase": "directory_route_discovery","binary": "feroxbuster", "modes": ["STANDARD", "AGGRESSIVE"]},
    "ffuf":         {"phase": "directory_route_discovery","binary": "ffuf",        "modes": ["STANDARD", "AGGRESSIVE"]},
    "dirsearch":    {"phase": "directory_route_discovery","binary": "python",      "modes": ["STANDARD", "AGGRESSIVE"]},
    "gobuster":     {"phase": "directory_route_discovery","binary": "gobuster",    "modes": ["STANDARD", "AGGRESSIVE"]},
    # ── Phase 5: API Reconnaissance ────────────────────────────────────────
    "kiterunner":   {"phase": "api_reconnaissance",      "binary": "kr",           "modes": ["STANDARD", "AGGRESSIVE"]},
    "inql":         {"phase": "api_reconnaissance",      "binary": "python",       "modes": ["AGGRESSIVE"]},
    # ── Phase 6: Visual Documentation ──────────────────────────────────────
    "gowitness":    {"phase": "visual_documentation",    "binary": "gowitness",    "modes": ["STANDARD", "AGGRESSIVE"]},
    "aquatone":     {"phase": "visual_documentation",    "binary": "aquatone",     "modes": ["STANDARD", "AGGRESSIVE"]},
    # ── Phase 7: Template Validation ───────────────────────────────────────
    "nuclei":       {"phase": "template_validation",     "binary": "nuclei",       "modes": ["STANDARD", "AGGRESSIVE"]},
    "dalfox":       {"phase": "template_validation",     "binary": "dalfox",       "modes": ["AGGRESSIVE"]},
    "interactsh":   {"phase": "template_validation",     "binary": "interactsh-client", "modes": ["AGGRESSIVE"]},
}


def check_tool_availability(name: str) -> dict:
    """Check if a tool is installed and accessible.

    Resolution order (Architecture §7 rule 2 + project-local integration):
      1. System PATH.
      2. Project-local recon bin: tools/recon_bin/ (installed by the recon
         installer script — keeps all 39 tools inside the project).
      3. ALPHA_TOOL_ROOT (D:\\projects) — binary, binary.exe, binary/binary.
      4. Go bin (~/go/bin) and Python Scripts dir (pip console scripts).
      5. Vendored Python scripts under the tool root for git-only tools.
    """
    spec = RECON_TOOLS.get(name)
    if not spec:
        return {"installed": False, "reason": f"unknown_tool:{name}"}
    binary = spec["binary"]
    tool_root = Path(getattr(settings, "ALPHA_TOOL_ROOT", r"D:\projects"))
    project_bin = Path(getattr(settings, "PROJECT_ROOT", ".")) / "tools" / "recon_bin"

    # 0. Docker recon image (Architecture §7 rule 3): when Docker + the bundled
    # recon image are ready, every arsenal tool is available with no host
    # install. This is the preferred backend for Linux-native tools on Windows.
    try:
        from backend.tools.recon.docker_runtime import DOCKER_RECON_TOOLS, docker_recon_ready
        if name in DOCKER_RECON_TOOLS and docker_recon_ready():
            return {"installed": True, "path": "docker://vigilagent-recon", "source": "docker"}
    except Exception:
        pass

    # 1. System PATH
    path = shutil.which(binary)
    if path:
        return {"installed": True, "path": path, "source": "PATH"}

    # 2. Project-local recon bin (in-repo integration)
    for cand in (project_bin / binary, project_bin / f"{binary}.exe"):
        if cand.exists():
            return {"installed": True, "path": str(cand), "source": "project_bin"}

    # 3. Tool root (D:\projects): binary, binary.exe, binary/binary[.exe]
    for cand in (tool_root / binary, tool_root / f"{binary}.exe",
                 tool_root / binary / binary, tool_root / binary / f"{binary}.exe"):
        if cand.exists():
            return {"installed": True, "path": str(cand), "source": "tool_root"}

    # 4. Go bin + Python Scripts dir
    import os
    go_bin = Path(os.path.expanduser("~")) / "go" / "bin"
    for cand in (go_bin / binary, go_bin / f"{binary}.exe"):
        if cand.exists():
            return {"installed": True, "path": str(cand), "source": "go_bin"}
    try:
        import sysconfig
        scripts_dir = Path(sysconfig.get_path("scripts"))
        for cand in (scripts_dir / binary, scripts_dir / f"{binary}.exe"):
            if cand.exists():
                return {"installed": True, "path": str(cand), "source": "pip_scripts"}
    except Exception:
        pass

    # 5. Vendored / git-only Python scripts
    if binary == "python":
        script_map = {
            "linkfinder": [tool_root / "LinkFinder" / "linkfinder.py", project_bin / "LinkFinder" / "linkfinder.py"],
            "secretfinder": [tool_root / "SecretFinder" / "SecretFinder.py", project_bin / "SecretFinder" / "SecretFinder.py"],
            "dirsearch": [tool_root / "dirsearch" / "dirsearch.py", project_bin / "dirsearch" / "dirsearch.py"],
            "inql": [tool_root / "inql" / "inql.py", project_bin / "inql" / "inql.py"],
            "spiderfoot": [tool_root / "spiderfoot" / "sf.py", project_bin / "spiderfoot" / "sf.py"],
            "paramspider": [tool_root / "ParamSpider" / "paramspider.py", project_bin / "ParamSpider" / "paramspider.py"],
        }
        for script in script_map.get(name, []):
            if script.exists():
                return {"installed": True, "path": str(script), "source": "python_script"}
        return {"installed": False, "reason": f"script_not_found:{name}"}

    return {"installed": False, "reason": f"binary_not_in_path:{binary}"}

