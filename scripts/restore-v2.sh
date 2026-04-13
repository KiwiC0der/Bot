#!/bin/bash
# NOVA V2 disaster-recovery bootstrap (run in WSL2 Ubuntu). Safe to re-run.
# Does not destroy data. Review before enabling NVIDIA/CUDA repos on unfamiliar systems.
set -euo pipefail

BOT_URL="${BOT_URL:-https://github.com/KiwiC0der/Bot.git}"
BOT_DIR="${BOT_DIR:-$HOME/Bot}"
OPENCLAW_ROOT="${OPENCLAW_ROOT:-$HOME/openclaw}"
OPENCLAW_DIR="$OPENCLAW_ROOT/openclaw"
MODELS=(mistral:7b-instruct phi3:mini nomic-embed-text:latest)

log() { echo "[restore-v2] $*"; }

ensure_pkg() {
  export DEBIAN_FRONTEND=noninteractive
  sudo apt-get update -y
  sudo apt-get install -y git curl ca-certificates build-essential
}

ensure_wsl_ubuntu() {
  if ! grep -qi microsoft /proc/version 2>/dev/null; then
    log "Warning: /proc/version does not look like WSL; continuing anyway."
  fi
}

ensure_clone_bot() {
  mkdir -p "$(dirname "$BOT_DIR")"
  if [[ ! -d "$BOT_DIR/.git" ]]; then
    git clone "$BOT_URL" "$BOT_DIR"
  else
    log "Bot repo exists at $BOT_DIR — skip clone"
  fi
}

ensure_clone_openclaw() {
  mkdir -p "$OPENCLAW_ROOT"
  if [[ ! -d "$OPENCLAW_DIR/.git" ]]; then
    git clone https://github.com/openclaw/openclaw.git "$OPENCLAW_DIR"
  else
    log "OpenClaw repo exists — skip clone"
  fi
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1; then
    docker info >/dev/null 2>&1 || log "docker present but daemon not reachable — start Docker Desktop / docker service"
    return 0
  fi
  log "Docker not in PATH. Install Docker Desktop (Windows) with WSL2 integration, or:"
  log "  https://docs.docker.com/engine/install/ubuntu/"
}

ensure_ollama() {
  if command -v ollama >/dev/null 2>&1; then
    :
  else
    log "Installing Ollama (curl | sh)…"
    curl -fsSL https://ollama.com/install.sh | sh || {
      log "Ollama install failed — install manually from https://ollama.com"
      return 0
    }
  fi
  for m in "${MODELS[@]}"; do
    ollama pull "$m" || log "pull failed for $m (retry later)"
  done
}

ensure_cuda_hint() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi || true
    log "NVIDIA driver visible. CUDA toolkit is optional for Ollama GPU; install from NVIDIA docs if you need nvcc."
  else
    log "nvidia-smi not found — GPU path may be unavailable in this environment."
  fi
}

start_openclaw() {
  if [[ ! -f "$OPENCLAW_DIR/docker-setup.sh" ]]; then
    log "No docker-setup.sh — skip OpenClaw start"
    return 0
  fi
  (
    cd "$OPENCLAW_DIR"
    export OPENCLAW_SANDBOX="${OPENCLAW_SANDBOX:-1}"
    if [[ -x ./docker-setup.sh ]]; then
      ./docker-setup.sh || log "docker-setup.sh exited non-zero — inspect logs"
    fi
  )
  for i in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:18789/healthz >/dev/null 2>&1; then
      log "OpenClaw gateway healthy on :18789"
      return 0
    fi
    sleep 3
  done
  log "Gateway health check failed — run: cd $OPENCLAW_DIR && docker compose ps"
}

main() {
  log "Starting idempotent restore (BOT_DIR=$BOT_DIR)"
  ensure_wsl_ubuntu
  ensure_pkg
  ensure_cuda_hint
  ensure_clone_bot
  ensure_ollama
  ensure_docker
  ensure_clone_openclaw
  start_openclaw
  log "Done. Next: configure secrets (see $BOT_DIR/docs/examples/nova-v2.env.example) and run:"
  log "  python3 $BOT_DIR/scripts/config.py apply-nova-v2"
}

main "$@"
