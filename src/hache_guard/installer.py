from __future__ import annotations
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from .policy import Policy

def install_settings(settings: str | Path | None = None) -> Path:
    target = Path(settings or "~/.claude/settings.json").expanduser()
    try: data = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    except json.JSONDecodeError as exc: raise SystemExit(f"Invalid Claude settings: {target}: {exc}")
    data.setdefault("env", {}).update(Policy().environment())
    data["env"]["CLAUDE_CODE_MAX_RETRIES"] = "3"
    # Keep an explicit user choice, but make the known-stable default portable.
    data.setdefault("model", "claude-sonnet-5")
    executable = subprocess.list2cmdline([sys.executable]) if os.name == "nt" else shlex.quote(sys.executable)
    command = f"{executable} -m hache_guard"
    hooks = data.setdefault("hooks", {})
    def add(event, suffix):
        bucket = hooks.setdefault(event, [])
        command_text = f"{command} {suffix}"
        if any(
            hook.get("command") == command_text
            for item in bucket
            for hook in item.get("hooks", [])
            if isinstance(hook, dict)
        ):
            return
        bucket.append({"matcher": "Read", "hooks": [{"type": "command", "command": command_text}]})
    add("PreToolUse", "pre")
    add("PostToolUse", "post")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
