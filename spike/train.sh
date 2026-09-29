#!/usr/bin/env bash
# Runs on the DGX Spark: LoRA fine-tuning with Ludwig inside an NVIDIA PyTorch container.
# Usage: CONFIG=train_ludwig.yaml DATASET=sft.jsonl TOKEN_NORM=614 MIN_FREE_GB=30 MAX_MINUTES=600 \
#          setsid nohup bash ~/spike/train.sh > ~/spike/train.out 2>&1 < /dev/null &
#
# The Spark shares 119 GB between CPU and GPU, and a container memory limit does not cover GPU
# allocations. A watchdog on the host therefore kills the container when available memory drops
# below MIN_FREE_GB (sampled every SAMPLE_S seconds) or the run exceeds MAX_MINUTES, so a
# runaway run cannot hang the machine
# again (it did on 2026-09-27). Memory is logged to mem.log. A smoke test on 2026-09-28 saw
# available memory drop 22 GB within 5 s, so MIN_FREE_GB must stay well above that.
set -euo pipefail
IMAGE="${IMAGE:-spike-ludwig:0.17.9}"   # built from Dockerfile.ludwig (Ludwig + BOS patch)
CONFIG="${CONFIG:-train_ludwig.yaml}"
DATASET="${DATASET:-sft.jsonl}"
TOKEN_NORM="${TOKEN_NORM:-1}"    # mean answer tokens of DATASET (token-weighted loss patch)
NAME=spike-train
MIN_FREE_GB="${MIN_FREE_GB:-30}"
MAX_MINUTES="${MAX_MINUTES:-600}"
SAMPLE_S="${SAMPLE_S:-2}"
OLLAMA="${OLLAMA:-http://localhost:11434}"
cd "$HOME/spike"

# Free memory held by Ollama models first (they reload on the next request).
for model in $(curl -s -m 10 "$OLLAMA/api/ps" | python3 -c \
    'import json,sys; print(" ".join(m["name"] for m in json.load(sys.stdin)["models"]))'); do
  curl -s -m 120 "$OLLAMA/api/generate" -d "{\"model\":\"$model\",\"keep_alive\":0}" > /dev/null
  echo "unloaded $model"
done

docker run -d --rm --name "$NAME" --gpus all --ipc=host --memory 80g \
  -v "$HOME/spike:/work" -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -w /work -e CONFIG="$CONFIG" -e DATASET="$DATASET" -e LUDWIG_LOSS_TOKEN_NORM="$TOKEN_NORM" "$IMAGE" bash -lc '
    ludwig train --config "$CONFIG" --dataset "$DATASET" --output_directory results \
      2>&1 | tee train.log'

start=$(date +%s)
min_seen=999
echo "time,available_gb" > mem.log
while docker ps -q --filter "name=^${NAME}$" | grep -q .; do
  free_gb=$(awk '/MemAvailable/ {print int($2 / 1048576)}' /proc/meminfo)
  echo "$(date +%H:%M:%S),$free_gb" >> mem.log
  [ "$free_gb" -lt "$min_seen" ] && min_seen=$free_gb
  if [ "$free_gb" -lt "$MIN_FREE_GB" ]; then
    echo "$(date -Is) watchdog: only ${free_gb} GB available, killing $NAME"
    docker kill "$NAME"
    exit 3
  fi
  if [ $(( $(date +%s) - start )) -gt $(( MAX_MINUTES * 60 )) ]; then
    echo "$(date -Is) watchdog: ${MAX_MINUTES} min exceeded, killing $NAME"
    docker kill "$NAME"
    exit 4
  fi
  sleep "$SAMPLE_S"
done
echo "$(date -Is) $NAME finished; lowest available memory ${min_seen} GB"
