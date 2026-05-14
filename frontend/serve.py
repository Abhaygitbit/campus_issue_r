#!/usr/bin/env python3
"""No-cache HTTP server for frontend development."""
from http.server import SimpleHTTPRequestHandler, HTTPServer

class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        pass  # silence logs

if __name__ == "__main__":
    server = HTTPServer(("", 3000), NoCacheHandler)
    print("Frontend serving at http://localhost:3000 (no-cache mode)")
    server.serve_forever()
