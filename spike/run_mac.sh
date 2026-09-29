#!/usr/bin/env bash
# Spike 002 on the MacBook: base benchmark, MLX LoRA training, tuned benchmark - strictly one after
# another (training next to a model server ran out of GPU memory on 36 GB), detached from any terminal.
# Start:  nohup caffeinate -dimsu bash spike/run_mac.sh > data/spike/run-mac.log 2>&1 &
# Label runs resume where they stopped (chunks with a parsed output are skipped).
set -uo pipefail
cd "$(dirname "$0")/.."
MLX="uvx --from mlx-lm==0.31.3"
MODEL=mlx-community/Qwen3-4B-Instruct-2507-4bit
PILOT="uv run pilot --config configs/spike-v1.yaml"
log() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*"; }

serve() {  # port [adapter]
  local extra=""
  [ -n "${2:-}" ] && extra="--adapter-path $2"
  # shellcheck disable=SC2086
  $MLX mlx_lm.server --model "$MODEL" $extra --host 127.0.0.1 --port "$1" \
    > "data/spike/server-$1.log" 2>&1 &
  echo $!
  until curl -s -m 3 "http://127.0.0.1:$1/v1/models" > /dev/null; do sleep 3; done
}

label() {  # model_id
  local attempt
  for attempt in 1 2 3; do
    $PILOT label --role baseline --backend openai_compat --model "$1" --split main && return 0
    $PILOT label --role baseline --backend openai_compat --model "$1" --split main --retry-failed \
      && return 0
    log "label $1 attempt $attempt failed"
  done
  return 1
}

log "base benchmark started"
BASE_SERVER=$(serve 8080)
label spike-base; log "base benchmark finished (rc $?)"
kill "$BASE_SERVER" 2>/dev/null; pkill -f "mlx_lm.server.*--port 8080"
sleep 5

log "training started"
$MLX mlx_lm.lora -c spike/train_mlx.yaml > data/spike/train-mlx.log 2>&1; rc=$?
log "training finished (rc $rc)"
[ "$rc" -ne 0 ] && exit "$rc"

log "tuned benchmark started"
TUNED_SERVER=$(serve 8082 data/spike/adapter-mlx)
label spike-tuned; log "tuned benchmark finished (rc $?)"
kill "$TUNED_SERVER" 2>/dev/null; pkill -f "mlx_lm.server.*--port 8082"
log "done"
