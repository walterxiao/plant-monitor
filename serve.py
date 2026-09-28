#!/usr/bin/env python3
"""Plant Monitor — dashboard web server with a manual refresh endpoint.

Serves data/ over HTTP and exposes POST /api/refresh, which runs
refresh.sh in the background. Progress is tracked in
data/refresh_status.json so the dashboard's "Refresh now" button can
poll for completion.
"""
import json
import subprocess
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATUS = DATA / "refresh_status.json"


def read_status() -> dict:
    if STATUS.exists():
        try:
            return json.loads(STATUS.read_text())
        except Exception:
            pass
    return {}


def write_status(**updates) -> None:
    s = read_status()
    s.update(updates)
    STATUS.write_text(json.dumps(s))


def run_refresh() -> None:
    write_status(refresh_in_progress=True, last_error=None,
                 started=datetime.now().isoformat(timespec="seconds"))
    try:
        subprocess.run([str(ROOT / "refresh.sh")], cwd=str(ROOT),
                       timeout=1800, check=True)
    except Exception as e:  # noqa: BLE001 — report, don't crash the server
        print(f"refresh failed: {e}", flush=True)
        write_status(last_error=f"{type(e).__name__}: {e}"[:200])
    finally:
        # dashboard.py already updated last_refresh; just clear the flag
        write_status(refresh_in_progress=False)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DATA), **kwargs)

    def do_POST(self):  # noqa: N802 — http.server naming
        if self.path != "/api/refresh":
            self.send_error(404)
            return
        if read_status().get("refresh_in_progress"):
            body = b'{"status":"already running"}'
            self.send_response(409)
        else:
            threading.Thread(target=run_refresh, daemon=True).start()
            body = b'{"status":"refresh started"}'
            self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # quiet


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("Dashboard at http://localhost:8000/dashboard/  (Ctrl+C to stop)",
          flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
