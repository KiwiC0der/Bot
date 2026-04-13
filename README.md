# Bot — OpenClaw notes & runbooks

This repository holds **documentation and helper scripts** for operating OpenClaw (gateway, Telegram, email, voice, web tools). The OpenClaw application source lives separately (e.g. `~/openclaw/openclaw`).

**Security:** Do not commit real secrets. `~/openclaw/openclaw/email.env` holds SMTP and API keys—keep it `chmod 600` and out of version control. Use `scripts/set-gemini-key-openclaw.sh` to avoid putting keys in shell history.

## Docs

| Doc | Purpose |
|-----|---------|
| [OPENCLAW_KALI_DOCKER_RUNBOOK.md](./OPENCLAW_KALI_DOCKER_RUNBOOK.md) | Kali + Docker install and operations |
| [docs/WEB_ACCESS.md](./docs/WEB_ACCESS.md) | `web_search`, `web_fetch`, keys, disable switches |
| [AGENT_HARDENING_BACKLOG.md](./AGENT_HARDENING_BACKLOG.md) | Security / polish backlog |

## Scripts

| Script | Purpose |
|--------|---------|
| [scripts/config.py](./scripts/config.py) | Safe `openclaw.json` editor (backup + optional `docker compose … doctor --fix`); `apply-nova-v2` merge |
| [scripts/install-openclaw-wsl.sh](./scripts/install-openclaw-wsl.sh) | WSL: clone OpenClaw, `docker-setup.sh`, health check |
| [scripts/restore-v2.sh](./scripts/restore-v2.sh) | WSL idempotent recovery (Bot, Ollama models, OpenClaw) |
| [scripts/sync-bot-to-flash.sh](./scripts/sync-bot-to-flash.sh) | `rsync` `~/Bot` to two flash mount points (cron-friendly) |
| [scripts/smoke-v2.sh](./scripts/smoke-v2.sh) | Gateway + VRAM probes; prints Telegram smoke checklist |
| [scripts/recon-v2.sh](./scripts/recon-v2.sh) | JSON recon report to `~/Bot/recon-report.json` |
| [scripts/check-web-access-env.sh](./scripts/check-web-access-env.sh) | Print which web-related env vars are set (no network I/O) |
| [scripts/set-gemini-key-openclaw.sh](./scripts/set-gemini-key-openclaw.sh) | Prompt for `GEMINI_API_KEY`, write `~/openclaw/openclaw/email.env`, restart gateway |
| [scripts/fix-openclaw-compose-dotenv-perms.sh](./scripts/fix-openclaw-compose-dotenv-perms.sh) | If Compose errors on `.env` permission denied: `sudo chown` to your user (after root-owned `docker-setup.sh`) |

## Nova V2 env example

See [docs/examples/nova-v2.env.example](./docs/examples/nova-v2.env.example). Python deps: [requirements-nova.txt](./requirements-nova.txt).
