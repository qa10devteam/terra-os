"""AXON Fine-Tuning Script — Qwen2.5-7B-Instruct with LoRA on 4x L4.

Uses PEFT LoRA + bitsandbytes 4-bit quantization + TRL SFTTrainer.
Dataset: services/ai/finetune/dataset_v1.jsonl (50 SFT pairs).
Output: services/ai/finetune/axon-qwen-7b-lora/

Usage:
    # Dry-run — print dataset stats and exit (no GPU required):
    python train.py --dry-run

    # Full training (requires GPU + HF_TOKEN env var):
    HF_TOKEN=hf_... python train.py
"""
import argparse
import json
import logging
import os
import sys
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# ─── Config ────────────────────────────────────────────────────────────
MODEL_ID    = "Qwen/Qwen2.5-7B-Instruct"  # 7B fits comfortably on 1x L4 with 4-bit
OUTPUT_DIR  = "/home/ubuntu/terra-os/services/ai/finetune/axon-qwen-7b-lora"
DATASET_PATH = "/home/ubuntu/terra-os/services/ai/finetune/dataset_v1.jsonl"
MAX_SEQ_LEN = 2048
EPOCHS      = 5
BATCH_SIZE  = 2
GRAD_ACCUM  = 4
LR          = 2e-4

# ─── CLI ───────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="AXON SFT trainer")
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print dataset statistics and exit without loading the model or training.",
)
args = parser.parse_args()

# ─── HuggingFace token check ───────────────────────────────────────────
HF_TOKEN = os.getenv("HF_TOKEN", "")
if not HF_TOKEN:
    warnings.warn(
        "HF_TOKEN environment variable is not set. "
        "Downloading gated models from HuggingFace Hub (e.g. Qwen2.5-7B-Instruct) "
        "will fail unless you are already authenticated via `huggingface-cli login`. "
        "Set HF_TOKEN=hf_... to suppress this warning.",
        stacklevel=1,
    )

# ─── Load dataset — handles both JSONL and JSON array ──────────────────
logger.info("Loading dataset from %s …", DATASET_PATH)

raw_data: list[dict] = []
with open(DATASET_PATH, encoding="utf-8") as f:
    content = f.read().strip()

if content.startswith("["):
    # JSON array format (legacy)
    raw_data = json.loads(content)
    logger.info("Detected JSON array format: %d examples", len(raw_data))
else:
    # JSONL format — one JSON object per line
    for lineno, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            raw_data.append(json.loads(line))
        except json.JSONDecodeError as exc:
            logger.error("JSONL parse error at line %d: %s", lineno, exc)
            sys.exit(1)
    logger.info("Detected JSONL format: %d examples", len(raw_data))

# ─── Dry-run: print stats and exit ────────────────────────────────────
if args.dry_run:
    from collections import Counter

    logger.info("─── DRY-RUN MODE ───────────────────────────────────────")
    logger.info("Dataset path  : %s", DATASET_PATH)
    logger.info("Total examples: %d", len(raw_data))

    # Count tasks by system prompt (first message)
    task_counters: Counter = Counter()
    role_errors = 0
    json_errors = 0
    total_tokens_approx = 0

    for i, ex in enumerate(raw_data):
        msgs = ex.get("messages", [])
        if not msgs:
            role_errors += 1
            continue
        sys_prompt = msgs[0].get("content", "")
        # Heuristic task label from system prompt keywords
        sp = sys_prompt.lower()
        if "klasyfikator" in sp or "kind" in sp:
            task_counters["CLASSIFY"] += 1
        elif "ekstrakcj" in sp and "przedmiar" not in sp:
            task_counters["EXTRACT_FIELDS"] += 1
        elif "przedmiar" in sp or "knr" in sp:
            task_counters["EXTRACT_PRZEDMIAR"] += 1
        elif "podsumow" in sp or "summary" in sp:
            task_counters["SUMMARIZE"] += 1
        elif "red_flag" in sp or "ryzyko" in sp or "klauzul" in sp:
            task_counters["RISK_FLAGS"] += 1
        elif "verdict" in sp or "decyzj" in sp or "bid" in sp:
            task_counters["DECISION"] += 1
        else:
            task_counters["OTHER"] += 1

        # Validate assistant response is valid JSON
        asst_content = msgs[-1].get("content", "") if msgs else ""
        try:
            json.loads(asst_content)
        except json.JSONDecodeError:
            json_errors += 1
            logger.warning("  Example %d assistant response is not valid JSON", i)

        # Approximate token count (≈ chars / 4)
        all_text = " ".join(m.get("content", "") for m in msgs)
        total_tokens_approx += len(all_text) // 4

    logger.info("")
    logger.info("Task distribution:")
    for task, cnt in sorted(task_counters.items()):
        logger.info("  %-25s %d", task, cnt)
    logger.info("")
    logger.info("Avg tokens/example (approx): %d", total_tokens_approx // max(len(raw_data), 1))
    logger.info("Total tokens (approx):        %d", total_tokens_approx)
    logger.info("Role errors:  %d", role_errors)
    logger.info("JSON errors:  %d", json_errors)
    logger.info("")
    logger.info("Training config (would use):")
    logger.info("  model_id  : %s", MODEL_ID)
    logger.info("  output_dir: %s", OUTPUT_DIR)
    logger.info("  epochs    : %d", EPOCHS)
    logger.info("  batch_size: %d (grad_accum=%d, effective=%d)", BATCH_SIZE, GRAD_ACCUM, BATCH_SIZE * GRAD_ACCUM)
    logger.info("  lr        : %g", LR)
    logger.info("  max_seq   : %d", MAX_SEQ_LEN)
    logger.info("")
    logger.info("DRY-RUN complete. Pass --no-dry-run or omit --dry-run to train.")
    sys.exit(0)

# ─── Full training ─────────────────────────────────────────────────────
import torch  # noqa: E402 — import after dry-run exit to avoid slow torch load
from datasets import Dataset  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # noqa: E402
from trl import SFTTrainer, SFTConfig  # noqa: E402


# Convert to chat template format
def format_conversation(example: dict) -> dict:
    """Format messages into Qwen chat template."""
    text = ""
    for msg in example["messages"]:
        role    = msg["role"]
        content = msg["content"]
        if role == "system":
            text += f"<|im_start|>system\n{content}<|im_end|>\n"
        elif role == "user":
            text += f"<|im_start|>user\n{content}<|im_end|>\n"
        elif role == "assistant":
            text += f"<|im_start|>assistant\n{content}<|im_end|>\n"
    return {"text": text}


dataset = Dataset.from_list(raw_data).map(format_conversation)
logger.info("Dataset: %d examples", len(dataset))

# ─── Quantization config ───────────────────────────────────────────────
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# ─── Load model + tokenizer ───────────────────────────────────────────
logger.info("Loading %s with 4-bit quantization…", MODEL_ID)
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    trust_remote_code=True,
    token=HF_TOKEN or None,
)
tokenizer.pad_token    = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="cuda:0",   # Single GPU — Qwen 7B 4-bit ~5 GB, L4 has 24 GB
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    token=HF_TOKEN or None,
)

model = prepare_model_for_kbit_training(model)

# ─── LoRA config ──────────────────────────────────────────────────────
lora_config = LoraConfig(
    r=64,
    lora_alpha=128,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ─── Training arguments ───────────────────────────────────────────────
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=LR,
    weight_decay=0.01,
    warmup_steps=2,
    lr_scheduler_type="cosine",
    logging_steps=5,
    save_strategy="epoch",
    bf16=True,
    gradient_checkpointing=True,
    max_grad_norm=1.0,
    report_to="none",
    dataloader_num_workers=2,
)

# ─── Trainer ──────────────────────────────────────────────────────────
logger.info("Starting SFT training…")
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=training_args,
    processing_class=tokenizer,
    max_seq_length=MAX_SEQ_LEN,
    dataset_text_field="text",
    packing=False,   # off — brak flash-attn, unikamy cross-contamination
)

trainer.train()

# ─── Save ─────────────────────────────────────────────────────────────
logger.info("Saving LoRA adapter to %s…", OUTPUT_DIR)
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n" + "=" * 60)
print("FINE-TUNING COMPLETE")
print(f"LoRA adapter saved: {OUTPUT_DIR}")
print(f"Base model: {MODEL_ID}")
print(f"Merge command: python -m peft.merge_and_unload {OUTPUT_DIR}")
print("=" * 60)
