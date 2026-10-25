"""
SafeChat Training Pipeline — Evaluation & Threshold Optimization

Computes proper multi-label metrics (never accuracy!) and finds
per-class optimal thresholds via Precision-Recall curves.
"""

import json
import os
import logging
from typing import Dict, List, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    precision_recall_curve,
    classification_report,
)

from training.config import LABEL_COLUMNS, NUM_LABELS

logger = logging.getLogger("Evaluator")


def run_evaluation(
    model,
    dataloader: DataLoader,
    device: torch.device,
    threshold: float = 0.5,
    per_class_thresholds: Dict[str, float] = None,
    use_amp: bool = True,
) -> Dict:
    """
    Full evaluation pass over a dataloader.

    Returns:
        Dict with macro_f1, micro_f1, per-class metrics, roc_auc, etc.
    """
    model.eval()
    all_logits = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"]

            with torch.amp.autocast("cuda", enabled=use_amp and device.type == "cuda"):
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)

            all_logits.append(outputs.logits.cpu())
            all_labels.append(labels)

    all_logits = torch.cat(all_logits, dim=0)
    all_labels = torch.cat(all_labels, dim=0)
    all_probs = torch.sigmoid(all_logits).numpy()
    all_targets = all_labels.numpy()

    # Apply thresholds (per-class if provided, else uniform)
    if per_class_thresholds:
        thresholds_array = np.array([per_class_thresholds.get(col, threshold) for col in LABEL_COLUMNS])
        all_preds = (all_probs >= thresholds_array).astype(int)
    else:
        all_preds = (all_probs >= threshold).astype(int)

    # Macro / Micro F1
    macro_f1 = float(f1_score(all_targets, all_preds, average="macro", zero_division=0))
    micro_f1 = float(f1_score(all_targets, all_preds, average="micro", zero_division=0))

    # Per-class metrics
    per_class = {}
    for i, col in enumerate(LABEL_COLUMNS):
        col_preds = all_preds[:, i]
        col_targets = all_targets[:, i]
        col_probs = all_probs[:, i]

        f1 = float(f1_score(col_targets, col_preds, zero_division=0))
        prec = float(precision_score(col_targets, col_preds, zero_division=0))
        rec = float(recall_score(col_targets, col_preds, zero_division=0))

        try:
            auc = float(roc_auc_score(col_targets, col_probs))
        except ValueError:
            auc = 0.5  # Only one class present

        per_class[col] = {"f1": round(f1, 4), "precision": round(prec, 4), "recall": round(rec, 4), "auc": round(auc, 4)}

    # Overall ROC-AUC
    try:
        overall_auc = float(roc_auc_score(all_targets, all_probs, average="macro"))
    except ValueError:
        overall_auc = 0.5

    return {
        "macro_f1": round(macro_f1, 4),
        "micro_f1": round(micro_f1, 4),
        "roc_auc": round(overall_auc, 4),
        "per_class": per_class,
        "num_samples": len(all_targets),
        "_raw_probs": all_probs,    # For threshold optimization
        "_raw_targets": all_targets,
    }


def optimize_thresholds(
    all_probs: np.ndarray,
    all_targets: np.ndarray,
) -> Dict[str, float]:
    """
    Find the optimal classification threshold per class using
    Precision-Recall curves — maximizing F1 at each point.

    This is CRITICAL for imbalanced data where 0.5 is rarely optimal.
    For rare classes like 'threat' (1.3%), the optimal threshold is often 0.3-0.4.
    """
    optimal_thresholds = {}

    for i, col in enumerate(LABEL_COLUMNS):
        col_probs = all_probs[:, i]
        col_targets = all_targets[:, i]

        if col_targets.sum() == 0:
            # No positive samples — keep default
            optimal_thresholds[col] = 0.5
            continue

        precisions, recalls, thresholds = precision_recall_curve(col_targets, col_probs)

        # Compute F1 at each threshold
        f1_scores = []
        for p, r in zip(precisions[:-1], recalls[:-1]):
            if p + r > 0:
                f1_scores.append(2 * p * r / (p + r))
            else:
                f1_scores.append(0.0)

        if not f1_scores:
            optimal_thresholds[col] = 0.5
            continue

        best_idx = int(np.argmax(f1_scores))
        best_threshold = float(thresholds[best_idx])
        best_f1 = f1_scores[best_idx]

        # Clamp to reasonable range
        best_threshold = max(0.15, min(0.85, best_threshold))
        optimal_thresholds[col] = round(best_threshold, 4)

        logger.info(f"  {col:<15}: threshold={best_threshold:.4f}  (F1={best_f1:.4f})")

    return optimal_thresholds


def log_evaluation(metrics: Dict, split_name: str = "Val"):
    """Pretty-print evaluation metrics."""
    logger.info(f"\n{'─' * 55}")
    logger.info(f"  {split_name} Results — Macro F1: {metrics['macro_f1']:.4f}  |  Micro F1: {metrics['micro_f1']:.4f}  |  AUC: {metrics['roc_auc']:.4f}")
    logger.info(f"{'─' * 55}")
    logger.info(f"  {'Tag':<15} | {'F1':>6} | {'Prec':>6} | {'Rec':>6} | {'AUC':>6}")
    logger.info(f"  {'─' * 49}")
    for col in LABEL_COLUMNS:
        m = metrics["per_class"][col]
        logger.info(f"  {col:<15} | {m['f1']:>6.4f} | {m['precision']:>6.4f} | {m['recall']:>6.4f} | {m['auc']:>6.4f}")
    logger.info(f"{'─' * 55}")

