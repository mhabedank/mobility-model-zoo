#!/usr/bin/env bash
# Private MLflow tracking server on the DGX Spark (feature 017, research R2, R3, R10).
#
# On the Spark:
#   scripts/spark/mlflow/mlflow.sh up | down | status | logs
#   scripts/spark/mlflow/mlflow.sh backup          # online SQLite backup + artifacts -> ~/mlflow-backups/<date>/
#   scripts/spark/mlflow/mlflow.sh restore DIR     # stop, replace the store with a backup, start
#   scripts/spark/mlflow/mlflow.sh upgrade TAG     # backup, stop, `mlflow db upgrade`, start TAG
# On the laptop:
#   scripts/spark/mlflow/mlflow.sh tunnel          # ssh -N -L 5000:127.0.0.1:5000 $SPARK_HOST
#   scripts/spark/mlflow/mlflow.sh pull-backup     # copy the newest backup from the Spark
#
# The server listens on 127.0.0.1:5000 of the Spark only; nothing on the network reaches it. Training
# containers join the Docker network `mmz-tracking` and reach it as http://mlflow:5000. No assistant,
# gateway or LLM key is configured (constitution XI). Store: ~/mlflow (SQLite + artifacts).
set -euo pipefail
cd "$(dirname "$0")/../../.."
set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
set +a

TAG=${MLFLOW_TAG:-v3.17.1}
IMAGE=ghcr.io/mlflow/mlflow
NAME=mlflow
NETWORK=mmz-tracking
STORE=${MLFLOW_STORE:-$HOME/mlflow}
BACKUPS=${MLFLOW_BACKUPS:-$HOME/mlflow-backups}
KEEP=14
# Host headers the server accepts: the SSH tunnel (localhost, 127.0.0.1) and the containers on
# $NETWORK (mlflow). Ports included; check `mlflow server --help` of a new tag before upgrading.
ALLOWED_HOSTS=${MLFLOW_ALLOWED_HOSTS:-localhost,localhost:5000,127.0.0.1,127.0.0.1:5000,mlflow,mlflow:5000}

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

start() {
  local tag=$1
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK" >/dev/null
  mkdir -p "$STORE/artifacts"
  docker run -d --name "$NAME" --restart unless-stopped --network "$NETWORK" \
    -p 127.0.0.1:5000:5000 -v "$STORE:/data" "$IMAGE:$tag" \
    mlflow server --host 0.0.0.0 --port 5000 \
      --backend-store-uri sqlite:////data/mlflow.db \
      --artifacts-destination /data/artifacts \
      --allowed-hosts "$ALLOWED_HOSTS" >/dev/null
  echo "started $IMAGE:$tag on 127.0.0.1:5000 (network $NETWORK, store $STORE)"
}

stop() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }

backup() {
  local day dir
  day=$(date +%F)
  dir="$BACKUPS/$day"
  mkdir -p "$dir"
  # Online backup through SQLite's backup API: consistent while the server keeps writing.
  docker exec "$NAME" python -c \
    "import sqlite3; s = sqlite3.connect('/data/mlflow.db'); d = sqlite3.connect('/data/backup.db'); s.backup(d); d.close()"
  mv "$STORE/backup.db" "$dir/mlflow.db"
  tar -C "$STORE" -czf "$dir/artifacts.tar.gz" artifacts
  docker inspect --format '{{.Config.Image}}' "$NAME" > "$dir/image.txt"
  ls -1d "$BACKUPS"/*/ | sort | head -n -"$KEEP" | xargs -r rm -rf
  echo "backup in $dir"
}

case "${1:-}" in
  up)
    docker ps -a --format '{{.Names}}' | grep -qx "$NAME" && { echo "already exists; use status or down"; exit 1; }
    start "$TAG"
    ;;
  down) stop; echo "stopped" ;;
  status)
    docker ps --filter "name=^${NAME}$" --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
    curl -fsS http://127.0.0.1:5000/health && echo
    curl -fsS http://127.0.0.1:5000/version && echo
    ;;
  logs) docker logs --tail 100 "$NAME" ;;
  backup) backup ;;
  restore)
    src=${2:?usage: mlflow.sh restore DIR}
    [ -f "$src/mlflow.db" ] && [ -f "$src/artifacts.tar.gz" ] || { echo "not a backup: $src" >&2; exit 1; }
    tag=$(sed 's/.*://' "$src/image.txt" 2>/dev/null || echo "$TAG")
    stop
    rm -rf "$STORE/artifacts" "$STORE/mlflow.db"
    cp "$src/mlflow.db" "$STORE/mlflow.db"
    tar -C "$STORE" -xzf "$src/artifacts.tar.gz"
    start "$tag"
    ;;
  upgrade)
    new=${2:?usage: mlflow.sh upgrade TAG}
    backup
    stop
    docker run --rm -v "$STORE:/data" "$IMAGE:$new" mlflow db upgrade sqlite:////data/mlflow.db
    start "$new"
    ;;
  tunnel)
    echo "tunnel to ${SPARK_HOST:?set SPARK_HOST=user@host in .env}: http://127.0.0.1:5000 (Ctrl-C closes it)"
    exec ssh -N -L 5000:127.0.0.1:5000 "$SPARK_HOST"
    ;;
  pull-backup)
    host=${SPARK_HOST:?set SPARK_HOST=user@host in .env}
    newest=$(ssh "$host" "ls -1d mlflow-backups/*/ | sort | tail -1")
    mkdir -p "$BACKUPS"
    rsync -a "$host:$newest" "$BACKUPS/"
    echo "copied $newest to $BACKUPS/"
    ;;
  *) usage ;;
esac
