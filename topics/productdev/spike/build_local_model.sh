#!/usr/bin/env bash
# Builds a standalone local MLX model from the spike's best student (spike-v3b: Qwen3-4B-Instruct-2507
# + LoRA trained on the four-teacher ensemble data). Steps: copy the adapter from the Spark, merge it
# into the bf16 base, convert to MLX 8-bit, store the training system prompt next to the weights.
# Result: data/models/spike-v3b-mlx-8bit (try it with topics/productdev/spike/try_model.py).
set -euo pipefail
cd "$(dirname "$0")/../../.."
SPARK=${SPARK:-dienstollama@10.123.47.52}
ADAPTER=data/models/spike-v3b-adapter
MERGED=data/models/spike-v3b-merged
OUT=data/models/spike-v3b-mlx-8bit

mkdir -p "$ADAPTER"
[ -f "$ADAPTER/adapter_model.safetensors" ] || \
  scp "$SPARK:topics/productdev/spike/adapters/v3b/adapter_config.json" "$SPARK:topics/productdev/spike/adapters/v3b/adapter_model.safetensors" "$ADAPTER/"
[ -f "$MERGED/MERGED_FROM.json" ] || \
  uv run --with torch --with transformers --with peft --with accelerate \
    python topics/productdev/spike/merge_adapter.py "$ADAPTER" "$MERGED"
rm -rf "$OUT"
uvx --from mlx-lm==0.31.3 mlx_lm.convert --hf-path "$MERGED" --mlx-path "$OUT" -q --q-bits 8
# The exact system prompt of the training data (guideline, worked examples, schema).
uv run python -c "import json,sys; r=json.loads(open('data/spike/sft/sft-v3b.jsonl').readline()); \
open(sys.argv[1],'w').write(r['messages'][0]['content'])" "$OUT/system_prompt.txt"
echo "built $OUT"
