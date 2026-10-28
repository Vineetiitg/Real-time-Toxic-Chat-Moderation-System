"""
SafeChat Detoxification — Configuration

Centralized configuration for Phase 3 Detoxification (Option A: Gemini API + Intent-Preserving Fallback).
Supports environment variables:
  - GEMINI_API_KEY / SAFECHAT_GEMINI_API_KEY
  - GEMINI_MODEL / SAFECHAT_GEMINI_MODEL
  - GEMINI_BASE_URL (for custom proxy / OpenAI-compatible endpoints)
  - REDIS_URL (optional for distributed caching)
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DetoxConfig:
    """Configuration for LLM detoxification and offline fallback scrubber."""

    # ── Gemini API Credentials & Model ──────────────────────────────
    api_key: str = field(
        default_factory=lambda: (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("SAFECHAT_GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or ""
        )
    )
    # Default: gemini-2.5-flash or gemini-2.0-flash (fast, cost-effective, high instruction fidelity)
    model: str = field(
        default_factory=lambda: (
            os.getenv("GEMINI_MODEL")
            or os.getenv("SAFECHAT_GEMINI_MODEL")
            or "gemini-1.5-flash"
        )
    )
    # Optional OpenAI-compatible base URL (e.g., OpenRouter, Groq, local vLLM, AICredits)
    base_url: Optional[str] = field(
        default_factory=lambda: (
            os.getenv("GEMINI_BASE_URL")
            or os.getenv("SAFECHAT_GEMINI_BASE_URL")
            or None
        )
    )

    # ── Generation Parameters ─────────────────────────────────────────
    temperature: float = 0.3            # Low temperature for consistent, faithful style transfer
    max_tokens: int = 500               # Sufficient budget for complete JSON arbitration & detoxified rewrite
    request_timeout_seconds: float = 8.0  # Cap API latency for real-time chat

    # ── Retry & Resilience ────────────────────────────────────────────
    max_retries: int = 3                # Exponential backoff retry attempts
    initial_retry_delay: float = 0.5    # Starting delay in seconds (0.5s -> 1.0s -> 2.0s)
    backoff_factor: float = 2.0

    # ── Caching ───────────────────────────────────────────────────────
    cache_enabled: bool = True
    cache_max_size: int = 1000          # In-memory LRU cache capacity
    cache_ttl_seconds: int = 3600       # 1 hour cache TTL
    redis_url: Optional[str] = field(
        default_factory=lambda: os.getenv("REDIS_URL") or None
    )

    # ── Validation ────────────────────────────────────────────────────
    enable_response_validation: bool = True
    max_length_multiplier: float = 3.0  # Rewrite cannot be >3x length of input

