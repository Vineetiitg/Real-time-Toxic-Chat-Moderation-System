
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from ensembleTraining import *MetaNet

# definition with 22 inputs
meta = MetaNet().to(device)
opt_m = torch.optim.Adam(meta.parameters(), lr=1e-3)


print("Training new 22-input Meta-Learner...")

# After training: 
torch.save(meta.state_dict(), "models/ensemble/meta_learner/meta_learner.pt")
print("✅ New Meta-Learner Saved.")