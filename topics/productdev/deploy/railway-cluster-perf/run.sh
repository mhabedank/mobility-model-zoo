#!/usr/bin/env bash
# Job runner of the reference machine for `jtbd cluster perf`. The container measures each stage
# settings file in PERF_SETTINGS on the real pool and on a scale set, prints every result to the
# deployment log between markers (read back by topics/productdev/scripts/railway/collect.py
# --out data/cluster/analysis/cluster-v1) and then idles, so Railway does not restart it.
#   PERF_SETTINGS  space-separated stage settings files (tuned candidates of T044)
#   PERF_SCALE     items of the scale set (default 50000)
#   PERF_LABEL     hardware label recorded in each result
set -uo pipefail
cd /app
CONFIG=configs/productdev/jtbd/cluster-v1.yaml
LABEL="${PERF_LABEL:-railway service eu-west, 4 vCPU limit, 8 GB RAM limit, no GPU}"
SCALE="${PERF_SCALE:-50000}"
OUT=data/cluster/analysis/cluster-v1
emit() {  # name, file
  echo "=== PERF_RESULT $1 ==="; base64 -w0 "$2"; echo; echo "=== END $1 ==="
}
echo "=== HARDWARE ==="
uv run python -c "import json; from mobility_model_zoo.productdev.jtbd.perf import hardware_info; print(json.dumps(hardware_info('$LABEL')))"
echo "cpu.max: $(cat /sys/fs/cgroup/cpu.max 2>/dev/null) memory.max: $(cat /sys/fs/cgroup/memory.max 2>/dev/null)"
for settings in ${PERF_SETTINGS:-}; do
  name=$(uv run python -c "from mobility_model_zoo.productdev.jtbd.cluster.stage import load_stage_settings as l; print(l('$settings')[0].get('name'))")
  echo "=== PREFETCH $name ==="
  # Models are downloaded before the measurement; the measurement itself runs offline.
  uv run python - "$settings" <<'PY' || { echo "=== PERF_ERROR $name prefetch ==="; continue; }
import sys
from huggingface_hub import snapshot_download
from mobility_model_zoo.productdev.jtbd.cluster.stage import load_stage_settings
s = load_stage_settings(sys.argv[1])[0]
for model in (s["encoder"], s.get("nli")):
    if model and model.get("model_id"):
        snapshot_download(model["model_id"], revision=model["revision"])
PY
  for scale in "" "$SCALE"; do
    args=(--settings "$settings" --hardware "$LABEL")
    suffix=""
    if [ -n "$scale" ]; then args+=(--scale "$scale"); suffix="-scale$scale"; fi
    if uv run jtbd --config "$CONFIG" cluster perf "${args[@]}" > /tmp/out.json 2> /tmp/err.log; then
      emit "perf-$name$suffix" "$OUT/perf-$name$suffix.json"
    else
      echo "=== PERF_ERROR $name$suffix ==="; tail -c 2000 /tmp/err.log; echo
    fi
  done
done
echo "=== ALL_DONE ==="
sleep infinity
