#!/usr/bin/env python3
"""
Safe editor for ~/.openclaw/openclaw.json (JSON or JSON5).
- Backs up before every write: openclaw.json.bak.<UTC>
- Optional: run OpenClaw doctor --fix via Docker Compose after writes
Usage:
  config.py get agents.defaults.model.primary
  config.py set agents.defaults.model.primary ollama/mistral:7b-instruct
  config.py unset agents.defaults.models.\"legacy\"
  config.py apply-nova-v2 [--no-doctor]
  config.py validate
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_COMPOSE_DIR = Path.home() / "openclaw" / "openclaw"
DOCKER_SERVICE = "openclaw-cli"


def load_config(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import json5  # type: ignore

            data = json5.loads(raw)
        except ImportError as e:
            raise SystemExit(
                "Config is not strict JSON. Install json5: pip install json5"
            ) from e
    if not isinstance(data, dict):
        raise SystemExit("openclaw.json root must be a JSON object")
    return data


def save_config(path: Path, data: dict[str, Any]) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def backup_config(path: Path) -> Path | None:
    if not path.is_file():
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = path.with_name(f"{path.name}.bak.{ts}")
    shutil.copy2(path, bak)
    return bak


def parse_path(key_path: str) -> list[str]:
    """Split dotted path; honor quoted segments for keys with dots."""
    parts: list[str] = []
    buf = ""
    in_quote = False
    quote_ch = ""
    for ch in key_path.strip():
        if in_quote:
            if ch == quote_ch:
                in_quote = False
                quote_ch = ""
            else:
                buf += ch
            continue
        if ch in "\"'":
            in_quote = True
            quote_ch = ch
            continue
        if ch == ".":
            if buf:
                parts.append(buf)
                buf = ""
            continue
        buf += ch
    if buf:
        parts.append(buf)
    if not parts:
        raise SystemExit("empty key path")
    return parts


def get_nested(obj: Any, parts: list[str]) -> Any:
    cur = obj
    for p in parts:
        if isinstance(cur, list):
            if not re.fullmatch(r"\d+", p):
                raise KeyError(p)
            cur = cur[int(p)]
        elif isinstance(cur, dict):
            if p not in cur:
                raise KeyError(".".join(parts))
            cur = cur[p]
        else:
            raise KeyError(".".join(parts))
    return cur


def set_nested(obj: dict[str, Any], parts: list[str], value: Any) -> None:
    cur: Any = obj
    for p in parts[:-1]:
        nxt = cur.get(p) if isinstance(cur, dict) else None
        if not isinstance(nxt, dict):
            nxt = {}
            if isinstance(cur, dict):
                cur[p] = nxt
            else:
                raise SystemExit(f"cannot create path at non-dict: {p}")
        cur = nxt
    if not isinstance(cur, dict):
        raise SystemExit("cannot set: parent is not an object")
    cur[parts[-1]] = value


def unset_nested(obj: dict[str, Any], parts: list[str]) -> bool:
    cur: Any = obj
    for p in parts[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return False
        cur = cur[p]
    if not isinstance(cur, dict):
        return False
    if parts[-1] not in cur:
        return False
    del cur[parts[-1]]
    return True


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if k == "agents" and isinstance(v, dict):
            out["agents"] = merge_agents_block(out.get("agents"), v)
        elif k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def merge_agents_block(
    old: Any,
    new: dict[str, Any],
) -> dict[str, Any]:
    o = copy.deepcopy(old) if isinstance(old, dict) else {}
    for ak, av in new.items():
        if ak == "list" and isinstance(av, list):
            merge_agent_list(o, av)
        elif ak == "defaults" and isinstance(av, dict):
            d0 = o.get("defaults")
            o["defaults"] = deep_merge(d0 if isinstance(d0, dict) else {}, av)
        else:
            o[ak] = copy.deepcopy(av)
    return o


def merge_agent_list(out_agents: dict[str, Any], incoming: list[Any]) -> None:
    existing = out_agents.get("list")
    if not isinstance(existing, list):
        existing = []
    by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for i, item in enumerate(existing):
        if isinstance(item, dict) and "id" in item:
            by_id[str(item["id"])] = (i, item)
    for item in incoming:
        if not isinstance(item, dict) or "id" not in item:
            existing.append(copy.deepcopy(item))
            continue
        aid = str(item["id"])
        if aid in by_id:
            idx, old = by_id[aid]
            merged = deep_merge(old, item)
            existing[idx] = merged
        else:
            existing.append(copy.deepcopy(item))
    out_agents["list"] = existing


def run_doctor(compose_dir: Path, dry_run: bool) -> int:
    if dry_run:
        print("[doctor] skipped (--no-doctor)")
        return 0
    if not (compose_dir / "docker-compose.yml").is_file():
        print(f"[doctor] skip: no docker-compose.yml in {compose_dir}", file=sys.stderr)
        return 0
    cmd = [
        "docker",
        "compose",
        "run",
        "--rm",
        "-T",
        DOCKER_SERVICE,
        "doctor",
        "--fix",
        "--yes",
    ]
    print("+", " ".join(cmd), f"(cwd={compose_dir})")
    return subprocess.call(cmd, cwd=str(compose_dir))


def validate_json_roundtrip(path: Path) -> None:
    data = load_config(path)
    json.dumps(data)  # ensure serializable
    print("validate: OK (load + json serializable)")


def build_nova_v2_patch() -> dict[str, Any]:
    owner = os.environ.get("NOVA_TELEGRAM_OWNER_ID", "").strip()
    if not owner:
        raise SystemExit(
            "Set NOVA_TELEGRAM_OWNER_ID to your numeric Telegram user id (export in shell)."
        )
    ollama_base = os.environ.get("NOVA_OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
    # Dockerized gateway on Docker Desktop WSL2 usually needs host.docker.internal

    openrouter_key_ref = os.environ.get("OPENROUTER_API_KEY", "").strip()
    providers: dict[str, Any] = {
        "ollama": {
            "apiKey": os.environ.get("OLLAMA_API_KEY", "ollama-local"),
            "baseUrl": ollama_base,
            "api": "ollama",
            "models": [
                {
                    "id": "mistral:7b-instruct",
                    "name": "mistral 7b instruct",
                    "reasoning": False,
                    "input": ["text"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 32768,
                    "maxTokens": 8192,
                    "contextTokens": 16000,
                },
                {
                    "id": "phi3:mini",
                    "name": "phi3 mini",
                    "reasoning": False,
                    "input": ["text"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 8192,
                    "maxTokens": 4096,
                    "contextTokens": 16000,
                },
                {
                    "id": "nomic-embed-text:latest",
                    "name": "nomic embed",
                    "reasoning": False,
                    "input": ["text"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 8192,
                    "maxTokens": 1024,
                    "contextTokens": 8192,
                },
            ],
        }
    }
    if openrouter_key_ref:
        providers["openrouter"] = {
            "apiKey": openrouter_key_ref,
        }

    if openrouter_key_ref:
        fallbacks: list[str] = ["openrouter/meta-llama/llama-3.3-70b-instruct:free"]
        model_allow_extra: dict[str, Any] = {
            "openrouter/meta-llama/llama-3.3-70b-instruct:free": {
                "alias": "fallback-free",
                "contextTokens": 16000,
            },
        }
    else:
        fallbacks = ["ollama/phi3:mini"]
        model_allow_extra = {}

    patch: dict[str, Any] = {
        "agents": {
            "defaults": {
                "model": {
                    "primary": "ollama/mistral:7b-instruct",
                    "fallbacks": fallbacks,
                },
                "models": {
                    "ollama/mistral:7b-instruct": {"alias": "actor", "contextTokens": 16000},
                    "ollama/phi3:mini": {"alias": "judge", "contextTokens": 16000},
                    **model_allow_extra,
                },
                "contextTokens": 16000,
                "sandbox": {
                    "mode": "non-main",
                    "scope": "agent",
                    "workspaceAccess": "rw",
                    "docker": {
                        "setupCommand": (
                            "apt-get update && DEBIAN_FRONTEND=noninteractive "
                            "apt-get install -y python3 python3-pip python3-venv && "
                            "python3 -m pip install --upgrade pip || true"
                        ),
                    },
                },
            },
            "list": [
                {"id": "main", "model": {"primary": "ollama/mistral:7b-instruct"}},
            ],
        },
        "models": {"providers": providers},
        "commands": {
            "ownerAllowFrom": [f"tg:{owner}"],
        },
        "channels": {
            "telegram": {
                "enabled": True,
                "dmPolicy": "allowlist",
                "allowFrom": [f"tg:{owner}"],
            },
        },
        "tools": {
            "elevated": {
                "enabled": True,
                "allowFrom": {"telegram": [owner]},
            },
        },
    }
    return patch


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe OpenClaw openclaw.json editor")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to openclaw.json",
    )
    parser.add_argument(
        "--compose-dir",
        default=str(DEFAULT_COMPOSE_DIR),
        help="OpenClaw repo with docker-compose.yml",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_get = sub.add_parser("get", help="Print JSON value for dotted path")
    p_get.add_argument("path")

    p_set = sub.add_parser("set", help="Set value (JSON literal or raw string)")
    p_set.add_argument("path")
    p_set.add_argument("value")
    p_set.add_argument("--raw-string", action="store_true", help="Treat value as string, not JSON")
    p_set.add_argument("--no-doctor", action="store_true")

    p_unset = sub.add_parser("unset", help="Remove a key")
    p_unset.add_argument("path")
    p_unset.add_argument("--no-doctor", action="store_true")

    p_val = sub.add_parser("validate", help="Load and verify JSON serializable")
    p_apply = sub.add_parser("apply-nova-v2", help="Merge NOVA V2 baseline (env-driven)")
    p_apply.add_argument("--no-doctor", action="store_true")

    args = parser.parse_args()
    cfg_path = Path(os.path.expanduser(args.config))
    compose_dir = Path(os.path.expanduser(args.compose_dir))

    if args.cmd == "validate":
        if not cfg_path.is_file():
            raise SystemExit(f"missing {cfg_path}")
        validate_json_roundtrip(cfg_path)
        return

    if args.cmd == "get":
        if not cfg_path.is_file():
            raise SystemExit(f"missing {cfg_path}")
        data = load_config(cfg_path)
        parts = parse_path(args.path)
        try:
            val = get_nested(data, parts)
        except KeyError as e:
            raise SystemExit(f"not found: {e}") from e
        print(json.dumps(val, indent=2, ensure_ascii=False))
        return

    if args.cmd == "set":
        parts = parse_path(args.path)
        if args.raw_string:
            val: Any = args.value
        else:
            try:
                val = json.loads(args.value)
            except json.JSONDecodeError:
                val = args.value
        if cfg_path.is_file():
            data = load_config(cfg_path)
        else:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
        b = backup_config(cfg_path)
        set_nested(data, parts, val)
        save_config(cfg_path, data)
        print(f"wrote {cfg_path}" + (f" (backup: {b})" if b else " (new file)"))
        sys.exit(run_doctor(compose_dir, args.no_doctor))

    if args.cmd == "unset":
        if not cfg_path.is_file():
            raise SystemExit(f"missing {cfg_path}")
        parts = parse_path(args.path)
        data = load_config(cfg_path)
        b = backup_config(cfg_path)
        if not unset_nested(data, parts):
            raise SystemExit("path not found or not an object key")
        save_config(cfg_path, data)
        print(f"unset {args.path} on {cfg_path}" + (f" (backup: {b})" if b else ""))
        sys.exit(run_doctor(compose_dir, args.no_doctor))

    if args.cmd == "apply-nova-v2":
        patch = build_nova_v2_patch()
        if cfg_path.is_file():
            data = load_config(cfg_path)
        else:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
        b = backup_config(cfg_path)
        merged = deep_merge(data, patch)
        save_config(cfg_path, merged)
        print(f"merged NOVA V2 patch into {cfg_path}" + (f" (backup: {b})" if b else ""))
        sys.exit(run_doctor(compose_dir, args.no_doctor))


if __name__ == "__main__":
    main()
