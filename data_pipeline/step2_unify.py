#!/usr/bin/env python3
"""
SafeChat Data Pipeline — Step 2: Unify & Clean

Reads each raw CSV from Step 1, maps their heterogeneous label schemas
into our standard 6-tag multi-label format, applies text cleaning, adds
curated Indic seed data, and outputs a single `unified_clean.csv`.

Key operations:
  - Schema mapping (binary → 6-tag, HASOC classes → 6-tag)
  - Text cleaning (unicode normalization, control char removal)
  - Adversarial normalization (homoglyphs, leetspeak, char repetition)
  - Deduplication (fuzzy near-duplicate removal)
  - Length filtering (drop too-short and too-long texts)
  - Source language tagging

Usage:
    python -m data_pipeline.step2_unify
"""

import os
import re
import sys
import logging
import unicodedata
from typing import List

import pandas as pd
import numpy as np

from data_pipeline.config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    LABEL_COLUMNS,
    TEXT_COLUMN,
    SOURCE_COLUMN,
    MAX_TEXT_LENGTH_CHARS,
    MIN_TEXT_LENGTH_CHARS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Step2-Unify")


# ── Text Cleaning Functions ────────────────────────────────────────

# Cyrillic homoglyphs (used to evade filters: "fuсk" with Cyrillic с)
CYRILLIC_TO_LATIN = {
    "\u0430": "a", "\u0435": "e", "\u0456": "i", "\u043e": "o",
    "\u0440": "p", "\u0441": "c", "\u0443": "y", "\u0445": "x",
    "\u0410": "A", "\u0412": "B", "\u0415": "E", "\u041a": "K",
    "\u041c": "M", "\u041d": "H", "\u041e": "O", "\u0420": "P",
    "\u0421": "C", "\u0422": "T", "\u0425": "X",
}
_HOMOGLYPH_TABLE = str.maketrans(CYRILLIC_TO_LATIN)

LEET_MAP = {
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "7": "t", "8": "b", "@": "a", "$": "s",
}


def clean_text(text: str) -> str:
    """
    Clean raw text for ML consumption:
      1. Unicode NFC normalization
      2. Remove zero-width and control characters (keep newlines)
      3. Normalize whitespace
      4. Strip leading/trailing whitespace
    Does NOT lowercase — the model handles casing.
    Does NOT remove emojis — they carry semantic signal.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    # Unicode normalization (canonical composition)
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width chars and most control characters (keep \n, \t)
    text = re.sub(r"[\u200b-\u200f\u2028-\u202f\u2060-\u2069\ufeff]", "", text)

    # Normalize repeated whitespace (but preserve single newlines)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_adversarial(text: str) -> str:
    """
    Normalize adversarial evasion techniques for consistent model input:
      - Cyrillic homoglyphs: "fuсk" → "fuck"
      - Character repetition: "fuckkkk" → "fuckk"
      - Separator insertion: "f.u.c.k" → "fuck"
      - Leet speak: "h4te" → "hate"
    
    Applied BOTH during data prep AND inference for consistency.
    """
    # Cyrillic → Latin
    text = text.translate(_HOMOGLYPH_TABLE)

    # Reduce character repetition (keep max 2 of same char)
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)

    # Remove separators between isolated single characters
    # "f.u.c.k" or "f u c k" → "fuck"
    text = re.sub(
        r"(?<=[a-zA-Z])[.\-_\s](?=[a-zA-Z](?:[.\-_\s][a-zA-Z]){1,})",
        "",
        text,
    )

    # Leet speak substitution (only in words that look like leet speak)
    def _deleet(match):
        word = match.group(0)
        if any(c in word for c in LEET_MAP):
            for leet, normal in LEET_MAP.items():
                word = word.replace(leet, normal)
        return word

    text = re.sub(r"\b\S+\b", _deleet, text)

    return text


# ── Source-Specific Schema Mappers ─────────────────────────────────

def map_jigsaw(raw_path: str) -> pd.DataFrame:
    """Map Jigsaw CSV → unified schema. Already has 6 columns."""
    if not raw_path or not os.path.exists(raw_path):
        logger.warning("[Jigsaw] Raw file not found, skipping.")
        return pd.DataFrame()

    df = pd.read_csv(raw_path)
    logger.info(f"[Jigsaw] Loaded {len(df)} rows from {raw_path}")

    # Jigsaw already has the exact 6 columns we need
    if "text" not in df.columns and "comment_text" in df.columns:
        df = df.rename(columns={"comment_text": "text"})

    for col in LABEL_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    df[SOURCE_COLUMN] = "english_jigsaw"
    return df[[TEXT_COLUMN, SOURCE_COLUMN] + LABEL_COLUMNS]


def map_prism(raw_path: str) -> pd.DataFrame:
    """
    Map Prism Hinglish binary labels → 6-tag schema.
    
    Prism has: text, label (0=not_hate, 1=hate), lang
    We map: hate → toxic=1, insult=1 (conservative mapping)
    """
    if not raw_path or not os.path.exists(raw_path):
        logger.warning("[Prism] Raw file not found, skipping.")
        return pd.DataFrame()

    df = pd.read_csv(raw_path)
    logger.info(f"[Prism] Loaded {len(df)} rows from {raw_path}")

    is_hate = (df["label"] == 1).astype(int)

    df[TEXT_COLUMN] = df["text"].astype(str)
    df[SOURCE_COLUMN] = "hinglish_prism"
    df["toxic"] = is_hate
    df["severe_toxic"] = 0
    df["obscene"] = 0
    df["threat"] = 0
    df["insult"] = is_hate
    df["identity_hate"] = 0  # Conservative: don't assume all hate is identity-based

    return df[[TEXT_COLUMN, SOURCE_COLUMN] + LABEL_COLUMNS]


def map_hasoc(raw_path: str) -> pd.DataFrame:
    """
    Map HASOC multi-class labels → 6-tag schema.
    
    HASOC has: binary class (HOF/NOT), Context class (HATE/OFFN/PRFN/NONE)
    We map:
      - HOF → toxic=1
      - PRFN (profanity) → obscene=1
      - OFFN (offensive) → insult=1
      - HATE → identity_hate=1
    """
    if not raw_path or not os.path.exists(raw_path):
        logger.warning("[HASOC] Raw file not found, skipping.")
        return pd.DataFrame()

    df = pd.read_csv(raw_path)
    logger.info(f"[HASOC] Loaded {len(df)} rows from {raw_path}")

    # Text column varies between HASOC versions
    if "cleaned Tweets" in df.columns:
        df[TEXT_COLUMN] = df["cleaned Tweets"].fillna(df.get("rawtweets", ""))
    elif "text" in df.columns:
        df[TEXT_COLUMN] = df["text"]
    else:
        logger.error(f"[HASOC] Could not find text column. Available: {list(df.columns)}")
        return pd.DataFrame()

    df[SOURCE_COLUMN] = "hindi_hasoc"

    is_hof = (df["binary class"].astype(str).str.upper() == "HOF").astype(int)
    ctx = df["Context class"].astype(str).str.upper() if "Context class" in df.columns else pd.Series("NONE", index=df.index)

    df["toxic"] = is_hof
    df["severe_toxic"] = 0
    df["obscene"] = (ctx == "PRFN").astype(int)
    df["threat"] = 0
    df["insult"] = ((ctx == "OFFN") | is_hof.astype(bool)).astype(int)
    df["identity_hate"] = (ctx == "HATE").astype(int)

    return df[[TEXT_COLUMN, SOURCE_COLUMN] + LABEL_COLUMNS]


def get_curated_indic_seed() -> pd.DataFrame:
    """
    Hand-curated high-quality Indic samples for underrepresented categories.
    These fill gaps where downloaded datasets lack coverage:
      - Hindi Devanagari threats
      - Hinglish obscenity
      - Identity hate in Indian context
    
    Each sample is unique, hand-labeled, and NOT duplicated.
    """
    curated_data = [
        # ── Safe / Positive ──────────────────────────────────────
        ("Hello brother, how are you doing today?", [0,0,0,0,0,0], "english_curated"),
        ("Bhai aaj ka match kaisa laga? Virat played really well!", [0,0,0,0,0,0], "hinglish_curated"),
        ("Aapka swagat hai hamare server par. Let's discuss AI.", [0,0,0,0,0,0], "hinglish_curated"),
        ("mujhe ye naya update bahut pasand aaya, good job team", [0,0,0,0,0,0], "hinglish_curated"),
        ("namaste dosto, kya haal chaal hain sabke?", [0,0,0,0,0,0], "hinglish_curated"),
        ("यह बहुत ही शानदार काम है, बधाई हो!", [0,0,0,0,0,0], "hindi_curated"),
        ("kya ham kal sham ko call par baat kar sakte hain?", [0,0,0,0,0,0], "hinglish_curated"),
        ("aapki mehnat rang laayi, proud of you!", [0,0,0,0,0,0], "hinglish_curated"),
        ("बहुत अच्छा काम किया आपने, ऐसे ही आगे बढ़ते रहो", [0,0,0,0,0,0], "hindi_curated"),
        ("Thank you for helping me with the project, really appreciate it", [0,0,0,0,0,0], "english_curated"),

        # ── Toxic & Insult (Hinglish) ────────────────────────────
        ("tu bahut bada bewakoof aur gadhha hai, chup kar", [1,0,0,0,1,0], "hinglish_curated"),
        ("abe saale apna dimag mat kharab kar mera yahan se nikal", [1,0,1,0,1,0], "hinglish_curated"),
        ("tum log sab ke sab nikamme aur ghatiya ho", [1,0,0,0,1,0], "hinglish_curated"),
        ("teri aukaat kya hai be mujhse baat karne ki? nalayak insaan", [1,0,0,0,1,0], "hinglish_curated"),
        ("bakwas band kar apni, dimag ka dahi bana diya hai", [1,0,0,0,1,0], "hinglish_curated"),
        ("तुम बहुत ही घटिया और नीच इंसान हो", [1,0,0,0,1,0], "hindi_curated"),
        ("अरे बेवकूफ इंसान, तुझे कुछ समझ नहीं आता क्या? भाग यहाँ से", [1,0,0,0,1,0], "hindi_curated"),

        # ── Severe Toxic & Obscene ───────────────────────────────
        ("madarchod harami kutte kahan chupa hai tu", [1,1,1,0,1,0], "hinglish_curated"),
        ("bhenchod bakwas mat kar warna accha nahi hoga", [1,1,1,0,1,0], "hinglish_curated"),
        ("teri maa ki aankh saale harami bsdwale", [1,1,1,0,1,0], "hinglish_curated"),
        ("chutiya saala dimag ki aisi taisi kar raha hai", [1,1,1,0,1,0], "hinglish_curated"),
        ("मादरचोद कमीने कुत्ते, तेरी औकात क्या है", [1,1,1,0,1,0], "hindi_curated"),
        ("बेहंचोद साले हरामजादे कुत्ते अपनी शक्ल मत दिखाना", [1,1,1,0,1,0], "hindi_curated"),

        # ── Threat ───────────────────────────────────────────────
        ("mai tujhe jaan se maar duga agar tu wahan dikha to", [1,1,0,1,0,0], "hinglish_curated"),
        ("tujhe ghar se nikal kar peetunga saale yaad rakhna", [1,0,0,1,1,0], "hinglish_curated"),
        ("mai tera muh tod duga agar tune ek aur shabd bola", [1,0,0,1,1,0], "hinglish_curated"),
        ("तुझे जान से मार दूंगा अगर फिर से फोन किया तो", [1,1,0,1,0,0], "hindi_curated"),
        ("तुझे घर से निकाल कर गोली मार दूंगा, आज रात तेरा आखिरी दिन है", [1,1,0,1,0,0], "hindi_curated"),
        ("mai tujhe zinda nahi chodunga saale kutte mil tu bahar", [1,1,0,1,1,0], "hinglish_curated"),
        ("teri jaan le lunga agar tune meri baat nahi maani", [1,1,0,1,1,0], "hinglish_curated"),
        ("आज शाम को तुझसे निपट लूंगा, तुझे कोई नहीं बचा पाएगा", [1,0,0,1,0,0], "hindi_curated"),
        ("goli se uda duga tereko agar ek aur sms kiya to kutte", [1,1,0,1,1,0], "hinglish_curated"),
        ("काट कर फेंक दूंगा तुझे अगर मेरे रास्ते में आया तो", [1,1,0,1,1,0], "hindi_curated"),

        # ── Identity Hate ────────────────────────────────────────
        ("all you people of your religion are terrorists and scum", [1,1,0,0,1,1], "english_curated"),
        ("tumhari jaati ke log hamesha se hi ghatiya aur chor rahe hain", [1,0,0,0,1,1], "hinglish_curated"),
        ("ye log desh ke gaddar hain, inko bahar nikalo sabko", [1,0,0,0,1,1], "hinglish_curated"),
        ("इस धर्म के सारे लोग आतंकवादी और देश के गद्दार हैं", [1,0,0,0,1,1], "hindi_curated"),
        ("तुम्हारी नीची जाति के लोग हमेशा से ही चोर और घटिया रहे हैं", [1,0,0,0,1,1], "hindi_curated"),
        ("aurton ki jagah sirf kitchen me khana banane ki hai", [1,0,0,0,1,1], "hinglish_curated"),
        ("औरतों की जगह सिर्फ किचन में है, ज्यादा दिमाग मत चलाओ", [1,0,0,0,1,1], "hindi_curated"),
        ("these foreigners are ruining our country, send them all back", [1,0,0,0,1,1], "english_curated"),
    ]

    rows = []
    for text, labels, source in curated_data:
        row = {TEXT_COLUMN: text, SOURCE_COLUMN: source}
        for tag, val in zip(LABEL_COLUMNS, labels):
            row[tag] = val
        rows.append(row)

    return pd.DataFrame(rows)


# ── Unification Pipeline ──────────────────────────────────────────

def unify_and_clean() -> pd.DataFrame:
    """
    Main pipeline: load all sources, map schemas, clean text,
    deduplicate, and output a single unified DataFrame.
    """
    logger.info("=" * 60)
    logger.info("  SafeChat Data Pipeline — Step 2: Unify & Clean")
    logger.info("=" * 60)

    dfs: List[pd.DataFrame] = []

    # Load and map each source
    jigsaw_path = os.path.join(RAW_DATA_DIR, "jigsaw_raw.csv")
    prism_path = os.path.join(RAW_DATA_DIR, "prism_raw.csv")
    hasoc_path = os.path.join(RAW_DATA_DIR, "hasoc_raw.csv")

    for name, mapper, path in [
        ("Jigsaw", map_jigsaw, jigsaw_path),
        ("Prism", map_prism, prism_path),
        ("HASOC", map_hasoc, hasoc_path),
    ]:
        df = mapper(path)
        if len(df) > 0:
            dfs.append(df)
            logger.info(f"[{name}] Mapped {len(df)} rows to unified schema.")

    # Add curated Indic seed
    curated = get_curated_indic_seed()
    dfs.append(curated)
    logger.info(f"[Curated] Added {len(curated)} hand-labeled Indic samples.")

    if not dfs or sum(len(d) for d in dfs) < 100:
        # Fallback: use pre-existing unified dataset if individual raw files aren't available
        fallback_paths = [
            os.path.join(RAW_DATA_DIR, "existing_unified.csv"),
            os.path.join(os.path.dirname(PROCESSED_DATA_DIR), "..", "ml-service", "training", "data", "real_datasets", "unified_dataset_full.csv"),
        ]
        for fb_path in fallback_paths:
            norm_path = os.path.normpath(fb_path)
            if os.path.exists(norm_path):
                logger.info(f"Using existing unified dataset as fallback: {norm_path}")
                fb_df = pd.read_csv(norm_path)
                fb_df[TEXT_COLUMN] = fb_df[TEXT_COLUMN].astype(str)
                if SOURCE_COLUMN not in fb_df.columns:
                    fb_df[SOURCE_COLUMN] = "unknown"
                for col in LABEL_COLUMNS:
                    if col not in fb_df.columns:
                        fb_df[col] = 0
                dfs = [fb_df[[TEXT_COLUMN, SOURCE_COLUMN] + LABEL_COLUMNS]]
                break

    if not dfs:
        logger.error("No data loaded! Run step1_download first or place data in raw/ directory.")
        sys.exit(1)

    # Merge all
    df = pd.concat(dfs, ignore_index=True)
    logger.info(f"\nMerged total: {len(df)} rows before cleaning.")

    # ── Clean text ──────────────────────────────────────────────
    logger.info("Applying text cleaning...")
    df[TEXT_COLUMN] = df[TEXT_COLUMN].astype(str).apply(clean_text)

    # ── Apply adversarial normalization ─────────────────────────
    # Create a normalized version for dedup, but keep original for training
    logger.info("Computing adversarial-normalized text for deduplication...")
    df["_text_norm"] = df[TEXT_COLUMN].apply(lambda t: normalize_adversarial(t.lower()))

    # ── Length filtering ────────────────────────────────────────
    before_len = len(df)
    df = df[df[TEXT_COLUMN].str.len() >= MIN_TEXT_LENGTH_CHARS]
    df = df[df[TEXT_COLUMN].str.len() <= MAX_TEXT_LENGTH_CHARS]
    logger.info(f"Length filter: {before_len} → {len(df)} rows (dropped {before_len - len(df)} too short/long)")

    # ── Deduplication ───────────────────────────────────────────
    # Drop exact duplicates on normalized text (catches homoglyph/leetspeak variants)
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["_text_norm"], keep="first").reset_index(drop=True)
    logger.info(f"Deduplication: {before_dedup} → {len(df)} rows (dropped {before_dedup - len(df)} duplicates)")

    # Drop the temp column
    df = df.drop(columns=["_text_norm"])

    # ── Ensure label columns are int ────────────────────────────
    for col in LABEL_COLUMNS:
        df[col] = df[col].fillna(0).astype(int)

    # ── Final shuffle ───────────────────────────────────────────
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    logger.info(f"\n✅ Final unified dataset: {len(df)} unique, clean rows")
    logger.info(f"   Sources: {df[SOURCE_COLUMN].value_counts().to_dict()}")

    return df


def main():
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

    df = unify_and_clean()

    output_path = os.path.join(PROCESSED_DATA_DIR, "unified_clean.csv")
    df.to_csv(output_path, index=False)
    logger.info(f"Saved to: {output_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

