"""
SafeChat Training Pipeline — Loss Functions

Weighted Multi-Label Focal Loss for extreme class imbalance.
Combines pos_weight (upweights rare positives) with focal modulation
(downweights easy negatives that dominate gradients).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class WeightedFocalLoss(nn.Module):
    """
    Focal Loss with per-class positive weights for multi-label classification.

    Standard BCE treats all samples equally, which causes gradient collapse
    on rare tags like 'threat' (1.3% positive rate). This loss fixes it:

      1. pos_weight: Multiplies positive-class gradients by weight
         (e.g., 25x for threat) so rare classes aren't ignored.

      2. Focal modulation: (1 - p_t)^gamma downweights easy negatives
         that the model is already confident about, focusing training
         on hard/ambiguous samples.

    Args:
        pos_weight: Tensor of shape (num_labels,) with per-class weights.
        gamma:      Focal loss focusing parameter. 0 = standard BCE.
                    2.0 is the standard value from Lin et al. (2017).
        reduction:  'mean' (default) or 'none'.
    """

    def __init__(
        self,
        pos_weight: torch.Tensor = None,
        gamma: float = 2.0,
        reduction: str = "mean",
    ):
        super().__init__()
        self.pos_weight = pos_weight
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Standard weighted BCE (per-element)
        bce_loss = F.binary_cross_entropy_with_logits(
            logits, targets, pos_weight=self.pos_weight, reduction="none"
        )

        # Focal modulation
        if self.gamma > 0:
            # p_t = probability of correct class
            pt = torch.exp(-bce_loss)
            focal_weight = (1.0 - pt) ** self.gamma
            loss = focal_weight * bce_loss
        else:
            loss = bce_loss

        if self.reduction == "mean":
            return loss.mean()
        return loss

