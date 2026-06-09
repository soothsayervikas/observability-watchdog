#!/usr/bin/env python3
"""Local webhook receiver for demo alert delivery."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.core.webhook_signing import verify_webhook_signature

WEBHOOK_HMAC_SECRET = os.environ.get("WEBHOOK_HMAC_SECRET", "")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body)
        signature = self.headers.get("X-Webhook-Signature", "")

        if WEBHOOK_HMAC_SECRET:
            if not verify_webhook_signature(WEBHOOK_HMAC_SECRET, payload, signature):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"invalid_signature"}')
                print("\n--- Webhook rejected: invalid HMAC signature ---")
                return

        print("\n--- Webhook received ---")
        print(json.dumps(payload, indent=2))
        if signature:
            print(f"Signature verified: {signature[:20]}...")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"received"}')

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock webhook receiver")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    host, port = args.host, args.port
    server = HTTPServer((host, port), WebhookHandler)
    if WEBHOOK_HMAC_SECRET:
        print("HMAC verification enabled (WEBHOOK_HMAC_SECRET set)")
    print(f"Mock webhook listening on http://{host}:{port}/webhook")
    server.serve_forever()
