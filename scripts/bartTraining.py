import os
import pandas as pd
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer
)
from peft import LoraConfig, get_peft_model, TaskType

# --- 1. PREVENT HANGS ---
os.environ["WANDB_DISABLED"] = "true"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "true"

# SETTINGS
MODEL_NAME = "facebook/mbart-large-50"
SAVE_PATH = "models/final_detox_mbart"
os.makedirs(SAVE_PATH, exist_ok=True)
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🚀 Environment ready. Target: Step 700. Device: {device}")

# --- 2. DATA PREPARATION ---
df = pd.read_csv(r"C:\Users\Vineet\Downloads\paradetox_flattened_processed.csv").dropna()
dataset = Dataset.from_pandas(df).train_test_split(test_size=0.1, seed=42)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.src_lang = "en_XX"
tokenizer.tgt_lang = "en_XX"

def preprocess_function(examples):
    model_inputs = tokenizer(examples["source_text"], max_length=128, truncation=True, padding="max_length")
    labels = tokenizer(text_target=examples["target_text"], max_length=128, truncation=True, padding="max_length")
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_dataset = dataset.map(preprocess_function, batched=True)

# --- 3. LOAD MODEL ---
model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto"
)

# --- 4. APPLY LORA ---
peft_config = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q_proj", "v_proj"]
)
model = get_peft_model(model, peft_config)

# --- 5. UPDATED ARGUMENTS (STOP AT STEP 700) ---
training_args = Seq2SeqTrainingArguments(
    output_dir="./temp_checkpoints",
    max_steps=700,                   # <--- NEW: Stop exactly at the point you requested
    eval_strategy="steps",           # Evaluate by steps instead of epochs
    eval_steps=100,                  # Check performance every 100 steps
    learning_rate=1e-4,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    num_train_epochs=1,              # This is now ignored because max_steps is set
    predict_with_generate=True,
    fp16=True,
    logging_steps=10,
    report_to="none",
    save_total_limit=1
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["test"],
    tokenizer=tokenizer,
    data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
)

# --- 6. EXECUTE ---
print("🔥 TRAINING UNTIL STEP 700...")
trainer.train()

print(f"💾 SAVING FINAL MODEL TO {SAVE_PATH}...")
model.save_pretrained(SAVE_PATH)
tokenizer.save_pretrained(SAVE_PATH)
print("✅ SUCCESS: Model saved at minimal loss point.")