"""
Alpha V6 Target-Specific Wordlist Builder.

Builds customized wordlists from:
- Discovered path segments
- Historical URL patterns
- Framework-specific vocabulary
- SecLists/Assetnote base lists
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.core.config import settings


class WordlistBuilder:
    """Builds target-specific wordlists from recon intelligence."""

    def __init__(self, tool_root: Path | None = None):
        self.tool_root = tool_root or Path(getattr(settings, "ALPHA_TOOL_ROOT", r"D:\projects"))

    def build(self, *, raw_dir: Path, discovered_paths: list[str],
              historical_urls: list[str], technologies: list[str]) -> Path:
        """Build a merged, deduplicated wordlist."""
        words: set[str] = set()

        # 1. Extract path segments from discovered paths
        for path in discovered_paths:
            segments = [s for s in path.strip("/").split("/") if s and len(s) < 50]
            words.update(segments)

        # 2. Extract from historical URLs
        for url in historical_urls:
            m = re.search(r'https?://[^/]+(/[^?#]*)', url)
            if m:
                segments = [s for s in m.group(1).strip("/").split("/") if s and len(s) < 50]
                words.update(segments)

        # 3. Framework-specific vocabulary
        for tech in technologies:
            words.update(self._framework_words(tech.lower()))

        # 4. Common API prefixes
        words.update(["api", "v1", "v2", "v3", "graphql", "rest", "internal",
                       "admin", "auth", "login", "debug", "health", "status",
                       "config", "settings", "backup", "export", "upload",
                       "swagger", "docs", "openapi", "actuator", "metrics"])

        # 5. Load base wordlists (partial, deduplicated)
        base_lists = [
            self.tool_root / "SecLists" / "Discovery" / "Web-Content" / "api" / "api-endpoints-res.txt",
            self.tool_root / "SecLists" / "Discovery" / "Web-Content" / "common.txt",
        ]
        for wl in base_lists:
            if wl.exists():
                for line in wl.read_text(encoding="utf-8", errors="replace").splitlines()[:5000]:
                    w = line.strip().strip("/")
                    if w and not w.startswith("#") and len(w) < 100:
                        words.add(w)

        # Write merged wordlist
        output = raw_dir / "alpha_custom_wordlist.txt"
        output.parent.mkdir(parents=True, exist_ok=True)
        sorted_words = sorted(words)
        output.write_text("\n".join(sorted_words) + "\n", encoding="utf-8")
        return output

    def _framework_words(self, tech: str) -> set[str]:
        """Technology-specific paths."""
        fw: dict[str, set[str]] = {
            "wordpress": {"wp-admin", "wp-login.php", "wp-content", "wp-includes",
                          "wp-json", "xmlrpc.php", "wp-cron.php"},
            "django": {"admin", "api", "static", "media", "__debug__", "accounts"},
            "rails": {"rails", "assets", "admin", "api", "sidekiq", "letter_opener"},
            "spring": {"actuator", "health", "info", "metrics", "beans", "env",
                        "configprops", "mappings", "trace", "jolokia"},
            "laravel": {"api", "storage", "telescope", "horizon", "_debugbar", "sanctum"},
            "express": {"api", "auth", "graphql", "socket.io", "health"},
            "flask": {"api", "static", "admin", "debug", "swagger"},
            "nextjs": {"_next", "api", "__nextjs_original-stack-frame"},
            "graphql": {"graphql", "graphiql", "playground", "altair", "voyager"},
            "openapi": {"swagger", "api-docs", "openapi.json", "swagger.json", "swagger-ui"},
        }
        result: set[str] = set()
        for key, paths in fw.items():
            if key in tech:
                result.update(paths)
        return result
