from __future__ import annotations

import argparse
import http.client
import os
import sqlite3
import time
import uuid
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class Budget:
    def __init__(self):
        path = os.environ.get("HACHE_PROXY_STATE", "~/.claude/hache-proxy.sqlite3").replace("~", os.path.expanduser("~"))
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK(id=1), input_tokens INTEGER NOT NULL DEFAULT 0)")
        self.db.execute("CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, estimated_tokens INTEGER, actual_input_tokens INTEGER, status INTEGER, latency_ms REAL)")
        self.db.execute("INSERT OR IGNORE INTO budget(id,input_tokens) VALUES(1,0)")
        self.db.commit()

    def charge(self, tokens: int) -> bool:
        limit = int(os.environ.get("HACHE_PROXY_INPUT_BUDGET", "250000000"))
        self.db.execute("BEGIN IMMEDIATE")
        current = self.db.execute("SELECT input_tokens FROM budget WHERE id=1").fetchone()[0]
        if current + tokens > limit:
            self.db.rollback()
            return False
        self.db.execute("UPDATE budget SET input_tokens=input_tokens+? WHERE id=1", (tokens,))
        self.db.commit()
        return True

    def close(self):
        self.db.close()

    def record(self, request_id: str, estimated: int, actual: int | None, status: int, latency_ms: float):
        self.db.execute("INSERT OR REPLACE INTO requests VALUES (?,?,?,?,?)", (request_id, estimated, actual, status, latency_ms))
        self.db.commit()


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        target = os.environ.get("HACHE_UPSTREAM", "https://api.anthropic.com")
        parsed = urlsplit(target)
        if parsed.scheme != "https" or not parsed.hostname:
            self.send_error(502, "invalid HTTPS Hache upstream")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "invalid content length")
            return
        if length < 0 or length > int(os.environ.get("HACHE_PROXY_MAX_BODY_BYTES", "20000000")):
            self.send_error(413, "request body exceeds local Hache limit")
            return
        body = self.rfile.read(length)
        # Conservative preflight estimate; response usage, when present, is charged below.
        budget = Budget()
        estimated = max(1, len(body) // 4)
        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        if not budget.charge(estimated):
            budget.record(request_id, estimated, None, 429, (time.perf_counter() - started) * 1000)
            budget.close()
            self.send_error(429, "hache local input budget exceeded")
            return
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=120)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length"}}
        upstream_path = parsed.path.rstrip("/") + self.path
        if parsed.query:
            upstream_path += "?" + parsed.query
        connection.request("POST", upstream_path, body=body, headers=headers)
        response = connection.getresponse()
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in {"transfer-encoding", "connection"}:
                self.send_header(key, value)
        self.end_headers()
        # Stream SSE and ordinary responses without buffering or altering provider output.
        actual = None
        line_buffer = b""
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            line_buffer += chunk
            while b"\n" in line_buffer:
                line, line_buffer = line_buffer.split(b"\n", 1)
                if b"data:" in line and b"usage" in line:
                    try:
                        event = json.loads(line.split(b"data:", 1)[1].strip())
                        usage = event.get("usage") or {}
                        candidate = int(usage.get("input_tokens", 0) or 0) + int(usage.get("cache_read_input_tokens", 0) or 0)
                        if candidate:
                            actual = candidate
                    except (ValueError, TypeError, json.JSONDecodeError):
                        pass
            self.wfile.write(chunk)
            self.wfile.flush()
        budget.record(request_id, estimated, actual, response.status, (time.perf_counter() - started) * 1000)
        budget.close()

    def log_message(self, *_args):
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=47831)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), ProxyHandler).serve_forever()
    return 0
