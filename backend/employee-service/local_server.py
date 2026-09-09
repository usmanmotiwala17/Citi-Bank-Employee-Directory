"""
Local-only HTTP server for the Employee Directory service.

Wraps the same `handler()` used by the AWS Lambda deployment behind a plain
Python http.server, so you can hit the API with curl/Postman/a browser
instead of calling handler() with hand-built event dicts.

This is NOT part of the actual Lambda deployment path - in AWS, API Gateway
invokes handler() directly. This file exists purely so you can run the
service locally (e.g. against a Vite dev server on localhost:5173) during
development.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from function import handler

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "*",
}


class LambdaProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_OPTIONS(self):
        self.send_response(204)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def _handle(self, method):
        path = urlsplit(self.path).path

        content_length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length else None

        event = {
            "httpMethod": method,
            "path": path,
            "headers": dict(self.headers.items()),
            "body": raw_body,
        }

        result = handler(event)

        self.send_response(result.get("statusCode", 500))
        for key, value in (result.get("headers") or {}).items():
            self.send_header(key, value)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

        body = result.get("body") or ""
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        print(f"  {self.address_string()} - {format % args}")


def main():
    port = int(os.getenv("LOCAL_PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), LambdaProxyHandler)

    print("=" * 60)
    print("Employee Directory - local dev server")
    print(f"  Listening on: http://localhost:{port}")
    print("  (This wraps handler() directly - not used in the real")
    print("   Lambda deployment, which goes through API Gateway.)")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
