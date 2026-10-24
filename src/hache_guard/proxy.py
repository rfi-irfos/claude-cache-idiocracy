from __future__ import annotations

import argparse
import http.client
import json
import os
import sqlite3
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class Budget:
    def __init__(self):
        path = os.environ.get("HACHE_PROXY_STATE", "~/.claude/hache-proxy.sqlite3").replace("~", os.path.expanduser("~"))
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK(id=1), input_tokens INTEGER NOT NULL DEFAULT 0)")
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


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        target = os.environ.get("HACHE_UPSTREAM", "https://api.anthropic.com")
        parsed = urlsplit(target)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        # Conservative preflight estimate; response usage, when present, is charged below.
        budget = Budget()
        if not budget.charge(max(1, len(body) // 4)):
            budget.close()
            self.send_error(429, "hache local input budget exceeded")
            return
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=120)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length"}}
        connection.request("POST", parsed.path.rstrip("/") + self.path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        try:
            usage = (json.loads(payload) or {}).get("usage") or {}
            actual = int(usage.get("input_tokens", 0) or 0) + int(usage.get("cache_read_input_tokens", 0) or 0)
            if actual:
                # The estimate is already charged; actual usage is retained as observability only.
                self.log_message("provider_input_tokens=%s", actual)
        except (ValueError, TypeError):
            pass
        budget.close()
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in {"transfer-encoding", "connection"}:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=47831)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), ProxyHandler).serve_forever()
    return 0
