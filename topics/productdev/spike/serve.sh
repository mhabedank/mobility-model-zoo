#!/usr/bin/env bash
# Runs on the DGX Spark: serves the base model and the LoRA adapter with vLLM (OpenAI-compatible).
# spike-base-spark = untrained base model; spike-v3a / spike-v3b = base + the LoRA adapters in
# ~/spike/adapters/ (copied out of Ludwig's results as the ssh user, files readable).
set -euo pipefail
docker rm -f spike-vllm >/dev/null 2>&1 || true
docker run -d --name spike-vllm --gpus all --ipc=host -p 8000:8000 \
  -v "$HOME/spike:/work" -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-4B-Instruct-2507 --served-model-name spike-base-spark \
  --enable-lora --lora-modules spike-v3a=/work/adapters/v3a spike-v3b=/work/adapters/v3b --max-lora-rank 16 \
  --max-model-len 16384 --gpu-memory-utilization 0.35
echo "started spike-vllm; check with: curl localhost:8000/v1/models"
