#!/usr/bin/env python3
"""Deterministic local token-savings benchmark; no provider or prompt data leaves memory."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hache_guard.read_guard import check, record


def main() -> int:
    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root); state = root_path / "state.json"; target = root_path / "large.md"
        payload = "x" * 400_000; target.write_text(payload)
        os.environ["HACHE_STATE"] = str(state)
        start = time.perf_counter(); allowed = 0
        for _ in range(100):
            if check(str(target), session="benchmark").allowed:
                allowed += 1; record(str(target), session="benchmark")
        elapsed = time.perf_counter() - start
        total_bytes = len(payload) * 100
        avoided = total_bytes - len(payload) * allowed
        if allowed != 1 or avoided <= 0:
            raise SystemExit("read guard did not demonstrate duplicate-read suppression")
        print(json.dumps({"attempted_reads": 100, "allowed_reads": allowed, "blocked_reads": 100 - allowed, "estimated_bytes_avoided": avoided, "elapsed_seconds": elapsed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
