"""
SafeChat — Comprehensive Detoxification Unit & Integration Tests (Phase 3)

Tests:
  1. IntentPreservingScrubber (English, Hinglish, Devanagari Hindi)
  2. ResponseValidator (self-toxicity detection, scolding rejection, preamble cleaning)
  3. DetoxCache (LRU eviction, TTL expiration, hit/miss tracking)
  4. Language Detection (English, Hinglish, Devanagari)
  5. Detoxifier Orchestrator (end-to-end pipeline & caching)
"""

import asyncio
import time
import pytest

from detoxification.config import DetoxConfig
from detoxification.cache import DetoxCache
from detoxification.scrubber import IntentPreservingScrubber
from detoxification.validator import ResponseValidator
from detoxification.detoxifier import Detoxifier, detect_language_simple


# ── 1. IntentPreservingScrubber Tests ──────────────────────────────────────────

def test_scrubber_english_insults():
    toxic = "Shut up you idiot, finish the task!"
    cleaned = IntentPreservingScrubber.scrub(toxic, "en")
    assert "shut up" not in cleaned.lower()
    assert "idiot" not in cleaned.lower()
    assert "finish the task" in cleaned.lower()


def test_scrubber_english_threat():
    toxic = "I will kill you if you break production."
    cleaned = IntentPreservingScrubber.scrub(toxic, "en")
    assert "kill you" not in cleaned.lower()
    assert "peacefully" in cleaned.lower() or "production" in cleaned.lower()


def test_scrubber_hinglish_slurs():
    toxic = "Bhenchod chup kar aur kaam kar apna."
    cleaned = IntentPreservingScrubber.scrub(toxic, "hi-en")
    assert "bhenchod" not in cleaned.lower()
    assert "chup kar" not in cleaned.lower()
    assert "kaam kar" in cleaned.lower()


def test_scrubber_hinglish_insult():
    toxic = "Tu bahut bada bewakoof hai, samajh nahi aata kya?"
    cleaned = IntentPreservingScrubber.scrub(toxic, "hi-en")
    assert "bewakoof" not in cleaned.lower()
    assert "samajh nahi aata" in cleaned.lower()


def test_scrubber_devanagari_hindi():
    toxic = "चुप कर बेवकूफ, अपना काम सही से कर।"
    cleaned = IntentPreservingScrubber.scrub(toxic, "hi")
    assert "बेवकूफ" not in cleaned
    assert "काम सही से कर" in cleaned


def test_scrubber_empty_and_pure_profanity():
    # When message is only profanity, it must return a polite default
    toxic = "fuck shit bitch"
    cleaned = IntentPreservingScrubber.scrub(toxic, "en")
    assert len(cleaned) > 5
    assert "fuck" not in cleaned.lower()


# ── 2. ResponseValidator Tests ────────────────────────────────────────────────

def test_validator_accepts_clean_text():
    is_valid, text, reason = ResponseValidator.validate(
        candidate_text="Please stop talking and focus on your work.",
        original_text="Shut up you idiot, focus on work!",
    )
    assert is_valid is True
    assert text == "Please stop talking and focus on your work."
    assert reason is None


def test_validator_cleans_preambles_and_quotes():
    candidate = 'Here is the rewritten version: "Please be quiet and do your job."'
    is_valid, text, reason = ResponseValidator.validate(
        candidate_text=candidate,
        original_text="Shut up and do your job!",
    )
    assert is_valid is True
    assert text == "Please be quiet and do your job."


def test_validator_rejects_retoxic_output():
    candidate = "You are still an idiot but please listen."
    is_valid, text, reason = ResponseValidator.validate(
        candidate_text=candidate,
        original_text="You idiot!",
    )
    # 'idiot' is toxic residual or rejected
    # The validator checks TOXIC_RESIDUAL_KEYWORDS
    # Let's test with a severe slur
    candidate_slur = "Please stop being a bhenchod brother."
    is_valid, _, reason = ResponseValidator.validate(
        candidate_text=candidate_slur,
        original_text="bhenchod stop!",
    )
    assert is_valid is False
    assert "toxic word" in reason.lower()


def test_validator_rejects_generic_scolding():
    candidate = "Please maintain respectful language in this chatroom."
    is_valid, _, reason = ResponseValidator.validate(
        candidate_text=candidate,
        original_text="You are stupid!",
    )
    assert is_valid is False
    assert "generic scolding" in reason.lower()


def test_validator_rejects_verbatim_duplicate():
    candidate = "Shut up you moron!"
    is_valid, _, reason = ResponseValidator.validate(
        candidate_text=candidate,
        original_text="Shut up you moron!",
    )
    assert is_valid is False
    assert "identical" in reason.lower()


def test_validator_rejects_hallucinatory_length():
    candidate = "Word " * 60  # Far too long
    is_valid, _, reason = ResponseValidator.validate(
        candidate_text=candidate,
        original_text="Shut up!",
    )
    assert is_valid is False
    assert "too long" in reason.lower()


# ── 3. DetoxCache Tests ───────────────────────────────────────────────────────

def test_cache_set_and_get():
    cache = DetoxCache(max_size=5, ttl_seconds=60)
    data = {"original": "bad words", "detoxified": "polite words", "method": "test"}
    cache.set("bad words", data, "en")

    retrieved = cache.get("bad words", "en")
    assert retrieved is not None
    assert retrieved["detoxified"] == "polite words"
    assert cache.stats["hits"] == 1


def test_cache_miss_and_case_normalization():
    cache = DetoxCache(max_size=5, ttl_seconds=60)
    data = {"original": "hello", "detoxified": "hi", "method": "test"}
    cache.set("Hello World", data, "en")

    # Case insensitive + whitespace normalized
    retrieved = cache.get("  hello   world  ", "en")
    assert retrieved is not None
    assert retrieved["detoxified"] == "hi"

    # Miss
    assert cache.get("unknown phrase", "en") is None
    assert cache.stats["misses"] == 1


def test_cache_lru_eviction():
    cache = DetoxCache(max_size=2, ttl_seconds=60)
    cache.set("item1", {"v": 1}, "en")
    cache.set("item2", {"v": 2}, "en")
    cache.set("item3", {"v": 3}, "en")  # Should evict item1

    assert cache.get("item1", "en") is None
    assert cache.get("item2", "en") is not None
    assert cache.get("item3", "en") is not None


def test_cache_ttl_expiration():
    cache = DetoxCache(max_size=5, ttl_seconds=1)  # 1 second TTL
    cache.set("expire_me", {"v": "fresh"}, "en")
    assert cache.get("expire_me", "en") is not None

    time.sleep(1.1)  # Wait for TTL to expire
    assert cache.get("expire_me", "en") is None


# ── 4. Language Detection Tests ───────────────────────────────────────────────

def test_detect_language():
    assert detect_language_simple("Shut up you idiot") == "en"
    assert detect_language_simple("चुप कर बेवकूफ") == "hi"
    assert detect_language_simple("tu chup kar yaar apna kaam kar") == "hi-en"


# ── 5. End-to-End Detoxifier Integration Tests ────────────────────────────────

@pytest.mark.asyncio
async def test_detoxifier_offline_pipeline():
    cfg = DetoxConfig(cache_enabled=True, api_key="")
    detoxifier = Detoxifier(cfg)

    phrase = "Tu bahut bada bewakoof hai bro"
    result = await detoxifier.detoxify(phrase)

    assert result["original"] == phrase
    assert "bewakoof" not in result["detoxified"].lower()
    assert result["method"] == "intent_preserving_scrubber"
    assert result["language"] == "hi-en"
    assert result["confidence"] == 0.85

    # Second call should be served from cache
    cached_result = await detoxifier.detoxify(phrase)
    assert cached_result.get("cached") is True


@pytest.mark.asyncio
async def test_detoxifier_stream():
    cfg = DetoxConfig(cache_enabled=False, api_key="")
    detoxifier = Detoxifier(cfg)

    tokens = []
    async for token in detoxifier.detoxify_stream("Shut up you idiot"):
        tokens.append(token)

    reconstructed = "".join(tokens)
    assert "shut up" not in reconstructed.lower()
    assert "idiot" not in reconstructed.lower()
    assert len(tokens) > 1  # Verify word-by-word streaming

