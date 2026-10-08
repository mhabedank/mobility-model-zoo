#!/usr/bin/env bash
# Trains one span-model candidate on the DGX Spark (feature 004, research R9, T033).
#
# Usage: scripts/spark/train_span.sh <candidate>          e.g. scripts/spark/train_span.sh c1
#
# Needs SPARK_HOST=user@host in .env. Copies the committed repository (with .git, so the training
# gates can check the release-bar commit), the frozen training data and the pilot's decision to
# ~/mobility-model-zoo on the Spark, then runs `jtbd span train` and `jtbd span tune` in the
# NVIDIA PyTorch container. The repository is mounted read-only except data/.
#
# Follow: ssh "$SPARK_HOST" tail -f mobility-model-zoo/data/models/span-xlmr-<candidate>.train.log
# Fetch:  rsync -a "$SPARK_HOST":mobility-model-zoo/data/models/span-xlmr-<candidate> data/models/
set -euo pipefail
cd "$(dirname "$0")/../.."
CANDIDATE=${1:?usage: scripts/spark/train_span.sh <candidate>}
set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
set +a
SPARK=${SPARK_HOST:?set SPARK_HOST=user@host in .env}
REMOTE=mobility-model-zoo
NAME=span-xlmr-$CANDIDATE
CONFIG=configs/productdev/jtbd/span-train-v1.yaml
IMAGE=nvcr.io/nvidia/pytorch:25.09-py3

if [ -n "$(git status --porcelain -- src configs)" ]; then
  echo "uncommitted changes under src/ or configs/; commit them first" >&2
  exit 1
fi
for f in data/span-train-v1/frozen.json data/span-train-v1/rows/rows.jsonl; do
  [ -f "$f" ] || { echo "missing $f; run build-rows and freeze-data first" >&2; exit 1; }
done

ssh "$SPARK" mkdir -p "$REMOTE/data/models"
rsync -a --delete --exclude data/ --exclude .venv/ --exclude __pycache__/ ./ "$SPARK:$REMOTE/"
# shellcheck disable=SC2046
rsync -a --relative data/span-train-v1/chunks data/span-train-v1/rows \
  data/span-train-v1/frozen.json $(ls data/analysis/*/decision.json) "$SPARK:$REMOTE/"

ssh "$SPARK" "docker rm -f $NAME >/dev/null 2>&1 || true; docker run -d --name $NAME --gpus all \
  --ipc=host -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True -e GIT_OPTIONAL_LOCKS=0 \
  -v \$HOME/$REMOTE:/work:ro -v \$HOME/$REMOTE/data:/work/data \
  -v \$HOME/.cache/huggingface:/root/.cache/huggingface $IMAGE bash -c 'cd /work && { \
  git config --global --add safe.directory /work && pip install -q \"/work[jtbd]\" \
  && jtbd --config $CONFIG span train --out data/models/$NAME --device cuda \
  && jtbd --config $CONFIG span tune --model-dir data/models/$NAME; \
  } > data/models/$NAME.train.log 2>&1; echo \"exit \$?\" >> data/models/$NAME.train.log; \
  chmod -R a+rwX /work/data/models'"
echo "started $NAME on $SPARK"
