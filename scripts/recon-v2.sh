#!/bin/bash
set -euo pipefail
OUT=~/Bot/recon-report.json
echo '{' > $OUT
echo '"timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",' >> $OUT
GPU=$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo 'not_detected')
echo '"gpu": "'"$GPU"'",' >> $OUT
RAM=$(free -h | awk '/^Mem/{print $2" total, "$7" available"}')
echo '"ram": "'"$RAM"'",' >> $OUT
DISK=$(df -h /mnt/c 2>/dev/null | awk 'NR==2{print $4" free of "$2}' || df -h ~ | awk 'NR==2{print $4" free of "$2}')
echo '"disk": "'"$DISK"'",' >> $OUT
CUDA=$(nvcc --version 2>/dev/null | grep release | awk '{print $6}' | tr -d ',' || echo 'not_installed')
echo '"cuda": "'"$CUDA"'",' >> $OUT
DOCKER=$(docker --version 2>/dev/null || echo 'not_installed')
echo '"docker": "'"$DOCKER"'",' >> $OUT
OLLAMA=$(ollama --version 2>/dev/null || echo 'not_installed')
MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | tr '\n' ',' || echo 'none')
echo '"ollama": "'"$OLLAMA"'",' >> $OUT
echo '"ollama_models": "'"$MODELS"'",' >> $OUT
FLASH=$(ls /mnt/ | grep -E '^[d-z]$' | tr '\n' ',' || echo 'none_detected')
echo '"flash_drives": "'"$FLASH"'",' >> $OUT
GIT_BRANCH=$(cd ~/Bot && git branch --show-current 2>/dev/null || echo 'unknown')
GIT_COMMITS=$(cd ~/Bot && git log --oneline | wc -l 2>/dev/null || echo '0')
echo '"git_branch": "'"$GIT_BRANCH"'",' >> $OUT
echo '"git_commits": '"$GIT_COMMITS"',' >> $OUT
PY=$(python3 --version 2>/dev/null || echo 'not_installed')
echo '"python": "'"$PY"'"' >> $OUT
echo '}' >> $OUT
echo 'Recon complete. Output:'
cat $OUT