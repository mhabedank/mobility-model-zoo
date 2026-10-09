"""Fallback LoRA fine-tuning with Hugging Face TRL + PEFT (used only if Ludwig fails; spike 002).

Same data (sft.jsonl, `messages` field), same base model and LoRA settings as train_ludwig.yaml.
Writes a PEFT adapter to /work/adapter for vLLM (--lora-modules spike-tuned=/work/adapter).
"""

import json
import sys

from datasets import Dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

BASE = "Qwen/Qwen3-4B-Instruct-2507"
rows = [json.loads(line) for line in open("/work/sft.jsonl", encoding="utf-8")]
data = Dataset.from_list([{"messages": r["messages"]} for r in rows])

config = SFTConfig(
    output_dir="/work/trl-out",
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    max_length=8192,
    assistant_only_loss=True,
    bf16=True,
    gradient_checkpointing=True,
    logging_steps=5,
    save_strategy="no",
    report_to=[],
)
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj",
                                  "down_proj"])
trainer = SFTTrainer(model=BASE, args=config, train_dataset=data, peft_config=lora)
trainer.train()
trainer.model.save_pretrained("/work/adapter")
trainer.processing_class.save_pretrained("/work/adapter")
print("adapter saved to /work/adapter", file=sys.stderr)
