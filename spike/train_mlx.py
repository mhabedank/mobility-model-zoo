"""MLX LoRA training for spike 002, second attempt (see data/spike/findings.md).

Differences to `mlx_lm.lora` with spike/train_mlx.yaml:
- Loss summed over answer tokens and divided by a constant, not averaged per example. With batch
  size 1 the per-example mean gave short "nothing found" answers ~50x the weight per token and the
  first run collapsed to {"relevant": false, "items": []}.
- Plain ChatML chat template without the empty <think></think> block Qwen3's template inserts into
  assistant turns, so training and inference see the same assistant prefix.
- No loss-based validation; checkpoints are chosen afterwards by generation (select_checkpoint.py).

Run: uv run --with mlx-lm==0.31.3 python spike/train_mlx.py spike/train_mlx.yaml
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np
import yaml
from mlx_lm import load
from mlx_lm.tuner.datasets import CacheDataset, ChatDataset
from mlx_lm.tuner.trainer import TrainingArgs, train
from mlx_lm.tuner.utils import linear_to_lora_layers, print_trainable_parameters
from mlx_lm.utils import save_config

CHATML = (
    "{% for message in messages %}<|im_start|>{{ message['role'] }}\n{{ message['content'] }}"
    "<|im_end|>\n{% endfor %}{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
)


def token_sum_loss(norm: float):
    def loss(model, batch, lengths):
        inputs, targets = batch[:, :-1], batch[:, 1:]
        logits = model(inputs)
        steps = mx.arange(1, targets.shape[1] + 1)
        mask = mx.logical_and(steps >= lengths[:, 0:1], steps <= lengths[:, 1:])
        ce = (nn.losses.cross_entropy(logits, targets) * mask).astype(mx.float32)
        ntoks = mask.sum()
        # Reported value: sum / norm. Every answer token has the same weight across examples.
        return ce.sum() / norm, ntoks

    return loss


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main(config_path: str) -> None:
    cfg = yaml.safe_load(Path(config_path).read_text())
    np.random.seed(cfg["seed"])
    mx.random.seed(cfg["seed"])
    model, tokenizer = load(cfg["model"])
    tokenizer._tokenizer.chat_template = CHATML  # noqa: SLF001 - no public setter on the wrapper

    data = Path(cfg["data"])
    train_rows = read_jsonl(data / "train.jsonl")
    train_set = ChatDataset(train_rows, tokenizer, mask_prompt=True)
    answer_tokens = [len(t) - off for t, off in (train_set.process(r) for r in train_rows)]
    norm = float(np.mean(answer_tokens))
    print(f"{len(train_rows)} training examples, mean answer tokens {norm:.0f} (loss norm)")

    model.freeze()
    linear_to_lora_layers(model, cfg["num_layers"], cfg["lora_parameters"])
    print_trainable_parameters(model)
    adapter_path = Path(cfg["adapter_path"])
    adapter_path.mkdir(parents=True, exist_ok=True)
    save_config({**cfg, "fine_tune_type": "lora", "loss": "token_sum", "loss_norm": norm,
                 "chat_template": "chatml-no-think"}, adapter_path / "adapter_config.json")

    iters = cfg["epochs"] * len(train_rows)
    args = TrainingArgs(
        batch_size=1, iters=iters, val_batches=1, steps_per_report=cfg["steps_per_report"],
        steps_per_eval=iters + 1, steps_per_save=cfg["save_every"],
        adapter_file=adapter_path / "adapters.safetensors",
        max_seq_length=cfg["max_seq_length"], grad_checkpoint=True,
        grad_accumulation_steps=cfg["grad_accumulation_steps"])
    train(model=model, optimizer=optim.Adam(learning_rate=cfg["learning_rate"]), args=args,
          train_dataset=CacheDataset(train_set),
          val_dataset=CacheDataset(ChatDataset(read_jsonl(data / "valid.jsonl"), tokenizer,
                                               mask_prompt=True)),
          loss=token_sum_loss(norm), training_callback=None)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "spike/train_mlx.yaml")
