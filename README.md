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
| [scripts/check-web-access-env.sh](./scripts/check-web-access-env.sh) | Print which web-related env vars are set (no network I/O) |
| [scripts/set-gemini-key-openclaw.sh](./scripts/set-gemini-key-openclaw.sh) | Prompt for `GEMINI_API_KEY`, write `~/openclaw/openclaw/email.env`, restart gateway |
