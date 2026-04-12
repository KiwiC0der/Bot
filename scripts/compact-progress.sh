#!/bin/bash
# Trims progress.md to last 10 iteration entries to prevent context drift
PROGRESS="$HOME/Desktop/Bot/progress.md"
MAX_ENTRIES=10

if [ ! -f "$PROGRESS" ]; then
  echo "progress.md not found"
  exit 1
fi

# Count iteration headers
COUNT=$(grep -c "^## Iteration:" "$PROGRESS" 2>/dev/null || echo 0)

if [ "$COUNT" -le "$MAX_ENTRIES" ]; then
  echo "progress.md has $COUNT entries — no compaction needed"
  exit 0
fi

# Keep header + last MAX_ENTRIES iteration blocks
echo "Compacting progress.md: $COUNT → $MAX_ENTRIES entries"
HEADER="# Nova Progress Log"
TEMP=$(mktemp)

echo "$HEADER" > "$TEMP"
echo "" >> "$TEMP"
grep -n "^## Iteration:" "$PROGRESS" | tail -"$MAX_ENTRIES" | while IFS=: read -r linenum rest; do
  sed -n "${linenum},\$p" "$PROGRESS" | head -20 >> "$TEMP"
  echo "" >> "$TEMP"
done

mv "$TEMP" "$PROGRESS"
echo "Compaction done"
