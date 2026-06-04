"""本地启动高德地图静态页面（小学/幼儿园）并把幼儿园坐标解析结果写回工程。

使用:
    python3 scripts/serve_amap_map.py              # 默认开小学页
    python3 scripts/serve_amap_map.py kindergarten # 开幼儿园页

幼儿园页面在解析每个园所坐标时会 POST 到 /api/kindergarten/geo,
本脚本会以「单条 upsert」的方式把数据写入
outputs/kindergarten/data/kindergarten_geocodes.json。
"""

import http.server
import json
import socket
import socketserver
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / "outputs" / "amap_map"
GEO_CACHE = PROJECT_ROOT / "outputs" / "kindergarten" / "data" / "kindergarten_geocodes.json"
DEFAULT_HTML = "海淀小学高德互动地图.html"
KNOWN_PAGES = {
    "primary": "海淀小学高德互动地图.html",
    "school": "海淀小学高德互动地图.html",
    "kindergarten": "海淀幼儿园高德互动地图.html",
    "yey": "海淀幼儿园高德互动地图.html",
    "yeyuan": "海淀幼儿园高德互动地图.html",
}
PORT = 8765
HOST = "127.0.0.1"

_geo_lock = threading.Lock()


def resolve_html_name(arg=None):
    if not arg:
        return DEFAULT_HTML
    if arg in KNOWN_PAGES:
        return KNOWN_PAGES[arg]
    if arg.endswith(".html"):
        return arg
    return DEFAULT_HTML


def map_url(html_name):
    version = int((ROOT / html_name).stat().st_mtime)
    encoded = urllib.request.pathname2url(html_name)
    return f"http://{HOST}:{PORT}/{encoded}?v={version}"


def healthy(html_name):
    try:
        with urllib.request.urlopen(map_url(html_name), timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def port_is_taken():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((HOST, PORT)) == 0


def _load_geo_cache():
    if not GEO_CACHE.exists():
        return {}
    try:
        return json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_geo_cache(cache):
    GEO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = GEO_CACHE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(GEO_CACHE)


class ReusableThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class AMapRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.endswith(".html") or "?v=" in self.path or self.path == "/":
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if self.path.startswith("/api/kindergarten/geo"):
            with _geo_lock:
                cache = _load_geo_cache()
            self._send_json(200, {"count": len(cache), "items": cache})
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/kindergarten/geo/clear"):
            with _geo_lock:
                _save_geo_cache({})
            self._send_json(200, {"ok": True, "count": 0})
            return
        if self.path.startswith("/api/kindergarten/geo"):
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
            with _geo_lock:
                cache = _load_geo_cache()
                cache[name] = payload
                _save_geo_cache(cache)
                count = len(cache)
            self._send_json(200, {"ok": True, "count": count})
            return
        self._send_json(404, {"ok": False, "error": "not found"})


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    html_name = resolve_html_name(arg)
    if not (ROOT / html_name).exists():
        raise SystemExit(f"Missing map HTML: {ROOT / html_name}")

    url = map_url(html_name)
    if healthy(html_name):
        print(url)
        webbrowser.open(url)
        return

    if port_is_taken():
        raise SystemExit(
            f"Port {PORT} is already in use but did not return the map page. "
            "Stop the stale process or change PORT in scripts/serve_amap_map.py."
        )

    handler = lambda *args, **kwargs: AMapRequestHandler(*args, directory=ROOT, **kwargs)
    with ReusableThreadingTCPServer((HOST, PORT), handler) as server:
        print(url)
        print(f"persisting kindergarten geocodes -> {GEO_CACHE}")
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
            sys.exit(0)


if __name__ == "__main__":
    main()
