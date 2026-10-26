"""
SafeChat — Comprehensive Preprocessing & Adversarial Evasion Tests (Phase 6)

Tests:
  1. Unicode NFC normalization & control character stripping
  2. Cyrillic homoglyph evasion detection (e.g. Cyrillic 'а', 'с')
  3. L33tspeak decoding (e.g. '@', '1', '3', '4', '$')
  4. Character repetition reduction ('fuckkkk' -> 'fuckk')
  5. Separator insertion evasion ('f.u.c.k' -> 'fuck')
  6. Script & code-mixed language detection (English, Hinglish, Devanagari Hindi)
"""

import sys
import os
import pytest

# Ensure ml-service is in sys.path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ml_app = os.path.join(_root, "ml-service")
if _ml_app not in sys.path:
    sys.path.insert(0, _ml_app)

from app.utils.preprocessing import (
    clean_text,
    normalize_homoglyphs,
    normalize_for_toxicity,
    detect_language,
    is_indian_language,
)


# ── 1. Text Cleaning & Normalization ──────────────────────────────────────────

def test_clean_text_basic():
    raw = "  Hello   World!\n\n\n\nHow are you?  "
    cleaned = clean_text(raw, preserve_case=True)
    assert cleaned == "Hello World!\n\nHow are you?"


def test_clean_text_zero_width_characters():
    # Insert zero-width space (\u200b) and byte order mark (\ufeff)
    raw = "f\u200buck\ufeff you"
    cleaned = clean_text(raw)
    assert "fuck you" in cleaned


# ── 2. Homoglyph Evasion ──────────────────────────────────────────────────────

def test_normalize_cyrillic_homoglyphs():
    # Cyrillic 'с' (\u0441) and 'а' (\u0430)
    cyrillic_text = "fu\u0441k \u0430ss"
    normalized = normalize_homoglyphs(cyrillic_text)
    assert normalized == "fuck ass"


# ── 3. Adversarial Toxicity Normalization ─────────────────────────────────────

def test_normalize_leetspeak():
    raw = "h4te th!s b!tch"
    normalized = normalize_for_toxicity(raw)
    assert "hate" in normalized
    assert "this" in normalized
    assert "bitch" in normalized


def test_normalize_character_repetition():
    raw = "fuuuckkkkk youuuu"
    normalized = normalize_for_toxicity(raw)
    # Consecutive repeats reduced to max 2
    assert "fuuckk" in normalized
    assert "youu" in normalized


def test_normalize_separator_insertion():
    raw = "f.u.c.k y.o.u"
    normalized = normalize_for_toxicity(raw)
    assert "fuck" in normalized
    assert "you" in normalized


# ── 4. Language & Script Detection ────────────────────────────────────────────

def test_detect_language_english():
    assert detect_language("This is a clean English message.") == "en"


def test_detect_language_devanagari_hindi():
    assert detect_language("यह एक सुरक्षित हिंदी संदेश है।") == "hi"


def test_detect_language_hinglish():
    # Uses common Hinglish marker words
    assert detect_language("bhai tu kya kar raha hai yahan?") == "hi-en"
    assert detect_language("yaar mujhe yeh theek nahi laga") == "hi-en"


def test_is_indian_language():
    assert is_indian_language("hi") is True
    assert is_indian_language("hi-en") is True
    assert is_indian_language("bn") is True
    assert is_indian_language("ta") is True
    assert is_indian_language("en") is False
    assert is_indian_language("fr") is False

