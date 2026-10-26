"""
SafeChat Detoxification Package

Intent-preserving style transfer for toxic chat messages.
Features:
  - Option A: Google Gemini API (gemini-2.5-flash / gemini-2.0-flash) with backoff & retry
  - Option B: Offline Intent-Preserving Scrubber (English, Hinglish, Devanagari Hindi)
  - Strict Response Validation (checks for re-toxicity, generic scolding, length anomalies)
  - Multi-layer LRU + TTL Cache
  - Streaming token generation for WebSockets
"""

from detoxification.config import DetoxConfig
from detoxification.cache import DetoxCache
from detoxification.scrubber import IntentPreservingScrubber
from detoxification.validator import ResponseValidator
from detoxification.gemini_client import GeminiClient
from detoxification.detoxifier import Detoxifier

__all__ = [
    "DetoxConfig",
    "DetoxCache",
    "IntentPreservingScrubber",
    "ResponseValidator",
    "GeminiClient",
    "Detoxifier",
]

