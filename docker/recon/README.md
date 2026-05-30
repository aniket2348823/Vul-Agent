# Vigilagent Recon Arsenal Image

Bundles the full 39-tool recon arsenal into one Linux image so Alpha (the recon
commander) runs every tool identically on any host — with **no per-host
installs** — exactly as Architecture §7 rule 3 requires:

> "Docker execution is preferred for Linux-native tools when running on Windows."

## Build

```bash
# from the project root
python scripts/install_recon_tools.py --docker
# or directly
docker build -t vigilagent/recon:latest docker/recon
```

The build is multi-stage: a `golang` stage compiles the ProjectDiscovery +
community Go tools, then a slim `debian` runtime adds the apt tools
(nmap, masscan, amass, whatweb), feroxbuster, the pipx Python tools
(arjun, wafw00f, dirsearch, spiderfoot), testssl.sh, and the vendored Python
scripts (LinkFinder, SecretFinder, inql, ParamSpider).

## How the runtime uses it

When `TERMINAL_PREFER_DOCKER=true` (default) and the daemon + image are ready,
the `TerminalEngine` Docker backend (`backend/core/terminal_engine.py`) runs each
recon tool in this image:

- scan artifact dir mounted **read-write** at `/scan`
- tool root (`D:\projects`: SecLists, wordlists, vendored data) mounted
  **read-only** at `/tools`
- host paths in argv rewritten to container paths
  (`backend/tools/recon/docker_runtime.py`)
- network = `bridge` (recon needs network), with `--memory`/`--cpus` caps

Every command still passes the governed pipeline first: guardrails (argv-only,
no shell metacharacters), scope extraction, budget, watchdog, and audit.

## Availability

With the image built, `check_tool_availability()` reports `source: docker` for
all 39 tools — they are available even when nothing is installed on the host.

```bash
python scripts/install_recon_tools.py --check
```

## Configuration

| Env var | Default | Meaning |
|---------|---------|---------|
| `VIGILAGENT_RECON_IMAGE` / `RECON_DOCKER_IMAGE` | `vigilagent/recon:latest` | image name |
| `VIGILAGENT_RECON_DOCKER_NETWORK` / `RECON_DOCKER_NETWORK` | `bridge` | container network |
| `TERMINAL_PREFER_DOCKER` | `true` | prefer Docker backend over local |
