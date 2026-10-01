#!/usr/bin/env bash
# Spike 002 on the MacBook, second training attempt: training, checkpoint selection on the
# validation examples, benchmark of the best checkpoint, scoring. Steps run one after another.
# Start:  nohup caffeinate -dimsu bash spike/run_mac_v2.sh > data/spike/run-mac.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
MLX_PY="uv run --with mlx-lm==0.31.3 python"
PILOT="uv run jtbd --config configs/productdev/jtbd/spike-v1.yaml"
PORT=8082
RUN=run-baseline-spike-tuned-main-3223351c
log() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*"; }

log "training started"
$MLX_PY spike/train_mlx.py spike/train_mlx.yaml > data/spike/train-mlx.log 2>&1; rc=$?
log "training finished (rc $rc)"
[ "$rc" -ne 0 ] && exit "$rc"

log "checkpoint selection started"
$MLX_PY spike/select_checkpoint.py spike/train_mlx.yaml > data/spike/select-checkpoint.log 2>&1
rc=$?
log "checkpoint selection finished (rc $rc)"
[ "$rc" -ne 0 ] && exit "$rc"

log "tuned benchmark started"
if lsof -nP -iTCP:$PORT -sTCP:LISTEN > /dev/null; then
  log "port $PORT is in use"; exit 1
fi
uvx --from mlx-lm==0.31.3 mlx_lm.server --model mlx-community/Qwen3-4B-Instruct-2507-4bit \
  --host 127.0.0.1 --port $PORT > data/spike/server-$PORT.log 2>&1 &
until curl -s -m 3 "http://127.0.0.1:$PORT/v1/models" | grep -q '"object"'; do sleep 3; done
for attempt in 1 2 3; do
  $PILOT label --role baseline --backend openai_compat --model spike-tuned --split main && break
  $PILOT label --role baseline --backend openai_compat --model spike-tuned --split main \
    --retry-failed && break
  log "label attempt $attempt failed"
done
pkill -f "mlx_lm.server.*--port $PORT"
log "tuned benchmark finished"

$PILOT check --run $RUN > /dev/null && $PILOT score --run $RUN > data/spike/score-tuned.json
log "scored (rc $?)"
uv run python spike/progress.py
log "done"
