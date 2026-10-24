#!/usr/bin/env python3
"""
SafeChat Data Pipeline — Step 3: EDA & Validation

Performs comprehensive Exploratory Data Analysis on the unified dataset:
  1. Class distribution analysis with pos_weight calculation
  2. Text length statistics (char & word level)
  3. Script/language breakdown (Latin vs Devanagari vs other)
  4. Multi-label co-occurrence matrix
  5. Data quality checks (empty labels, all-zero rows ratio)
  6. Exports Markdown report + pos_weights.json

Usage:
    python -m data_pipeline.step3_eda
"""

import os
import sys
import json
import time
import logging
from typing import Dict

import numpy as np
import pandas as pd

from data_pipeline.config import (
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
    LABEL_COLUMNS,
    TEXT_COLUMN,
    SOURCE_COLUMN,
    POS_WEIGHT_CAP,
    POS_WEIGHT_FLOOR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Step3-EDA")


def compute_pos_weights(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate BCEWithLogitsLoss pos_weight for each label.
    pos_weight = num_negatives / num_positives (capped to prevent explosion).
    """
    total = len(df)
    weights = {}
    for col in LABEL_COLUMNS:
        pos = int(df[col].sum())
        neg = total - pos
        raw_weight = neg / max(1, pos)
        capped = min(POS_WEIGHT_CAP, max(POS_WEIGHT_FLOOR, round(raw_weight, 2)))
        weights[col] = capped
    return weights


def compute_cooccurrence(df: pd.DataFrame) -> pd.DataFrame:
    """Compute label co-occurrence matrix (how often labels appear together)."""
    labels = df[LABEL_COLUMNS].values
    cooccurrence = np.zeros((len(LABEL_COLUMNS), len(LABEL_COLUMNS)), dtype=int)
    for i in range(len(LABEL_COLUMNS)):
        for j in range(len(LABEL_COLUMNS)):
            cooccurrence[i][j] = int(((labels[:, i] == 1) & (labels[:, j] == 1)).sum())
    return pd.DataFrame(cooccurrence, index=LABEL_COLUMNS, columns=LABEL_COLUMNS)


def run_eda(df: pd.DataFrame) -> Dict:
    """Run full EDA and return all statistics as a dictionary."""
    logger.info("=" * 60)
    logger.info("  SafeChat Data Pipeline — Step 3: EDA & Validation")
    logger.info("=" * 60)

    total = len(df)
    stats = {"total_samples": total, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    # ── 1. Source distribution ──────────────────────────────────
    logger.info("\n1. Source Language Distribution:")
    source_counts = df[SOURCE_COLUMN].value_counts().to_dict()
    stats["source_distribution"] = source_counts
    for src, count in source_counts.items():
        pct = (count / total) * 100
        logger.info(f"   {src:<30}: {count:>6} ({pct:>5.1f}%)")

    # ── 2. Class distribution & pos_weights ─────────────────────
    logger.info("\n2. Class Distribution & pos_weight:")
    logger.info(f"   {'Tag':<15} | {'Pos':>7} | {'Neg':>7} | {'Rate':>7} | {'pos_weight':>10}")
    logger.info("   " + "-" * 58)

    pos_weights = compute_pos_weights(df)
    class_stats = []
    for col in LABEL_COLUMNS:
        pos = int(df[col].sum())
        neg = total - pos
        rate = (pos / total) * 100
        w = pos_weights[col]
        logger.info(f"   {col:<15} | {pos:>7} | {neg:>7} | {rate:>6.2f}% | {w:>10.2f}")
        class_stats.append({"tag": col, "positives": pos, "negatives": neg, "rate_pct": round(rate, 2), "pos_weight": w})

    stats["class_stats"] = class_stats
    stats["pos_weights"] = pos_weights

    # ── 3. Text length stats ───────────────────────────────────
    logger.info("\n3. Text Length Statistics:")
    char_lens = df[TEXT_COLUMN].str.len()
    word_lens = df[TEXT_COLUMN].str.split().str.len()

    length_stats = {
        "char_mean": round(float(char_lens.mean()), 1),
        "char_median": round(float(char_lens.median()), 1),
        "char_p95": round(float(np.percentile(char_lens, 95)), 1),
        "char_max": int(char_lens.max()),
        "word_mean": round(float(word_lens.mean()), 1),
        "word_median": round(float(word_lens.median()), 1),
        "word_p95": round(float(np.percentile(word_lens, 95)), 1),
        "word_max": int(word_lens.max()),
    }
    stats["length_stats"] = length_stats
    logger.info(f"   Characters: mean={length_stats['char_mean']}, median={length_stats['char_median']}, "
                f"p95={length_stats['char_p95']}, max={length_stats['char_max']}")
    logger.info(f"   Words:      mean={length_stats['word_mean']}, median={length_stats['word_median']}, "
                f"p95={length_stats['word_p95']}, max={length_stats['word_max']}")

    # ── 4. Script breakdown ────────────────────────────────────
    logger.info("\n4. Script Breakdown:")
    ascii_count = 0
    devanagari_count = 0
    total_chars = 0
    for text in df[TEXT_COLUMN]:
        for ch in str(text):
            total_chars += 1
            if ord(ch) < 128:
                ascii_count += 1
            elif 0x0900 <= ord(ch) <= 0x097F:
                devanagari_count += 1

    latin_pct = round((ascii_count / max(1, total_chars)) * 100, 1)
    dev_pct = round((devanagari_count / max(1, total_chars)) * 100, 1)
    other_pct = round(100 - latin_pct - dev_pct, 1)

    stats["script_breakdown"] = {"latin_ascii_pct": latin_pct, "devanagari_pct": dev_pct, "other_pct": other_pct}
    logger.info(f"   Latin ASCII:  {latin_pct}%")
    logger.info(f"   Devanagari:   {dev_pct}%")
    logger.info(f"   Other:        {other_pct}%")

    # ── 5. Label co-occurrence ─────────────────────────────────
    logger.info("\n5. Label Co-occurrence Matrix:")
    cooc = compute_cooccurrence(df)
    stats["cooccurrence"] = cooc.to_dict()
    logger.info(f"\n{cooc.to_string()}")

    # ── 6. Data quality checks ─────────────────────────────────
    logger.info("\n6. Data Quality Checks:")
    all_zero = (df[LABEL_COLUMNS].sum(axis=1) == 0).sum()
    all_zero_pct = round((all_zero / total) * 100, 1)
    stats["safe_samples"] = int(all_zero)
    stats["safe_pct"] = all_zero_pct
    logger.info(f"   Safe samples (all labels=0): {all_zero} ({all_zero_pct}%)")

    any_toxic = total - all_zero
    logger.info(f"   Toxic samples (any label=1): {any_toxic} ({round((any_toxic/total)*100, 1)}%)")

    empty_text = (df[TEXT_COLUMN].str.strip() == "").sum()
    logger.info(f"   Empty text rows: {empty_text}")
    if empty_text > 0:
        logger.warning(f"   ⚠️ {empty_text} empty text rows found — should be 0 after Step 2!")

    logger.info("=" * 60)
    return stats


def generate_markdown_report(stats: Dict, output_path: str):
    """Generate a human-readable Markdown EDA report."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# SafeChat Data Pipeline — EDA Report\n\n")
        f.write(f"**Total Samples:** `{stats['total_samples']}`  \n")
        f.write(f"**Generated:** `{stats['generated_at']}`\n\n")
        f.write("---\n\n")

        # Source distribution
        f.write("## 1. Source Distribution\n\n")
        f.write("| Source | Count | Percentage |\n|---|---|---|\n")
        for src, count in stats["source_distribution"].items():
            pct = round((count / stats["total_samples"]) * 100, 1)
            f.write(f"| `{src}` | {count} | {pct}% |\n")
        f.write("\n")

        # Class stats
        f.write("## 2. Class Distribution & pos_weight\n\n")
        f.write("| Tag | Positives | Negatives | Rate | pos_weight |\n|---|---|---|---|---|\n")
        for cs in stats["class_stats"]:
            f.write(f"| **{cs['tag']}** | {cs['positives']} | {cs['negatives']} | {cs['rate_pct']}% | `{cs['pos_weight']}` |\n")
        f.write("\n")

        # Length stats
        ls = stats["length_stats"]
        f.write("## 3. Text Length Statistics\n\n")
        f.write(f"- **Characters:** mean={ls['char_mean']}, median={ls['char_median']}, p95={ls['char_p95']}, max={ls['char_max']}\n")
        f.write(f"- **Words:** mean={ls['word_mean']}, median={ls['word_median']}, p95={ls['word_p95']}, max={ls['word_max']}\n\n")

        # Script breakdown
        sb = stats["script_breakdown"]
        f.write("## 4. Script Breakdown\n\n")
        f.write(f"- Latin ASCII: `{sb['latin_ascii_pct']}%`\n")
        f.write(f"- Devanagari: `{sb['devanagari_pct']}%`\n")
        f.write(f"- Other: `{sb['other_pct']}%`\n\n")

        # Quality
        f.write("## 5. Data Quality\n\n")
        f.write(f"- Safe samples (all labels=0): `{stats['safe_samples']}` ({stats['safe_pct']}%)\n")
        f.write(f"- Toxic samples (any label=1): `{stats['total_samples'] - stats['safe_samples']}`\n\n")

    logger.info(f"📄 Markdown report saved to: {output_path}")


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    input_path = os.path.join(PROCESSED_DATA_DIR, "unified_clean.csv")
    if not os.path.exists(input_path):
        logger.error(f"Unified dataset not found at {input_path}. Run step2_unify first!")
        sys.exit(1)

    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} rows from {input_path}")

    stats = run_eda(df)

    # Save pos_weights JSON
    weights_path = os.path.join(REPORTS_DIR, "pos_weights.json")
    with open(weights_path, "w", encoding="utf-8") as f:
        json.dump(stats["pos_weights"], f, indent=2)
    logger.info(f"📊 pos_weights saved to: {weights_path}")

    # Save full stats JSON
    stats_path = os.path.join(REPORTS_DIR, "eda_stats.json")
    # Remove non-serializable items
    serializable_stats = {k: v for k, v in stats.items() if k != "cooccurrence"}
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(serializable_stats, f, indent=2)
    logger.info(f"📊 Full stats saved to: {stats_path}")

    # Save markdown report
    report_path = os.path.join(REPORTS_DIR, "EDA_REPORT.md")
    generate_markdown_report(stats, report_path)


if __name__ == "__main__":
    main()

