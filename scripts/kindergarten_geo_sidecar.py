"""幼儿园坐标写回 sidecar：监听本地一个独立端口（默认 8766），
接收浏览器 POST 来的坐标并增量写入 outputs/kindergarten/data/kindergarten_geocodes.json。

用法：
    python3 scripts/kindergarten_geo_sidecar.py        # 监听 127.0.0.1:8766
    python3 scripts/kindergarten_geo_sidecar.py 8770   # 自定义端口

API:
    GET  /geo               -> 当前缓存 {园所名称: 条目}
    POST /geo  body=JSON    -> upsert 单条
    POST /geo/clear         -> 清空
"""

import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GEO_CACHE = PROJECT_ROOT / "outputs" / "kindergarten" / "data" / "kindergarten_geocodes.json"
HOST = "127.0.0.1"
DEFAULT_PORT = 8766
LOCK = threading.Lock()


def load_cache():
    if not GEO_CACHE.exists():
        return {}
    try:
        return json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache):
    GEO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = GEO_CACHE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(GEO_CACHE)


class ReusableServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/geo"):
            with LOCK:
                cache = load_cache()
            self._send_json(200, {"count": len(cache), "items": cache})
            return
        self._send_json(404, {"ok": False})

    def do_POST(self):
        if self.path.startswith("/geo/clear"):
            with LOCK:
                save_cache({})
            self._send_json(200, {"ok": True, "count": 0})
            return
        if self.path.startswith("/geo"):
            length = int(self.headers.get("Content-Length", 0) or 0)
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception:
                self._send_json(400, {"ok": False, "error": "invalid json"})
                return
            name = (payload.get("园所名称") or payload.get("name") or "").strip()
            if not name:
                self._send_json(400, {"ok": False, "error": "missing 园所名称"})
                return
            with LOCK:
                cache = load_cache()
                cache[name] = payload
                save_cache(cache)
                count = len(cache)
            self._send_json(200, {"ok": True, "count": count})
            return
        self._send_json(404, {"ok": False})

    # silence noisy default logging
    def log_message(self, format, *args):
        sys.stderr.write("[geo-sidecar] " + (format % args) + "\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    print(f"kindergarten geo sidecar listening on http://{HOST}:{port}")
    print(f"writing to {GEO_CACHE}")
    with ReusableServer((HOST, port), Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
