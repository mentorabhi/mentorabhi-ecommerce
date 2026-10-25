"""Local Prometheus exporter for service readiness and dependency reachability."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import time
from urllib.error import URLError
from urllib.request import urlopen

if os.getenv("HEALTH_TARGETS_FILE"):
    TARGETS_FILE = Path(os.environ["HEALTH_TARGETS_FILE"])
else:
    TARGETS_FILE = Path(__file__).resolve().parents[2] / "devops/observability/health-targets.json"
with TARGETS_FILE.open(encoding="utf-8") as targets_file:
    TARGETS = json.load(targets_file)


def probe(target):
    started = time.monotonic()
    try:
        if target["url"].startswith("tcp://"):
            host_port = target["url"][6:].rsplit(":", 1)
            with socket.create_connection((host_port[0], int(host_port[1])), timeout=0.7):
                pass
        else:
            with urlopen(target["url"], timeout=0.7) as response:
                if response.status != 200:
                    raise URLError(f"unexpected status {response.status}")
        up = 1
    except (OSError, ValueError, URLError, TimeoutError):
        up = 0
    return target["name"], up, time.monotonic() - started


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok\n"); return
        if self.path != "/metrics":
            self.send_error(404); return
        with ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(probe, TARGETS))
        body = ["# HELP supersports_service_up Whether a local service readiness probe succeeded.",
                "# TYPE supersports_service_up gauge",
                "# HELP supersports_service_probe_seconds Duration of the latest readiness probe.",
                "# TYPE supersports_service_probe_seconds gauge"]
        for name, up, elapsed in rows:
            escaped = name.replace("\\", "\\\\").replace('"', '\\"')
            body.append(f'supersports_service_up{{service="{escaped}"}} {up}')
            body.append(f'supersports_service_probe_seconds{{service="{escaped}"}} {elapsed:.6f}')
        encoded = ("\n".join(body) + "\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers(); self.wfile.write(encoded)

    def log_message(self, _format, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9108), Handler).serve_forever()
