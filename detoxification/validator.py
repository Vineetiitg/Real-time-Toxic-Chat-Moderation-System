"""
SafeChat Detoxification — Response Validation Gatekeeper

Verifies that generated detoxified text from the LLM is truly non-toxic,
intent-preserving, free of hallucinations or meta-preambles, and not
a generic corporate lecture.
"""

import re
from typing import Optional, Tuple


class ResponseValidator:
    """
    Validates LLM detoxification output before presenting to the user.
    """

    # Generic moralizing phrases that LLMs default to instead of rephrasing
    GENERIC_SCOLDING_KEYWORDS = [
        "please maintain respectful",
        "let's keep the conversation respectful",
        "avoid using offensive language",
        "please refrain from using offensive",
        "as an ai",
        "i cannot fulfill",
        "i am programmed to be",
        "kripya apashabd",
        "vinaamrata banaye",
        "shishtachar",
        "bhasha ka prayog na kare",
        "respectful language",
        "polite conversation",
        "opinion respectfully",
    ]

    # Critical toxicity words that MUST NOT appear in detoxified text
    TOXIC_RESIDUAL_KEYWORDS = [
        # English
        "fuck", "bitch", "cunt", "asshole", "retard", "dickhead", "kill yourself", "die in a fire", "scoundrel", "rascal",
        # Hinglish / Hindi
        "bhenchod", "madarchod", "chutiya", "bhosdike", "harami", "haramkhor", "machod", "randi",
        "बहनचोद", "मादरचोद", "भोसड़ी", "चूतिया", "हरामखोर",
    ]

    # Meta-preamble patterns that LLMs sometimes generate
    PREAMBLE_PATTERNS = [
        r'^(here is (the )?(rewritten|polite|non-toxic) (message|text|version)[:\-]?\s*)',
        r'^(rewritten message[:\-]?\s*)',
        r'^(alternative[:\-]?\s*)',
        r'^(polite version[:\-]?\s*)',
    ]

    @classmethod
    def clean_preambles(cls, text: str) -> str:
        """Strip quotes and LLM preambles ('Here is the rewritten text: ...')."""
        if not text:
            return ""

        cleaned = text.strip()

        # Remove surrounding quotes
        if len(cleaned) >= 2:
            if (cleaned[0] == '"' and cleaned[-1] == '"') or (cleaned[0] == "'" and cleaned[-1] == "'"):
                cleaned = cleaned[1:-1].strip()

        # Remove preambles
        for pattern in cls.PREAMBLE_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

        # Remove surrounding quotes again if they were inside preamble
        if len(cleaned) >= 2:
            if (cleaned[0] == '"' and cleaned[-1] == '"') or (cleaned[0] == "'" and cleaned[-1] == "'"):
                cleaned = cleaned[1:-1].strip()

        return cleaned

    @classmethod
    def validate(
        cls,
        candidate_text: Optional[str],
        original_text: str,
        max_length_multiplier: float = 3.5,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate whether candidate text is a good, safe detoxification.

        Returns:
            Tuple[is_valid: bool, cleaned_text: str, reason_if_invalid: Optional[str]]
        """
        if not candidate_text:
            return False, "", "Output is empty"

        cleaned = cls.clean_preambles(candidate_text)

        if len(cleaned) < 2:
            return False, cleaned, "Output too short"

        lower_cleaned = cleaned.lower()

        # Check 1: Generic moralizing lecture / scolding
        for scolding in cls.GENERIC_SCOLDING_KEYWORDS:
            if scolding in lower_cleaned:
                return False, cleaned, f"Output is generic scolding ('{scolding}')"

        # Check 2: Residual severe toxicity
        for toxic_word in cls.TOXIC_RESIDUAL_KEYWORDS:
            # Word boundary check for latin, substring for devanagari
            if re.search(r'\b' + re.escape(toxic_word) + r'\b', lower_cleaned, re.IGNORECASE):
                return False, cleaned, f"Output still contains toxic word ('{toxic_word}')"
            if any('\u0900' <= c <= '\u097F' for c in toxic_word) and toxic_word in cleaned:
                return False, cleaned, f"Output contains toxic word ('{toxic_word}')"

        # Check 3: Verbatim identical to original toxic text
        if cleaned.strip().lower() == original_text.strip().lower():
            return False, cleaned, "Output is identical to original toxic text"

        # Check 4: Length explosion (LLM hallucinated a long paragraph)
        if len(cleaned) > max(40, len(original_text) * max_length_multiplier):
            return False, cleaned, f"Output too long ({len(cleaned)} chars vs original {len(original_text)})"

        return True, cleaned, None
