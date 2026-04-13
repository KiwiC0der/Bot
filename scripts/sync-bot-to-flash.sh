#!/bin/bash
# Sync ~/Bot to a second flash drive (cron example). Set PRIMARY and SECONDARY mount points.
# Crontab example (daily 3am):
#   0 3 * * * PRIMARY=/mnt/d SECONDARY=/mnt/e /home/you/Bot/scripts/sync-bot-to-flash.sh >>/tmp/nova-flash-sync.log 2>&1
set -euo pipefail
PRIMARY="${PRIMARY:?Set PRIMARY=/mnt/d (or your first flash mount)}"
SECONDARY="${SECONDARY:?Set SECONDARY=/mnt/e (or your second flash mount)}"
SRC="${SYNC_SRC:-$HOME/Bot}"

if [[ ! -d "$PRIMARY" ]] || [[ ! -d "$SECONDARY" ]]; then
  echo "Mounts missing: PRIMARY=$PRIMARY SECONDARY=$SECONDARY" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "Install rsync: sudo apt-get install -y rsync" >&2
  exit 1
fi

rsync -a --delete --exclude '.git/objects' --exclude '.chroma' "$SRC/" "$PRIMARY/Bot-backup/" 
rsync -a --delete "$PRIMARY/Bot-backup/" "$SECONDARY/Bot-backup/"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) sync complete"
