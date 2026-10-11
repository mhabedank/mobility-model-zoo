#!/usr/bin/env bash
# Stage the build context for topics/productdev/deploy/railway-cluster-perf in $1 (default
# /tmp/cluster-perf): the repository at HEAD and the redacted benchmark pool of cluster-v1
# (decision D-railway-perf). Nothing else from data/ is sent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
DATA="${DATA_DIR:-$ROOT/data}"
OUT="${1:-/tmp/cluster-perf}"
rm -rf "$OUT" && mkdir -p "$OUT"
git -C "$ROOT" archive HEAD | tar -x -C "$OUT"
cp "$ROOT/topics/productdev/deploy/railway-cluster-perf/Dockerfile" "$OUT/Dockerfile"
mkdir -p "$OUT/data/cluster/bench/cluster-v1"
cp "$DATA/cluster/bench/cluster-v1/pool-bundle.jsonl" "$OUT/data/cluster/bench/cluster-v1/"
echo "$OUT"
