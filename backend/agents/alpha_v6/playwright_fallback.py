"""
Alpha V6 Playwright Browser Fallback.

When PinchTab is unavailable, falls back to Playwright for:
- Page screenshots
- Network request capture
- DOM snapshot extraction
- Cookie collection
- Console error monitoring
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from backend.agents.alpha_v6.models import stable_id
from backend.core.queue import command_lane
from backend.parsers.recon.base import ParsedEntity

logger = logging.getLogger("alpha.playwright_fallback")


class PlaywrightFallback:
    """Lightweight Playwright-based browser intelligence when PinchTab is down."""

    def __init__(self, scan_id: str, artifacts_root: Path):
        self.scan_id = scan_id
        self.screenshots_dir = artifacts_root / "screenshots"
        self.browser_dir = artifacts_root / "browser"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.browser_dir.mkdir(parents=True, exist_ok=True)
        self._pw = None
        self._browser = None

    async def _ensure_browser(self):
        """Lazily launch a browser instance."""
        if self._browser:
            return
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-background-networking",
                ],
            )
            logger.info("[PLAYWRIGHT] Browser launched")
        except ImportError:
            logger.warning("[PLAYWRIGHT] playwright not installed, skipping browser fallback")
            raise
        except Exception as exc:
            logger.warning(f"[PLAYWRIGHT] Browser launch failed: {exc}")
            raise

    async def capture_page(self, url: str, *, timeout_ms: int = 30000) -> dict[str, Any]:
        """Full page capture: screenshot + network + cookies + console."""
        try:
            await self._ensure_browser()
        except Exception:
            return {"used": False, "reason": "browser_unavailable"}

        context = await self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        page = await context.new_page()
        network_requests: list[dict] = []
        console_messages: list[dict] = []
        errors: list[str] = []

        # Capture network
        page.on("request", lambda req: network_requests.append({
            "url": req.url, "method": req.method,
            "resource_type": req.resource_type,
            "headers": dict(req.headers)}))

        # Capture console
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type, "text": msg.text[:500]}))

        page.on("pageerror", lambda exc: errors.append(str(exc)[:500]))

        try:
            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except Exception:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            status_code = resp.status if resp else 0

            # Wait for dynamic content
            await page.wait_for_timeout(2000)

            # Screenshot
            safe_name = url.replace("://", "_").replace("/", "_")[:80]
            screenshot_path = self.screenshots_dir / f"{safe_name}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            # Cookies
            cookies = await context.cookies()

            # Page title and content
            title = await page.title()
            content = await page.content()

            # Extract links
            links = await page.eval_on_selector_all("a[href]",
                "elements => elements.map(e => e.href)")

            # Extract forms
            forms = await page.eval_on_selector_all("form",
                """elements => elements.map(f => ({
                    action: f.action, method: f.method,
                    inputs: Array.from(f.querySelectorAll('input,select,textarea'))
                        .map(i => ({name: i.name, type: i.type, id: i.id}))
                }))""")

            # Save DOM snapshot
            dom_path = self.browser_dir / f"{safe_name}_dom.html"
            dom_path.write_text(content[:2_000_000], encoding="utf-8", errors="replace")

            # Save network log
            net_path = self.browser_dir / f"{safe_name}_network.json"
            net_path.write_text(json.dumps(network_requests, default=str),
                                encoding="utf-8")

            # Save cookies
            cookie_path = self.browser_dir / f"{safe_name}_cookies.json"
            cookie_path.write_text(json.dumps(cookies, default=str),
                                   encoding="utf-8")

            result = {
                "used": True,
                "url": url,
                "status_code": status_code,
                "title": title,
                "screenshot_path": str(screenshot_path),
                "dom_path": str(dom_path),
                "network_path": str(net_path),
                "cookie_path": str(cookie_path),
                "network_requests_count": len(network_requests),
                "cookies_count": len(cookies),
                "console_messages": len(console_messages),
                "errors": errors[:10],
                "links_count": len(links),
                "forms_count": len(forms),
            }

            return result

        except Exception as exc:
            logger.warning(f"[PLAYWRIGHT] Capture failed for {url}: {exc}")
            return {"used": False, "reason": f"capture_failed:{exc}"}
        finally:
            await context.close()

    async def batch_capture(self, urls: list[str], *,
                             max_concurrent: int = 3) -> list[dict[str, Any]]:
        """Capture multiple pages with concurrency control."""
        results = []

        async def _capture(url):
            async with command_lane.slot():
                return await self.capture_page(url)

        tasks = [_capture(u) for u in urls[:30]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r if isinstance(r, dict) else {"used": False, "reason": str(r)}
                for r in results]

    def extract_entities(self, capture_result: dict) -> list[ParsedEntity]:
        """Convert Playwright capture results into ParsedEntity objects."""
        entities: list[ParsedEntity] = []
        if not capture_result.get("used"):
            return entities

        url = capture_result.get("url", "")

        # Screenshot entity
        if capture_result.get("screenshot_path"):
            entities.append(ParsedEntity(
                kind="visual_artifact",
                label=url,
                confidence=0.9,
                source_tool="playwright",
                phase="visual_documentation",
                scan_id=self.scan_id,
                properties={
                    "screenshot_path": capture_result["screenshot_path"],
                    "title": capture_result.get("title", ""),
                    "status_code": capture_result.get("status_code", 0),
                }))

        # Network requests as XHR endpoints
        net_path = capture_result.get("network_path")
        if net_path and Path(net_path).exists():
            try:
                requests = json.loads(Path(net_path).read_text(encoding="utf-8"))
                for req in requests:
                    if req.get("resource_type") in ("xhr", "fetch"):
                        entities.append(ParsedEntity(
                            kind="crawled_endpoint",
                            label=req["url"],
                            confidence=0.85,
                            source_tool="playwright_network",
                            phase="http_browser_intelligence",
                            scan_id=self.scan_id,
                            properties={
                                "method": req.get("method", "GET"),
                                "resource_type": req["resource_type"],
                                "source_page": url,
                            }))
            except Exception:
                pass

        # Cookies with security flags
        cookie_path = capture_result.get("cookie_path")
        if cookie_path and Path(cookie_path).exists():
            try:
                cookies = json.loads(Path(cookie_path).read_text(encoding="utf-8"))
                for c in cookies:
                    if not c.get("httpOnly") or not c.get("secure"):
                        entities.append(ParsedEntity(
                            kind="insecure_cookie",
                            label=f"{c.get('name', '?')}@{c.get('domain', '?')}",
                            confidence=0.7,
                            source_tool="playwright_cookies",
                            phase="http_browser_intelligence",
                            scan_id=self.scan_id,
                            properties={
                                "name": c.get("name", ""),
                                "domain": c.get("domain", ""),
                                "httpOnly": c.get("httpOnly", False),
                                "secure": c.get("secure", False),
                                "sameSite": c.get("sameSite", "None"),
                                "path": c.get("path", "/"),
                            }))
            except Exception:
                pass

        return entities

    async def close(self):
        """Clean shutdown."""
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
