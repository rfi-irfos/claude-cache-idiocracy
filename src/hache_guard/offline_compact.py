from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .handover import write
from .metrics import transcript_usage


def compact(transcript: str | Path, replace: bool = False) -> Path:
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
            elif isinstance(content, str):
                text = content.strip()
            else:
                text = ""
            if text and message.get("role") in ("user", "assistant"):
                recent.append({"role": message["role"], "text": re.sub(r"\s+", " ", text)[-1000:]})
            for key in ("file_path", "path", "notebook_path"):
                value = (row.get("tool_input") or {}).get(key)
                if isinstance(value, str) and value.startswith(("/", "~")):
                    files.add(value)
    metrics = transcript_usage(path)
    handover = write(
        "offline_compaction",
        {
            "source_transcript": str(path),
            "metrics": metrics,
            "recent_messages": recent[-20:],
            "files_seen": sorted(files)[-200:],
            "note": "Deterministic local summary. With --replace, the original is archived before its path is replaced by this summary.",
        },
    )
    if replace:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = path.with_name(f"{path.stem}.full-{stamp}.jsonl")
        shutil.move(str(path), str(archive))
        summary = {
            "type": "user",
            "sessionId": path.stem,
            "isCompactSummary": True,
            "isVisibleInTranscriptOnly": True,
            "message": {
                "role": "user",
                "content": (
                    "Offline compact summary. Full transcript archived at: " + str(archive) +
                    "\nHandover: " + str(handover) +
                    "\nMetrics: " + json.dumps(metrics, sort_keys=True) +
                    "\nRecent work: " + json.dumps(recent[-20:], ensure_ascii=False)
                ),
            },
        }
        path.write_text(json.dumps(summary, ensure_ascii=False) + "\n", encoding="utf-8")
    return handover
