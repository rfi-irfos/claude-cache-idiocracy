from __future__ import annotations
import json
import sys
from pathlib import Path
from .policy import Policy

def install_settings(settings: str | Path | None = None) -> Path:
    target = Path(settings or "~/.claude/settings.json").expanduser()
    try: data = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    except json.JSONDecodeError as exc: raise SystemExit(f"Invalid Claude settings: {target}: {exc}")
    data.setdefault("env", {}).update(Policy().environment())
    data["env"]["CLAUDE_CODE_MAX_RETRIES"] = "3"
    command = f"{sys.executable} -m hache_guard"
    hooks = data.setdefault("hooks", {})
    hooks.setdefault("PreToolUse", []).append({"matcher": "Read", "hooks": [{"type": "command", "command": f"{command} pre"}]})
    hooks.setdefault("PostToolUse", []).append({"matcher": "Read", "hooks": [{"type": "command", "command": f"{command} post"}]})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
