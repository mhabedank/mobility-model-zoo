#!/usr/bin/env bash
# Private MLflow tracking server on the owner's laptop (feature 017, research R2, R3, R10).
#
#   scripts/mlflow/mlflow.sh up                # start on 127.0.0.1:5000 in the background (uvx, no Docker)
#   scripts/mlflow/mlflow.sh down              # backup, then stop
#   scripts/mlflow/mlflow.sh status | logs
#   scripts/mlflow/mlflow.sh backup            # online SQLite backup + artifacts -> $MMZ_TRACKING_BACKUP/<time>/
#   scripts/mlflow/mlflow.sh restore DIR       # stop, replace the store with a backup, start
#   scripts/mlflow/mlflow.sh upgrade VERSION   # backup, stop, `mlflow db upgrade`, start VERSION
#
# The server listens on the laptop's 127.0.0.1 only; nothing on the network reaches it, and nothing
# runs on the DGX Spark (runs there log offline, scripts/spark/tracking-pull.sh). No assistant,
# gateway or LLM key is configured (constitution XI). Store: $MMZ_TRACKING_HOME (SQLite + artifacts).
set -euo pipefail
cd "$(dirname "$0")/../.."

# Only the tracking keys of .env: the server process never sees tokens or other settings.
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    value=${value%\"}; value=${value#\"}; value=${value%\'}; value=${value#\'}
    if [ -z "${!key:-}" ] && [ -n "$value" ]; then export "$key=$value"; fi
  done < <(grep -E '^(MMZ_TRACKING_[A-Z_]+|MLFLOW_VERSION)=' .env || true)
fi

STORE=${MMZ_TRACKING_HOME:-$HOME/.local/share/mobility-model-zoo/mlflow}
BACKUPS=${MMZ_TRACKING_BACKUP:-$HOME/mlflow-backups}
PORT=${MMZ_TRACKING_PORT:-5000}
KEEP=14
PIDFILE=$STORE/server.pid
LOG=$STORE/server.log
URL=http://127.0.0.1:$PORT

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

version() {
  # an explicit MLFLOW_VERSION, else the version the store was last started or upgraded with
  if [ -n "${MLFLOW_VERSION:-}" ]; then echo "$MLFLOW_VERSION"
  elif [ -f "$STORE/version.txt" ]; then cat "$STORE/version.txt"
  else echo 3.17.1; fi
}

running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

start() {
  local ver=$1
  running && { echo "already running (pid $(cat "$PIDFILE")); use status or down"; exit 1; }
  mkdir -p "$STORE/artifacts"
  # Own process group (job control), so that `down` also stops the server's workers.
  set -m
  nohup uvx --from "mlflow==$ver" mlflow server --host 127.0.0.1 --port "$PORT" \
    --backend-store-uri "sqlite:///$STORE/mlflow.db" \
    --artifacts-destination "$STORE/artifacts" > "$LOG" 2>&1 &
  echo $! > "$PIDFILE"
  set +m
  echo "$ver" > "$STORE/version.txt"
  # the first start downloads mlflow into uv's cache, so allow a few minutes
  for _ in $(seq 1 180); do
    if curl -fsS "$URL/health" >/dev/null 2>&1; then
      echo "started mlflow $ver on $URL (store $STORE)"
      return
    fi
    running || { echo "server exited; last lines of $LOG:" >&2; tail -20 "$LOG" >&2; exit 1; }
    sleep 1
  done
  echo "no answer on $URL/health after 3 minutes; see $LOG" >&2
  exit 1
}

stop() {
  running || { rm -f "$PIDFILE"; return 0; }
  local pid
  pid=$(cat "$PIDFILE")
  kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
  kill -0 "$pid" 2>/dev/null && { kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true; }
  rm -f "$PIDFILE"
}

backup() {
  [ -f "$STORE/mlflow.db" ] || { echo "no store in $STORE yet; nothing to back up"; return 0; }
  local dir
  dir="$BACKUPS/$(date +%F-%H%M%S)"
  [ -e "$dir" ] && dir="$dir-$$"  # two backups within one second
  mkdir -p "$dir"
  # Online backup through SQLite's backup API: consistent while the server keeps writing.
  python3 -c 'import sqlite3, sys; s = sqlite3.connect(sys.argv[1]); d = sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()' \
    "$STORE/mlflow.db" "$dir/mlflow.db"
  tar -C "$STORE" -czf "$dir/artifacts.tar.gz" artifacts
  version > "$dir/version.txt"
  # keep the newest $KEEP (portable: no GNU head/xargs options on macOS)
  ls -1d "$BACKUPS"/*/ 2>/dev/null | sort -r | tail -n +"$((KEEP + 1))" | while read -r old; do rm -rf "$old"; done
  echo "backup in $dir"
}

case "${1:-}" in
  up) start "$(version)" ;;
  down)
    running || { echo "not running"; exit 0; }
    backup
    stop
    echo "stopped"
    ;;
  status)
    if running; then echo "running (pid $(cat "$PIDFILE")), store $STORE"; else echo "not running, store $STORE"; fi
    if curl -fsS "$URL/health" >/dev/null 2>&1; then
      echo "health OK, mlflow $(curl -fsS "$URL/version")"
    else
      echo "no answer on $URL"
    fi
    # only this server's process group: on macOS the AirPlay receiver (ControlCenter) also holds *:5000
    if running; then
      lsof -nP -a -g "$(cat "$PIDFILE")" -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null \
        | awk 'NR > 1 {print "listening on", $(NF - 1)}' | sort -u || true
    fi
    ;;
  logs) tail -100 "$LOG" ;;
  backup) backup ;;
  restore)
    src=${2:?usage: mlflow.sh restore DIR}
    [ -f "$src/mlflow.db" ] && [ -f "$src/artifacts.tar.gz" ] || { echo "not a backup: $src" >&2; exit 1; }
    ver=$(cat "$src/version.txt" 2>/dev/null || version)
    if running; then backup; stop; fi
    rm -rf "$STORE/artifacts" "$STORE/mlflow.db"
    mkdir -p "$STORE"
    cp "$src/mlflow.db" "$STORE/mlflow.db"
    tar -C "$STORE" -xzf "$src/artifacts.tar.gz"
    start "$ver"
    ;;
  upgrade)
    new=${2:?usage: mlflow.sh upgrade VERSION}
    backup
    stop
    uvx --from "mlflow==$new" mlflow db upgrade "sqlite:///$STORE/mlflow.db"
    start "$new"
    ;;
  *) usage ;;
esac
