#!/usr/bin/env bash
# Trains the encoder span model on the DGX Spark GPU (NVIDIA PyTorch container).
# Usage: bash spike/train_span_spark.sh <name> <rows: ensemble|teachers> <encoder> <lr> <epochs> [extra args]
#   e.g. bash spike/train_span_spark.sh span-large-teachers teachers FacebookAI/xlm-roberta-large 1.5e-5 6
# Export the rows first (here, with the mobility_model_zoo.productdev.jtbd package):
#   uv run --with torch --with transformers python spike/train_span.py [--teachers] \
#       --val-from data/models/span-xlmr-unit/span_model.json --export-rows data/models/spark/rows-<rows>.jsonl
# Follow:   ssh $SPARK tail -f spike/span/<name>.log
# Fetch:    rsync -a $SPARK:spike/span/models/<name> data/models/
set -euo pipefail
cd "$(dirname "$0")/.."
SPARK=${SPARK:-dienstollama@10.123.47.52}
NAME=$1 ROWS=$2 ENCODER=$3 LR=$4 EPOCHS=$5 EXTRA=${6:-}

ssh "$SPARK" mkdir -p spike/span/models
rsync -a spike/span_model.py spike/train_span.py "data/models/spark/rows-$ROWS.jsonl" "$SPARK:spike/span/"
ssh "$SPARK" "docker rm -f $NAME >/dev/null 2>&1 || true; docker run -d --name $NAME --gpus all --ipc=host \
  -v \$HOME/spike/span:/work -v \$HOME/.cache/huggingface:/root/.cache/huggingface \
  nvcr.io/nvidia/pytorch:25.09-py3 bash -c 'pip install -q transformers sentencepiece protobuf \
  && cd /work && python train_span.py --rows rows-$ROWS.jsonl --encoder $ENCODER --lr $LR \
     --epochs $EPOCHS $EXTRA --out /work/models/$NAME > /work/$NAME.log 2>&1; \
  echo \"exit \$?\" >> /work/$NAME.log; chmod -R a+rwX /work'"
echo "started $NAME on $SPARK"
