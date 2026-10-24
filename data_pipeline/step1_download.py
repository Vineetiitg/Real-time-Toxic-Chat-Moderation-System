#!/usr/bin/env python3
"""
SafeChat Data Pipeline — Step 1: Download Raw Datasets

Downloads real-world toxicity datasets from HuggingFace Hub and saves
them as raw CSVs. Each source is saved individually — NO merging here.

Sources:
  1. Jigsaw Toxic Comment Classification (English, ~160K rows, 6-label multi-label)
  2. Prism Hinglish Hate Speech (Romanized Hindi-English, binary labels)
  3. HASOC 2019 Indic Hate Speech (Hindi/Hinglish, multi-class)

Usage:
    python -m data_pipeline.step1_download
"""

import os
import sys
import logging
import pandas as pd

from data_pipeline.config import (
    RAW_DATA_DIR,
    JIGSAW_HF_URL,
    PRISM_HF_URL,
    HASOC_HF_URL,
    MAX_JIGSAW_SAMPLES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Step1-Download")


def download_jigsaw(output_dir: str) -> str:
    """
    Download Jigsaw English Toxicity dataset from HuggingFace.
    Keeps ALL rare-class positives (severe_toxic, threat, identity_hate)
    and samples the rest up to MAX_JIGSAW_SAMPLES.
    """
    output_path = os.path.join(output_dir, "jigsaw_raw.csv")
    if os.path.exists(output_path):
        logger.info(f"[Jigsaw] Already downloaded: {output_path}")
        return output_path

    logger.info("[Jigsaw] Downloading from HuggingFace Hub...")
    try:
        df = pd.read_csv(JIGSAW_HF_URL)
    except Exception as e:
        logger.error(f"[Jigsaw] Download failed: {e}")
        logger.info("[Jigsaw] Tip: Make sure you have internet access and `pandas` can read HF URLs.")
        logger.info("[Jigsaw] Alternative: Download manually from Kaggle and place as jigsaw_raw.csv")
        return ""

    logger.info(f"[Jigsaw] Downloaded {len(df)} rows. Columns: {list(df.columns)}")

    # Rename text column
    if "comment_text" in df.columns:
        df = df.rename(columns={"comment_text": "text"})

    # Smart sampling: keep ALL rare-class positive samples, sample the rest
    rare_tags = ["severe_toxic", "threat", "identity_hate"]
    rare_mask = df[rare_tags].any(axis=1)
    rare_df = df[rare_mask]
    common_df = df[~rare_mask]

    n_remaining = max(0, MAX_JIGSAW_SAMPLES - len(rare_df))
    sampled_common = common_df.sample(n=min(len(common_df), n_remaining), random_state=42)
    df_final = pd.concat([rare_df, sampled_common], ignore_index=True)
    df_final = df_final.sample(frac=1.0, random_state=42).reset_index(drop=True)

    logger.info(f"[Jigsaw] Kept {len(rare_df)} rare-class samples + {len(sampled_common)} common = {len(df_final)} total")

    df_final.to_csv(output_path, index=False)
    logger.info(f"[Jigsaw] Saved to: {output_path}")
    return output_path


def download_prism(output_dir: str) -> str:
    """Download Prism Hinglish Hate Speech dataset from HuggingFace."""
    output_path = os.path.join(output_dir, "prism_raw.csv")
    if os.path.exists(output_path):
        logger.info(f"[Prism] Already downloaded: {output_path}")
        return output_path

    logger.info("[Prism] Downloading from HuggingFace Hub...")
    try:
        df = pd.read_csv(PRISM_HF_URL)
    except Exception as e:
        logger.error(f"[Prism] Download failed: {e}")
        return ""

    logger.info(f"[Prism] Downloaded {len(df)} rows. Columns: {list(df.columns)}")
    df.to_csv(output_path, index=False)
    logger.info(f"[Prism] Saved to: {output_path}")
    return output_path


def download_hasoc(output_dir: str) -> str:
    """Download HASOC 2019 Indic Hate Speech dataset from HuggingFace."""
    output_path = os.path.join(output_dir, "hasoc_raw.csv")
    if os.path.exists(output_path):
        logger.info(f"[HASOC] Already downloaded: {output_path}")
        return output_path

    logger.info("[HASOC] Downloading from HuggingFace Hub...")
    try:
        df = pd.read_csv(HASOC_HF_URL)
    except Exception as e:
        logger.error(f"[HASOC] Download failed: {e}")
        return ""

    logger.info(f"[HASOC] Downloaded {len(df)} rows. Columns: {list(df.columns)}")
    df.to_csv(output_path, index=False)
    logger.info(f"[HASOC] Saved to: {output_path}")
    return output_path


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    logger.info("=" * 60)
    logger.info("  SafeChat Data Pipeline — Step 1: Download Raw Datasets")
    logger.info("=" * 60)

    results = {}
    results["jigsaw"] = download_jigsaw(RAW_DATA_DIR)
    results["prism"] = download_prism(RAW_DATA_DIR)
    results["hasoc"] = download_hasoc(RAW_DATA_DIR)

    logger.info("\n" + "=" * 60)
    logger.info("  Download Summary")
    logger.info("=" * 60)
    for name, path in results.items():
        status = "✅" if path and os.path.exists(path) else "❌ FAILED"
        size = ""
        if path and os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            size = f" ({size_mb:.1f} MB)"
        logger.info(f"  {name:>10}: {status}{size}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

