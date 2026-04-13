# Nova Progress Log

## V2 hardware baseline
Hardware: RTX 3060 12GB | Actor: ollama/mistral:7b-instruct | Judge: ollama/phi3:mini (tools/judge.py)

## Iteration: 0
## Last updated: 2026-04-12
## Current goal: Complete NOVA V2.0 initial build (OpenClaw + local Ollama + Chroma memory)
## Last attempt: Repo deliverables: scripts/config.py, memory.py, restore-v2.sh, path migration to ~/Bot
## Last failure reason: N/A (Cursor agent environment: WSL/bash not available here — run recon + install scripts on your machine)
## Sub-agents registered: none
## Iteration count: 0

## Step 1 validation note
Run `~/Bot/scripts/recon-v2.sh` in WSL and confirm: CUDA, Docker, Ollama models (`mistral:7b-instruct`, `phi3:mini`, `nomic-embed-text:latest`), `/mnt/*` flash mounts. This workspace could not execute WSL from automation.
