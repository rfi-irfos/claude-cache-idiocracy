from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def write(reason: str, payload: dict, directory: str = "~/.claude/handovers") -> Path:
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = root / f"hache-{stamp}-{uuid.uuid4().hex[:8]}.json"
    safe = {"schema": 1, "reason": reason, "created_at": stamp, **payload}
    target.write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
