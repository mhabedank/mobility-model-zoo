#!/usr/bin/env bash
# Job runner of the reference machine. A Railway project token cannot open `railway ssh`, so the
# container runs the jobs itself at start and prints each result to the deployment log between
# markers; scripts/railway/collect.py reads them back with `railway logs`.
#   PERF_MODELS  space-separated model IDs from models.yaml (Ollama baselines), measured in order
#   PERF_SPAN    space-separated span model directories under /app/models (feature 004)
#   PERF_LABEL   hardware label recorded in each result
set -uo pipefail
cd /app
CONFIG=configs/productdev/jtbd/pilot-v1.yaml
LABEL="${PERF_LABEL:-railway service, 4 vCPU limit, 8 GB RAM limit, no GPU}"
ollama serve > /tmp/ollama.log 2>&1 &
until curl -sf 127.0.0.1:11434/api/version > /dev/null; do sleep 1; done
emit() {  # name, file
  echo "=== PERF_RESULT $1 ==="; base64 -w0 "$2"; echo; echo "=== END $1 ==="
}
echo "=== HARDWARE ==="
uv run python -c "import json; from mobility_model_zoo.productdev.jtbd.perf import hardware_info; print(json.dumps(hardware_info('$LABEL')))"
echo "cpu.max: $(cat /sys/fs/cgroup/cpu.max 2>/dev/null) memory.max: $(cat /sys/fs/cgroup/memory.max 2>/dev/null)"
VERSION=$(cat benchmarks/current)
for model in ${PERF_MODELS:-}; do
  api=$(uv run python -c "from mobility_model_zoo.productdev.jtbd.config import load_settings; print(load_settings('$CONFIG').model('$model').api_model)")
  echo "=== PULL $model ($api) ==="
  ollama pull "$api" > /dev/null 2>&1 || echo "pull failed: $api"
  if uv run jtbd --config "$CONFIG" perf --model "$model" --host vm --hardware "$LABEL" > /tmp/out.json 2>&1; then
    emit "$model" "data/analysis/$VERSION/perf/$model.json"
  else
    echo "=== PERF_ERROR $model ==="; tail -c 2000 /tmp/out.json; echo
    echo "--- ollama log ---"; grep -v -E "GIN|level=DEBUG" /tmp/ollama.log | tail -40
  fi
  ollama rm "$api" > /dev/null 2>&1 || true
done
for dir in ${PERF_SPAN:-}; do
  name=$(basename "$dir")
  if uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml perf --backend span \
      --model-dir "models/$dir" --hardware "$LABEL" > /tmp/out.json 2>&1; then
    echo "=== PERF_RESULT span-$name ==="; base64 -w0 /tmp/out.json; echo; echo "=== END span-$name ==="
  else
    echo "=== PERF_ERROR span-$name ==="; tail -c 2000 /tmp/out.json; echo
  fi
done
echo "=== ALL_DONE ==="
wait
