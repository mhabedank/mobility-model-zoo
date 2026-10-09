#!/usr/bin/env bash
# Stage the build context for the reference machine (topics/productdev/deploy/railway-perf) in $1 (default
# /tmp/jtbd-perf): the repository at HEAD, the benchmark chunks and the run manifests (no raw model
# outputs). Chunks are redacted benchmark texts; nothing else from data/ is sent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
OUT="${1:-/tmp/jtbd-perf}"
rm -rf "$OUT" && mkdir -p "$OUT"
git -C "$ROOT" archive HEAD | tar -x -C "$OUT"
cp "$ROOT/deploy/railway-perf/Dockerfile" "$OUT/Dockerfile"
mkdir -p "$OUT/data/chunks" "$OUT/data/runs"
cp "$ROOT"/data/chunks/ch-*.json "$OUT/data/chunks/"
for m in "$ROOT"/data/runs/run-*/manifest.json; do
  d="$OUT/data/runs/$(basename "$(dirname "$m")")"; mkdir -p "$d"; cp "$m" "$d/"
done
mkdir -p "$OUT/topics/productdev" \&\& cp -r "$ROOT/topics/productdev/benchmarks" "$OUT/topics/productdev/"
# Span model directories to measure (feature 004): STAGE_MODELS="span-xlmr-c1 ..."
for m in ${STAGE_MODELS:-}; do
  mkdir -p "$OUT/models" && cp -r "$ROOT/data/models/$m" "$OUT/models/"
done
echo "$OUT"
