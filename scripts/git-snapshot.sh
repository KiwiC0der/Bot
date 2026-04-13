#!/bin/bash
MSG="${1:-auto-snapshot before self-modification}"
cd ~/Bot
git add -A
git commit -m "snapshot: $MSG [$(date -u +%Y-%m-%dT%H:%M:%SZ)]" || echo "Nothing to commit"
