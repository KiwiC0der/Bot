#!/bin/bash
# Step 8 helpers: gateway latency + VRAM snapshot (run from WSL). Telegram steps are manual.
set -euo pipefail
export NOVA_BOT_ROOT="${NOVA_BOT_ROOT:-$HOME/Bot}"

echo "=== VRAM ==="
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi n/a"

echo "=== Gateway health ==="
if command -v curl >/dev/null 2>&1; then
  for i in 1 2 3; do
    curl -fsS -o /dev/null -w "try $i http_code=%{http_code} time_total_s=%{time_total}\n" http://127.0.0.1:18789/healthz || echo "curl failed"
  done
else
  echo "curl not installed"
fi

echo "=== Manual Telegram sequence (record model + latency per step) ==="
echo "1) /reset"
echo "2) ping"
echo "3) run python3 -c 'import datetime; print(datetime.date.today())'"
echo "4) read progress.md — report iteration from Nova"
echo "5) Judge: echo hello world (or invoke tools/judge.py)"
echo "After each step: nvidia-smi snapshot + note response time."
