from __future__ import annotations

import argparse
import http.client
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        target = os.environ.get("HACHE_UPSTREAM", "https://api.anthropic.com")
        parsed = urlsplit(target)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=120)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length"}}
        connection.request("POST", parsed.path.rstrip("/") + self.path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
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
