#!/usr/bin/env python3
"""Small deterministic local benchmark; never contacts a provider."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hache_guard.indexer import SessionIndexer


def main() -> int:
    with tempfile.TemporaryDirectory() as root:
        directory = Path(root)
        transcript = directory / "session.jsonl"
        transcript.write_text("".join(json.dumps({"id": str(i), "type": "assistant"}) + "\n" for i in range(10000)))
        index = SessionIndexer(directory / "index.sqlite")
        start = time.perf_counter(); first = index.index(transcript); first_seconds = time.perf_counter() - start
        start = time.perf_counter(); second = index.index(transcript); second_seconds = time.perf_counter() - start
        print(json.dumps({"first": first, "second": second, "first_seconds": first_seconds, "second_seconds": second_seconds}, indent=2))
        index.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
