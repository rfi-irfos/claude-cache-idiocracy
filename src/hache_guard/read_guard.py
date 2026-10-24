from __future__ import annotations
from pathlib import Path
from .state import file_hash, load, lock, save


class ReadDecision:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed, self.reason = allowed, reason


def _session_key(session: str) -> str:
    return session or "__global__"


def _contains(existing_start, existing_end, requested_start, requested_end):
    if existing_start > requested_start:
        return False
    if existing_end is None:
        return True
    return requested_end is not None and existing_end >= requested_end


def check(path: str, offset: int = 0, limit: int | None = None, session: str = "") -> ReadDecision:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return ReadDecision(True)
    digest = file_hash(str(p))
    data = load()
    record = data.setdefault("files", {}).get(str(p), {}).get(_session_key(session))
    if not record or record.get("hash") != digest:
        return ReadDecision(True)
    requested = [offset, offset + limit] if limit else [0, None]
    for start, end in record.get("ranges", []):
        if _contains(start, end, requested[0], requested[1]):
            return ReadDecision(False, f"unchanged content already read: {p}")
    return ReadDecision(True)


def record(path: str, offset: int = 0, limit: int | None = None, session: str = "") -> None:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return
    with lock():
        data = load()
        files = data.setdefault("files", {})
        by_session = files.setdefault(str(p), {})
        key = _session_key(session)
        entry = by_session.setdefault(key, {"hash": file_hash(str(p)), "ranges": []})
        digest = file_hash(str(p))
        if entry.get("hash") != digest:
            entry = {"hash": digest, "ranges": []}
            by_session[key] = entry
        entry.setdefault("ranges", []).append([offset, offset + limit] if limit else [0, None])
        save(data)
