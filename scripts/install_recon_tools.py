#!/usr/bin/env python3
"""
Vigilagent Recon Tool Installer (Architecture §7)
================================================================================
Installs the full 39-tool recon arsenal INTO the project so Alpha (the recon
commander) can run all of them. Tools land in:

  - Go tools     -> GOBIN = <project>/tools/recon_bin
  - pip tools    -> current environment (resolved via Scripts dir)
  - git tools    -> <project>/tools/recon_bin/<repo>

Run:  python scripts/install_recon_tools.py            (install everything)
      python scripts/install_recon_tools.py --check    (report availability only)
      python scripts/install_recon_tools.py --only nuclei,httpx

This is reproducible and offline-friendly: tools already present are skipped.
Requires `go`, `pip`, and `git` on PATH for the respective tool classes; any
missing toolchain is reported, not fatal.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECON_BIN = PROJECT_ROOT / "tools" / "recon_bin"

# Go-installable tools: name -> go install path (@latest).
GO_TOOLS = {
    "subfinder": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    "dnsx": "github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
    "naabu": "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest",
    "tlsx": "github.com/projectdiscovery/tlsx/cmd/tlsx@latest",
    "httpx": "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "katana": "github.com/projectdiscovery/katana/cmd/katana@latest",
    "nuclei": "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    "interactsh-client": "github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest",
    "shuffledns": "github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest",
    "cdncheck": "github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest",
    "cloudlist": "github.com/projectdiscovery/cloudlist/cmd/cloudlist@latest",
    "gau": "github.com/lc/gau/v2/cmd/gau@latest",
    "waybackurls": "github.com/tomnomnom/waybackurls@latest",
    "assetfinder": "github.com/tomnomnom/assetfinder@latest",
    "httprobe": "github.com/tomnomnom/httprobe@latest",
    "hakrawler": "github.com/hakluke/hakrawler@latest",
    "gobuster": "github.com/OJ/gobuster/v3@latest",
    "ffuf": "github.com/ffuf/ffuf/v2@latest",
    "gowitness": "github.com/sensepost/gowitness@latest",
    "dalfox": "github.com/hahwul/dalfox/v2@latest",
    "gospider": "github.com/jaeles-project/gospider@latest",
    "puredns": "github.com/d3mondev/puredns/v2@latest",
    "github-subdomains": "github.com/gwen001/github-subdomains@latest",
}

# Go tools that must be built from a cloned source tree (non-standard module
# layout). name -> (repo URL, build subdir relative to clone, output binary).
GO_SOURCE_TOOLS = {
    "kr": ("https://github.com/assetnote/kiterunner.git", "cmd/kiterunner", "kr"),
}

# pip-installable tools: name -> pip package.
PIP_TOOLS = {
    "arjun": "arjun",
    "dirsearch": "dirsearch",
    "wafw00f": "wafw00f",
    "spiderfoot": "spiderfoot",
}

# git-clone tools: name -> repo URL (Python scripts run via `python`).
GIT_TOOLS = {
    "LinkFinder": "https://github.com/GerbenJavado/LinkFinder.git",
    "SecretFinder": "https://github.com/m4ll0k/SecretFinder.git",
    "inql": "https://github.com/doyensec/inql.git",
    "ParamSpider": "https://github.com/devanshbatham/ParamSpider.git",
}

# Cargo (Rust) tools.
CARGO_TOOLS = {
    "feroxbuster": "feroxbuster",
}

# Tools that must be installed via the OS package manager / vendor download.
MANUAL_TOOLS = {
    "amass": "https://github.com/owasp-amass/amass (snap/brew/go releases)",
    "nmap": "https://nmap.org/download.html",
    "masscan": "https://github.com/robertdavidgraham/masscan",
    "whatweb": "https://github.com/urbanadventurer/WhatWeb (ruby)",
    "testssl.sh": "https://github.com/drwetter/testssl.sh",
}


def _run(cmd: list[str], env=None) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
        return p.returncode == 0, (p.stdout + p.stderr)[-500:]
    except Exception as exc:
        return False, str(exc)


def install_go_tools(only: set[str] | None) -> dict:
    results = {}
    if shutil.which("go") is None:
        return {k: "go-not-installed" for k in GO_TOOLS}
    env = dict(os.environ)
    env["GOBIN"] = str(RECON_BIN)
    RECON_BIN.mkdir(parents=True, exist_ok=True)
    for name, path in GO_TOOLS.items():
        if only and name not in only:
            continue
        ok, msg = _run(["go", "install", "-v", path], env=env)
        results[name] = "installed" if ok else f"failed: {msg[-120:]}"
    return results


def install_go_source_tools(only: set[str] | None) -> dict:
    """Build Go tools that need a cloned source tree (e.g. kiterunner)."""
    results = {}
    if shutil.which("go") is None:
        return {k: "go-not-installed" for k in GO_SOURCE_TOOLS}
    if shutil.which("git") is None:
        return {k: "git-not-installed" for k in GO_SOURCE_TOOLS}
    RECON_BIN.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["GOFLAGS"] = "-buildvcs=false"
    for name, (url, subdir, out) in GO_SOURCE_TOOLS.items():
        if only and name not in only:
            continue
        out_path = RECON_BIN / (out + (".exe" if os.name == "nt" else ""))
        if out_path.exists():
            results[name] = "already-built"
            continue
        clone_dir = RECON_BIN / f"_src_{name}"
        if not clone_dir.exists():
            ok, msg = _run(["git", "clone", "--depth", "1", url, str(clone_dir)])
            if not ok:
                results[name] = f"clone-failed: {msg[-120:]}"
                continue
        build_dir = clone_dir / subdir
        ok, msg = _run_in(["go", "build", "-o", str(out_path), "."], cwd=build_dir, env=env)
        results[name] = "built" if out_path.exists() else f"failed: {msg[-160:]}"
    return results


def _run_in(cmd: list[str], cwd, env=None) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(cwd), timeout=900)
        return p.returncode == 0, (p.stdout + p.stderr)[-500:]
    except Exception as exc:
        return False, str(exc)


def install_pip_tools(only: set[str] | None) -> dict:
    results = {}
    for name, pkg in PIP_TOOLS.items():
        if only and name not in only:
            continue
        ok, msg = _run([sys.executable, "-m", "pip", "install", "--quiet", pkg])
        results[name] = "installed" if ok else f"failed: {msg[-120:]}"
    return results


def install_cargo_tools(only: set[str] | None) -> dict:
    results = {}
    if shutil.which("cargo") is None:
        return {k: "cargo-not-installed" for k in CARGO_TOOLS}
    for name, crate in CARGO_TOOLS.items():
        if only and name not in only:
            continue
        ok, msg = _run(["cargo", "install", "--root", str(RECON_BIN.parent), crate])
        results[name] = "installed" if ok else f"failed: {msg[-120:]}"
    return results


def install_git_tools(only: set[str] | None) -> dict:
    results = {}
    if shutil.which("git") is None:
        return {k: "git-not-installed" for k in GIT_TOOLS}
    RECON_BIN.mkdir(parents=True, exist_ok=True)
    for name, url in GIT_TOOLS.items():
        if only and name not in only:
            continue
        dest = RECON_BIN / name
        if dest.exists():
            results[name] = "already-cloned"
            continue
        ok, msg = _run(["git", "clone", "--depth", "1", url, str(dest)])
        results[name] = "cloned" if ok else f"failed: {msg[-120:]}"
    return results


def check_availability() -> dict:
    from backend.tools.recon.registry import RECON_TOOLS, check_tool_availability
    report = {}
    for name in RECON_TOOLS:
        a = check_tool_availability(name)
        report[name] = "OK:" + a.get("source", "") if a.get("installed") else "MISSING"
    return report


def build_docker_image() -> int:
    """Build the bundled recon arsenal image (Architecture §7 rule 3).

    This gives the full 39-tool arsenal on any host with a Docker daemon and
    NO per-host installs. Returns the docker build exit code.
    """
    if shutil.which("docker") is None:
        print("[installer] docker not found on PATH; cannot build the recon image.")
        return 127
    image = os.getenv("VIGILAGENT_RECON_IMAGE", "vigilagent/recon:latest")
    ctx = PROJECT_ROOT / "docker" / "recon"
    print(f"[installer] building recon image '{image}' from {ctx} ...")
    try:
        p = subprocess.run(["docker", "build", "-t", image, str(ctx)], timeout=3600)
        if p.returncode == 0:
            print(f"[installer] built {image}. Recon now runs fully in Docker.")
        else:
            print(f"[installer] docker build failed (exit {p.returncode}).")
        return p.returncode
    except Exception as exc:
        print(f"[installer] docker build error: {exc}")
        return 1


def main():
    ap = argparse.ArgumentParser(description="Install the 39-tool recon arsenal into the project.")
    ap.add_argument("--check", action="store_true", help="Only report availability.")
    ap.add_argument("--only", help="Comma-separated tool names to install.")
    ap.add_argument("--docker", action="store_true",
                    help="Build the bundled recon Docker image (full arsenal, no host installs).")
    args = ap.parse_args()

    sys.path.insert(0, str(PROJECT_ROOT))

    if args.docker:
        rc = build_docker_image()
        print("\n[installer] Availability after docker build:")
        for name, status in check_availability().items():
            print(f"  {name:22} {status}")
        sys.exit(rc)

    if args.check:
        for name, status in check_availability().items():
            print(f"  {name:22} {status}")
        return

    only = set(args.only.split(",")) if args.only else None
    print(f"[installer] target bin: {RECON_BIN}")
    print("[installer] Go tools...");        go = install_go_tools(only)
    print("[installer] Go source tools..."); gosrc = install_go_source_tools(only)
    print("[installer] pip tools...");       pip = install_pip_tools(only)
    print("[installer] cargo tools...");     cargo = install_cargo_tools(only)
    print("[installer] git tools...");       git = install_git_tools(only)

    for group, res in (("go", go), ("go-src", gosrc), ("pip", pip), ("cargo", cargo), ("git", git)):
        for name, status in res.items():
            print(f"  [{group}] {name:22} {status}")

    if MANUAL_TOOLS:
        print("\n[installer] Manual install required for:")
        for name, where in MANUAL_TOOLS.items():
            print(f"  {name:22} {where}")

    print("\n[installer] Final availability:")
    for name, status in check_availability().items():
        print(f"  {name:22} {status}")


if __name__ == "__main__":
    main()
