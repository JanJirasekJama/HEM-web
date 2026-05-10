#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  alembic upgrade head
fi

python -m app.core.seed

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
