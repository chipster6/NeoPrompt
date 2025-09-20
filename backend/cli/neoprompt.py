#!/usr/bin/env python3
"""
NeoPrompt CLI: minimal command-line client for NeoPrompt FastAPI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

import httpx

DEFAULT_API_BASE = os.environ.get("NEOPROMPT_API_BASE", "http://localhost/api")


def _client(base_url: str, timeout: float = 15.0) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        timeout=timeout,
        headers={"Accept": "application/json"},
    )


def cmd_health(args: argparse.Namespace) -> None:
    with _client(args.api_base) as c:
        r = c.get("/healthz")
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))


def _read_stdin_or_interactive() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Enter raw prompt (end with an empty line):")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines)


def _feedback_prompt(c: httpx.Client, choose_resp: Dict[str, Any]) -> None:
    decision_id = choose_resp.get("decision_id") or choose_resp.get("id")
    engineered = choose_resp.get("engineered_prompt") or choose_resp.get("prompt")
    if engineered:
        print("\nEngineered Prompt:\n")
        print(engineered)
    if not decision_id:
        return
    ans = input("\nSend feedback? [u]p/[d]own/[s]kip: ").strip().lower()
    if ans in ("u", "up", "+", "y", "yes"):
        reward = 1.0
    elif ans in ("d", "down", "-", "n", "no"):
        reward = -1.0
    else:
        return
    fr = c.post(
        "/feedback",
        json={"decision_id": decision_id, "reward": reward, "reward_components": {}},
    )
    if 200 <= fr.status_code < 300:
        print("feedback: ok")
    else:
        print(f"feedback failed: {fr.status_code}", file=sys.stderr)


def cmd_choose(args: argparse.Namespace) -> None:
    raw = args.raw if args.raw is not None else _read_stdin_or_interactive()
    payload: Dict[str, Any] = {
        "assistant": args.assistant,
        "category": args.category,
        "raw_input": raw,
        "options": {
            "enhance": bool(args.enhance),
            "force_json": bool(args.force_json),
        },
        "context_features": {},
    }
    with _client(args.api_base) as c:
        r = c.post("/choose", json=payload)
        r.raise_for_status()
        data = r.json()
        print(json.dumps(data, indent=2))
        if args.interactive:
            _feedback_prompt(c, data)


def cmd_feedback(args: argparse.Namespace) -> None:
    payload: Dict[str, Any] = {
        "decision_id": args.decision_id,
        "reward": float(args.reward),
    }
    if args.reward_components:
        try:
            payload["reward_components"] = json.loads(args.reward_components)
        except Exception as e:  # pragma: no cover - simple CLI parsing error
            print(f"Invalid JSON for --reward-components: {e}", file=sys.stderr)
            sys.exit(2)
    with _client(args.api_base) as c:
        r = c.post("/feedback", json=payload)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))


def cmd_history(args: argparse.Namespace) -> None:
    params: Dict[str, Any] = {}
    if args.limit is not None:
        params["limit"] = args.limit
    if args.assistant:
        params["assistant"] = args.assistant
    if args.category:
        params["category"] = args.category
    if args.with_text:
        params["with_text"] = True
    with _client(args.api_base) as c:
        r = c.get("/history", params=params)
        r.raise_for_status()
        data = r.json()
        print(json.dumps(data, indent=2) if args.with_text else json.dumps(data))


def cmd_templates(args: argparse.Namespace) -> None:
    with _client(args.api_base) as c:
        r = c.get("/prompt-templates")
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))


def cmd_schema(args: argparse.Namespace) -> None:
    with _client(args.api_base) as c:
        r = c.get("/prompt-templates/schema")
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="neoprompt", description="NeoPrompt CLI")
    p.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help="API base URL (default from NEOPROMPT_API_BASE)",
    )
    sub = p.add_subparsers(dest="cmd")

    p_health = sub.add_parser("health", help="Check API health")
    p_health.set_defaults(func=cmd_health)

    p_choose = sub.add_parser("choose", help="Generate prompt decision")
    p_choose.add_argument("--assistant", required=True)
    p_choose.add_argument("--category", required=True)
    p_choose.add_argument("--raw", help="Raw text (reads stdin if omitted)")
    p_choose.add_argument("--enhance", action="store_true")
    p_choose.add_argument("--force-json", action="store_true")
    p_choose.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode with immediate feedback prompt",
    )
    p_choose.set_defaults(func=cmd_choose)

    p_feedback = sub.add_parser("feedback", help="Send feedback for a decision")
    p_feedback.add_argument("--decision-id", required=True)
    p_feedback.add_argument("--reward", required=True, type=float, choices=[-1.0, 0.0, 1.0])
    p_feedback.add_argument("--reward-components", help="Optional JSON string with component scores")
    p_feedback.set_defaults(func=cmd_feedback)

    p_hist = sub.add_parser("history", help="List decision history")
    p_hist.add_argument("--limit", type=int)
    p_hist.add_argument("--assistant")
    p_hist.add_argument("--category")
    p_hist.add_argument("--with-text", action="store_true")
    p_hist.set_defaults(func=cmd_history)

    p_tpl = sub.add_parser("templates", help="List prompt templates")
    p_tpl.set_defaults(func=cmd_templates)

    p_sch = sub.add_parser("schema", help="Get prompt templates JSON Schema")
    p_sch.set_defaults(func=cmd_schema)

    args = p.parse_args(argv)
    if not getattr(args, "cmd", None):
        p.print_help()
        return 0
    try:
        args.func(args)
        return 0
    except httpx.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
