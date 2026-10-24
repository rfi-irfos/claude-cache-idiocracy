from __future__ import annotations
import argparse
import json
import sys
from .policy import Policy
from .read_guard import check, record


def hook(event: str) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool = payload.get("tool_name", "")
    inp = payload.get("tool_input") or {}
    if event == "pre" and tool == "Read" and inp.get("file_path"):
        decision = check(inp["file_path"], int(inp.get("offset") or 0), inp.get("limit"), payload.get("session_id", ""))
        if not decision.allowed:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": decision.reason}}))
    elif event == "post" and tool == "Read" and inp.get("file_path"):
        record(inp["file_path"], int(inp.get("offset") or 0), inp.get("limit"), payload.get("session_id", ""))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["pre", "post", "policy"])
    args = parser.parse_args()
    if args.command in ("pre", "post"):
        return hook(args.command)
    print(json.dumps(Policy.from_env().__dict__, indent=2))
    return 0
