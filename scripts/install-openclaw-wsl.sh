#!/bin/bash
# Run inside WSL2 Ubuntu (Step 2 of NOVA V2 build). Idempotent-ish: clone skips if present.
set -euo pipefail
OPENCLAW_ROOT="${OPENCLAW_ROOT:-$HOME/openclaw}"
REPO_DIR="$OPENCLAW_ROOT/openclaw"
mkdir -p "$OPENCLAW_ROOT"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone https://github.com/openclaw/openclaw.git "$REPO_DIR"
fi
cd "$REPO_DIR"
export OPENCLAW_SANDBOX="${OPENCLAW_SANDBOX:-1}"
if [[ -x ./docker-setup.sh ]]; then
  ./docker-setup.sh
else
  echo "docker-setup.sh not found or not executable in $REPO_DIR" >&2
  exit 1
fi
echo "Waiting for gateway health..."
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18789/healthz >/dev/null 2>&1; then
    echo "OK: http://127.0.0.1:18789/healthz"
    exit 0
  fi
  sleep 2
done
echo "Health check failed after retries. Try: cd $REPO_DIR && docker compose ps" >&2
exit 1
