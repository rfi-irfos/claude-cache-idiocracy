from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .policy import Policy


def uninstall(settings: str | Path | None = None) -> Path:
    target = Path(settings or "~/.claude/settings.json").expanduser()
    if not target.exists():
        return target
    data = json.loads(target.read_text(encoding="utf-8"))
    for key in Policy().environment():
        data.get("env", {}).pop(key, None)
    data.get("env", {}).pop("CLAUDE_CODE_MAX_RETRIES", None)
    for event in ("PreToolUse", "PostToolUse", "SessionStart", "PreCompact", "SessionEnd"):
        bucket = data.get("hooks", {}).get(event, [])
        data.setdefault("hooks", {})[event] = [
            item for item in bucket
            if "hache_guard" not in json.dumps(item)
        ]
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def backup_path(target: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return target.with_name(target.name + ".hache-backup-" + stamp)


def rollback(settings: str | Path | None = None) -> Path | None:
    target = Path(settings or "~/.claude/settings.json").expanduser()
    backups = sorted(target.parent.glob(target.name + ".hache-backup-*"))
    if not backups:
        return None
    target.write_text(backups[-1].read_text(encoding="utf-8"), encoding="utf-8")
    return backups[-1]
