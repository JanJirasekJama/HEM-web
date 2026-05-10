#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_DIR="${ROOT_DIR}/.local"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///${LOCAL_DIR}/hem-test.sqlite}"
FILE_STORAGE_ROOT="${FILE_STORAGE_ROOT:-${LOCAL_DIR}/files}"
APP_BASE_URL="${APP_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"
CORS_ORIGINS="${CORS_ORIGINS:-[\"http://${FRONTEND_HOST}:${FRONTEND_PORT}\"]}"
REDIS_URL="${REDIS_URL:-memory://linux-test}"
SECRET_KEY="${SECRET_KEY:-linux-test-secret-change-me}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
INSTALL_DEPS="${INSTALL_DEPS:-1}"

BACKEND_PID=""
FRONTEND_PID=""

log() {
  printf '\033[1;34m[HEM]\033[0m %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local attempt

  for attempt in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$name běží: $url"
      return 0
    fi
    sleep 0.5
  done

  printf '%s se nespustil včas: %s\n' "$name" "$url" >&2
  return 1
}

cleanup() {
  local status=$?

  trap - EXIT INT TERM
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  wait >/dev/null 2>&1 || true

  exit "$status"
}

trap cleanup EXIT INT TERM

require_command uv
require_command npm
require_command curl

mkdir -p "$LOCAL_DIR" "$FILE_STORAGE_ROOT"

log "Lokální data: $LOCAL_DIR"
log "Databáze: $DATABASE_URL"
log "Redis/fronta: $REDIS_URL"

if [ "$INSTALL_DEPS" = "1" ]; then
  log "Instaluji/synchronizuji backend závislosti přes uv"
  (cd "$BACKEND_DIR" && uv sync --dev)

  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log "Instaluji frontend závislosti přes npm"
    (cd "$FRONTEND_DIR" && npm install)
  fi
fi

if [ "$RUN_MIGRATIONS" = "1" ]; then
  log "Pouštím migrace"
  (
    cd "$BACKEND_DIR"
    DATABASE_URL="$DATABASE_URL" \
    REDIS_URL="$REDIS_URL" \
    FILE_STORAGE_ROOT="$FILE_STORAGE_ROOT" \
    APP_BASE_URL="$APP_BASE_URL" \
    CORS_ORIGINS="$CORS_ORIGINS" \
    SECRET_KEY="$SECRET_KEY" \
    uv run alembic upgrade head
  )
fi

log "Seeduji základní role, moduly a admin účet"
(
  cd "$BACKEND_DIR"
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  FILE_STORAGE_ROOT="$FILE_STORAGE_ROOT" \
  APP_BASE_URL="$APP_BASE_URL" \
  CORS_ORIGINS="$CORS_ORIGINS" \
  SECRET_KEY="$SECRET_KEY" \
  uv run python -m app.core.seed
)

log "Startuji backend na http://${BACKEND_HOST}:${BACKEND_PORT}"
(
  cd "$BACKEND_DIR"
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  FILE_STORAGE_ROOT="$FILE_STORAGE_ROOT" \
  APP_BASE_URL="$APP_BASE_URL" \
  CORS_ORIGINS="$CORS_ORIGINS" \
  SECRET_KEY="$SECRET_KEY" \
  uv run uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

wait_for_url "http://${BACKEND_HOST}:${BACKEND_PORT}/api/health" "Backend"

log "Startuji frontend na http://${FRONTEND_HOST}:${FRONTEND_PORT}"
(
  cd "$FRONTEND_DIR"
  VITE_BACKEND_TARGET="http://${BACKEND_HOST}:${BACKEND_PORT}" \
  npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

wait_for_url "http://${FRONTEND_HOST}:${FRONTEND_PORT}" "Frontend"

cat <<EOF

HEM testovací prostředí běží.

Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}
Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}
Login:    admin / 061004

Ukončení: Ctrl+C

Tipy:
  REDIS_URL=redis://127.0.0.1:6379/0 ./scripts/run-linux-test.sh
  INSTALL_DEPS=0 ./scripts/run-linux-test.sh
  BACKEND_PORT=8010 FRONTEND_PORT=5174 ./scripts/run-linux-test.sh

EOF

wait -n "$BACKEND_PID" "$FRONTEND_PID"
