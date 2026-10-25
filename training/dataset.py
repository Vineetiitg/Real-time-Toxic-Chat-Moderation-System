"""
SafeChat Training Pipeline — Dataset

PyTorch Dataset for multi-label toxicity classification.
Handles tokenization with proper padding and truncation.
"""

from typing import List

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from training.config import LABEL_COLUMNS


class ToxicityDataset(Dataset):
    """
    Multi-label toxicity dataset for fine-tuning.

    Each sample returns:
      - input_ids:      (max_length,) tensor of token IDs
      - attention_mask:  (max_length,) tensor of 1s/0s
      - labels:          (num_labels,) float tensor of 0.0/1.0
    """

    def __init__(self, csv_path: str, tokenizer, max_length: int = 256):
        df = pd.read_csv(csv_path)
        df["text"] = df["text"].astype(str).fillna("")
        self.texts = df["text"].tolist()
        self.labels = df[LABEL_COLUMNS].values.astype(np.float32)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> dict:
        text = self.texts[idx]
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.float32),
        }

