from __future__ import annotations

import json
import re
from pathlib import Path

from .handover import write
from .metrics import transcript_usage


def compact(transcript: str | Path) -> Path:
    path = Path(transcript)
    recent = []
    files = set()
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = row.get("message") or {}
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                texts = [x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text"]
                text = " ".join(texts).strip()
                if text and message.get("role") in ("user", "assistant"):
                    recent.append({"role": message["role"], "text": re.sub(r"\s+", " ", text)[-1000:]})
            for key in ("file_path", "path", "notebook_path"):
                value = (row.get("tool_input") or {}).get(key)
                if isinstance(value, str) and value.startswith(("/", "~")):
                    files.add(value)
    metrics = transcript_usage(path)
    return write(
        "offline_compaction",
        {
            "source_transcript": str(path),
            "metrics": metrics,
            "recent_messages": recent[-20:],
            "files_seen": sorted(files)[-200:],
            "note": "Deterministic local summary. Original transcript remains untouched.",
        },
    )
