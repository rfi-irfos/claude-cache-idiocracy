from __future__ import annotations

from .policy import Policy
from .state import load, lock, save


def admit(session: str, policy: Policy | None = None) -> tuple[bool, str]:
    policy = policy or Policy.from_env()
    key = session or "__global__"
    with lock():
        data = load()
        active = data.setdefault("agents", {}).get(key, 0)
        if active >= policy.max_subagents:
            return False, f"maximum active subagents reached ({policy.max_subagents})"
        data["agents"][key] = active + 1
        save(data)
    return True, ""


def release(session: str) -> None:
    key = session or "__global__"
    with lock():
        data = load()
        active = data.setdefault("agents", {}).get(key, 0)
        if active <= 1:
            data["agents"].pop(key, None)
        else:
            data["agents"][key] = active - 1
        save(data)
