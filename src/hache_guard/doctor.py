from __future__ import annotations

import json
import shutil
import sys
import argparse
from pathlib import Path

from .policy import Policy
from .state import default_state, load


def report(settings: str | Path | None = None) -> dict:
    settings_path = Path(settings or "~/.claude/settings.json").expanduser()
    checks = {}
    checks["python"] = sys.version_info >= (3, 9)
    checks["state_parent"] = default_state().parent.exists() or default_state().parent.parent.exists()
    checks["settings_exists"] = settings_path.exists()
    checks["settings_valid"] = False
    checks["hooks_installed"] = False
    checks["policy"] = Policy().environment()
    checks["rtk"] = bool(shutil.which("rtk"))
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            checks["settings_valid"] = isinstance(data, dict)
            hooks = data.get("hooks", {})
            serialized = json.dumps(hooks)
            checks["hooks_installed"] = "hache_guard" in serialized
        except (OSError, json.JSONDecodeError):
            pass
    checks["state_readable"] = isinstance(load(), dict)
    checks["strict_ok"] = all(value for key, value in checks.items() if key not in ("policy", "rtk", "settings_exists"))
    return checks


def run(strict: bool = False) -> int:
    result = report()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if (not strict or result["strict_ok"]) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Hache installation")
    parser.add_argument("--strict", action="store_true")
    return run(parser.parse_args().strict)
