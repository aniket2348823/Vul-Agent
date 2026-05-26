# ═══════════════════════════════════════════════════════════════════════════════
# ANTIGRAVITY :: GEMINI CLIENT — GEMINI 2.5 FLASH INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
# PURPOSE: Production-grade async client for Google Gemini API.
#          Provides payload generation, validation, narrative synthesis,
#          and vector embeddings for Agent Kappa memory via Gemini 2.5 Flash
#          and text-embedding-004 (cloud inference).
# ═══════════════════════════════════════════════════════════════════════════════

import aiohttp
import asyncio
import json
import logging
import os
import time as _time
from typing import Optional, Dict, Any, List

logger = logging.getLogger("GEMINI")

# ─── Configuration ────────────────────────────────────────────────────────────
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_EMBEDDING_FALLBACK_MODELS = [
    model.strip()
    for model in os.environ.get("GEMINI_EMBEDDING_FALLBACK_MODELS", "text-embedding-004").split(",")
    if model.strip()
]
GEMINI_TIMEOUT = 120  # seconds
MAX_RETRIES = 2


class GeminiClient:
    """
    Production-grade async client for Google Gemini API.
    Powers tactical payload generation, validation, narrative synthesis,
    and vector embeddings for Agent Kappa memory.
    """

    def __init__(self, api_key: Optional[str] = None):
        from dotenv import load_dotenv
        load_dotenv(override=True)

        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

        if self._api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI: Key is still the placeholder! Please update .env")
            self._api_key = ""

        self._session: Optional[aiohttp.ClientSession] = None
        self._telemetry = {
            "calls": 0,
            "successes": 0,
            "errors": 0,
            "total_latency": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

        if self._api_key:
            logger.info(f"GEMINI: Client initialized → model={GEMINI_MODEL}")
        else:
            logger.warning("GEMINI: No valid API key found. Gemini inference disabled.")

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=GEMINI_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def call(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 1500,
        scan_ctx=None,
    ) -> str:
        """
        Send a prompt to Gemini 2.5 Flash via the Generative Language API.
        Returns the raw text response or an error string.
        """
        if not self._api_key:
            return "[GEMINI OFFLINE] No API key configured."

        self._telemetry["calls"] += 1
        call_start = _time.perf_counter()

        if scan_ctx and getattr(scan_ctx, "is_cancelled", False):
            raise asyncio.CancelledError()

        await self._ensure_session()

        url = f"{GEMINI_API_URL}/models/{GEMINI_MODEL}:generateContent?key={self._api_key}"

        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": min(max_tokens, 8192),
                "topP": 0.9,
            },
        }

        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        for attempt in range(MAX_RETRIES + 1):
            try:
                if scan_ctx and getattr(scan_ctx, "is_cancelled", False):
                    raise asyncio.CancelledError()

                async with self._session.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        candidates = data.get("candidates", [])
                        if not candidates:
                            self._telemetry["errors"] += 1
                            logger.error("GEMINI: Empty candidates in response")
                            return "[GEMINI ERROR] No candidates returned."

                        result = (
                            candidates[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )

                        usage = data.get("usageMetadata", {})
                        self._telemetry["input_tokens"] += usage.get("promptTokenCount", 0)
                        self._telemetry["output_tokens"] += usage.get("candidatesTokenCount", 0)

                        latency = _time.perf_counter() - call_start
                        self._telemetry["successes"] += 1
                        self._telemetry["total_latency"] += latency

                        total_tokens = usage.get("totalTokenCount", "N/A")
                        logger.info(f"GEMINI: Call succeeded in {latency:.2f}s (tokens: {total_tokens})")
                        return result.strip()

                    elif response.status == 429:
                        logger.warning(f"GEMINI: Rate limited (429). Retry {attempt + 1}/{MAX_RETRIES}")
                        await asyncio.sleep(2 ** attempt)
                        continue

                    else:
                        error_text = await response.text()
                        logger.error(f"GEMINI: HTTP {response.status} — {error_text[:200]}")
                        self._telemetry["errors"] += 1
                        return f"[GEMINI ERROR] HTTP {response.status}: {error_text[:100]}"

            except asyncio.CancelledError:
                raise
            except aiohttp.ClientConnectorError:
                self._telemetry["errors"] += 1
                logger.error("GEMINI: Cannot connect to Gemini API")
                return "[GEMINI OFFLINE] Cannot connect to Gemini API."
            except asyncio.TimeoutError:
                self._telemetry["errors"] += 1
                logger.error(f"GEMINI: Request timed out after {GEMINI_TIMEOUT}s")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return f"[GEMINI TIMEOUT] Request exceeded {GEMINI_TIMEOUT}s."
            except Exception as e:
                self._telemetry["errors"] += 1
                logger.error(f"GEMINI: Unexpected error — {type(e).__name__}: {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return f"[GEMINI ERROR] {type(e).__name__}: {str(e)[:100]}"

        return "[GEMINI ERROR] Max retries exceeded."

    # ─── Specialized Call Methods ─────────────────────────────────────────────

    async def generate_payloads(self, prompt: str, *, max_tokens: int = 1024, scan_ctx=None) -> str:
        """Generate attack payloads via Gemini 2.5 Flash."""
        return await self.call(prompt, temperature=0.2, max_tokens=max_tokens, scan_ctx=scan_ctx)

    async def validate_candidate(self, prompt: str, *, max_tokens: int = 4096, scan_ctx=None) -> str:
        """Validate a vulnerability candidate with deterministic reasoning."""
        return await self.call(prompt, temperature=0.0, max_tokens=max_tokens, scan_ctx=scan_ctx)

    async def generate_narrative(self, prompt: str, scan_ctx=None) -> str:
        """Generate narrative text for reports and summaries."""
        return await self.call(prompt, temperature=0.3, max_tokens=500, scan_ctx=scan_ctx)

    async def generate_embedding(self, text: str, scan_ctx=None) -> List[float]:
        """
        Generate a vector embedding via Gemini embeddings.
        Returns the embedding values or an empty list on failure.
        """
        if not self._api_key:
            return []

        if scan_ctx and getattr(scan_ctx, "is_cancelled", False):
            raise asyncio.CancelledError()

        await self._ensure_session()

        models = [GEMINI_EMBEDDING_MODEL, *GEMINI_EMBEDDING_FALLBACK_MODELS]
        seen_models = set()

        for model in models:
            if model in seen_models:
                continue
            seen_models.add(model)

            url = f"{GEMINI_API_URL}/models/{model}:embedContent?key={self._api_key}"
            body = {
                "content": {"parts": [{"text": text[:8000]}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "outputDimensionality": 768,
            }

            try:
                async with self._session.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        values = data.get("embedding", {}).get("values", [])
                        logger.info(f"GEMINI: Embedding generated by {model} (dim={len(values)})")
                        return values

                    error_text = await response.text()
                    if response.status == 404 and model != models[-1]:
                        logger.warning("GEMINI: Embedding model %s returned 404; trying fallback", model)
                        continue
                    logger.error(f"GEMINI: Embedding HTTP {response.status} - {error_text[:200]}")
                    return []

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"GEMINI: Embedding error with {model} - {type(e).__name__}: {e}")
                return []

        return []

    def get_telemetry(self) -> dict:
        """Return telemetry counters."""
        t = dict(self._telemetry)
        if t["successes"] > 0:
            t["avg_latency"] = round(t["total_latency"] / t["successes"], 2)
        else:
            t["avg_latency"] = 0.0
        return t

    async def shutdown(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("GEMINI: Session closed.")


# ─── Global Singleton ─────────────────────────────────────────────────────────
gemini_client = GeminiClient()
