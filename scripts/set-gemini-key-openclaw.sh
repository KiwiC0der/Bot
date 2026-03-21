#!/usr/bin/env bash
# Prompts for GEMINI_API_KEY (hidden), updates email.env, restarts gateway.
# Backs up the previous file, chmod 600, strips CR; does not echo the key.

set -euo pipefail

OPENCLAW_COMPOSE_DIR="${OPENCLAW_COMPOSE_DIR:-$HOME/openclaw/openclaw}"
ENV_FILE="$OPENCLAW_COMPOSE_DIR/email.env"
umask 077

if [[ ! -f "$OPENCLAW_COMPOSE_DIR/docker-compose.yml" ]]; then
  echo "Missing $OPENCLAW_COMPOSE_DIR/docker-compose.yml — set OPENCLAW_COMPOSE_DIR or clone OpenClaw there."
  exit 1
fi

read -r -s -p "Paste GEMINI_API_KEY (input hidden): " key
echo

# Normalize pasted input (Windows/newlines, outer whitespace)
key="${key//$'\r'/}"
key="${key#"${key%%[![:space:]]*}"}"
key="${key%"${key##*[![:space:]]}"}"

if [[ -z "$key" ]]; then
  echo "Empty key; aborting."
  exit 1
fi

if [[ "$key" != AIza* ]]; then
  echo "Warning: Google Gemini API keys usually start with \"AIza\". Continue only if this key is intentional."
fi

if [[ -f "$ENV_FILE" ]]; then
  cp -a "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
fi

tmp=$(mktemp)
if [[ -f "$ENV_FILE" ]]; then
  grep -v '^[[:space:]]*GEMINI_API_KEY=' "$ENV_FILE" >"$tmp" || true
else
  : >"$tmp"
fi
mv "$tmp" "$ENV_FILE"
printf 'GEMINI_API_KEY=%s\n' "$key" >>"$ENV_FILE"
chmod 600 "$ENV_FILE"
unset key

echo "Updated $ENV_FILE (mode 600). Timestamped backup: ${ENV_FILE}.bak.* (if file existed). Restarting gateway..."
if docker info >/dev/null 2>&1; then
  (cd "$OPENCLAW_COMPOSE_DIR" && docker compose up -d openclaw-gateway)
else
  (cd "$OPENCLAW_COMPOSE_DIR" && sudo docker compose up -d openclaw-gateway)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Done. Verify: $SCRIPT_DIR/check-web-access-env.sh"
