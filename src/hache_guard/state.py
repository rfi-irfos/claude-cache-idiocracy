from __future__ import annotations
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def default_state() -> Path:
    return Path(os.environ.get("HACHE_STATE", "~/.claude/hache-state.json")).expanduser()


def load(path: Path | None = None) -> dict:
    path = path or default_state()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"files": {}, "sessions": {}}


def save(data: dict, path: Path | None = None) -> None:
    path = path or default_state()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".hache-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, sort_keys=True)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def lock():
    path = default_state().with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        if os.name == "nt":
            import msvcrt
            handle.write(" ")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(os.path.realpath(os.path.expanduser(path)), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
