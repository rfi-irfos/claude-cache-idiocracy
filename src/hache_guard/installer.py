from __future__ import annotations
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from .policy import Policy
from .lifecycle import backup_path

def install_settings(settings: str | Path | None = None) -> Path:
    target = Path(settings or "~/.claude/settings.json").expanduser()
    try: data = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    except json.JSONDecodeError as exc: raise SystemExit(f"Invalid Claude settings: {target}: {exc}")
    if target.exists():
        backup = backup_path(target)
        backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    data.setdefault("env", {}).update(Policy().environment())
    data["env"]["CLAUDE_CODE_MAX_RETRIES"] = "3"
    # Do not force an arbitrary compact threshold; Claude should use the model-native context window.
    data["env"].pop("CLAUDE_CODE_AUTO_COMPACT_WINDOW", None)
    # Keep an explicit user choice, but make the known-stable default portable.
    data.setdefault("model", "claude-sonnet-5")
    executable = subprocess.list2cmdline([sys.executable]) if os.name == "nt" else shlex.quote(sys.executable)
    command = f"{executable} -m hache_guard"
    hooks = data.setdefault("hooks", {})
    def add(event, suffix, matcher="Read"):
        bucket = hooks.setdefault(event, [])
        command_text = f"{command} {suffix}"
        if any(
            item.get("matcher") == matcher and
            hook.get("command") == command_text
            for item in bucket
            for hook in item.get("hooks", [])
            if isinstance(hook, dict)
        ):
            return
        bucket.append({"matcher": matcher, "hooks": [{"type": "command", "command": command_text}]})
    add("PreToolUse", "pre")
    add("PostToolUse", "post")
    add("PreToolUse", "pre", "Task|Agent")
    add("PostToolUse", "post", "Task|Agent")
    # RTK owns Bash-output rewriting; only wire it when already installed.
    # The guard itself remains functional when RTK is absent.
    if shutil.which("rtk"):
        bucket = hooks.setdefault("PreToolUse", [])
        if not any(
            any(h.get("command") == "rtk hook claude" for h in item.get("hooks", []) if isinstance(h, dict))
            for item in bucket
        ):
            bucket.append({"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
