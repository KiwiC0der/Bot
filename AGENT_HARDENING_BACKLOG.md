# Agent hardening & cleanup backlog

Living notes for **small bugs, security tightening, and polish** while we keep shipping features.  
Goal: capture items quickly during development; batch-fix when we revisit an area.

**How to use**

- Add a line under the right section when something bugs you (one sentence + optional “see: …”).
- When you fix something, move it to **Done (archive)** at the bottom with a date, or delete it.
- Don’t let this block feature work—just park the detail here.

---

## Security & trust

- [ ] **Email send confirmation** — Verify end-to-end that real sends only happen after explicit user approval (e.g. `SEND` / `CONFIRM`) and that `dryRun=true` cannot be bypassed by sloppy tool args. If sends can occur without that second human step, treat as **bug** (OpenClaw tool policy, agent instructions, or model behavior).
- [ ] **Secrets hygiene** — `~/.openclaw/openclaw.json` holds bot token, gateway token, etc. Confirm it is **never** committed; prefer env substitution where OpenClaw supports it; rotate anything ever pasted into chat or logs.
- [ ] **Recipient allowlist** — Keep `EMAIL_ALLOWLIST_*` tight in production; re-test after config changes.
- [ ] **Telegram surface** — `commands.ownerAllowFrom` is set for owner-only tools; re-audit if the bot becomes public or is added to groups.
- [ ] **Gateway bind / auth** — Confirm `gateway.bind` and `gateway.auth` match threat model (loopback + token is good for local-only).

---

## Reliability & correctness

- [ ] **Email tool errors** — Log and handle SMTP/API failures clearly in chat (without leaking credentials).
- [ ] **Session / model drift** — After config changes, document “restart gateway + `/reset`” or automate where safe.
- [ ] **Timeouts** — Revisit `agents.defaults.timeoutSeconds` vs model/provider behavior if flaky.

---

## UX & docs

- [ ] **Nova prompts** — Keep a short “test email” snippet in runbook or here if the workflow changes.
- [ ] **Runbook drift** — When OpenClaw upgrades, re-check sections 4.7 (voice) and 4.8 (email) against actual behavior.

---

## Nice-to-have / polish

- [ ] **Cursor rule** — Trim or split `.cursor/rules/nova-openclaw-assistant.mdc` if it conflicts with new workflows.
- [ ] **Automated checks** — Optional: script dry-run email from host CI or a `make check-openclaw` target.

---

## Done (archive)

<!-- Example:
- [x] 2026-03-19 — Added `commands.ownerAllowFrom` for Telegram owner-only tools — see OPENCLAW_KALI_DOCKER_RUNBOOK §4.8
-->
