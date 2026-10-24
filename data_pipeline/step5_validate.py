#!/usr/bin/env python3
"""
SafeChat Data Pipeline — Step 5: Validate & Export

Final validation gate before training:
  1. Loads the split files
  2. Runs integrity checks (schema, types, leakage, distribution)
  3. Copies final validated splits to ml-service/training/data/ for the training script
  4. Prints a summary ready for training

Usage:
    python -m data_pipeline.step5_validate
"""

import os
import sys
import json
import shutil
import logging

import pandas as pd
import numpy as np

from data_pipeline.config import (
    SPLITS_DIR,
    REPORTS_DIR,
    LABEL_COLUMNS,
    TEXT_COLUMN,
    SOURCE_COLUMN,
    PROJECT_ROOT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Step5-Validate")

# Where the training script expects data
TRAINING_DATA_DIR = os.path.join(PROJECT_ROOT, "ml-service", "training", "data", "real_datasets")


def validate_schema(df: pd.DataFrame, split_name: str) -> int:
    """Verify the DataFrame has the expected columns and types."""
    errors = 0

    # Check required columns exist
    for col in [TEXT_COLUMN, SOURCE_COLUMN] + LABEL_COLUMNS:
        if col not in df.columns:
            logger.error(f"  [{split_name}] Missing column: {col}")
            errors += 1

    # Check text is non-empty string
    empty_count = (df[TEXT_COLUMN].isna() | (df[TEXT_COLUMN].str.strip() == "")).sum()
    if empty_count > 0:
        logger.error(f"  [{split_name}] {empty_count} empty/null text rows!")
        errors += 1

    # Check labels are 0 or 1
    for col in LABEL_COLUMNS:
        if col in df.columns:
            unique_vals = set(df[col].unique())
            if not unique_vals.issubset({0, 1}):
                logger.error(f"  [{split_name}] Column '{col}' has non-binary values: {unique_vals}")
                errors += 1

    return errors


def validate_distribution(train_df, val_df, test_df) -> int:
    """
    Check that class distribution is roughly consistent across splits.
    Flag if any split's class rate deviates by more than 5% absolute from overall.
    """
    warnings = 0
    total_df = pd.concat([train_df, val_df, test_df], ignore_index=True)

    for col in LABEL_COLUMNS:
        overall_rate = total_df[col].mean() * 100
        for name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
            split_rate = split_df[col].mean() * 100
            deviation = abs(split_rate - overall_rate)
            if deviation > 5.0:
                logger.warning(f"  [{name}] '{col}' rate={split_rate:.1f}% vs overall={overall_rate:.1f}% (Δ={deviation:.1f}%)")
                warnings += 1

    return warnings


def main():
    logger.info("=" * 60)
    logger.info("  SafeChat Data Pipeline — Step 5: Validate & Export")
    logger.info("=" * 60)

    # Load splits
    train_path = os.path.join(SPLITS_DIR, "train.csv")
    val_path = os.path.join(SPLITS_DIR, "val.csv")
    test_path = os.path.join(SPLITS_DIR, "test.csv")

    for path in [train_path, val_path, test_path]:
        if not os.path.exists(path):
            logger.error(f"Split file not found: {path}. Run step4_split first!")
            sys.exit(1)

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    logger.info(f"  Loaded splits: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # ── Validation 1: Schema ───────────────────────────────────
    logger.info("\n  Validation 1: Schema check...")
    total_errors = 0
    total_errors += validate_schema(train_df, "train")
    total_errors += validate_schema(val_df, "val")
    total_errors += validate_schema(test_df, "test")

    if total_errors == 0:
        logger.info("  ✅ Schema validation passed.")
    else:
        logger.error(f"  ❌ Schema validation failed with {total_errors} errors!")
        sys.exit(1)

    # ── Validation 2: No data leakage ──────────────────────────
    logger.info("\n  Validation 2: Data leakage check...")
    train_texts = set(train_df[TEXT_COLUMN].values)
    val_texts = set(val_df[TEXT_COLUMN].values)
    test_texts = set(test_df[TEXT_COLUMN].values)

    leaks = len(train_texts & val_texts) + len(train_texts & test_texts) + len(val_texts & test_texts)
    if leaks == 0:
        logger.info("  ✅ No data leakage across splits.")
    else:
        logger.error(f"  ❌ {leaks} leaked samples found across splits!")
        sys.exit(1)

    # ── Validation 3: Distribution consistency ─────────────────
    logger.info("\n  Validation 3: Distribution consistency...")
    dist_warnings = validate_distribution(train_df, val_df, test_df)
    if dist_warnings == 0:
        logger.info("  ✅ Class distribution consistent across splits.")
    else:
        logger.warning(f"  ⚠️ {dist_warnings} distribution deviation warnings (acceptable if small).")

    # ── Export to training directory ────────────────────────────
    logger.info(f"\n  Exporting validated splits to: {TRAINING_DATA_DIR}")
    os.makedirs(TRAINING_DATA_DIR, exist_ok=True)

    export_files = {
        "real_toxicity_train.csv": train_df,
        "real_toxicity_val.csv": val_df,
        "real_toxicity_test.csv": test_df,
    }
    for filename, df in export_files.items():
        dest = os.path.join(TRAINING_DATA_DIR, filename)
        df.to_csv(dest, index=False)
        logger.info(f"    → {dest}")

    # Also export the unified full dataset
    full_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
    full_dest = os.path.join(TRAINING_DATA_DIR, "unified_dataset_full.csv")
    full_df.to_csv(full_dest, index=False)
    logger.info(f"    → {full_dest}")

    # Copy pos_weights if it exists
    weights_src = os.path.join(REPORTS_DIR, "pos_weights.json")
    if os.path.exists(weights_src):
        weights_dest = os.path.join(TRAINING_DATA_DIR, "pos_weights_real.json")
        shutil.copy2(weights_src, weights_dest)
        logger.info(f"    → {weights_dest}")

    # Copy EDA report
    eda_src = os.path.join(REPORTS_DIR, "EDA_REPORT.md")
    if os.path.exists(eda_src):
        eda_dest = os.path.join(TRAINING_DATA_DIR, "EDA_REPORT.md")
        shutil.copy2(eda_src, eda_dest)
        logger.info(f"    → {eda_dest}")

    # ── Final Summary ──────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ ALL VALIDATIONS PASSED — DATA READY FOR TRAINING")
    logger.info("=" * 60)
    logger.info(f"  Total samples:  {len(full_df)}")
    logger.info(f"  Train:          {len(train_df)}")
    logger.info(f"  Validation:     {len(val_df)}")
    logger.info(f"  Test:           {len(test_df)}")
    logger.info(f"  Labels:         {LABEL_COLUMNS}")
    logger.info(f"  Leakage:        0")
    logger.info(f"  Output dir:     {TRAINING_DATA_DIR}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

