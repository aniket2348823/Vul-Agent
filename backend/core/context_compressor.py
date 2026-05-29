"""
Vigilagent Context Compressor (Architecture §13, §29.3, §29.13)
================================================================================
Token-aware context compaction adopted from the Hermes `context_compressor.py`
pattern. Summarizes the middle of a long transcript with Gemini 2.5 Flash while
protecting the parts that must never be summarized away.

Compression rules (Architecture §13):
  - Preserve system policy.
  - Preserve scope.
  - Preserve latest events (last N turns).
  - Preserve confirmed findings and evidence IDs (VULN_CONFIRMED).
  - Compress noisy tool output.
  - NEVER summarize away approval decisions.
  - Use Gemini 2.5 Flash for summarization (the tactical LLM, §11.2).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("vigilagent.compressor")

# Lines matching these markers are protected and never compressed (Architecture §13).
_PROTECTED_MARKERS = (
    "VULN_CONFIRMED",
    "[SYSTEM]",
    "[POLICY]",
    "[SCOPE]",
    "APPROVAL",
    "APPROVED",
    "DENIED",
    "scope.authorized",
)


def estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token) good enough for budgeting."""
    return max(1, len(text) // 4)


@dataclass
class CompressionResult:
    transcript: list[str]
    original_tokens: int
    compressed_tokens: int
    summarized_segments: int
    used_llm: bool


class ContextCompressor:
    """Sliding-window summarizer with protected head/tail (Architecture §13)."""

    def __init__(self, max_tokens: int = 24000, keep_last: int = 20,
                 keep_first: int = 4) -> None:
        self.max_tokens = max_tokens
        self.keep_last = keep_last
        self.keep_first = keep_first

    @staticmethod
    def _is_protected(line: str) -> bool:
        return any(marker in line for marker in _PROTECTED_MARKERS)

    async def compress(self, transcript: list[str], *, cortex=None, scan_ctx=None) -> CompressionResult:
        """Compress a transcript if it exceeds the token budget.

        ``cortex`` is the CortexEngine (used for Gemini summarization). If it is
        None or offline, a deterministic extractive fallback is used so the
        compressor never blocks the scan (Architecture §14 degradation)."""
        joined = "\n".join(transcript)
        original_tokens = estimate_tokens(joined)
        if original_tokens <= self.max_tokens or len(transcript) <= (self.keep_first + self.keep_last):
            return CompressionResult(transcript, original_tokens, original_tokens, 0, False)

        head = transcript[: self.keep_first]
        tail = transcript[-self.keep_last :]
        middle = transcript[self.keep_first : -self.keep_last]

        # Always carry protected lines from the middle forward verbatim.
        protected = [ln for ln in middle if self._is_protected(ln)]
        compressible = [ln for ln in middle if not self._is_protected(ln)]

        used_llm = False
        summary_block = ""
        if compressible:
            summary_block, used_llm = await self._summarize(compressible, cortex, scan_ctx)

        new_transcript: list[str] = []
        new_transcript.extend(head)
        if protected:
            new_transcript.append("[COMPRESSION] Preserved critical lines:")
            new_transcript.extend(protected)
        if summary_block:
            new_transcript.append(
                "[COMPRESSION_SUMMARY] (older context compressed by Gemini)\n" + summary_block
            )
        new_transcript.extend(tail)

        compressed_tokens = estimate_tokens("\n".join(new_transcript))
        return CompressionResult(
            transcript=new_transcript,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            summarized_segments=1 if summary_block else 0,
            used_llm=used_llm,
        )

    async def _summarize(self, lines: list[str], cortex, scan_ctx) -> tuple[str, bool]:
        text = "\n".join(lines)
        if cortex is not None and hasattr(cortex, "_call_gemini"):
            prompt = (
                "Compress the following security-scan transcript segment into a dense, "
                "factual summary. Preserve: discovered endpoints/parameters, tool results, "
                "tech stack, auth/session facts, and any decisions. Drop noise and duplicates. "
                "Do NOT invent findings. Output plain prose, no markdown.\n\n"
                f"SEGMENT:\n{text[:16000]}"
            )
            try:
                result = await cortex._call_gemini(prompt, temperature=0.1, max_tokens=512, scan_ctx=scan_ctx)
                if result and not str(result).startswith("["):
                    return str(result).strip(), True
            except Exception as exc:
                logger.warning("Compressor LLM summarization failed: %s", exc)
        return self._extractive_fallback(lines), False

    @staticmethod
    def _extractive_fallback(lines: list[str]) -> str:
        """Deterministic summary when the LLM is unavailable (Architecture §11.3 fallback)."""
        endpoints = sorted(set(re.findall(r"https?://[^\s\"'<>]+|/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{2,}",
                                           "\n".join(lines))))[:30]
        codes = sorted(set(re.findall(r"\b[1-5][0-9]{2}\b", "\n".join(lines))))[:15]
        parts = [f"{len(lines)} older lines compressed."]
        if endpoints:
            parts.append("Paths seen: " + ", ".join(endpoints[:20]))
        if codes:
            parts.append("Status codes: " + ", ".join(codes))
        return " ".join(parts)


# Default compressor instance.
context_compressor = ContextCompressor()
