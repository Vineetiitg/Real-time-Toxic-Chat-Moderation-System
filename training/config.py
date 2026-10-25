"""
SafeChat Training Pipeline — Configuration

All hyperparameters and paths in one place.
Override via CLI args in run_training.py or edit defaults here.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

# ── Paths ───────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLITS_DIR = os.path.join(PROJECT_ROOT, "data_pipeline", "splits")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "data_pipeline", "reports")

# Where the ml-service inference code expects the checkpoint
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "ml-service", "checkpoints", "hingbert-toxicity-finetuned")

# ── Schema ──────────────────────────────────────────────────────
LABEL_COLUMNS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
NUM_LABELS = len(LABEL_COLUMNS)


@dataclass
class TrainingConfig:
    """All training hyperparameters."""

    # ── Model ───────────────────────────────────────────────
    # Default: L3Cube Hing-RoBERTa (best for Hindi/Hinglish/English code-mixed)
    # Alternatives: "google/muril-base-cased", "microsoft/deberta-v3-base",
    #               "xlm-roberta-base", "bert-base-multilingual-cased"
    model_name: str = "l3cube-pune/hing-roberta-mixed"

    # ── LoRA (Parameter-Efficient Fine-Tuning) ──────────────
    use_lora: bool = True
    lora_r: int = 32                    # Rank (higher = more capacity, more VRAM)
    lora_alpha: int = 64                # Scaling factor
    lora_dropout: float = 0.1
    lora_target_modules: List[str] = field(
        default_factory=lambda: ["query", "key", "value", "dense"]
    )
    merge_lora_before_save: bool = True  # Merge into base model for simple inference

    # ── Data ────────────────────────────────────────────────
    max_length: int = 256               # Token length (covers 95th percentile)
    train_path: str = ""                # Auto-filled from SPLITS_DIR
    val_path: str = ""
    test_path: str = ""
    pos_weights_path: str = ""          # Auto-filled from REPORTS_DIR

    # ── Training ────────────────────────────────────────────
    epochs: int = 5
    batch_size: int = 16
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0
    fp16: bool = True                   # Auto Mixed Precision

    # ── Loss ────────────────────────────────────────────────
    focal_loss_gamma: float = 2.0       # Focal loss focusing parameter
    use_pos_weights: bool = True        # Use class-imbalance weights

    # ── Evaluation ──────────────────────────────────────────
    eval_every_n_steps: int = 0         # 0 = eval at end of each epoch
    default_threshold: float = 0.5      # Starting threshold for binary predictions
    optimize_thresholds: bool = True    # Find per-class optimal thresholds on val set

    # ── Output ──────────────────────────────────────────────
    output_dir: str = DEFAULT_OUTPUT_DIR
    save_best_only: bool = True         # Only keep the best checkpoint by val Macro-F1

    # ── Reproducibility ─────────────────────────────────────
    seed: int = 42

    def __post_init__(self):
        """Fill in auto paths if not explicitly provided."""
        if not self.train_path:
            self.train_path = os.path.join(SPLITS_DIR, "train.csv")
        if not self.val_path:
            self.val_path = os.path.join(SPLITS_DIR, "val.csv")
        if not self.test_path:
            self.test_path = os.path.join(SPLITS_DIR, "test.csv")
        if not self.pos_weights_path:
            self.pos_weights_path = os.path.join(REPORTS_DIR, "pos_weights.json")

