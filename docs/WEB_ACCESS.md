# Web access for OpenClaw (search + fetch + browser)

OpenClaw ships **first-party web tools** in the gateway runtime. You do **not** add a separate Node/Python module in this repo for basic search/fetch—the agent calls:

| Tool | Role | Typical use |
|------|------|-------------|
| `web_search` | Search APIs (Brave, Gemini, Grok, Kimi, Perplexity, Firecrawl search) | Current docs, versions, CVEs, “what is X” |
| `web_fetch` | HTTP(S) fetch + readable extraction (optional Firecrawl) | Pull a specific URL after you have a link |
| `browser` | Full browser automation (separate stack; heavier) | Sites that need JS rendering, complex flows |

All outbound HTTP for `web_search` / `web_fetch` goes through OpenClaw’s **guarded fetch** path (SSRF protections, timeouts, size limits)—not arbitrary shell `curl`.

**Upstream reference:** [OpenClaw web tools](https://docs.openclaw.ai/tools/web)

---

## Free / low-cost options (skip Brave)

OpenClaw does **not** ship a “totally unlimited, no-signup” web search. Practical choices:

### A) Gemini + Google Search grounding (usual “free tier” path)

1. Open [Google AI Studio](https://aistudio.google.com/) (Google account).
2. Create an **API key** for the Gemini API (free quotas apply; limits and availability are set by Google and can change).
3. Put the key in the gateway env file your Compose uses (stock setup: `~/openclaw/openclaw/email.env`):
   ```bash
   GEMINI_API_KEY=your_key_here
   ```
4. **Pin the provider** so OpenClaw does not prefer Brave when you add other keys later:
   ```json5
   tools: {
     web: {
       search: {
         enabled: true,
         provider: "gemini",
       },
     },
   },
   ```
5. Restart the gateway: `cd ~/openclaw/openclaw && sudo docker compose up -d openclaw-gateway`.

Auto-detection: if **only** `GEMINI_API_KEY` is set (no `BRAVE_API_KEY`), OpenClaw selects Gemini without needing `provider`.

### B) No search API — use `web_fetch` only

- **Cost:** free (HTTP only; no search provider).
- **Limitation:** the model must already have a **URL** (you paste a link, or it uses a URL from context). It cannot “discover” the whole web without search.
- Disable search if you want: `tools.web.search.enabled: false` and keep `tools.web.fetch.enabled: true`.

### C) Brave (for context)

OpenClaw’s docs note Brave Search includes **monthly free API credit** on their plan, then paid usage—see [Brave Search API](https://brave.com/search/api/). If you want **zero Brave account**, use **Gemini (A)** or **fetch-only (B)**.

---

## 1) Enable / disable

### Search + fetch (config)

```json5
{
  tools: {
    web: {
      search: {
        enabled: true, // set false to drop web_search entirely
        // provider: "brave", // optional; auto from env keys if omitted
      },
      fetch: {
        enabled: true, // set false to drop web_fetch
        maxChars: 50000,
        timeoutSeconds: 30,
        readability: true,
        firecrawl: {
          enabled: true, // optional; needs FIRECRAWL_API_KEY when enabled
        },
      },
    },
  },
}
```

### Deny the whole “web” tool group + browser (policy)

`group:web` expands to core tools in the **Web** section (includes `web_search` and `web_fetch`). `browser` is separate.

```json5
{
  tools: {
    deny: ["group:web", "browser"],
  },
}
```

Use this on surfaces that must not call the public internet, or when debugging with a small model (see `openclaw security audit` guidance).

### Tool profile

The **coding** profile includes `web_search` and `web_fetch`. If you use a minimal/messaging profile, add them explicitly, e.g. `tools.alsoAllow: ["web_search", "web_fetch"]` (and ensure `tools.deny` does not block them).

---

## 2) API keys and environment variables

Keys can live in **gateway environment** (Docker env files, systemd, etc.) or in **config** (`tools.web.search.*.apiKey`) / OpenClaw secrets—prefer env + least privilege.

### Stock OpenClaw `docker-compose.yml` (important)

The `openclaw-gateway` service uses `env_file: ./email.env` (same for `openclaw-cli`). **Web API keys must appear in a file that Compose actually loads into that service**—for this layout, that usually means **adding lines to `~/openclaw/openclaw/email.env`**, then recreating the gateway:

```bash
cd "$HOME/openclaw/openclaw"
sudo docker compose up -d openclaw-gateway
```

`compose.env` (or `.env` used only for Compose variable substitution) does **not** automatically inject `BRAVE_API_KEY` into the container unless you also reference it under `environment:` or add another `env_file` entry.

Optional cleaner split: create `web.env` with `BRAVE_API_KEY=...` and add `- ./web.env` under `env_file` for `openclaw-gateway` (edit `docker-compose.yml` once).

| Purpose | Common env vars |
|--------|------------------|
| Brave (default-friendly) | `BRAVE_API_KEY` |
| Google / Gemini grounding | `GEMINI_API_KEY` |
| xAI Grok | `XAI_API_KEY` |
| Kimi / Moonshot | `KIMI_API_KEY` or `MOONSHOT_API_KEY` |
| Perplexity / OpenRouter | `PERPLEXITY_API_KEY` or `OPENROUTER_API_KEY` |
| Firecrawl (fetch and/or search) | `FIRECRAWL_API_KEY` |

Wizard shortcut (on a machine with CLI):

```bash
openclaw configure --section web
```

Docker: add the same variables to the file your `docker compose` uses (often `compose.env` next to OpenClaw’s `docker-compose.yml`), then recreate/restart the gateway container.

---

## 3) Domain allowlists (expectations)

OpenClaw’s `web_fetch` does **not** expose a simple `WEB_ALLOWED_DOMAINS` knob in config. Control surface is:

- **Disable** `web_fetch` or `group:web` when you do not want arbitrary URLs.
- Rely on **built-in SSRF / redirect limits** (see upstream implementation).
- For **hard** domain allowlists, you’d need a custom gateway proxy or a plugin—out of scope for stock OpenClaw.

---

## 4) Agent behavior (prompt / instructions)

Add short instructions to your agent’s system prompt or `AGENTS.md` (whatever your setup uses):

- Use **`web_search`** for open-ended or time-sensitive facts; keep queries short.
- Use **`web_fetch`** only when you already have a **specific HTTPS URL** (docs page, release notes).
- **Do not** paste secrets, tokens, or proprietary code into queries or URLs.
- **Summarize** results; name sources; say when uncertain.

---

## 5) Verification

### Env sanity (host + optional Docker)

From this repo:

```bash
./scripts/check-web-access-env.sh
```

The first block is your **interactive shell** only. If keys are in `compose.env` for Docker, they will still show `(unset)` there until you **export** them on the host—which you usually should **not** do. When the `openclaw-gateway` container is up, the script also prints **set/unset inside the container** (still no secret values). Override the compose path with `OPENCLAW_COMPOSE_DIR=/path/to/openclaw`.

### Runtime (Docker)

```bash
cd "$HOME/openclaw/openclaw"
sudo docker compose exec openclaw-gateway sh -lc 'test -n "$GEMINI_API_KEY" && echo GEMINI_OK || echo GEMINI_MISSING'
sudo docker compose exec openclaw-gateway sh -lc 'test -n "$BRAVE_API_KEY" && echo BRAVE_OK || echo BRAVE_MISSING'
```

### Chat smoke test

1. “Search the web for OpenClaw web_search tool documentation.”
2. “Fetch https://example.com and summarize in one sentence.”

If the model says tools are missing, check `tools.profile`, `tools.allow` / `tools.deny`, and sandbox tool policy (`tools.sandbox.tools.*`).

---

## 6) Hardening & operational hygiene

- **Secrets:** Keep `email.env` (and `openclaw.json`) **out of git** and off pasteboards/chat. Use `chmod 600` on env files. Rotate any key ever pasted into Telegram, Cursor, or logs.
- **Provider pinning:** If you use Gemini and might add `BRAVE_API_KEY` later, set `tools.web.search.provider: "gemini"` so auto-detection does not flip to Brave.
- **Public or group bots:** Re-evaluate `web_search` / `web_fetch` exposure; consider `tools.deny: ["group:web", "browser"]` for untrusted surfaces, or disable `web_fetch` only if you want search but not arbitrary URLs.
- **Audit:** After policy changes, run `openclaw security audit` (from a context with the CLI) and restart the gateway.
- **Gemini install helper:** `scripts/set-gemini-key-openclaw.sh` writes the key with hidden input, backs up the previous `email.env`, and restarts the gateway.

---

## 7) Alternatives

- **Search-only:** enable `tools.web.search`, disable `tools.web.fetch.enabled` so the agent cannot request arbitrary URLs.
- **Fetch-heavy:** enable Firecrawl for `web_fetch` when raw HTML extraction is brittle.
- **JS-heavy sites:** enable and lock down `browser` separately (different threat model; often denied in sandbox configs).
