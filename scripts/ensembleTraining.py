import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from peft import LoraConfig, get_peft_model, TaskType
from sklearn.model_selection import KFold, train_test_split
from sklearn.metrics import classification_report, f1_score
from tqdm import tqdm
import gc
import os

# --- NVIDIA 30-SERIES STABILITY FLAGS ---
cudnn.benchmark = False
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
scaler = torch.amp.GradScaler('cuda')

# 1. DIRECTORY SETUP
dirs = [
    "models/ensemble/xlmr",
    "models/ensemble/muril",
    "models/ensemble/bilstm",
    "models/ensemble/meta_learner"
]
for d in dirs: os.makedirs(d, exist_ok=True)


# 2. MODEL DEFINITIONS
class TransformerMTL(nn.Module):
    def __init__(self, model_name):
        super().__init__()
        self.backbone = AutoModel.from_pretrained(model_name)
        target_modules = ["query", "value"] if "roberta" in model_name else ["query", "key", "value"]
        peft_config = LoraConfig(task_type=TaskType.FEATURE_EXTRACTION, r=16, lora_alpha=32,
                                 target_modules=target_modules)
        self.backbone = get_peft_model(self.backbone, peft_config)
        dim = self.backbone.config.hidden_size
        self.safety_head = nn.Linear(dim, 1)
        self.cat_head = nn.Linear(dim, 6)
        self.sev_head = nn.Linear(dim, 4)

    def forward(self, ids, mask):
        out = self.backbone(ids, mask)
        pooler = out.last_hidden_state[:, 0, :]
        return self.safety_head(pooler), self.cat_head(pooler), self.sev_head(pooler)


class BiLSTMMTL(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, 128)
        self.lstm = nn.LSTM(128, 64, bidirectional=True, batch_first=True)
        self.safety_head = nn.Linear(128, 1)
        self.cat_head = nn.Linear(128, 6)
        self.sev_head = nn.Linear(128, 4)

    def forward(self, ids):
        x = self.embed(ids).float()
        self.lstm.float()
        with torch.amp.autocast('cuda', enabled=False):
            x, _ = self.lstm(x)
            x_pool = x.mean(dim=1)
        return self.safety_head(x_pool), self.cat_head(x_pool), self.sev_head(x_pool)


class MetaNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(33, 64), nn.ReLU(), nn.Linear(64, 11))

    def forward(self, x):
        out = self.net(x)
        return out[:, 0:1], out[:, 1:7], out[:, 7:11]


class ToxicityDataset(Dataset):
    def __init__(self, texts, s, c, v, tok):
        self.texts = texts;
        self.s = s;
        self.c = c;
        self.v = v;
        self.tok = tok

    def __len__(self): return len(self.texts)

    def __getitem__(self, i):
        enc = self.tok(str(self.texts[i]), max_length=128, padding='max_length', truncation=True, return_tensors='pt')
        return {'input_ids': enc['input_ids'].flatten(), 'attention_mask': enc['attention_mask'].flatten(),
                'safety': torch.tensor(self.s[i], dtype=torch.float),
                'categories': torch.tensor(self.c[i], dtype=torch.float),
                'severity': torch.tensor(self.v[i], dtype=torch.long)}


# 3. TRAINING FUNCTION
def run_train(model, loader):
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=5e-5)
    crit_bce = nn.BCEWithLogitsLoss()
    crit_ce = nn.CrossEntropyLoss()
    model.train()
    for batch in tqdm(loader, desc="Training"):
        opt.zero_grad()
        with torch.amp.autocast('cuda'):
            if isinstance(model, BiLSTMMTL):
                s, c, v = model(batch['input_ids'].to(device))
            else:
                s, c, v = model(batch['input_ids'].to(device), batch['attention_mask'].to(device))
            loss = crit_bce(s.squeeze(), batch['safety'].to(device)) + crit_bce(c, batch['categories'].to(
                device)) + crit_ce(v, batch['severity'].to(device))
        scaler.scale(loss).backward();
        scaler.step(opt);
        scaler.update()


# 4. MAIN EXECUTION (K-FOLD + SAVING)
df = pd.read_csv(r"C:\Users\Vineet\Downloads\sampled_final_LoRa_data.csv")
df_stack, df_test = train_test_split(df, test_size=0.2, random_state=42)
df_stack = df_stack.reset_index(drop=True)

tok_xlmr = AutoTokenizer.from_pretrained("xlm-roberta-base")
tok_muril = AutoTokenizer.from_pretrained("google/muril-base-cased")

# --- STEP 1: GENERATE OOF FEATURES FOR META-LEARNER ---
kf = KFold(n_splits=3, shuffle=True, random_state=42)
oof_feats = np.zeros((len(df_stack), 33))

for fold, (t_idx, v_idx) in enumerate(kf.split(df_stack)):
    print(f"\n--- FOLD {fold + 1} ---")
    t_df, v_df = df_stack.iloc[t_idx], df_stack.iloc[v_idx]

    configs = [("xlmr", TransformerMTL, tok_xlmr, "xlm-roberta-base"),
               ("muril", TransformerMTL, tok_muril, "google/muril-base-cased"),
               ("bilstm", BiLSTMMTL, tok_xlmr, len(tok_xlmr))]

    for i, (name, m_cls, tok, path) in enumerate(configs):
        m = m_cls(path)
        t_ldr = DataLoader(ToxicityDataset(t_df.Sentence.values, t_df.binary_toxicity.values, t_df[
            ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']].values,
                                           t_df['Toxicity Level'].values, tok), batch_size=8, shuffle=True)
        v_ldr = DataLoader(ToxicityDataset(v_df.Sentence.values, v_df.binary_toxicity.values, v_df[
            ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']].values,
                                           v_df['Toxicity Level'].values, tok), batch_size=8)

        run_train(m, t_ldr)

        # Get OOF Predictions
        m.eval()
        with torch.no_grad():
            preds = []
            for b in v_ldr:
                if isinstance(m, BiLSTMMTL):
                    s, c, v = m(b['input_ids'].to(device))
                else:
                    s, c, v = m(b['input_ids'].to(device), b['attention_mask'].to(device))
                preds.append(
                    torch.cat([torch.sigmoid(s), torch.sigmoid(c), torch.softmax(v, dim=1)], dim=1).cpu().numpy())
            oof_feats[v_idx, i * 11:(i + 1) * 11] = np.vstack(preds)
        del m;
        gc.collect();
        torch.cuda.empty_cache()

# --- STEP 2: TRAIN & SAVE META-LEARNER ---
meta = MetaNet().to(device)
opt_m = torch.optim.Adam(meta.parameters(), lr=1e-3)
x_m = torch.tensor(oof_feats, dtype=torch.float).to(device)
y_s = torch.tensor(df_stack.binary_toxicity.values).to(device)
y_c = torch.tensor(df_stack[['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']].values).to(
    device)
y_v = torch.tensor(df_stack['Toxicity Level'].values).to(device)

print("\n--- Training Meta-Learner ---")
for _ in range(200):
    opt_m.zero_grad()
    sl, cl, vl = meta(x_m)
    loss = nn.BCEWithLogitsLoss()(sl.squeeze(), y_s.float()) + nn.BCEWithLogitsLoss()(cl,
                                                                                      y_c.float()) + nn.CrossEntropyLoss()(
        vl, y_v)
    loss.backward();
    opt_m.step()

torch.save(meta.state_dict(), "models/ensemble/meta_learner/meta_learner.pt")
print("✅ Meta-Learner Saved.")

# --- STEP 3: FINAL TRAINING & SAVING BASE MODELS ---
print("\n--- Finalizing Base Models ---")
final_jobs = [
    ("xlmr", TransformerMTL, tok_xlmr, "xlm-roberta-base", "models/ensemble/xlmr"),
    ("muril", TransformerMTL, tok_muril, "google/muril-base-cased", "models/ensemble/muril"),
    ("bilstm", BiLSTMMTL, tok_xlmr, len(tok_xlmr), "models/ensemble/bilstm")
]

for name, m_cls, tok, path, save_path in final_jobs:
    m = m_cls(path);
    m.to(device)
    ldr = DataLoader(ToxicityDataset(df_stack.Sentence.values, df_stack.binary_toxicity.values, df_stack[
        ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']].values,
                                     df_stack['Toxicity Level'].values, tok), batch_size=8, shuffle=True)
    run_train(m, ldr)

    if name != "bilstm":
        m.backbone.save_pretrained(save_path)
        tok.save_pretrained(save_path)
        torch.save({'safety': m.safety_head.state_dict(), 'category': m.cat_head.state_dict(),
                    'severity': m.sev_head.state_dict()}, os.path.join(save_path, "mtl_heads.bin"))
    else:
        torch.save(m.state_dict(), os.path.join(save_path, "bilstm_weights.pt"))
        tok.save_pretrained(save_path)
    print(f"✅ {name} Saved.")
    del m;
    gc.collect();
    torch.cuda.empty_cache()