# OpenClaw (Clawbot) on Kali Linux (HP Laptop): Docker-First, Sandbox-Hardened Runbook

This guide installs and operates **OpenClaw (Clawbot)** on **Kali Linux (Debian-based)** with a strong emphasis on **sandboxing** and **safety**.

It follows OpenClaw’s current docs and avoids inventing CLI flags or undocumented behaviors.

## Assumptions

- Kali Linux with `sudo` configured (non-root daily user).
- You want **Docker isolation**.
- You want **Telegram** integration (Bot API).
- Model provider is **undecided** (you’ll choose OpenAI or Anthropic during onboarding; optional Ollama noted).

## Security posture (read this first)

- **Primary risk** is not “exploits” — it’s giving a tool-capable agent too much access. Start tight, widen only when needed.
- Prefer **two layers**:
  - **Containerized Gateway**: OpenClaw itself runs inside Docker (isolation from host).
  - **Tool sandboxing**: OpenClaw runs tools (exec/file edits) inside per-session Docker sandboxes to reduce blast radius.
- Keep tokens out of shell history:
  - Avoid pasting secrets into your terminal when possible.
  - Prefer environment variables or OpenClaw SecretRefs when supported by your flow.

---

## Phase 0 — Preflight

### 0.1 Confirm you’re a non-root user

```bash
id
whoami
groups
```

Expected: your user is **not** `root`, and `sudo` works.

```bash
sudo -v
```

### 0.2 Create a dedicated working directory

Pick a directory that is *not* synced to cloud storage and *not* a git repo that you push publicly.

```bash
mkdir -p "$HOME/openclaw"
cd "$HOME/openclaw"
```

---

## Phase 1 — Kali environment hardening + dependencies

This phase focuses on safe updates + Docker Engine + Compose v2. (Node.js is optional for the Docker gateway flow, but included for completeness and for any future host CLI usage.)

### 1.1 Update Kali safely (apt hygiene)

On Kali, prefer `full-upgrade` to avoid partial upgrades in a rolling distro.

```bash
sudo apt update
sudo apt -y full-upgrade
```

Optional cleanup:

```bash
sudo apt -y autoremove --purge
```

### 1.2 Install base tooling

```bash
sudo apt install -y git curl ca-certificates build-essential
```

### 1.3 Install Docker Engine + Compose v2 (official Debian repo method)

This follows Docker’s official Debian instructions, with the **Kali derivative** note: if `VERSION_CODENAME` doesn’t map cleanly, you may need to substitute a Debian codename (commonly `bookworm`).

#### 1.3.1 Remove conflicting packages (if present)

From Docker’s Debian guide:

```bash
sudo apt remove $(dpkg --get-selections docker.io docker-compose docker-doc podman-docker containerd runc | cut -f1)
```

#### 1.3.2 Add Docker’s apt repo + keyring

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Add the repository. First, check what Kali reports:

```bash
. /etc/os-release && echo "$VERSION_CODENAME"
```

If that prints nothing useful for Docker’s Debian repository, substitute a Debian codename explicitly (often `bookworm` on modern Kali).

```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: bookworm
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Then:

```bash
sudo apt update
```

#### 1.3.3 Install Docker packages

```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Start Docker and verify:

```bash
sudo systemctl enable --now docker
sudo systemctl status docker --no-pager
```

#### 1.3.4 Verify Docker works

```bash
sudo docker run --rm hello-world
```

Expected: a success message confirming Docker can run containers.

#### 1.3.5 Optional: allow running Docker without sudo

This is convenient, but note it effectively grants root-equivalent power through the Docker daemon. If you want maximum safety, skip this and keep using `sudo docker ...`.

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker version
docker compose version
```

### 1.4 Optional: Node.js 24 (recommended by OpenClaw; Node 22.16+ supported)

If you only run the **Docker gateway**, Node is already in the container image. Install Node on the host only if you plan to use the host CLI or build from source outside Docker.

OpenClaw docs show a NodeSource-based Debian/Ubuntu method:

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v
```

Expected: `node -v` prints `v24.x.x` (recommended) or `v22.16+` (supported).

---

## Phase 2 — Core OpenClaw installation (Docker-first)

OpenClaw’s Docker docs provide a repo-root script that sets up Compose and bootstraps onboarding.

### 2.1 Clone OpenClaw

```bash
cd "$HOME/openclaw"
git clone https://github.com/openclaw/openclaw.git
cd openclaw
```

### 2.2 Run the Docker setup script (recommended path)

Optional: if you want OpenClaw to also bootstrap **agent tool sandboxing** (tools run in additional Docker sandbox containers), enable it before setup:

```bash
export OPENCLAW_SANDBOX=1
```

If your Docker socket path is non-standard (for example rootless Docker), set it explicitly:

```bash
export OPENCLAW_DOCKER_SOCKET=/run/user/1000/docker.sock
```

```bash
./docker-setup.sh
```

What this does (per docs):

- Builds (or pulls) the gateway image
- Starts the gateway via Docker Compose
- Generates a gateway token and writes it to `.env`
- Runs onboarding

### 2.3 Open the Dashboard / Control UI link again (later)

```bash
docker compose run --rm openclaw-cli dashboard --no-open
```

Then open the printed URL in your browser.

### 2.4 Verify gateway health (no auth required)

From the Docker doc:

```bash
curl -fsS http://127.0.0.1:18789/healthz
curl -fsS http://127.0.0.1:18789/readyz
```

Expected: both commands succeed (exit code 0). `readyz` may temporarily return `503` during initial startup and channel grace periods.

### 2.5 Verify the CLI in Docker

```bash
docker compose run --rm openclaw-cli -V
docker compose run --rm openclaw-cli doctor
docker compose run --rm openclaw-cli status
```

---

## Phase 3 — Onboarding, model provider setup, and token hygiene

### 3.1 Run onboarding explicitly (Docker)

If you need to rerun onboarding:

```bash
docker compose run --rm openclaw-cli onboard
```

### 3.2 Choose a model provider (OpenAI or Anthropic)

You’ll set provider credentials during onboarding or with the models/auth helpers.

#### OpenAI (API key)

From OpenClaw’s OpenAI provider docs:

```bash
# interactive (choose OpenAI API key)
docker compose run --rm openclaw-cli onboard --auth-choice openai-api-key

# non-interactive (expects OPENAI_API_KEY to be set in the environment you run this from)
docker compose run --rm openclaw-cli onboard --openai-api-key "$OPENAI_API_KEY"
```

#### OpenAI (Codex / ChatGPT sign-in)

If you prefer OAuth (subscription) instead of an API key:

```bash
docker compose run --rm openclaw-cli onboard --auth-choice openai-codex
```

#### Anthropic (API key)

From OpenClaw’s Anthropic provider docs:

```bash
# interactive (choose Anthropic API key)
docker compose run --rm openclaw-cli onboard

# non-interactive
docker compose run --rm openclaw-cli onboard --anthropic-api-key "$ANTHROPIC_API_KEY"
```

#### Anthropic (Claude setup-token / subscription)

From OpenClaw’s Anthropic provider docs:

```bash
# Generate a setup-token with the Claude CLI (on any machine with claude installed)
claude setup-token

# Then, on the gateway host, add it to OpenClaw auth
docker compose run --rm openclaw-cli models auth setup-token --provider anthropic
```

Useful verification commands (from CLI docs):

```bash
docker compose run --rm openclaw-cli models status
docker compose run --rm openclaw-cli models list --json
```

If you configure auth profiles, `models status --probe` can do live probes (may consume tokens and trigger rate limits):

```bash
docker compose run --rm openclaw-cli models status --probe
```

#### Secret handling note (recommended)

Onboarding supports storing keys as **SecretRefs** instead of plaintext in config/auth profiles.
From the CLI onboarding docs:

- `--secret-input-mode ref` (non-interactive) stores env-backed refs in auth profiles instead of plaintext key values.
- In that mode, the provider env var must be set (for example `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).

### 3.3 Optional: Ollama (local-first)

If you want full local execution, OpenClaw supports an Ollama provider. Use OpenClaw’s provider docs to avoid mismatched base URLs/models:

- `https://docs.openclaw.ai/providers/ollama.md`

At minimum, verify your local Ollama endpoint is reachable before pointing OpenClaw at it.

### 3.4 Secure the Gateway token and local state

Key guidance from OpenClaw security docs:

- Run audits regularly:

```bash
docker compose run --rm openclaw-cli security audit
docker compose run --rm openclaw-cli security audit --deep
docker compose run --rm openclaw-cli security audit --fix
```

- Treat `~/.openclaw` as sensitive (contains sessions, credentials, tokens, logs). Lock down permissions on the host user that owns those directories.

Note: in the Docker flow, OpenClaw bind-mounts host paths under `~/.openclaw/` and `~/.openclaw/workspace/` (see Docker docs). Protect them accordingly.

---

## Phase 4 — Telegram integration (BotFather + pairing)

OpenClaw’s Telegram channel is production-ready for DMs + groups.

### 4.1 Create a bot token with @BotFather

1. In Telegram, open chat with **`@BotFather`** (verify the handle).
2. Run `/newbot`.
3. Follow the prompts and save the token.

### 4.2 Configure Telegram in OpenClaw

Telegram does **not** use `openclaw channels login telegram`. You configure the bot token via config (or env fallback for the default account).

Minimal config shape from Telegram docs:

```json5
{
  channels: {
    telegram: {
      enabled: true,
      botToken: "123:abc",
      dmPolicy: "pairing",
      groups: { "*": { requireMention: true } },
    },
  },
}
```

If you prefer env fallback (default account only):

- `TELEGRAM_BOT_TOKEN=...`

### 4.3 Start gateway and approve your first DM (pairing)

Start gateway (Docker):

```bash
docker compose up -d openclaw-gateway
```

Then DM your bot in Telegram. Approve the pairing request:

```bash
docker compose run --rm openclaw-cli pairing list telegram
docker compose run --rm openclaw-cli pairing approve telegram <CODE>
```

Pairing codes expire after 1 hour.

### 4.4 Verify Telegram send works

If you know your chat ID or username:

```bash
docker compose run --rm openclaw-cli message send \
  --channel telegram \
  --target <chatId_or_username> \
  --message "hi"
```

### 4.5 Find your Telegram user ID (for allowlists)

Telegram docs recommend a “no third-party bot” approach:

1. Follow gateway logs.
2. DM your bot.
3. Read `from.id` in the inbound log line.

```bash
docker compose run --rm openclaw-cli logs --follow
```

Official Bot API alternative:

```bash
curl "https://api.telegram.org/bot<bot_token>/getUpdates"
```

### 4.6 Telegram group notes (privacy mode + mentions)

- By default, bots may not see all group messages due to Telegram Privacy Mode.
- If you set `requireMention=false` and expect the bot to see all group traffic:
  - consider making the bot a group admin, or
  - disable privacy mode in BotFather (`/setprivacy`), then remove + re-add the bot to the group.

For network instability / DNS/IPv6 issues, see Troubleshooting below.

### 4.7 Telegram voice notes (free, local STT quick-enable)

If you want to send voice notes to your Telegram bot and have OpenClaw process them, enable audio media understanding in your live config:

```json5
{
  tools: {
    media: {
      audio: {
        enabled: true,
        echoTranscript: true, // optional: send recognized transcript back to chat
      },
    },
  },
}
```

Why this works:

- OpenClaw handles inbound Telegram voice/audio and can transcribe before agent reply.
- Audio preflight mention checks are supported for mention-gated groups (`requireMention: true`).
- `echoTranscript` is off by default; turn it on during setup so you can verify recognition quality quickly.

Local/free path (recommended):

- The **gateway container** must contain a local STT binary (typically `whisper-cli` from whisper.cpp, or Python `whisper`).
- OpenClaw auto-detects `whisper-cli` / `whisper` on `PATH` when `tools.media.audio.enabled` is not `false`.
- If neither exists inside the container, voice notes will **not** transcribe (text DMs may still work).

Sanity checks (host):

```bash
# Gateway port + HTTP stack OK (use a colon: 127.0.0.1:18789 — not 127.0.0.1.18789)
curl -fsS http://127.0.0.1:18789/healthz

# STT present inside the running gateway image?
cd "$HOME/openclaw/openclaw"
sudo docker compose exec openclaw-gateway sh -lc 'command -v whisper-cli || command -v whisper || echo NO_STT_CLI'
```

If you see `NO_STT_CLI`, rebuild the local image with whisper.cpp (see below).

**OpenRouter / non-audio primary model:** If your default chat model is a text-only provider, OpenClaw’s **auto** audio path may still try provider-based transcription first and never reach `whisper-cli`. Fix: set `tools.media.audio.models` to a **`whisper-cli` CLI entry** (see OpenClaw `resolveLocalWhisperCppEntry` args: `-m <ggml-file> -otxt -of {{OutputBase}} -np -nt {{MediaPath}}`). The `-m` path must match the file inside the container (same as `echo $WHISPER_CPP_MODEL` in `docker compose exec openclaw-gateway sh -lc 'echo $WHISPER_CPP_MODEL'`).

Logs CLI note:

- `openclaw-cli logs` supports **`--limit`** (max lines), not `--tail`.
- Example: `sudo docker compose run --rm openclaw-cli logs --limit 30`
- Long `logs --follow` runs can show WebSocket `handshake timeout` in gateway logs during restarts; that is usually the **tail client**, not proof the gateway port is wrong. Prefer `curl` health checks + `docker compose logs openclaw-gateway` when debugging.

Durable image: whisper.cpp inside `openclaw:local` (recommended for Docker)

From your OpenClaw source tree, rebuild the image with the optional Dockerfile layer (compiles `whisper-cli` and downloads the English `base.en` ggml model):

```bash
cd "$HOME/openclaw/openclaw"
sudo docker build -t openclaw:local \
  --build-arg OPENCLAW_INSTALL_WHISPER_CPP=1 \
  .
sudo docker compose up -d openclaw-gateway
```

Note: this rebuild compiles `whisper-cli` with FFmpeg support so it can decode Telegram voice-note formats (usually OGG/Opus).

Optional: different model size (faster vs more accurate), e.g. `tiny.en`:

```bash
sudo docker build -t openclaw:local \
  --build-arg OPENCLAW_INSTALL_WHISPER_CPP=1 \
  --build-arg OPENCLAW_WHISPER_CPP_MODEL=tiny.en \
  .
```

Then confirm:

```bash
sudo docker compose exec openclaw-gateway sh -lc 'command -v whisper-cli && echo "WHISPER_CPP_MODEL=$WHISPER_CPP_MODEL"'
```

Quick verification:

```bash
cd "$HOME/openclaw/openclaw"
sudo docker compose restart openclaw-gateway
until curl -fsS http://127.0.0.1:18789/healthz >/dev/null; do sleep 1; done
sudo docker compose run --rm openclaw-cli logs --limit 40
```

Then send a Telegram voice note to your bot. Expected behavior:

1. transcript appears in logs (and in chat if `echoTranscript: true`)
2. OpenClaw replies normally to the transcribed text

Mention-gated groups note:

- For groups with `requireMention: true`, voice preflight is enabled by default.
- If needed, you can disable it per group/topic with:
  - `channels.telegram.groups.<chatId>.disableAudioPreflight: true`
  - `channels.telegram.groups.<chatId>.topics.<threadId>.disableAudioPreflight: true`

### 4.8 Email sending (SMTP or SendGrid-like API, safe confirmation)

OpenClaw now includes a core tool named `email` (owner-only). It can send:

- Via local `SMTP` (with STARTTLS or SSL)
- Via a `SendGrid/SES-like` HTTP `POST` API (API-key + Bearer-style auth)

Safety model (important):

- The tool requires `confirm=true` to actually send.
- It also enforces a recipient allowlist if you configure it.

Prerequisite: install `python3` in the OpenClaw runtime image

Rebuild your local image with `python3` included:

```bash
cd "$HOME/openclaw/openclaw"
sudo docker build -t openclaw:local \
  --build-arg OPENCLAW_INSTALL_WHISPER_CPP=1 \
  --build-arg OPENCLAW_DOCKER_APT_PACKAGES="python3" \
  .
sudo docker compose up -d openclaw-gateway
```

Configure environment variables (for the gateway container)

Allowlist (recommended):

- `EMAIL_ALLOWLIST_DOMAINS` (comma-separated, e.g. `example.com,contoso.com`)
- `EMAIL_ALLOWLIST_EMAILS` (comma-separated, e.g. `a@example.com,b@example.com`)

SMTP (example variables):

- `EMAIL_SMTP_HOST`
- `EMAIL_SMTP_PORT` (default `587`)
- `EMAIL_SMTP_USERNAME`
- `EMAIL_SMTP_PASSWORD`
- `EMAIL_SMTP_USE_STARTTLS` (default `true`)
- `EMAIL_SMTP_USE_SSL` (default `false`)

API (example variables):

- `EMAIL_API_ENDPOINT` (e.g. `https://api.sendgrid.com/v3/mail/send`)
- `EMAIL_API_KEY`
- `EMAIL_API_AUTH_SCHEME` (default `Bearer`)

Sender identity:

- `EMAIL_FROM_EMAIL` (optional if you pass `fromEmail` to the tool)
- `EMAIL_FROM_NAME` (optional if you pass `fromName` to the tool)

Attachments limits:

- `EMAIL_MAX_ATTACHMENTS` (default `5`)
- `EMAIL_MAX_ATTACHMENT_BYTES` (default `10000000`)

Quick local test (dry-run)

This validates payload/recipients/attachments without needing SMTP/API env:

```bash
python3 "$HOME/openclaw/openclaw/skills/email-sender/scripts/send_email.py" <<'EOF'
{"provider":"smtp","fromEmail":"sender@example.com","to":["rcpt@example.com"],"subject":"Test","text":"Hello","dryRun":true}
EOF
```

First chat test with Nova:

1. Ask Nova to send a simple email (no attachments yet).
2. On the first attempt, the tool returns a confirmation preview.
3. Reply with explicit confirmation (so Nova re-runs with `confirm=true`).

#### Telegram: “email tool not available” / model says it can’t use `email`

The `email` tool is **owner-only**. OpenClaw only exposes it to the model when **`senderIsOwner`** is true for that inbound message. If your bot accepts DMs from anyone (`channels.telegram.allowFrom` empty / open), **no sender is treated as owner** until you declare who the owner is.

**Fix (recommended):** set a global owner allowlist (channel-native IDs; Telegram user id is numeric):

```json5
{
  commands: {
    ownerAllowFrom: ["telegram:6069715107"], // owner Telegram user id (owner-only tools, e.g. email)
  },
}
```

You can also use the bare id if you prefer (`"6069715107"`); OpenClaw normalizes Telegram allow-from entries (lowercase, optional `telegram:` / `tg:` prefix stripped during matching).

**Still required for the tool to appear in the allowlisted tool set:**

- `tools.profile` that includes `email` (e.g. coding profile + `tools.alsoAllow: ["email"]`), or equivalent per-channel tool policy — same as any other gated tool.

**Alternative (different semantics):** put **only** your user id in `channels.telegram.allowFrom`. That both restricts who can message the bot **and** makes you the command/owner candidate for that channel. Use this only if you want a closed bot, not a public one.

After editing config, restart the gateway (or apply config reload if you use it), then **`/reset`** in Telegram so the session doesn’t keep stale assumptions.

---

## Phase 5 — Skills, sandboxing, and “don’t rm -rf my machine” guardrails

This phase is about **limiting damage if the model makes a mistake**.

### 5.1 Tool policy: deny high-risk control-plane tools by default

From OpenClaw’s security guidance, deny control-plane tools on any surface that might see untrusted messages.

The docs’ baseline recommendation includes denying:

- `gateway` (can apply config/updates)
- `cron` (persistent background jobs)
- `sessions_spawn`, `sessions_send` (cross-session control surfaces)

Implementing this is a config change; run `openclaw security audit` afterward to confirm you didn’t open a network surface accidentally.

### 5.2 Enable tool sandboxing (Docker-backed) to isolate exec/files

OpenClaw can run tools inside Docker sandboxes when `agents.defaults.sandbox` is enabled.

Key hardening knobs (from sandboxing docs):

- `mode`: `off | non-main | all`
- `scope`: `session` (strongest isolation) or `agent`
- `workspaceAccess`: `none` baseline (don’t mount your real workspace)
- Docker runtime hardening:
  - `readOnlyRoot: true`
  - `capDrop: ["ALL"]`
  - `network: "none"` (opt-in only)
  - resource limits (`memory`, `cpus`, `pidsLimit`, `ulimits`)

Minimal enable example from docs:

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "non-main",
        scope: "session",
        workspaceAccess: "none",
      },
    },
  },
}
```

#### Safe container profile (recommended starting point)

This mirrors the sandboxing docs’ hardening knobs (tight defaults; opt in to more access only when you need it):

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "non-main", // off | non-main | all
        scope: "session", // session | agent | shared
        backend: "docker",
        workspaceAccess: "none", // none | ro | rw
        docker: {
          image: "openclaw-sandbox:bookworm-slim",
          workdir: "/workspace",
          readOnlyRoot: true,
          tmpfs: ["/tmp", "/var/tmp", "/run"],
          network: "none",
          user: "1000:1000",
          capDrop: ["ALL"],
          pidsLimit: 256,
          memory: "1g",
          memorySwap: "2g",
          cpus: 1,
          ulimits: {
            nofile: { soft: 1024, hard: 2048 },
            nproc: 256,
          },
          env: { LANG: "C.UTF-8" },
        },
        prune: { idleHours: 24, maxAgeDays: 7 },
      },
    },
  },
  tools: {
    sandbox: {
      tools: {
        // deny always wins; if allow is non-empty, only allowlisted tools are available (minus deny)
        allow: ["exec", "process", "read", "write", "edit"],
        deny: ["browser", "canvas", "nodes", "cron", "gateway"],
      },
    },
  },
}
```

To debug what’s actually effective:

```bash
docker compose run --rm openclaw-cli sandbox explain
docker compose run --rm openclaw-cli sandbox list
```

If you change sandbox Docker settings and need to force recreation:

```bash
docker compose run --rm openclaw-cli sandbox recreate
```

### 5.3 Check skills readiness

```bash
docker compose run --rm openclaw-cli skills check
docker compose run --rm openclaw-cli skills list
```

---

## 24/7 operation (persistence)

### Docker gateway persistence

- Use Docker Compose to keep the gateway up.
- Consider adding a restart policy in Compose (`restart: unless-stopped`) if your Compose stack doesn’t already.
- Use the documented health endpoints for external watchdogs:

```bash
curl -fsS http://127.0.0.1:18789/healthz
curl -fsS http://127.0.0.1:18789/readyz
```

### Logs

From CLI docs:

```bash
docker compose run --rm openclaw-cli logs --follow
```

### Host install persistence (systemd user unit)

If you install OpenClaw on the host (non-Docker) instead of containerizing the gateway, OpenClaw’s onboarding can install a Linux systemd **user** unit:

```bash
openclaw onboard --install-daemon
```

Onboarding docs note that the daemon step installs a systemd user unit (Linux/WSL2) and validates required gateway auth/token settings before installing.

---

## Troubleshooting (Kali-focused)

### Kali upgrades / broken deps after `full-upgrade`

Common recovery steps:

```bash
sudo apt -f install
sudo dpkg --configure -a
sudo apt update
sudo apt -y full-upgrade
```

### Docker install issues on Kali derivative

- If Docker’s repo setup using `$(. /etc/os-release && echo "$VERSION_CODENAME")` doesn’t work on Kali, use a Debian codename explicitly (commonly `bookworm`) in the `.sources` file.
- Ensure Docker is running:

```bash
sudo systemctl status docker --no-pager
```

- If you can’t run Docker without sudo:
  - either keep using `sudo docker ...`, or
  - add your user to the `docker` group (see Phase 1.3.5) and log out/in.

### Docker + firewall quirks (Kali)

Docker’s docs warn that Docker is compatible with `iptables-nft` and `iptables-legacy`, but not with raw `nft` rulesets. If you use a firewall on Kali, prefer managing rules with `iptables`/`ip6tables` and put policy in the `DOCKER-USER` chain.

### Ports or “can’t open dashboard”

- Confirm the gateway is up and listening:

```bash
curl -v http://127.0.0.1:18789/healthz
```

- If another service is bound to `18789`, stop it or change OpenClaw’s bind/port (use OpenClaw’s config reference; don’t guess).

### Telegram: bot doesn’t respond

- Follow logs:

```bash
docker compose run --rm openclaw-cli logs --follow
```

- Verify pairing is approved:

```bash
docker compose run --rm openclaw-cli pairing list telegram
```

### Telegram: DNS/IPv6 weirdness

Telegram docs call out IPv6/egress and DNS-family selection issues. Quick checks:

```bash
dig +short api.telegram.org A
dig +short api.telegram.org AAAA
```

If your network has broken IPv6 egress, you may need to force IPv4-first behavior using the channel’s network config (see the Telegram troubleshooting section in OpenClaw docs).

---

## Final security checklist

Run these after setup and after any config change:

```bash
docker compose run --rm openclaw-cli security audit --deep
```

Keep these defaults unless you explicitly need otherwise:

- **Gateway not publicly exposed**: prefer `gateway.mode=local` and safe bind behavior; avoid public exposure.
- **DM access control**: keep `dmPolicy: "pairing"` or explicit allowlists.
- **DM session isolation if multiple people can DM**: consider `session.dmScope: "per-channel-peer"` (prevents cross-user context bleed).
- **Sandbox by default**: use Docker sandboxing for tools; keep sandbox `network: "none"` unless required.
- **Minimize plugins/extensions**: treat plugin installs as trusted code.
- **Protect state on disk**: lock down permissions for `~/.openclaw` (sessions, credentials, tokens).
