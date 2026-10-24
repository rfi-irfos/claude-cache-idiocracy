from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .state import default_state, load


def proxy_stats(database: str | Path | None = None) -> dict:
    path = Path(database or os.environ.get("HACHE_PROXY_STATE", "~/.claude/hache-proxy.sqlite3")).expanduser()
    if not path.exists():
        return {"database": str(path), "requests": 0, "estimated_input_tokens": 0, "actual_input_tokens": 0, "blocked": 0}
    db = sqlite3.connect(path)
    rows = db.execute("SELECT estimated_tokens,actual_input_tokens,status FROM requests").fetchall()
    db.close()
    return {
        "database": str(path),
        "requests": len(rows),
        "estimated_input_tokens": sum(row[0] or 0 for row in rows),
        "actual_input_tokens": sum(row[1] or 0 for row in rows),
        "blocked": sum(row[2] == 429 for row in rows),
        "upstream_errors": sum(500 <= (row[2] or 0) < 600 for row in rows),
    }


def report() -> dict:
    state = load()
    files = state.get("files", {})
    agents = state.get("agents", {})
    ranges = sum(len(session.get("ranges", [])) for item in files.values() for session in item.values() if isinstance(session, dict))
    return {
        "read_paths": len(files),
        "indexed_read_ranges": ranges,
        "active_agent_sessions": len(agents),
        "active_agents": sum(agents.values()),
        "proxy": proxy_stats(),
    }


def main() -> int:
    print(json.dumps(report(), indent=2, sort_keys=True))
    return 0
