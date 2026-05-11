#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run-linux-test.sh"

cat <<'EOF'
HEM local start

This starts a local development setup:
- backend on http://127.0.0.1:8000
- frontend on http://127.0.0.1:5173
- local SQLite database in .local/
- local file storage in .local/files/

Login after startup:
  admin / 061004

Stop both servers with Ctrl+C.
EOF

if [ ! -x "$SCRIPT" ]; then
  chmod +x "$SCRIPT"
fi

exec "$SCRIPT"
