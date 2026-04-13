#!/usr/bin/env python3
"""
judge.py - Evo-Evaluator for Nova's self-evolving loop
Usage: python3 judge.py --task "what was asked" --output "nova's solution" --criteria "acceptance criteria"
Returns: PASS/FAIL verdict to stdout
Uses local Ollama (phi3:mini) at NOVA_OLLAMA_BASE_URL (default http://172.27.80.201:11434).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

JUDGE_MODEL = "phi3:mini"
OLLAMA_CHAT = (
    os.environ.get("NOVA_OLLAMA_BASE_URL", "http://172.27.80.201:11434").rstrip("/")
    + "/api/chat"
)

JUDGE_SYSTEM = """You are the Evo-Evaluator, a strict code and config critic.
Your only job is to review work produced by the Actor agent (Nova) and return a structured verdict.
You do NOT produce solutions — only evaluations.

For every review, respond in this EXACT format (no extra text before or after):

VERDICT: PASS or FAIL
REASON: One sentence explaining why.
BLOCKERS:
- issue 1 (or "none" if PASS)
SUGGESTIONS:
- suggestion 1 (or "none")

Evaluate strictly against:
1. Does the code/config do what was asked?
2. Does it pass basic safety checks (no rm -rf, no plaintext secrets, no unbounded loops)?
3. Is it idempotent — safe to run twice?
4. Are edge cases handled?

A PASS means you would ship this. A FAIL means you would not. Be strict."""


def bot_root() -> str:
    return os.path.expanduser(os.environ.get("NOVA_BOT_ROOT", "~/Bot"))


def call_judge(task: str, output: str, criteria: str) -> str:
    user_msg = f"""Review this work:

TASK: {task}

ACCEPTANCE CRITERIA: {criteria}

ACTOR OUTPUT:
{output}

Return your verdict in the exact format specified."""

    payload = json.dumps(
        {
            "model": JUDGE_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_CHAT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
            msg = data.get("message") or {}
            content = (msg.get("content") or "").strip()
            if not content:
                print(f"ERROR: empty judge response: {data}", file=sys.stderr)
                sys.exit(2)
            return content
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} from Ollama: {body}", file=sys.stderr)
        sys.exit(2)
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach Ollama at {OLLAMA_CHAT}: {e.reason}", file=sys.stderr)
        sys.exit(2)


def log_result(task: str, verdict_text: str, iteration: int) -> bool:
    timestamp = datetime.now(timezone.utc).isoformat()
    passed = verdict_text.startswith("VERDICT: PASS")
    log_entry = {
        "timestamp": timestamp,
        "iteration": iteration,
        "task_summary": task[:120],
        "verdict": "PASS" if passed else "FAIL",
        "full_response": verdict_text,
    }
    log_path = os.path.join(bot_root(), "tools", "judge-log.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova Evo-Evaluator Judge (Ollama)")
    parser.add_argument("--task", required=True, help="What Nova was asked to do")
    parser.add_argument(
        "--output", required=True, help="Nova's solution/output to evaluate"
    )
    parser.add_argument(
        "--criteria",
        default="Complete the task correctly and safely",
        help="Acceptance criteria",
    )
    parser.add_argument(
        "--iteration", type=int, default=0, help="Current loop iteration number"
    )
    args = parser.parse_args()

    print(f"[Judge] Evaluating iteration {args.iteration}...", file=sys.stderr)
    verdict_text = call_judge(args.task, args.output, args.criteria)
    passed = log_result(args.task, verdict_text, args.iteration)

    print(verdict_text)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
