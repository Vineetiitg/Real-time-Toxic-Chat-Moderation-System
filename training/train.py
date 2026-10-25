"""
SafeChat Training Pipeline — Core Trainer

Fine-tunes a transformer model for 6-tag multi-label toxicity classification.

Key design decisions:
  - LoRA (PEFT) for memory-efficient fine-tuning on 6GB VRAM
  - Weighted Focal Loss for extreme class imbalance (threat=1.3%)
  - Merged LoRA export so inference uses plain AutoModelForSequenceClassification
  - Per-class threshold optimization on validation set
  - No accuracy metric (misleading for multi-label imbalanced data)
"""

import copy
import json
import os
import time
import logging
from typing import Dict, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader
from torch.optim import AdamW
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)

from training.config import TrainingConfig, LABEL_COLUMNS, NUM_LABELS
from training.dataset import ToxicityDataset
from training.losses import WeightedFocalLoss
from training.evaluate import run_evaluation, optimize_thresholds, log_evaluation

logger = logging.getLogger("Trainer")


def set_seed(seed: int):
    """Set all random seeds for reproducibility."""
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_pos_weights(path: str, device: torch.device) -> torch.Tensor:
    """Load per-class positive weights from JSON (computed in data pipeline)."""
    with open(path, "r", encoding="utf-8") as f:
        weights_dict = json.load(f)
    weights = [weights_dict[col] for col in LABEL_COLUMNS]
    logger.info(f"Loaded pos_weights: {dict(zip(LABEL_COLUMNS, weights))}")
    return torch.tensor(weights, dtype=torch.float32).to(device)


def train(cfg: TrainingConfig) -> Dict:
    """
    Full training pipeline.

    Returns:
        Dict with best metrics, optimal thresholds, and output paths.
    """
    set_seed(cfg.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")
    if device.type == "cuda":
        try:
            total_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"GPU: {torch.cuda.get_device_name(0)} ({total_gb:.1f} GB)")
        except Exception as e:
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

    # ── 1. Load tokenizer ──────────────────────────────────────
    logger.info(f"Loading tokenizer: {cfg.model_name}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    except Exception as e:
        logger.warning(f"Could not load {cfg.model_name}: {e}. Falling back to bert-base-multilingual-cased")
        cfg.model_name = "bert-base-multilingual-cased"
        tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)

    # ── 2. Load datasets ───────────────────────────────────────
    logger.info("Loading datasets...")
    for p in [cfg.train_path, cfg.val_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Dataset not found: {p}\nRun data pipeline first: python -m data_pipeline.run_all")

    train_dataset = ToxicityDataset(cfg.train_path, tokenizer, cfg.max_length)
    val_dataset = ToxicityDataset(cfg.val_path, tokenizer, cfg.max_length)

    train_loader = DataLoader(train_dataset, batch_size=cfg.batch_size, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=cfg.batch_size, shuffle=False, num_workers=0, pin_memory=True)

    logger.info(f"Train: {len(train_dataset)} samples | Val: {len(val_dataset)} samples")

    # ── 3. Load model ──────────────────────────────────────────
    logger.info(f"Loading model: {cfg.model_name} (num_labels={NUM_LABELS})")
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.model_name,
        num_labels=NUM_LABELS,
        problem_type="multi_label_classification",
        ignore_mismatched_sizes=True,
    )

    # ── 4. Apply LoRA if enabled ───────────────────────────────
    if cfg.use_lora:
        try:
            from peft import LoraConfig, get_peft_model, TaskType

            lora_config = LoraConfig(
                task_type=TaskType.SEQ_CLS,
                r=cfg.lora_r,
                lora_alpha=cfg.lora_alpha,
                lora_dropout=cfg.lora_dropout,
                target_modules=cfg.lora_target_modules,
            )
            model = get_peft_model(model, lora_config)

            trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
            total = sum(p.numel() for p in model.parameters())
            logger.info(f"LoRA enabled: {trainable:,} trainable / {total:,} total params ({trainable/total*100:.1f}%)")
        except Exception as e:
            logger.warning(f"Could not initialize LoRA ({e}). Falling back to full fine-tuning.")
            cfg.use_lora = False
            trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
            logger.info(f"Full fine-tuning: {trainable:,} trainable params")
    else:
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info(f"Full fine-tuning: {trainable:,} trainable params")

    model.to(device)

    # ── 5. Loss function ───────────────────────────────────────
    pos_weight = None
    if cfg.use_pos_weights and os.path.exists(cfg.pos_weights_path):
        pos_weight = load_pos_weights(cfg.pos_weights_path, device)

    criterion = WeightedFocalLoss(pos_weight=pos_weight, gamma=cfg.focal_loss_gamma)

    # ── 6. Optimizer + Scheduler ───────────────────────────────
    optimizer = AdamW(model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay)
    total_steps = len(train_loader) * cfg.epochs
    warmup_steps = int(total_steps * cfg.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # ── 7. AMP Scaler ─────────────────────────────────────────
    use_amp = cfg.fp16 and device.type == "cuda"
    device_type = "cuda" if device.type == "cuda" else "cpu"
    try:
        scaler = torch.amp.GradScaler(device_type, enabled=use_amp)
    except Exception:
        scaler = torch.cuda.amp.GradScaler(enabled=use_amp)
    logger.info(f"FP16 AMP: {use_amp} | Epochs: {cfg.epochs} | LR: {cfg.learning_rate} | Batch: {cfg.batch_size}")
    logger.info(f"Total steps: {total_steps} | Warmup: {warmup_steps}")

    # ── 8. Training loop ───────────────────────────────────────
    best_macro_f1 = 0.0
    best_metrics = {}
    best_epoch = 0

    for epoch in range(1, cfg.epochs + 1):
        model.train()
        total_loss = 0.0
        epoch_start = time.time()

        for step, batch in enumerate(train_loader, 1):
            optimizer.zero_grad()

            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            with torch.amp.autocast(device_type, enabled=use_amp):
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                loss = criterion(outputs.logits, labels)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=cfg.max_grad_norm)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            total_loss += loss.item()

            # Progress logging
            if step % max(1, len(train_loader) // 5) == 0 or step == len(train_loader):
                avg_loss = total_loss / step
                lr_now = scheduler.get_last_lr()[0]
                logger.info(f"  Epoch {epoch}/{cfg.epochs} | Step {step}/{len(train_loader)} | "
                            f"Loss: {loss.item():.4f} (avg: {avg_loss:.4f}) | LR: {lr_now:.2e}")

        avg_train_loss = total_loss / len(train_loader)
        elapsed = time.time() - epoch_start

        # ── Validation ─────────────────────────────────────────
        val_metrics = run_evaluation(model, val_loader, device, threshold=cfg.default_threshold, use_amp=use_amp)
        log_evaluation(val_metrics, f"Epoch {epoch} Val")

        logger.info(f"  Epoch {epoch} done in {elapsed:.0f}s | Train Loss: {avg_train_loss:.4f}")

        # ── Save best ─────────────────────────────────────────
        if val_metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = val_metrics["macro_f1"]
            best_metrics = val_metrics
            best_epoch = epoch
            logger.info(f"  ★ New best Macro F1: {best_macro_f1:.4f} — saving checkpoint...")
            _save_checkpoint(model, tokenizer, cfg, val_metrics, epoch)
        else:
            logger.info(f"  No improvement (best: {best_macro_f1:.4f} at epoch {best_epoch})")

    # ── 9. Threshold optimization on best model ────────────────
    optimal_thresholds = {}
    if cfg.optimize_thresholds and "_raw_probs" in best_metrics:
        logger.info("\nOptimizing per-class thresholds on validation set...")
        optimal_thresholds = optimize_thresholds(best_metrics["_raw_probs"], best_metrics["_raw_targets"])

        # Re-evaluate with optimal thresholds
        logger.info("\nRe-evaluating with optimized thresholds:")
        optimized_metrics = run_evaluation(model, val_loader, device, per_class_thresholds=optimal_thresholds, use_amp=use_amp)
        log_evaluation(optimized_metrics, "Val (optimized thresholds)")

        # Save thresholds
        thresholds_path = os.path.join(cfg.output_dir, "optimal_thresholds.json")
        with open(thresholds_path, "w") as f:
            json.dump(optimal_thresholds, f, indent=2)
        logger.info(f"Saved optimal thresholds to: {thresholds_path}")

    # ── 10. Test set evaluation (if available) ─────────────────
    if os.path.exists(cfg.test_path):
        logger.info("\nEvaluating on held-out test set...")
        test_dataset = ToxicityDataset(cfg.test_path, tokenizer, cfg.max_length)
        test_loader = DataLoader(test_dataset, batch_size=cfg.batch_size, shuffle=False, num_workers=0)

        test_metrics = run_evaluation(
            model, test_loader, device,
            per_class_thresholds=optimal_thresholds if optimal_thresholds else None,
            use_amp=use_amp,
        )
        log_evaluation(test_metrics, "Test (final)")

        # Save test report
        test_report = {k: v for k, v in test_metrics.items() if not k.startswith("_")}
        test_report["thresholds"] = optimal_thresholds
        report_path = os.path.join(cfg.output_dir, "test_results.json")
        with open(report_path, "w") as f:
            json.dump(test_report, f, indent=2)
        logger.info(f"Saved test results to: {report_path}")

    logger.info(f"\n{'═' * 55}")
    logger.info(f"  TRAINING COMPLETE")
    logger.info(f"  Best Macro F1: {best_macro_f1:.4f} (epoch {best_epoch})")
    logger.info(f"  Model saved:   {cfg.output_dir}")
    logger.info(f"{'═' * 55}")

    return {
        "best_macro_f1": best_macro_f1,
        "best_epoch": best_epoch,
        "optimal_thresholds": optimal_thresholds,
        "output_dir": cfg.output_dir,
    }


def _save_checkpoint(model, tokenizer, cfg: TrainingConfig, metrics: Dict, epoch: int):
    """Save model checkpoint compatible with inference code.

    IMPORTANT: When LoRA merge is enabled, we deep-copy the model first so the
    original PEFT model remains intact for continued training. merge_and_unload()
    is destructive — it permanently removes LoRA layers from the model it's called on.
    """
    os.makedirs(cfg.output_dir, exist_ok=True)

    if cfg.use_lora and cfg.merge_lora_before_save:
        # Deep-copy so the original PEFT model survives for continued training
        logger.info("  Merging LoRA weights into base model (on a copy)...")
        model_copy = copy.deepcopy(model).cpu()
        merged_model = model_copy.merge_and_unload()
        merged_model.save_pretrained(cfg.output_dir)
        del model_copy, merged_model
        torch.cuda.empty_cache()
    else:
        model.save_pretrained(cfg.output_dir)

    tokenizer.save_pretrained(cfg.output_dir)

    # Save metadata for the inference code
    metadata = {
        "base_model": cfg.model_name,
        "num_labels": NUM_LABELS,
        "labels": LABEL_COLUMNS,
        "max_length": cfg.max_length,
        "epochs_trained": epoch,
        "best_macro_f1": metrics.get("macro_f1", 0),
        "best_roc_auc": metrics.get("roc_auc", 0),
        "lora_config": {
            "enabled": cfg.use_lora,
            "merged": cfg.merge_lora_before_save,
            "r": cfg.lora_r,
            "alpha": cfg.lora_alpha,
        } if cfg.use_lora else None,
    }
    with open(os.path.join(cfg.output_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"  Checkpoint saved to: {cfg.output_dir}")
