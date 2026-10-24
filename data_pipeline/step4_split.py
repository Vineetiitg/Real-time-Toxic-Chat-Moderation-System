#!/usr/bin/env python3
"""
SafeChat Data Pipeline — Step 4: Stratified Split

Splits the unified clean dataset into Train / Val / Test sets with
multi-label stratification to preserve class distribution across splits.

Uses iterative-stratification (MultilabelStratifiedKFold) which is the
gold standard for multi-label splits — much better than random splitting
or single-label stratification.

Outputs:
  - splits/train.csv  (80%)
  - splits/val.csv    (10%)
  - splits/test.csv   (10%)
  - splits/split_report.json

Usage:
    python -m data_pipeline.step4_split
"""

import os
import sys
import json
import logging

import numpy as np
import pandas as pd

from data_pipeline.config import (
    PROCESSED_DATA_DIR,
    SPLITS_DIR,
    LABEL_COLUMNS,
    TEXT_COLUMN,
    SOURCE_COLUMN,
    SPLIT_SEED,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Step4-Split")


def split_dataset(df: pd.DataFrame):
    """
    Split into 80/10/10 using MultilabelStratifiedKFold.
    
    Strategy:
      1. Use 10-fold MSKF → take 1 fold as test (10%)
      2. From remaining 90%, use 9-fold MSKF → take 1 fold as val (~10%)
      3. Rest is train (~80%)
    """
    try:
        from iterstrat.ml_stratifiers import MultilabelStratifiedKFold
    except ImportError:
        logger.error(
            "iterative-stratification not installed!\n"
            "Install with: pip install iterative-stratification\n"
            "This is required for proper multi-label stratified splitting."
        )
        sys.exit(1)

    X = df[TEXT_COLUMN].values
    y = df[LABEL_COLUMNS].values

    # Split 1: 90% train+val, 10% test
    mskf = MultilabelStratifiedKFold(n_splits=10, shuffle=True, random_state=SPLIT_SEED)
    train_val_idx, test_idx = next(mskf.split(X, y))

    train_val_df = df.iloc[train_val_idx].reset_index(drop=True)
    test_df = df.iloc[test_idx].reset_index(drop=True)

    # Split 2: From the 90%, take 1/9 as val (~10% of total), 8/9 as train (~80%)
    X_tv = train_val_df[TEXT_COLUMN].values
    y_tv = train_val_df[LABEL_COLUMNS].values

    mskf_val = MultilabelStratifiedKFold(n_splits=9, shuffle=True, random_state=SPLIT_SEED)
    train_idx, val_idx = next(mskf_val.split(X_tv, y_tv))

    train_df = train_val_df.iloc[train_idx].reset_index(drop=True)
    val_df = train_val_df.iloc[val_idx].reset_index(drop=True)

    return train_df, val_df, test_df


def verify_no_leakage(train_df, val_df, test_df):
    """Verify no text appears in multiple splits (data leakage check)."""
    train_texts = set(train_df[TEXT_COLUMN].values)
    val_texts = set(val_df[TEXT_COLUMN].values)
    test_texts = set(test_df[TEXT_COLUMN].values)

    train_val_overlap = train_texts & val_texts
    train_test_overlap = train_texts & test_texts
    val_test_overlap = val_texts & test_texts

    leaks = len(train_val_overlap) + len(train_test_overlap) + len(val_test_overlap)

    if leaks > 0:
        logger.warning(f"⚠️ DATA LEAKAGE DETECTED!")
        logger.warning(f"   Train ∩ Val:  {len(train_val_overlap)} overlapping texts")
        logger.warning(f"   Train ∩ Test: {len(train_test_overlap)} overlapping texts")
        logger.warning(f"   Val ∩ Test:   {len(val_test_overlap)} overlapping texts")
    else:
        logger.info("✅ No data leakage — all splits are disjoint.")

    return leaks


def compute_split_stats(df: pd.DataFrame, split_name: str) -> dict:
    """Compute per-split class distribution for the report."""
    total = len(df)
    stats = {"split": split_name, "total": total}
    for col in LABEL_COLUMNS:
        pos = int(df[col].sum())
        stats[f"{col}_pos"] = pos
        stats[f"{col}_rate"] = round((pos / max(1, total)) * 100, 2)
    return stats


def main():
    os.makedirs(SPLITS_DIR, exist_ok=True)

    input_path = os.path.join(PROCESSED_DATA_DIR, "unified_clean.csv")
    if not os.path.exists(input_path):
        logger.error(f"Unified dataset not found at {input_path}. Run step2_unify first!")
        sys.exit(1)

    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} rows from {input_path}")

    logger.info("=" * 60)
    logger.info("  SafeChat Data Pipeline — Step 4: Stratified Split")
    logger.info("=" * 60)

    # Split
    train_df, val_df, test_df = split_dataset(df)

    logger.info(f"\n  Split sizes:")
    logger.info(f"    Train: {len(train_df):>6} ({len(train_df)/len(df)*100:.1f}%)")
    logger.info(f"    Val:   {len(val_df):>6} ({len(val_df)/len(df)*100:.1f}%)")
    logger.info(f"    Test:  {len(test_df):>6} ({len(test_df)/len(df)*100:.1f}%)")

    # Verify no leakage
    leaks = verify_no_leakage(train_df, val_df, test_df)

    # Verify class distribution is preserved
    logger.info("\n  Per-split class rates (should be similar across splits):")
    logger.info(f"  {'Tag':<15} | {'Train':>8} | {'Val':>8} | {'Test':>8}")
    logger.info("  " + "-" * 48)
    for col in LABEL_COLUMNS:
        train_rate = round((train_df[col].sum() / len(train_df)) * 100, 1)
        val_rate = round((val_df[col].sum() / len(val_df)) * 100, 1)
        test_rate = round((test_df[col].sum() / len(test_df)) * 100, 1)
        logger.info(f"  {col:<15} | {train_rate:>7.1f}% | {val_rate:>7.1f}% | {test_rate:>7.1f}%")

    # Save splits
    train_path = os.path.join(SPLITS_DIR, "train.csv")
    val_path = os.path.join(SPLITS_DIR, "val.csv")
    test_path = os.path.join(SPLITS_DIR, "test.csv")

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    logger.info(f"\n  Saved: {train_path}")
    logger.info(f"  Saved: {val_path}")
    logger.info(f"  Saved: {test_path}")

    # Save split report
    report = {
        "source_file": input_path,
        "total_samples": len(df),
        "seed": SPLIT_SEED,
        "data_leakage_count": leaks,
        "splits": [
            compute_split_stats(train_df, "train"),
            compute_split_stats(val_df, "val"),
            compute_split_stats(test_df, "test"),
        ],
    }
    report_path = os.path.join(SPLITS_DIR, "split_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info(f"  Report: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

