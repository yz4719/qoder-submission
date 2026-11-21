#!/usr/bin/env python3
"""LeadGuard dashboard server.

Serves dashboard/live.html plus the local decision artifacts, and proxies
read-only Cloud Agents requests so the Qoder PAT never reaches the browser.

    python3 dashboard/serve.py          # http://127.0.0.1:8765
    QODER_PAT=... python3 dashboard/serve.py

The PAT is read from the environment or from a gitignored .env at the repo root.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard"
STATE = DASH / "data" / "state.json"
DECISIONS = DASH / "data" / "decisions.jsonl"

CLOUD_API = os.environ.get("QODER_CLOUD_API", "https://api.qoder.com/api/v1/cloud")
CLOUD_PREFIXES = ("sessions", "agents", "templates", "schedules")
PORT = int(os.environ.get("PORT", "8765"))


def load_dotenv():
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def cloud_get(path, query):
    """Proxy one GET to the Cloud Agents API. Returns (status, body_bytes)."""
    pat = os.environ.get("QODER_PAT", "").strip()
    if not pat:
        return 503, json.dumps({
            "error": "QODER_PAT not configured",
            "hint": "Create a token at https://qoder.com/cloud/pat-keys and put "
                    "QODER_PAT=... in the gitignored .env, then restart this server.",
        }).encode()

    url = f"{CLOUD_API}/{path}"
    if query:
        url += "?" + query
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {pat}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        return 502, json.dumps({"error": f"cloud API unreachable: {exc.reason}"}).encode()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASH), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[dashboard] {fmt % args}", flush=True)

    def send_body(self, status, body, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path

        if route in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/live.html")
            self.end_headers()
            return

        if route == "/api/state":
            state = read_json(STATE)
            if state is None:
                return self.send_body(404, b'{"error":"dashboard/data/state.json missing"}')
            return self.send_body(200, json.dumps(state).encode())

        if route == "/api/decisions":
            return self.send_body(200, json.dumps(read_jsonl(DECISIONS)).encode())

        if route.startswith("/api/cloud/"):
            rest = route[len("/api/cloud/"):]
            prefix = rest.split("/", 1)[0]
            if prefix not in CLOUD_PREFIXES:
                return self.send_body(400, json.dumps({
                    "error": "unsupported cloud path",
                    "allowed": list(CLOUD_PREFIXES),
                }).encode())
            status, body = cloud_get(rest, parsed.query)
            return self.send_body(status, body)

        return super().do_GET()


def main():
    load_dotenv()
    pat = os.environ.get("QODER_PAT", "").strip()
    print(f"LeadGuard dashboard  http://127.0.0.1:{PORT}/live.html")
    print(f"cloud API            {CLOUD_API}")
    print(f"PAT                  {'configured' if pat else 'MISSING (local panels only)'}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
