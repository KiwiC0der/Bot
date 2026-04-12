#!/usr/bin/env bash
# Non-destructive: only reports whether common OpenClaw web-related env vars are set.
# Does not call search or fetch APIs. Never prints secret values.

set -euo pipefail

vars=(
  BRAVE_API_KEY
  GEMINI_API_KEY
  XAI_API_KEY
  KIMI_API_KEY
  MOONSHOT_API_KEY
  PERPLEXITY_API_KEY
  OPENROUTER_API_KEY
  FIRECRAWL_API_KEY
)

report_vars() {
  for v in "${vars[@]}"; do
    if [[ -n "${!v:-}" ]]; then
      echo "  $v=set"
    else
      echo "  $v=(unset)"
    fi
  done
}

echo "Host shell (only what is exported here — often empty if keys live in Docker only):"
report_vars

# Optional: same check inside the running gateway (where web_search actually runs).
OPENCLAW_COMPOSE_DIR="${OPENCLAW_COMPOSE_DIR:-$HOME/openclaw/openclaw}"

# Use sudo when the current user cannot talk to the Docker socket (common on Kali before docker group).
compose_gateway_exec() {
  if docker info >/dev/null 2>&1; then
    (cd "$OPENCLAW_COMPOSE_DIR" && docker compose exec -T openclaw-gateway "$@")
  else
    (cd "$OPENCLAW_COMPOSE_DIR" && sudo docker compose exec -T openclaw-gateway "$@")
  fi
}

compose_gateway_ping() {
  if docker info >/dev/null 2>&1; then
    (cd "$OPENCLAW_COMPOSE_DIR" && docker compose exec -T openclaw-gateway true) >/dev/null 2>&1
  else
    (cd "$OPENCLAW_COMPOSE_DIR" && sudo docker compose exec -T openclaw-gateway true) >/dev/null 2>&1
  fi
}

if [[ -f "$OPENCLAW_COMPOSE_DIR/docker-compose.yml" ]] && command -v docker >/dev/null 2>&1; then
  vars_csv=$(IFS=,; echo "${vars[*]}")
  # shellcheck disable=SC2016
  inner='for v in $(echo "$0" | tr "," " "); do eval "x=\${$v-}"; if [ -n "$x" ]; then echo "  $v=set"; else echo "  $v=(unset)"; fi; done'
  using_sudo=""
  docker info >/dev/null 2>&1 || using_sudo="sudo "

  if compose_gateway_ping; then
    echo ""
    echo "Gateway container openclaw-gateway (${using_sudo}docker compose; $OPENCLAW_COMPOSE_DIR):"
    compose_gateway_exec sh -lc "$inner" "$vars_csv"
  else
    echo ""
    echo "Gateway container: could not exec into openclaw-gateway. Typical causes:"
    echo "  - stack not running: cd \"$OPENCLAW_COMPOSE_DIR\" && sudo docker compose up -d openclaw-gateway"
    echo "  - wrong path: OPENCLAW_COMPOSE_DIR=/path/to/openclaw ./scripts/check-web-access-env.sh"
    echo "  - Docker permission: sudo docker works; or add your user to group 'docker' and re-login"
  fi
else
  echo ""
  echo "Skipping container check: no docker or missing $OPENCLAW_COMPOSE_DIR/docker-compose.yml"
fi

echo ""
echo "Tip: stock OpenClaw compose loads ./email.env into the gateway. Add GEMINI_API_KEY / BRAVE_API_KEY / etc., or use scripts/set-gemini-key-openclaw.sh for Gemini. Then: sudo docker compose up -d openclaw-gateway"
echo "Hardening: chmod 600 email.env; never commit it; pin tools.web.search.provider:\"gemini\" if you use Gemini and might add Brave later."
