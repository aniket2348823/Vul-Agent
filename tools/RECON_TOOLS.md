# Vigilagent Recon Arsenal — 39 Tools (Architecture §7)

Alpha is the recon commander. It drives the full real-tool recon pipeline across
7 phases. This document tracks the complete 39-tool arsenal, how each tool is
installed, and how Alpha resolves it at runtime.

> DVWA (in `D:\projects\dvwa`) is a **vulnerable target application**, not a recon
> tool. It is intentionally **excluded** from the recon registry. The arsenal is
> 39 genuine recon tools.

## Install

```bash
python scripts/install_recon_tools.py            # install everything available
python scripts/install_recon_tools.py --check     # report availability only
python scripts/install_recon_tools.py --only nuclei,httpx
```

- **Go tools** build into `tools/recon_bin/` (set as `GOBIN`). Requires Go on PATH.
- **pip tools** install into the active Python environment (resolved via the
  Scripts dir).
- **git/python tools** clone into `tools/recon_bin/<repo>` and run via `python`.
- `tools/recon_bin/` is gitignored — binaries are reproducible, not committed.

## Runtime resolution order (`registry.check_tool_availability`)

1. System `PATH`
2. Project-local `tools/recon_bin/`
3. `ALPHA_TOOL_ROOT` (`D:\projects`) — `bin`, `bin.exe`, `bin/bin[.exe]`
4. Go bin (`~/go/bin`) and pip Scripts dir
5. Vendored Python scripts (LinkFinder, SecretFinder, dirsearch, inql,
   spiderfoot, ParamSpider)

## The 39 tools by phase

| Phase | Tools |
|-------|-------|
| 1 Passive Intelligence | subfinder, amass, assetfinder, github-subdomains, gau, waybackurls, cloudlist, spiderfoot |
| 2 DNS & Infrastructure | dnsx, shuffledns, puredns, cdncheck, naabu, masscan, nmap, tlsx, testssl |
| 3 HTTP & Browser Intel | httpx, httprobe, whatweb, wafw00f, katana, gospider, hakrawler, linkfinder, secretfinder, arjun, paramspider |
| 4 Directory & Route | feroxbuster, ffuf, dirsearch, gobuster |
| 5 API Recon | kiterunner (kr), inql |
| 6 Visual Documentation | gowitness, aquatone |
| 7 Template Validation | nuclei, dalfox, interactsh |

Every tool has: a registry entry (`backend/tools/recon/registry.py`), a command
builder (`backend/tools/recon/commands.py`), an output parser
(`backend/parsers/recon/`), and a guardrail allowlist entry
(`backend/tools/recon/guardrails.py`).

## Tools requiring manual install

These cannot be installed via Go/pip/cargo and need a system toolchain:

- `masscan` — needs a C compiler + raw-socket privileges
  (https://github.com/robertdavidgraham/masscan)
- `testssl.sh` — bash script (https://github.com/drwetter/testssl.sh)
- `whatweb` — Ruby (https://github.com/urbanadventurer/WhatWeb)

When absent, Alpha records them as `tools_skipped` and continues — the pipeline
degrades gracefully.
