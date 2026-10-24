#!/usr/bin/env python3
"""Exercise settings install, upgrade-like repeat, rollback and uninstall locally."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hache_guard.installer import install_settings
from hache_guard.lifecycle import rollback, uninstall


def main() -> int:
    with tempfile.TemporaryDirectory() as root:
        settings = Path(root) / "settings.json"
        settings.write_text(json.dumps({"custom": "preserve"}))
        install_settings(settings)
        install_settings(settings)
        assert list(Path(root).glob("settings.json.hache-backup-*"))
        settings.write_text(json.dumps({"corrupt_upgrade": True}))
        assert rollback(settings) is not None
        assert json.loads(settings.read_text())["custom"] == "preserve"
        uninstall(settings)
        final = json.loads(settings.read_text())
        assert final["custom"] == "preserve" and "hache_guard" not in json.dumps(final)
    print("lifecycle-smoke-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
