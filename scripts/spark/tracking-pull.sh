#!/usr/bin/env bash
# Fetches the offline run logs of Spark training runs and syncs them into the laptop's MLflow server
# (feature 017, research R17). Runs on the laptop; needs only SSH to the Spark.
#
# Usage: scripts/spark/tracking-pull.sh [REMOTE_DATA_DIR]     default: mobility-model-zoo/data
#
# Copies only *.mmz-run.jsonl, their *.mmz-run/ artifact folders and *.tracking.json sidecars into the
# same paths under data/ here, never models or training data, then runs `zoo tracking sync data/`.
# Run it during a training to see the epochs so far; a second run adds only what is new. The server
# must be running (scripts/mlflow/mlflow.sh up) and MLFLOW_TRACKING_URI set.
set -euo pipefail
cd "$(dirname "$0")/../.."
REMOTE=${1:-mobility-model-zoo/data}

# only SPARK_HOST from .env
if [ -z "${SPARK_HOST:-}" ] && [ -f .env ]; then
  SPARK_HOST=$(grep -E '^SPARK_HOST=' .env | tail -1 | cut -d= -f2- | tr -d "\"'")
fi
SPARK=${SPARK_HOST:?set SPARK_HOST=user@host in .env}

mkdir -p data
rsync -am \
  --include='*/' \
  --include='*.mmz-run.jsonl' \
  --include='*.mmz-run/***' \
  --include='*.tracking.json' \
  --exclude='*' \
  "$SPARK:$REMOTE/" data/
exec uv run zoo tracking sync data/
