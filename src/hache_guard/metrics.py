from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")

def transcript_usage(path: str | Path) -> dict:
    totals = Counter(); errors = Counter(); requests = set(); compactions = 0
    with Path(path).open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            if row.get("type") == "system" and "compact" in line.lower(): compactions += 1
            if row.get("type") != "api-request": continue
            rid = row.get("id") or row.get("requestId") or row.get("uuid")
            if rid and rid in requests: continue
            if rid: requests.add(rid)
            usage = (row.get("message") or {}).get("usage") or row.get("usage") or {}
            for field in FIELDS: totals[field] += int(usage.get(field, 0) or 0)
            low = line.lower()
            for marker in ("429", "500", "502", "503", "529", "timeout", "overloaded"):
                if marker in low: errors[marker] += 1
    return {"requests": len(requests), "compactions": compactions, "errors": dict(errors), **totals}
