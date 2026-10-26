"""
SafeChat Detoxification — Master Orchestrator

Integrates:
  - Cache Layer (DetoxCache: LRU + TTL + optional Redis)
  - Primary Route: Google Gemini API (gemini-2.5-flash / gemini-2.0-flash)
  - Strict Response Validation (ResponseValidator)
  - Offline Fallback Route: IntentPreservingScrubber
  - Real-time streaming generator for WebSocket clients
"""

import logging
from typing import AsyncGenerator, Dict, List, Optional

from detoxification.config import DetoxConfig
from detoxification.cache import DetoxCache
from detoxification.gemini_client import GeminiClient, build_detox_prompt
from detoxification.validator import ResponseValidator
from detoxification.scrubber import IntentPreservingScrubber

logger = logging.getLogger("Detoxifier")


def detect_language_simple(text: str) -> str:
    """
    Fast script-based language identification.
    Returns: 'hi' (Devanagari), 'hi-en' (Hinglish), or 'en' (English).
    """
    if not text:
        return "en"

    devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    total_alpha = sum(1 for c in text if c.isalpha())

    if total_alpha > 0 and (devanagari_count / total_alpha) > 0.25:
        return "hi"

    # Common Hinglish marker words
    hinglish_markers = {
        "yaar", "bhai", "hai", "hain", "kya", "kyu", "kyun", "kar", "karo", "raha",
        "rahe", "rahi", "nahi", "nahin", "mujhe", "tujhe", "tera", "mera", "yeh",
        "woh", "kaise", "kaisa", "tha", "the", "thi", "hoga", "apna", "apni", "pehle"
    }
    words = {w.lower() for w in text.split()}
    if len(words.intersection(hinglish_markers)) >= 1:
        return "hi-en"

    return "en"


class Detoxifier:
    """
    Production-grade Intent-Preserving Detoxification Engine.
    """

    def __init__(self, config: Optional[DetoxConfig] = None):
        self.cfg = config or DetoxConfig()
        self.cache = DetoxCache(
            max_size=self.cfg.cache_max_size,
            ttl_seconds=self.cfg.cache_ttl_seconds,
            redis_url=self.cfg.redis_url,
        ) if self.cfg.cache_enabled else None

        self.client = GeminiClient(self.cfg)
        self.scrubber = IntentPreservingScrubber()
        self.validator = ResponseValidator()

    @property
    def is_api_available(self) -> bool:
        """Whether Gemini API is configured and ready."""
        return self.client.is_configured

    async def detoxify(
        self,
        text: str,
        toxicity_categories: Optional[Dict[str, float]] = None,
        target_language: Optional[str] = None,
        context: Optional[List[str]] = None,
    ) -> Dict:
        """
        Detoxify a toxic message.

        Steps:
          1. Check cache (instant return if cached)
          2. Detect language if not specified
          3. Try Option A: Gemini API
          4. Validate LLM response
          5. Fallback to Option B: Local Intent-Preserving Scrubber if needed
          6. Cache and return
        """
        if not text or not text.strip():
            return {
                "original": text,
                "detoxified": text,
                "method": "passthrough",
                "language": target_language or "en",
                "confidence": 1.0,
            }

        lang = target_language or detect_language_simple(text)

        # ── Step 1: Cache check ─────────────────────────────────────
        if self.cache:
            cached = self.cache.get(text, lang)
            if cached:
                cached["cached"] = True
                return cached

        # ── Step 2: Try Option A (Gemini API) ───────────────────────
        if self.is_api_available:
            try:
                prompt = build_detox_prompt(text, lang, toxicity_categories, context)
                candidate = await self.client.generate(prompt)

                if candidate:
                    is_valid, cleaned, reason = self.validator.validate(
                        candidate_text=candidate,
                        original_text=text,
                        max_length_multiplier=self.cfg.max_length_multiplier,
                    )
                    if is_valid:
                        result = {
                            "original": text,
                            "detoxified": cleaned,
                            "method": "gemini",
                            "language": lang,
                            "confidence": 0.95,
                            "model": self.cfg.model,
                            "cached": False,
                        }
                        if self.cache:
                            self.cache.set(text, result, lang)
                        return result
                    else:
                        logger.warning(f"LLM response failed validation ({reason}). Falling back to scrubber.")
            except Exception as e:
                logger.error(f"Gemini API detoxification failed: {e}. Falling back to scrubber.")

        # ── Step 3: Option B (Offline Intent-Preserving Scrubber) ────
        fallback_text = self.scrubber.scrub(text, detected_language=lang)
        result = {
            "original": text,
            "detoxified": fallback_text,
            "method": "intent_preserving_scrubber",
            "language": lang,
            "confidence": 0.85,
            "cached": False,
        }

        if self.cache:
            self.cache.set(text, result, lang)

        return result

    async def arbitrate_and_detoxify(
        self,
        text: str,
        roberta_labels: Optional[List[str]] = None,
        target_language: Optional[str] = None,
        context: Optional[List[str]] = None,
    ) -> Dict:
        """
        Jointly classify and detoxify via Gemini.
        Evaluates context to overrule false positives, or detoxifies genuine toxicity.
        Returns final accepted classification and detoxified text.
        """
        if not text or not text.strip():
            return {
                "original": text,
                "is_toxic": False,
                "severity": "SAFE",
                "categories": [],
                "detoxified": text,
                "reason": "Empty text",
                "method": "passthrough",
                "language": target_language or "en",
                "confidence": 1.0,
            }

        lang = target_language or detect_language_simple(text)

        # Step 1: Cache check
        cache_key = f"arbitrate:{text}"
        if self.cache:
            cached = self.cache.get(cache_key, lang)
            if cached:
                cached["cached"] = True
                return cached

        # Step 2: Gemini API Arbitration
        if self.is_api_available:
            try:
                res = await self.client.generate_arbitration(
                    text=text,
                    language=lang,
                    roberta_labels=roberta_labels,
                    context=context,
                )
                if res:
                    is_toxic = res["is_toxic"]
                    detox_text = res["detoxified_text"]

                    if is_toxic:
                        is_valid, cleaned, _ = self.validator.validate(
                            candidate_text=detox_text,
                            original_text=text,
                            max_length_multiplier=self.cfg.max_length_multiplier,
                        )
                        if is_valid:
                            detox_text = cleaned

                    result = {
                        "original": text,
                        "is_toxic": is_toxic,
                        "severity": res["severity"],
                        "categories": res["active_labels"],
                        "detoxified": detox_text,
                        "reason": res.get("reason", ""),
                        "method": "gemini_arbitration",
                        "language": lang,
                        "confidence": res.get("confidence", 0.95),
                        "model": self.cfg.model,
                        "cached": False,
                    }
                    if self.cache:
                        self.cache.set(cache_key, result, lang)
                    return result
            except Exception as e:
                logger.error(f"Gemini arbitration failed ({e}). Falling back to RoBERTa + Scrubber.")

        # Step 3: Offline Scrubber Fallback (preserves RoBERTa's preliminary verdict)
        is_toxic = bool(roberta_labels)
        fallback_text = self.scrubber.scrub(text, detected_language=lang) if is_toxic else text
        result = {
            "original": text,
            "is_toxic": is_toxic,
            "severity": "MEDIUM" if is_toxic else "SAFE",
            "categories": roberta_labels or [],
            "detoxified": fallback_text,
            "reason": "Offline heuristic fallback",
            "method": "intent_preserving_scrubber",
            "language": lang,
            "confidence": 0.85,
            "cached": False,
        }
        if self.cache:
            self.cache.set(cache_key, result, lang)
        return result

    async def detoxify_stream(
        self,
        text: str,
        toxicity_categories: Optional[Dict[str, float]] = None,
        target_language: Optional[str] = None,
        context: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream detoxified tokens in real-time for WebSocket clients.
        If Gemini is available, streams from Gemini SSE.
        Otherwise, yields words from the offline scrubber.
        """
        lang = target_language or detect_language_simple(text)

        if self.is_api_available:
            prompt = build_detox_prompt(text, lang, toxicity_categories, context)
            full_text = ""
            try:
                async for chunk in self.client.stream_generate(prompt):
                    full_text += chunk
                    yield chunk

                # Validate the complete streamed response
                if full_text:
                    is_valid, _, _ = self.validator.validate(full_text, text)
                    if is_valid:
                        return
            except Exception as e:
                logger.warning(f"Streaming failed: {e}. Falling back to scrubber stream.")

        # Fallback word-by-word streaming
        fallback_text = self.scrubber.scrub(text, detected_language=lang)
        words = fallback_text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    def get_info(self) -> Dict:
        """Health check and status metadata."""
        return {
            "mode": "gemini" if self.is_api_available else "offline_fallback",
            "gemini_configured": self.is_api_available,
            "model": self.cfg.model if self.is_api_available else "none",
            "cache": self.cache.stats if self.cache else "disabled",
        }

