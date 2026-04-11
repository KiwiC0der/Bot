#!/usr/bin/env python3
"""
judge.py - Evo-Evaluator for Nova's self-evolving loop
Usage: python3 judge.py --task "what was asked" --output "nova's solution" --criteria "acceptance criteria"
Returns: PASS/FAIL verdict to stdout
Requires: OPENROUTER_API_KEY_JUDGE env var
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

JUDGE_MODEL = "google/gemini-2.0-flash-001"
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"

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

def call_judge(task, output, criteria):
    api_key = os.environ.get("OPENROUTER_API_KEY_JUDGE")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY_JUDGE not set in environment")
        sys.exit(2)

    user_msg = f"""Review this work:

TASK: {task}

ACCEPTANCE CRITERIA: {criteria}

ACTOR OUTPUT:
{output}

Return your verdict in the exact format specified."""

    payload = json.dumps({
        "model": JUDGE_MODEL,
        "max_tokens": 512,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_msg}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_API,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/openclaw",
            "X-Title": "Nova-Judge"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            verdict_text = data["choices"][0]["message"]["content"].strip()
            return verdict_text
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} from OpenRouter: {body}")
        sys.exit(2)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}")
        sys.exit(2)

def log_result(task, verdict_text, iteration):
    timestamp = datetime.now(timezone.utc).isoformat()
    passed = verdict_text.startswith("VERDICT: PASS")
    log_entry = {
        "timestamp": timestamp,
        "iteration": iteration,
        "task_summary": task[:120],
        "verdict": "PASS" if passed else "FAIL",
        "full_response": verdict_text
    }
    log_path = os.path.expanduser("~/Desktop/Bot/tools/judge-log.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    return passed

def main():
    parser = argparse.ArgumentParser(description="Nova Evo-Evaluator Judge")
    parser.add_argument("--task", required=True, help="What Nova was asked to do")
    parser.add_argument("--output", required=True, help="Nova's solution/output to evaluate")
    parser.add_argument("--criteria", default="Complete the task correctly and safely", help="Acceptance criteria")
    parser.add_argument("--iteration", type=int, default=0, help="Current loop iteration number")
    args = parser.parse_args()

    print(f"[Judge] Evaluating iteration {args.iteration}...", file=sys.stderr)
    verdict_text = call_judge(args.task, args.output, args.criteria)
    passed = log_result(args.task, verdict_text, args.iteration)

    print(verdict_text)
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
