"""
SafeChat — LLM-Powered Text Detoxifier (Gemini API + Intent-Preserving Fallback)

Option A (Recommended): Google Gemini API for intent-preserving style transfer
Option B (Offline Fallback): Expanded multi-lingual regex scrubber

Features:
  - Direct async REST calls via httpx with exponential backoff & retry
  - OpenAI-compatible endpoint support (AICredits, OpenRouter, Groq)
  - Strict response validation (checks for residual toxicity, generic scolding, length anomalies)
  - In-memory LRU + TTL cache to eliminate repeated API costs & latency
  - Real-time token streaming for WebSocket moderation modal
  - Comprehensive fallback scrubber for English, Hinglish, Devanagari Hindi
"""

import sys
import os
from typing import AsyncGenerator, Dict, List, Optional
from loguru import logger

# Add project root to sys.path so detoxification package is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.config import settings
from detoxification.config import DetoxConfig
from detoxification.detoxifier import Detoxifier as CoreDetoxifier


class LLMDetoxifier:
    """
    Production-grade LLM detoxifier adapter for FastAPI ML service.
    Exposes detoxify() and detoxify_stream() matching the existing API contract.
    """

    def __init__(self):
        # Configure using ml-service settings
        cfg = DetoxConfig(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            base_url=getattr(settings, "GEMINI_BASE_URL", None),
            max_tokens=getattr(settings, "DETOX_MAX_TOKENS", 256),
            cache_enabled=True,
            cache_max_size=1000,
            cache_ttl_seconds=3600,
            redis_url=getattr(settings, "REDIS_URL", None),
        )

        self._core = CoreDetoxifier(cfg)

        if self._core.is_api_available:
            logger.success(f"LLM Detoxifier initialized with Gemini API (model: {cfg.model})")
        else:
            logger.warning("SAFECHAT_GEMINI_API_KEY not set. Detoxifier will run in offline intent-preserving mode.")

    @property
    def is_available(self) -> bool:
        """Whether Gemini API is configured and operational."""
        return self._core.is_api_available

    async def detoxify(
        self,
        text: str,
        toxicity_categories: Optional[Dict[str, float]] = None,
        target_language: Optional[str] = None,
        context: Optional[List[str]] = None,
    ) -> Dict:
        """
        Detoxify a message preserving user intent.
        Returns dict matching DetoxifyResponse schema.
        """
        return await self._core.detoxify(
            text=text,
            toxicity_categories=toxicity_categories,
            target_language=target_language,
            context=context,
        )

    async def arbitrate_and_detoxify(
        self,
        text: str,
        roberta_labels: Optional[List[str]] = None,
        target_language: Optional[str] = None,
        context: Optional[List[str]] = None,
    ) -> Dict:
        """
        Jointly classify context and detoxify via Gemini.
        Returns final accepted classification and detoxified text.
        """
        return await self._core.arbitrate_and_detoxify(
            text=text,
            roberta_labels=roberta_labels,
            target_language=target_language,
            context=context,
        )

    async def detoxify_stream(
        self,
        text: str,
        toxicity_categories: Optional[Dict[str, float]] = None,
        target_language: Optional[str] = None,
        context: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream detoxified tokens for real-time display via WebSocket.
        """
        async for chunk in self._core.detoxify_stream(
            text=text,
            toxicity_categories=toxicity_categories,
            target_language=target_language,
            context=context,
        ):
            yield chunk

    def get_info(self) -> Dict:
        """Return detoxifier metadata for health checks."""
        core_info = self._core.get_info()
        return {
            "mode": core_info["mode"],
            "gemini_api_configured": core_info["gemini_configured"],
            "model": core_info["model"],
            "cache": core_info["cache"],
        }
