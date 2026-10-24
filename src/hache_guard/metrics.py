from __future__ import annotations
import json
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")

def transcript_usage(path: str | Path) -> dict:
    totals = Counter(); errors = Counter(); error_events = []; requests = set(); compactions = 0
    with Path(path).open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            if row.get("type") == "system" and "compact" in line.lower(): compactions += 1
            usage = (row.get("message") or {}).get("usage") or row.get("usage") or {}
            if not usage and row.get("type") != "api-request":
                continue
            rid = row.get("requestId") or row.get("id") or row.get("uuid") or (row.get("message") or {}).get("id")
            if rid and rid in requests: continue
            if rid: requests.add(rid)
            for field in FIELDS: totals[field] += int(usage.get(field, 0) or 0)
            if row.get("type") == "api-request":
                low = line.lower()
                marker = next((m for m in ("429", "500", "502", "503", "529", "timeout", "overloaded") if m in low), None)
                if marker:
                    stamp = row.get("timestamp") or row.get("created_at") or row.get("createdAt")
                    parsed = None
                    if isinstance(stamp, (int, float)):
                        parsed = float(stamp)
                    elif isinstance(stamp, str):
                        try:
                            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
                        except ValueError:
                            pass
                    error_events.append((parsed, marker))
    timestamps = [stamp for stamp, _ in error_events if stamp is not None]
    cutoff = max(timestamps) - 900 if timestamps else None
    for stamp, marker in error_events:
        if cutoff is None or stamp is None or stamp >= cutoff:
            errors[marker] += 1
    return {"requests": len(requests), "compactions": compactions, "errors": dict(errors), **totals}
