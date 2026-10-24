"""
SafeChat Data Pipeline — Configuration & Constants

Central configuration for the entire data pipeline.
All paths, schema definitions, and tunable parameters live here.
"""

import os

# ── Schema ──────────────────────────────────────────────────────────
LABEL_COLUMNS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
NUM_LABELS = len(LABEL_COLUMNS)
TEXT_COLUMN = "text"
SOURCE_COLUMN = "source_language"

# ── Paths ───────────────────────────────────────────────────────────
PIPELINE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PIPELINE_ROOT)

# Where raw downloaded CSVs land (never modified after download)
RAW_DATA_DIR = os.path.join(PIPELINE_ROOT, "raw")

# Where cleaned + unified data goes
PROCESSED_DATA_DIR = os.path.join(PIPELINE_ROOT, "processed")

# Final splits ready for training
SPLITS_DIR = os.path.join(PIPELINE_ROOT, "splits")

# Reports and stats
REPORTS_DIR = os.path.join(PIPELINE_ROOT, "reports")

# ── HuggingFace Dataset URLs ───────────────────────────────────────
JIGSAW_HF_URL = "hf://datasets/thesofakillers/jigsaw-toxic-comment-classification-challenge/train.csv"
PRISM_HF_URL = "hf://datasets/pankajbiswas6/prism-hinglish-hate-speech/data/train.csv"
HASOC_HF_URL = "hf://datasets/nikitadesai/hasoc/traindata-basic.csv"

# ── Sampling / Balancing ───────────────────────────────────────────
MAX_JIGSAW_SAMPLES = 15000      # Cap English samples to avoid drowning Indic data
POS_WEIGHT_CAP = 25.0           # Max pos_weight to prevent gradient explosion
POS_WEIGHT_FLOOR = 1.0          # Min pos_weight

# ── Text Preprocessing ────────────────────────────────────────────
MAX_TEXT_LENGTH_CHARS = 2000     # Drop texts longer than this (likely scraped noise)
MIN_TEXT_LENGTH_CHARS = 3        # Drop texts shorter than this

# ── Split Ratios ──────────────────────────────────────────────────
TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10
SPLIT_SEED = 42

