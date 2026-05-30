"""
Alpha Unified — Browser Recon Module (Architecture §5.1.1, §5.1)
================================================================================
Legacy Alpha browser-intelligence behaviors, merged INTO the Alpha V6 runtime
spine as a module (Architecture §5.1.1: "Move useful legacy Alpha behaviors into
Alpha V6 as modules"). This eliminates the second recon orchestration path that
previously lived in agents/alpha.py.

Provides browser-aware recon (Architecture §5.1.1 Alpha Unified responsibilities):
  - SPA detection (React/Vue/Angular/Svelte)
  - JavaScript route extraction
  - XHR/fetch network interception
  - WebSocket discovery
  - endpoint merge/dedupe → ParsedEntity for the entity engine

It drives Delta/Prism/OpenClaw/PinchTab via the shared BrowserOrchestrator and
normalizes everything into ParsedEntity records so the single entity engine,
scoring, and artifact store handle them (no duplicate storage/scoring).
"""
from __future__ import annotations

import logging
from typing import Any

from backend.parsers.recon.base import ParsedEntity

logger = logging.getLogger("alpha.browser_recon")

_SPA_FRAMEWORKS = {"react", "vue", "angular", "svelte"}


class BrowserReconModule:
    """Browser-aware recon, normalized into ParsedEntity records."""

    def __init__(self, browser, scan_id: str, *, agent_name: str = "agent_alpha"):
        # ``browser`` is the shared BrowserOrchestrator (OpenClaw + PinchTab).
        self.browser = browser
        self.scan_id = scan_id
        self.agent_name = agent_name

    async def recon(self, url: str) -> list[ParsedEntity]:
        """Run browser recon for ``url``; return normalized entities.

        Safe-degrades: if no browser engine is available, returns []."""
        entities: list[ParsedEntity] = []
        if self.browser is None:
            return entities
        try:
            is_spa = await self._detect_spa(url)
        except Exception as exc:
            logger.debug("[BrowserRecon] SPA detect failed: %s", exc)
            is_spa = False

        if not is_spa:
            # Still attempt endpoint extraction for non-SPA dynamic apps.
            pass

        endpoints = await self._extract_endpoints(url)
        network = await self._intercept_network(url)
        js_routes = await self._extract_js_routes(url)
        websockets = await self._find_websockets(url)

        merged = self._merge(endpoints, network, js_routes, websockets)
        for ep in merged:
            kind = "browser_endpoint"
            src = ep.get("source", "browser")
            if ep.get("method") == "WS" or src == "websocket_monitor":
                kind = "websocket"
            elif "router" in src:
                kind = "javascript_route"
            entities.append(ParsedEntity(
                kind=kind,
                label=str(ep.get("url", "")),
                confidence=0.7,
                source_tool=src,
                phase="http_browser_intelligence",
                scan_id=self.scan_id,
                properties={"method": ep.get("method", "GET"), "source": src,
                            "spa": is_spa, "headers": ep.get("headers", {})},
            ))
        logger.info("[BrowserRecon] %s: %d browser entities (spa=%s)", url, len(entities), is_spa)
        return entities

    # ── Browser primitives (delegated to the shared orchestrator) ─────────────

    async def _detect_spa(self, url: str) -> bool:
        try:
            result = await self.browser.navigate(url, stealth=False, wait_for="networkidle")
            if not result.get("success"):
                return False
            framework = await self.browser.detect_framework(url)
            return str(framework or "").lower() in _SPA_FRAMEWORKS
        except Exception:
            return False

    async def _extract_endpoints(self, url: str) -> list[dict[str, Any]]:
        try:
            eps = await self.browser.extract_endpoints(url, deep=True)
            return [{"url": e.get("url"), "method": e.get("method", "GET"),
                     "source": e.get("source", "browser")} for e in (eps or [])]
        except Exception:
            return []

    async def _intercept_network(self, url: str) -> list[dict[str, Any]]:
        try:
            evts = await self.browser.intercept_network(url)
            return [{"url": e.get("url"), "method": e.get("method", "GET"),
                     "source": "network_intercept", "headers": e.get("headers", {})}
                    for e in (evts or [])]
        except Exception:
            return []

    async def _find_websockets(self, url: str) -> list[dict[str, Any]]:
        try:
            ws_urls = await self.browser.find_websockets(url)
            return [{"url": w, "method": "WS", "source": "websocket_monitor"} for w in (ws_urls or [])]
        except Exception:
            return []

    async def _extract_js_routes(self, url: str) -> list[dict[str, Any]]:
        try:
            framework = await self.browser.detect_framework(url)
            page = getattr(getattr(self.browser, "openclaw", None), "current_page", None)
            if page is None:
                return []
            fw = str(framework or "").lower()
            if fw == "react":
                js = """() => { const r=[]; if(window.__REACT_ROUTER__&&window.__REACT_ROUTER__.routes){window.__REACT_ROUTER__.routes.forEach(x=>{if(x.path)r.push({url:x.path,method:'GET',source:'react_router'})})} document.querySelectorAll('[data-route]').forEach(e=>{const p=e.getAttribute('data-route'); if(p)r.push({url:p,method:'GET',source:'react_dom'})}); return r; }"""
            elif fw == "vue":
                js = """() => { const r=[]; if(window.$router&&window.$router.options){(window.$router.options.routes||[]).forEach(x=>{if(x.path)r.push({url:x.path,method:'GET',source:'vue_router'})})} return r; }"""
            elif fw == "angular":
                js = """() => { const r=[]; if(window.ng&&window.ng.probe){(window.ng.probe.getAllRoutes?.()||[]).forEach(x=>{if(x.path)r.push({url:x.path,method:'GET',source:'angular_router'})})} return r; }"""
            else:
                return []
            routes = await page.evaluate(js)
            return list(routes or [])
        except Exception:
            return []

    @staticmethod
    def _merge(*lists) -> list[dict[str, Any]]:
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for lst in lists:
            for ep in lst:
                u = ep.get("url", "")
                if u and u not in seen:
                    seen.add(u)
                    merged.append(ep)
        return merged
