#!/usr/bin/env python3
"""
SafeChat Training Pipeline — Entry Point

Fine-tunes a multi-label toxicity classifier on real multilingual data.

Prerequisites:
    Run the data pipeline first:
        python -m data_pipeline.run_all

Usage:
    # Default config (Hing-RoBERTa, LoRA, 5 epochs)
    python -m training.run_training

    # Custom model and epochs
    python -m training.run_training --model google/muril-base-cased --epochs 3

    # Full fine-tuning (no LoRA, needs more VRAM)
    python -m training.run_training --no-lora --batch-size 8

    # Quick test run
    python -m training.run_training --epochs 1 --batch-size 8
"""

import argparse
import logging
import sys

from training.config import TrainingConfig
from training.train import train

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("RunTraining")


def main():
    parser = argparse.ArgumentParser(description="SafeChat Toxicity Classifier Training")

    # Model
    parser.add_argument("--model", type=str, default="l3cube-pune/hing-roberta-mixed",
                        help="HuggingFace model name to fine-tune")
    parser.add_argument("--no-lora", action="store_true",
                        help="Disable LoRA (full fine-tuning, needs more VRAM)")
    parser.add_argument("--lora-r", type=int, default=32,
                        help="LoRA rank")

    # Training
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=256,
                        help="Max token sequence length")

    # Loss
    parser.add_argument("--gamma", type=float, default=2.0,
                        help="Focal loss gamma (0 = standard BCE)")
    parser.add_argument("--no-pos-weights", action="store_true",
                        help="Disable class-imbalance pos_weights")

    # Output
    parser.add_argument("--output-dir", type=str, default="",
                        help="Model output directory (default: ml-service/checkpoints/)")
    parser.add_argument("--no-threshold-opt", action="store_true",
                        help="Skip per-class threshold optimization")

    args = parser.parse_args()

    # Build config
    cfg = TrainingConfig(
        model_name=args.model,
        use_lora=not args.no_lora,
        lora_r=args.lora_r,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_length=args.max_length,
        focal_loss_gamma=args.gamma,
        use_pos_weights=not args.no_pos_weights,
        optimize_thresholds=not args.no_threshold_opt,
    )
    if args.output_dir:
        cfg.output_dir = args.output_dir

    logger.info("=" * 60)
    logger.info("  SafeChat — Toxicity Classifier Training Pipeline")
    logger.info("=" * 60)
    logger.info(f"  Model:       {cfg.model_name}")
    logger.info(f"  LoRA:        {'r=' + str(cfg.lora_r) if cfg.use_lora else 'disabled (full FT)'}")
    logger.info(f"  Epochs:      {cfg.epochs}")
    logger.info(f"  Batch size:  {cfg.batch_size}")
    logger.info(f"  LR:          {cfg.learning_rate}")
    logger.info(f"  Max length:  {cfg.max_length}")
    logger.info(f"  Focal gamma: {cfg.focal_loss_gamma}")
    logger.info(f"  Output:      {cfg.output_dir}")
    logger.info("=" * 60)

    results = train(cfg)

    logger.info("\n🎉 Training complete!")
    logger.info(f"   Best Macro F1: {results['best_macro_f1']:.4f}")
    logger.info(f"   Checkpoint:    {results['output_dir']}")
    if results.get("optimal_thresholds"):
        logger.info(f"   Thresholds:    {results['optimal_thresholds']}")


if __name__ == "__main__":
    main()

