#!/usr/bin/env bash
# Fallback training on the DGX Spark (only if Ludwig fails): TRL + PEFT in the NVIDIA PyTorch image.
set -euo pipefail
IMAGE="${1:-nvcr.io/nvidia/pytorch:25.09-py3}"
docker run --rm --gpus all --ipc=host \
  -v "$HOME/spike:/work" -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -w /work "$IMAGE" bash -lc 'pip install -q "trl>=0.20" peft datasets && python train_trl.py 2>&1 | tee train_trl.log'
