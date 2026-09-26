#!/usr/bin/env bash
# Runs on the DGX Spark: LoRA fine-tuning with Ludwig inside an NVIDIA PyTorch container.
# Usage: bash ~/spike/train.sh [image]   (expects ~/spike/sft.jsonl and ~/spike/train_ludwig.yaml)
set -euo pipefail
IMAGE="${1:-nvcr.io/nvidia/pytorch:25.09-py3}"
docker run --rm --gpus all --ipc=host \
  -v "$HOME/spike:/work" -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -w /work "$IMAGE" bash -lc '
    pip install -q "ludwig[llm]" && \
    ludwig train --config train_ludwig.yaml --dataset sft.jsonl --output_directory results \
      2>&1 | tee train.log'
