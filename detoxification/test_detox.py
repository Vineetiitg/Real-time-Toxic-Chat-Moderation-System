#!/usr/bin/env python3
"""
SafeChat Detoxification — Interactive & Automated CLI Tester

Usage:
  # Test with default offline scrubber:
  python -m detoxification.test_detox

  # Test with custom text:
  python -m detoxification.test_detox --text "tu bahut bada bewakoof hai"

  # Test with Gemini API key:
  python -m detoxification.test_detox --api-key YOUR_GEMINI_KEY --text "shut up you idiot"
"""

import argparse
import asyncio
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from detoxification.config import DetoxConfig
from detoxification.detoxifier import Detoxifier

TEST_PHRASES = [
    # English tests
    "Shut up you idiot, do your job properly!",
    "I will kill you if you touch my code again.",
    "Why are you being such a retard and wasting everyone's time?",
    
    # Hinglish tests
    "Tu bahut bada bewakoof hai bro, samajh nahi aata kya?",
    "Bhenchod chup kar aur kaam pe dhyan de.",
    "Aukat me reh apni saale, warna muh tod dunga.",
    
    # Devanagari Hindi tests
    "चुप कर बेवकूफ, अपना काम सही से कर।",
    "बकवास बंद कर और शांति से बात कर।",
    "तू बहुत बड़ा गधा है, कुछ नहीं आता तुझे।",
]


async def run_tests(args):
    cfg = DetoxConfig()
    if args.api_key:
        cfg.api_key = args.api_key
    if args.model:
        cfg.model = args.model

    detoxifier = Detoxifier(cfg)
    info = detoxifier.get_info()

    print("=" * 65)
    print("  SafeChat Detoxification Engine — Test Suite")
    print("=" * 65)
    print(f"  Mode:       {info['mode']}")
    print(f"  Gemini API: {'Configured (' + info['model'] + ')' if info['gemini_configured'] else 'Not configured (using offline scrubber)'}")
    print(f"  Cache:      {'Enabled' if cfg.cache_enabled else 'Disabled'}")
    print("=" * 65)
    print()

    phrases = [args.text] if args.text else TEST_PHRASES

    for i, phrase in enumerate(phrases, 1):
        print(f"[{i}/{len(phrases)}]")
        print(f"  🔴 Original:   {phrase}")
        result = await detoxifier.detoxify(phrase)
        print(f"  🟢 Detoxified: {result['detoxified']}")
        print(f"  ℹ️  Method:     {result['method']} | Lang: {result['language']} | Conf: {result['confidence']}")
        print()

    # Test cache
    if cfg.cache_enabled and len(phrases) > 0:
        first = phrases[0]
        cached_result = await detoxifier.detoxify(first)
        print(f"Cache test for '{first[:30]}...': cached={cached_result.get('cached', False)}")
        print(f"Cache stats: {detoxifier.cache.stats}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Test SafeChat Detoxification")
    parser.add_argument("--text", type=str, default="", help="Custom sentence to detoxify")
    parser.add_argument("--api-key", type=str, default="", help="Optional Gemini API key")
    parser.add_argument("--model", type=str, default="", help="Optional model name")
    args = parser.parse_args()

    asyncio.run(run_tests(args))


if __name__ == "__main__":
    main()
