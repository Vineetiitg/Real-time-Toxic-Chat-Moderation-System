"""
SafeChat Detoxification — Advanced Intent-Preserving Fallback Scrubber

Option B (Offline Fallback):
Scrubs abusive keywords, threats, profanities, and slurs while preserving
the user's underlying intent, conversational nuance, question structure,
and language (English, Hinglish, Devanagari Hindi).
"""

import re
from typing import Dict, List, Tuple


class IntentPreservingScrubber:
    """
    Rule-based, dictionary-driven detoxification engine.
    Runs 100% locally with zero latency (<1ms) and zero external API dependencies.
    """

    # ── Hinglish / Romanized Hindi Replacements ──────────────────────────
    HINGLISH_RULES: List[Tuple[str, str]] = [
        # Severe slurs & mother/sister abuses -> neutral address or remove
        (r'\b(bhenchod|behenchod|bhenchodd|banchod|bc|bsdk|bhosdike|bhosadike|bhosadi|machod|madarchod|madarchodd|mc)\b', 'yaar'),
        (r'\b(chutiya|chutiye|chutye|chomu|lukkha|nalayak|kamina|kamine|kamini)\b', 'naasamajh'),
        (r'\b(saale|saala|sale|sala|harami|haramkhor|dalla|randi|suar|kutta|kutte|kutti|bhikari)\b', ''),
        (r'\b(gadhha|gadha|gadhe|bewakoof|ullu|ullu ke patthe)\b', 'bhai thoda samajhdaari dikhao'),
        # Violent threats & hostility -> de-escalate intent
        (r'\b(jaan se maar duga|jaan se maar dunga|maar duga|maar dunga|khatam kar dunga)\b', 'baat karke suljha lete hain'),
        (r'\b(muh tod duga|muh tod dunga|thappad marunga|pitai karunga)\b', 'shanti se baat karo'),
        (r'\b(aukat me reh|aukat dekh|apni aukaat me reh)\b', 'apni hadd aur maryada me raho'),
        (r'\b(nikal yahan se|nikal pehli fursat mein|dafa ho ja)\b', 'kripya abhi yahan se chale jao'),
        (r'\b(bakwas mat kar|bakwas band kar|faltu baat band kar|bakwaas)\b', 'sahi mudde par baat karo'),
        (r'\b(chup kar|muh band rakh|bolna band kar)\b', 'kripya thoda suno'),
    ]

    # ── Devanagari Hindi Replacements ────────────────────────────────────
    HINDI_DEVANAGARI_RULES: List[Tuple[str, str]] = [
        (r'बहनचोद|मादरचोद|भोसड़ीके|हरामी|हरामखोर', 'भाई'),
        (r'बेवकूफ|गधा|गधे|चूतिया|नालायक|कमीने|कमीना|उल्लू', 'नासमझ'),
        (r'साले|साला|सूअर|कुत्ता|कुत्ते|भिखारी', ''),
        (r'जान से मार दूंगा|मार दूंगा|खत्म कर दूंगा', 'शांति से सुलझाते हैं'),
        (r'मुंह तोड़ दूंगा|थप्पड़ मारूंगा', 'शांति से बात करो'),
        (r'औकात में रह|औकात देख', 'मर्यादा में रहो'),
        (r'बकवास मत कर|बकवास बंद कर|फालतू बात', 'सही से बात करो'),
        (r'निकल यहां से|दफा हो जा', 'कृपया यहां से जाएं'),
        (r'चुप कर|मुंह बंद रख', 'कृपया ध्यान से सुनें'),
    ]

    # ── English Replacements ─────────────────────────────────────────────
    ENGLISH_RULES: List[Tuple[str, str]] = [
        # Threats & physical violence
        (r'\b(i will kill you|gonna kill you|kill yourself|die in a fire)\b', "let's resolve this peacefully"),
        (r'\b(beat you up|break your face|smash your head)\b', "let's keep our tempers in check"),
        # Toxic commands & hostility
        (r'\b(shut up|shut your mouth|shut the fuck up)\b', 'please listen for a moment'),
        (r'\b(get lost|go to hell|fuck off|piss off)\b', 'please step away for a bit'),
        # Insults & slurs -> polite alternatives
        (r'\b(retard|retarded|moron|idiot|fool|clown|loser|scumbag|scum|parasite|bastard|jackass)\b', 'mistaken'),
        (r'\b(fucking|motherfucker|cocksucker|dickhead|asshole|bitch|cunt)\b', ''),
        (r'\b(fuck|shit|damn|crap)\b', ''),
    ]

    # ── Common Structural Cleaning ───────────────────────────────────────
    CLEANUP_PATTERNS: List[Tuple[str, str]] = [
        (r'\s+', ' '),              # Multiple spaces -> single space
        (r'\s*,\s*', ', '),        # Clean commas
        (r'^\s*,\s*', ''),         # Leading commas
        (r',\s*$', ''),            # Trailing commas
        (r'\s+([?.!,])', r'\1'),   # Space before punctuation
        (r'([?.!,]){2,}', r'\1'),  # Duplicate punctuation
    ]

    @classmethod
    def scrub(cls, text: str, detected_language: str = "en") -> str:
        """
        Scrub offensive language while keeping conversational intent and language structure.

        Args:
            text: Raw toxic message
            detected_language: Detected language code (en, hi, hi-en, etc.)

        Returns:
            Intent-preserving detoxified message
        """
        if not text or not text.strip():
            return text

        result = text

        # Apply Devanagari rules if text contains Hindi characters
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in text)
        if has_devanagari:
            for pattern, replacement in cls.HINDI_DEVANAGARI_RULES:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Apply Hinglish rules (works for romanized Hindi + code-mixed text)
        for pattern, replacement in cls.HINGLISH_RULES:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Apply English rules
        for pattern, replacement in cls.ENGLISH_RULES:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Structural cleanup
        for pattern, replacement in cls.CLEANUP_PATTERNS:
            result = re.sub(pattern, replacement, result)

        result = result.strip()

        # If everything was stripped (pure profanity message), provide a polite standard reply
        if not result or len(result) < 2:
            if has_devanagari:
                return "कृपया बातचीत को सम्मानजनक बनाए रखें।"
            elif detected_language in ("hi-en", "hinglish", "indic-en"):
                return "Yaar, thoda respectfully baat karte hain."
            else:
                return "Let's keep the conversation respectful."

        # Ensure sentence capitalization
        if len(result) > 0 and result[0].isalpha():
            result = result[0].upper() + result[1:]

        return result

