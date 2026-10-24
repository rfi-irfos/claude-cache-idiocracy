from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


class SessionIndexer:
    """Incrementally indexes transcript metadata without persisting message bodies."""

    def __init__(self, database: str | Path = "~/.claude/hache-index.sqlite3"):
        self.database = Path(database).expanduser()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.database)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS cursors (path TEXT PRIMARY KEY, offset INTEGER NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (path TEXT, request_id TEXT, kind TEXT, bytes INTEGER, PRIMARY KEY(path, request_id, kind))")
        self.db.commit()

    def index(self, transcript: str | Path) -> dict:
        path = Path(transcript).expanduser().resolve()
        row = self.db.execute("SELECT offset FROM cursors WHERE path=?", (str(path),)).fetchone()
        offset = int(row[0]) if row else 0
        if path.stat().st_size < offset:
            offset = 0
            self.db.execute("DELETE FROM events WHERE path=?", (str(path),))
        added = 0
        with path.open("rb") as stream:
            stream.seek(offset)
            for raw in stream:
                try:
                    item = json.loads(raw.decode("utf-8", "replace"))
                except json.JSONDecodeError:
                    continue
                request_id = str(item.get("requestId") or item.get("id") or hashlib.sha256(raw).hexdigest())
                kind = str(item.get("type") or "unknown")
                cur = self.db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?)", (str(path), request_id, kind, len(raw)))
                added += cur.rowcount
            end = stream.tell()
        self.db.execute("INSERT OR REPLACE INTO cursors VALUES (?,?)", (str(path), end))
        self.db.commit()
        return {"path": str(path), "offset": end, "new_events": added}

    def close(self):
        self.db.close()
