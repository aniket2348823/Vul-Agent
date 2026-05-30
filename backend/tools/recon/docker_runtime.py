"""
Vigilagent Recon Docker Runtime (Architecture §7 rule 3, §8).

Linux-native recon tools (nmap, masscan, nuclei, subfinder, ...) are bundled
into a single recon image so the full 39-tool arsenal runs identically on any
host — with NO per-host installs — exactly as §7 rule 3 requires:

    "Docker execution is preferred for Linux-native tools when running on
     Windows."

This module is the bridge between a ReconCommand (host argv + host paths) and a
`docker run` invocation:

  - mounts the scan artifact dir (host raw_dir) at /scan,
  - mounts the tool root (D:\\projects: SecLists, wordlists, vendored scripts)
    read-only at /tools,
  - rewrites every host path embedded in argv to its container path,
  - runs the tool inside the recon image with a bounded, recon-appropriate
    network policy (bridge — recon needs network, unlike the exploit sandbox
    which is network=none).

Execution still flows through the governed TerminalEngine: guardrails, scope
extraction, budget, watchdog, and audit all run on the original host argv before
this module ever builds a container command.
"""
from __future__ import annotations

import functools
import os
import shutil
import subprocess
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Sequence

from backend.core.config import settings

# Container mount points.
SCAN_MNT = "/scan"
TOOLS_MNT = "/tools"


def recon_image() -> str:
    """The recon tool image name (configurable)."""
    return (
        os.getenv("VIGILAGENT_RECON_IMAGE")
        or getattr(settings, "RECON_DOCKER_IMAGE", None)
        or "vigilagent/recon:latest"
    )


def recon_network() -> str:
    """Container network for recon (bridge by default; recon needs network)."""
    return os.getenv("VIGILAGENT_RECON_DOCKER_NETWORK", "bridge")


@functools.lru_cache(maxsize=1)
def docker_daemon_available() -> bool:
    """True when the docker CLI exists AND the daemon answers."""
    if shutil.which("docker") is None:
        return False
    try:
        p = subprocess.run(["docker", "info", "--format", "{{.OSType}}"],
                           capture_output=True, text=True, timeout=15)
        return p.returncode == 0 and "linux" in (p.stdout or "").lower()
    except Exception:
        return False


@functools.lru_cache(maxsize=8)
def recon_image_present(image: str | None = None) -> bool:
    """True when the recon image exists locally (docker image inspect)."""
    img = image or recon_image()
    if shutil.which("docker") is None:
        return False
    try:
        p = subprocess.run(["docker", "image", "inspect", img],
                           capture_output=True, text=True, timeout=15)
        return p.returncode == 0
    except Exception:
        return False


def docker_recon_ready() -> bool:
    """True when both the daemon and the recon image are available."""
    return docker_daemon_available() and recon_image_present()


def _container_name_env() -> str:
    return os.getenv("VIGILAGENT_RECON_CONTAINER", "")


@functools.lru_cache(maxsize=1)
def _running_recon_container_cached(image: str, override: str) -> str:
    """Find a RUNNING container started from the recon image (cached).

    Some Docker Desktop setups hit an overlay/layer bug where fresh
    ``docker run`` of an image fails with "cannot execute binary file" while a
    long-lived container from the SAME image runs fine. When such a container is
    already up we exec into it instead of spawning fresh ones — more reliable and
    faster (no per-tool container spin-up). Returns the container name or "".
    """
    if shutil.which("docker") is None:
        return ""
    # 1. Explicit override (VIGILAGENT_RECON_CONTAINER) wins if it is running.
    if override:
        try:
            p = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", override],
                               capture_output=True, text=True, timeout=10)
            if p.returncode == 0 and "true" in (p.stdout or "").lower():
                return override
        except Exception:
            pass
    # 2. Otherwise pick the first running container based on the recon image.
    try:
        p = subprocess.run(
            ["docker", "ps", "--filter", f"ancestor={image}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10)
        if p.returncode == 0:
            names = [n.strip() for n in (p.stdout or "").splitlines() if n.strip()]
            if names:
                return names[0]
    except Exception:
        pass
    return ""


def running_recon_container() -> str:
    """Name of a running recon container to exec into, or "" if none."""
    return _running_recon_container_cached(recon_image(), _container_name_env())


def reset_container_cache() -> None:
    """Clear the running-container cache (after start/stop)."""
    _running_recon_container_cached.cache_clear()


# Container-internal working dir for exec-based runs (output written here then
# copied back to the host artifact path).
EXEC_WORKDIR = "/scan"


def build_exec_argv(
    inner_argv: Sequence[str],
    *,
    container: str,
    raw_dir: Path,
    tool_root: Path,
    container_out: str,
) -> list[str]:
    """Build a ``docker exec`` argv that runs a recon tool inside a RUNNING
    container, rewriting host paths to the container's /scan + /tools layout.

    The running container does not bind-mount the host scan dir, so output is
    written under the container's EXEC_WORKDIR and copied back by the caller via
    ``docker cp``. Tool-root paths (wordlists/vendored scripts) are rewritten to
    /tools and expected to be present in the image.
    """
    raw_dir = raw_dir.resolve()
    container_argv = _rewrite_for_exec(inner_argv, raw_dir, tool_root, container_out)
    return ["docker", "exec", "-w", EXEC_WORKDIR, container, *container_argv]


def _rewrite_for_exec(argv: Sequence[str], raw_dir: Path, tool_root: Path,
                      container_out: str) -> list[str]:
    """Rewrite host paths for the exec backend: raw_dir paths -> /scan/<name>,
    tool_root paths -> /tools/<rel>. Other tokens pass through unchanged."""
    raw_s = str(raw_dir)
    tool_s = str(tool_root)
    out: list[str] = []
    for tok in argv:
        s = str(tok)
        low = s.lower()
        if low.startswith(raw_s.lower()):
            rel = s[len(raw_s):].lstrip("\\/")
            out.append(f"{EXEC_WORKDIR}/{PureWindowsPath(rel).as_posix()}".rstrip("/"))
        elif low.startswith(tool_s.lower()):
            rel = s[len(tool_s):].lstrip("\\/")
            out.append(f"{TOOLS_MNT}/{PureWindowsPath(rel).as_posix()}".rstrip("/"))
        else:
            out.append(s)
    return out


# Tools that live INSIDE the recon image. The image is built to carry the full
# arsenal, so this mirrors the registry. Kept explicit so availability can be
# answered without shelling into the container.
DOCKER_RECON_TOOLS: set[str] = {
    "subfinder", "amass", "assetfinder", "github-subdomains", "gau", "waybackurls",
    "cloudlist", "spiderfoot", "dnsx", "shuffledns", "puredns", "cdncheck",
    "naabu", "masscan", "nmap", "tlsx", "testssl", "httpx", "httprobe",
    "whatweb", "wafw00f", "katana", "gospider", "hakrawler", "linkfinder",
    "secretfinder", "arjun", "paramspider", "feroxbuster", "ffuf", "dirsearch",
    "gobuster", "kiterunner", "inql", "gowitness", "aquatone", "nuclei",
    "dalfox", "interactsh",
}


def _to_container_path(host_path: str, raw_dir: Path, tool_root: Path) -> str | None:
    """Map a host path under raw_dir/tool_root to its container path, else None."""
    try:
        hp = Path(host_path)
    except Exception:
        return None
    raw_s, tool_s = str(raw_dir), str(tool_root)
    # Normalize for case-insensitive Windows prefix comparison.
    host_norm = host_path.replace("/", "\\") if "\\" in raw_s else host_path

    def _rel_posix(child: str, parent: str) -> str:
        rel = child[len(parent):].lstrip("\\/")
        return PureWindowsPath(rel).as_posix() if "\\" in child else PurePosixPath(rel).as_posix()

    if host_norm.lower().startswith(raw_s.lower()):
        return f"{SCAN_MNT}/{_rel_posix(host_norm, raw_s)}".rstrip("/")
    if host_norm.lower().startswith(tool_s.lower()):
        return f"{TOOLS_MNT}/{_rel_posix(host_norm, tool_s)}".rstrip("/")
    return None


def rewrite_argv(argv: Sequence[str], raw_dir: Path, tool_root: Path) -> list[str]:
    """Rewrite host paths embedded in argv tokens to their container paths."""
    out: list[str] = []
    for tok in argv:
        s = str(tok)
        mapped = _to_container_path(s, raw_dir, tool_root)
        out.append(mapped if mapped is not None else s)
    return out


def build_docker_argv(
    inner_argv: Sequence[str],
    *,
    raw_dir: Path,
    tool_root: Path,
    scan_id: str = "GLOBAL",
    image: str | None = None,
    network: str | None = None,
    memory: str = "1g",
    cpus: str = "2.0",
) -> list[str]:
    """Build the full `docker run ...` argv for a recon tool.

    The scan dir is mounted read-write at /scan; the tool root (wordlists,
    vendored scripts) is mounted read-only at /tools. argv host paths are
    rewritten to container paths.
    """
    img = image or recon_image()
    net = network or recon_network()
    raw_dir = raw_dir.resolve()
    tool_root = Path(tool_root)
    raw_dir.mkdir(parents=True, exist_ok=True)

    container_argv = rewrite_argv(inner_argv, raw_dir, tool_root)
    name = f"vigil-recon-{scan_id.lower().replace('/', '-')}-{os.urandom(4).hex()}"

    docker_argv = [
        "docker", "run", "--rm", "--name", name,
        "--network", net,
        "--memory", memory,
        "--cpus", cpus,
        "-v", f"{raw_dir}:{SCAN_MNT}",
    ]
    if tool_root.exists():
        docker_argv += ["-v", f"{tool_root}:{TOOLS_MNT}:ro"]
    # Pass through optional credentials some tools use, when present.
    for env_key in ("GITHUB_TOKEN",):
        if os.getenv(env_key):
            docker_argv += ["-e", env_key]
    docker_argv += ["-w", SCAN_MNT, img]
    docker_argv += container_argv
    return docker_argv
