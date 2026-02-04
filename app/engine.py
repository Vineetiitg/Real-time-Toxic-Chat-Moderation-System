import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel, AutoModelForSeq2SeqLM
from peft import PeftModel
from langdetect import detect
import os


# --- MODEL ARCHITECTURES ---

class TransformerMTL(nn.Module):
    def __init__(self, model_name):
        super().__init__()
        self.backbone = AutoModel.from_pretrained(model_name)
        dim = self.backbone.config.hidden_size
        self.safety_head = nn.Linear(dim, 1)
        self.cat_head = nn.Linear(dim, 6)
        self.sev_head = nn.Linear(dim, 4)

    def forward(self, ids, mask):
        out = self.backbone(ids, mask)
        pooler = out.last_hidden_state[:, 0, :]
        return self.safety_head(pooler), self.cat_head(pooler), self.sev_head(pooler)


class BiLSTMMTL(nn.Module):
    def __init__(self, vocab_size=250002):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, 128)
        self.lstm = nn.LSTM(128, 64, bidirectional=True, batch_first=True)
        self.safety_head = nn.Linear(128, 1)
        self.cat_head = nn.Linear(128, 6)
        self.sev_head = nn.Linear(128, 4)

    def forward(self, ids):
        x = self.embed(ids)
        x, _ = self.lstm(x)
        return self.safety_head(x.mean(dim=1)), self.cat_head(x.mean(dim=1)), self.sev_head(x.mean(dim=1))


class MetaNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(33, 64), nn.ReLU(), nn.Linear(64, 11))

    def forward(self, x):
        out = self.net(x)
        return out[:, 0:1], out[:, 1:7], out[:, 7:11]


# --- THE FIXED ENGINE ---

class ModerationEngine:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🚀 Initializing Moderation Engine on {self.device}...")

        # 1. LOAD CLASSIFIERS
        # Helper to load tokenizer safely
        def load_tokenizer(name, local_path=None):
            if local_path and os.path.exists(local_path):
                return AutoTokenizer.from_pretrained(local_path)
            return AutoTokenizer.from_pretrained(name)

        self.tok_xlmr = load_tokenizer("xlm-roberta-base") # You can map this to a local path if needed
        self.tok_muril = load_tokenizer("google/muril-base-cased")

        # Define paths relative to the script location for reliability
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        xlmr_path = os.path.join(base_path, "models", "ensemble", "xlmr")
        muril_path = os.path.join(base_path, "models", "ensemble", "muril")
        bilstm_path = os.path.join(base_path, "models", "ensemble", "bilstm", "bilstm_weights.pt")
        meta_path = os.path.join(base_path, "models", "ensemble", "meta_learner", "meta_learner.pt")
        mbart_path = os.path.join(base_path, "models", "final_detox_mbart")

        self.xlmr = self._load_mtl_model("xlm-roberta-base", xlmr_path)
        self.muril = self._load_mtl_model("google/muril-base-cased", muril_path)

        # BiLSTM
        self.bilstm = BiLSTMMTL(len(self.tok_xlmr)).to(self.device).half().eval()
        if os.path.exists(bilstm_path):
            self.bilstm.load_state_dict(torch.load(bilstm_path, map_location=self.device))
        else:
            print(f"⚠️ Warning: BiLSTM weights not found at {bilstm_path}")

        # Meta Learner
        self.meta = MetaNet().to(self.device).eval()
        if os.path.exists(meta_path):
            self.meta.load_state_dict(torch.load(meta_path, map_location=self.device))
        else:
             print(f"⚠️ Warning: MetaNet weights not found at {meta_path}")

        # 2. FIXED REWRITER LOADING (CRITICAL FIX)
        print("📦 Synchronizing mBART-50 Adapters...")
        base_model_name = os.path.join(base_path, "models", "final_detox_mbart")
        self.rewriter_tok = AutoTokenizer.from_pretrained(base_model_name)

        # Load base, then wrap with Peft
        # Check if we have a local cache or offline requirement, else load from hub
        base_rewriter = AutoModelForSeq2SeqLM.from_pretrained(
            base_model_name,
            dtype=torch.float16 if self.device.type == 'cuda' else torch.float32,
            low_cpu_mem_usage=True
        )
        
        if os.path.exists(mbart_path):
             self.rewriter_model = PeftModel.from_pretrained(
                base_rewriter,
                mbart_path
            ).to(self.device).eval()
        else:
             print(f"⚠️ Warning: Detox adapter not found at {mbart_path}. Using base model.")
             self.rewriter_model = base_rewriter.to(self.device).eval()

    def _load_mtl_model(self, base, path):
        print(f"Loading MTL model based on {base} from {path}...")
        try:
            model = TransformerMTL(base)
            if os.path.exists(path):
                model.backbone = PeftModel.from_pretrained(model.backbone, path)
                heads_path = os.path.join(path, "mtl_heads.bin")
                if os.path.exists(heads_path):
                    heads = torch.load(heads_path, map_location=self.device)
                    model.safety_head.load_state_dict(heads['safety'])
                    model.cat_head.load_state_dict(heads['category'])
                    model.sev_head.load_state_dict(heads['severity'])
                else:
                     print(f"⚠️ Warning: MTL heads not found at {heads_path}")
            else:
                 print(f"⚠️ Warning: Adapter path {path} not found")
            
            return model.to(self.device).eval()
        except Exception as e:
            print(f"❌ Error loading MTL model {base}: {e}")
            # Return a basic version so code doesn't crash, or raise
            return TransformerMTL(base).to(self.device).eval()

    def moderate(self, text):
        if not text.strip(): return {"toxic": False, "severity": 0, "suggestion": ""}

        with torch.no_grad():
            # Classifier predictions
            def get_scores(m, t, txt):
                inputs = t(txt, return_tensors="pt", padding=True, truncation=True).to(self.device)
                if isinstance(m, BiLSTMMTL):
                    s, c, v = m(inputs['input_ids'])
                else:
                    s, c, v = m(inputs['input_ids'], inputs['attention_mask'])
                return torch.cat([torch.sigmoid(s), torch.sigmoid(c), torch.softmax(v, dim=1)], dim=1).float()

            f1 = get_scores(self.xlmr, self.tok_xlmr, text)
            f2 = get_scores(self.muril, self.tok_muril, text)
            f3 = get_scores(self.bilstm, self.tok_xlmr, text)

            # Meta-Decision
            s_l, c_l, v_l = self.meta(torch.cat([f1, f2, f3], dim=1))
            is_toxic = torch.sigmoid(s_l).item() > 0.5
            severity = torch.argmax(v_l, dim=1).item()

        # 3. FIXED GENERATION LOGIC (DETOXIFICATION)
        suggestion = text
        if is_toxic:

            try:
                lang = "hi_IN" if detect(text) == 'hi' else "en_XX"
            except:
                lang = "en_XX"

            self.rewriter_tok.src_lang = lang
            inputs = self.rewriter_tok(text, return_tensors="pt").to(self.device)

            # Use Beam Search and Repetition Penalty to prevent "Enough thinking" loops
            gen_tokens = self.rewriter_model.generate(
                **inputs,
                forced_bos_token_id=self.rewriter_tok.lang_code_to_id[lang],
                max_length=128,
                num_beams=5,  # Use Beam Search for quality
                no_repeat_ngram_size=3,  # Stop repeating words
                repetition_penalty=2.5,  # Penalize the model for being "lazy"
                early_stopping=True
            )
            suggestion = self.rewriter_tok.decode(gen_tokens[0], skip_special_tokens=True)

        return {"toxic": is_toxic, "severity": severity, "suggestion": suggestion}