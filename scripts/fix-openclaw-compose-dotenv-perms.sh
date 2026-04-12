#!/usr/bin/env bash
# If docker compose fails with: open .../.env: permission denied
# the compose dir's .env is often owned by root (e.g. after docker-setup.sh with sudo).
# This script gives ownership back to your user so docker compose can read it.

set -euo pipefail

DIR="${OPENCLAW_COMPOSE_DIR:-$HOME/openclaw/openclaw}"
ENV="$DIR/.env"

if [[ ! -e "$ENV" ]]; then
  echo "No file at $ENV — nothing to fix."
  exit 0
fi

if [[ -r "$ENV" ]]; then
  echo "$ENV is already readable by $(whoami)."
  ls -la "$ENV"
  exit 0
fi

echo "Not readable as $(whoami): $ENV"
ls -la "$ENV" || true
echo "Fixing ownership (requires sudo once)..."
sudo chown "$(id -un)":"$(id -gn)" "$ENV"
chmod 600 "$ENV"
ls -la "$ENV"
echo "Done. Retry: cd $DIR && docker compose up -d openclaw-gateway"
