from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .breaker import evaluate
from .handover import write
from .metrics import transcript_usage


def find_transcript(cwd: str, since: float) -> Path | None:
    root = Path(os.environ.get("CLAUDE_PROJECTS", "~/.claude/projects")).expanduser()
    if not root.exists():
        return None
    candidates = []
    for path in root.glob("**/*.jsonl"):
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_mtime >= since and stat.st_size and "/subagents/" not in str(path):
            candidates.append((stat.st_mtime, path))
    return max(candidates, default=(0, None))[1]


def run(command: list[str], interval: float = 2.0) -> int:
    started = time.time()
    process = subprocess.Popen(command)
    warned = False
    transcript = None
    try:
        while process.poll() is None:
            if transcript is None:
                transcript = find_transcript(os.getcwd(), started)
            if transcript is not None:
                metrics = transcript_usage(transcript)
                decision = evaluate(metrics)
                if decision["state"] == "warn" and not warned:
                    warned = True
                    print(
                        "hache: soft breaker reached; finish the current step and start a fresh session. "
                        f"metrics={metrics}", file=sys.stderr, flush=True
                    )
                elif decision["state"] == "break":
                    handover = write(
                        "context_budget_or_retry_threshold",
                        {
                            "cwd": os.getcwd(),
                            "transcript_reference": str(transcript),
                            "metrics": metrics,
                            "completed": [],
                            "open_tasks": ["Recover from the guarded session using the transcript reference."],
                            "files_changed": [],
                            "tests_run": [],
                            "known_failures": decision["reasons"],
                        },
                    )
                    print(f"hache: hard breaker stopped the session; handover={handover}", file=sys.stderr, flush=True)
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return 78
            time.sleep(interval)
    except KeyboardInterrupt:
        process.send_signal(signal.SIGINT)
    return process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Claude Code behind the Hache circuit breaker")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("command", nargs=argparse.REMAINDER, default=["claude"])
    args = parser.parse_args()
    command = args.command or ["claude"]
    if command[0] == "--":
        command = command[1:]
    return run(command, max(0.25, args.interval))
