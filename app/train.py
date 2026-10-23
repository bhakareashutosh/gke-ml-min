"""Fine-tune a small LLM on CPU. Checkpoints go to /data (a GCS bucket), so a restarted pod resumes."""
import glob, os
from datasets import load_dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling,
                          Trainer, TrainingArguments)

BASE = os.getenv("BASE_MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")
OUT = os.getenv("OUTPUT_DIR", "/data")
SAMPLES = int(os.getenv("MAX_SAMPLES", "500"))
CKPT = f"{OUT}/checkpoints"

tok = AutoTokenizer.from_pretrained(BASE)
tok.pad_token = tok.pad_token or tok.eos_token

ds = load_dataset("databricks/databricks-dolly-15k", split="train").shuffle(seed=42).select(range(SAMPLES))
ds = ds.map(lambda e: tok(f"### Instruction:\n{e['instruction']}\n\n### Response:\n{e['response']}{tok.eos_token}",
                          truncation=True, max_length=256),
            remove_columns=ds.column_names)

args = TrainingArguments(
    output_dir=CKPT, use_cpu=True, report_to="none",
    per_device_train_batch_size=4, num_train_epochs=1, learning_rate=5e-5,
    logging_steps=10, save_steps=50, save_total_limit=2,
)
trainer = Trainer(model=AutoModelForCausalLM.from_pretrained(BASE), args=args, train_dataset=ds,
                  data_collator=DataCollatorForLanguageModeling(tok, mlm=False))

resume = bool(glob.glob(f"{CKPT}/checkpoint-*"))
print(f"resume_from_checkpoint={resume}", flush=True)
trainer.train(resume_from_checkpoint=resume or None)

trainer.save_model(f"{OUT}/model")   # the "production" artifact
tok.save_pretrained(f"{OUT}/model")
print(f"model saved to {OUT}/model", flush=True)
