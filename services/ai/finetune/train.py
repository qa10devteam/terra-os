"""AXON Fine-Tuning Script — Qwen2.5-7B-Instruct with LoRA on 4x L4.

Uses PEFT LoRA + bitsandbytes 4-bit quantization + TRL SFTTrainer.
Dataset: services/ai/finetune/dataset_v1.jsonl (40 SFT pairs).
Output: services/ai/finetune/axon-qwen-7b-lora/
"""
import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# ─── Config ────────────────────────────────────────────────────────────
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"  # 7B fits comfortably on 1x L4 with 4-bit
OUTPUT_DIR = "/home/ubuntu/terra-os/services/ai/finetune/axon-qwen-7b-lora"
DATASET_PATH = "/home/ubuntu/terra-os/services/ai/finetune/dataset_v1.jsonl"
MAX_SEQ_LEN = 2048
EPOCHS = 5
BATCH_SIZE = 2
GRAD_ACCUM = 4
LR = 2e-4

# ─── Load dataset ──────────────────────────────────────────────────────
print("Loading dataset...")
with open(DATASET_PATH) as f:
    raw_data = json.load(f)

# Convert to chat template format
def format_conversation(example):
    """Format messages into Qwen chat template."""
    text = ""
    for msg in example["messages"]:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            text += f"<|im_start|>system\n{content}<|im_end|>\n"
        elif role == "user":
            text += f"<|im_start|>user\n{content}<|im_end|>\n"
        elif role == "assistant":
            text += f"<|im_start|>assistant\n{content}<|im_end|>\n"
    return {"text": text}

dataset = Dataset.from_list(raw_data).map(format_conversation)
print(f"Dataset: {len(dataset)} examples")

# ─── Quantization config ───────────────────────────────────────────────
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# ─── Load model + tokenizer ───────────────────────────────────────────
print(f"Loading {MODEL_ID} with 4-bit quantization...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="cuda:0",  # Single GPU — Qwen 7B 4-bit ~5GB, L4 ma 24GB
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
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
print("Starting SFT training...")
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=training_args,
    processing_class=tokenizer,
    max_seq_length=MAX_SEQ_LEN,
    dataset_text_field="text",
    packing=False,  # off — brak flash-attn, unikamy cross-contamination
)

trainer.train()

# ─── Save ─────────────────────────────────────────────────────────────
print(f"Saving LoRA adapter to {OUTPUT_DIR}...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n" + "="*60)
print("FINE-TUNING COMPLETE")
print(f"LoRA adapter saved: {OUTPUT_DIR}")
print(f"Base model: {MODEL_ID}")
print(f"Merge command: python -m peft.merge_and_unload {OUTPUT_DIR}")
print("="*60)
