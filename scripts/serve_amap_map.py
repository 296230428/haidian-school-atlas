import http.server
import socket
import socketserver
import sys
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "outputs" / "amap_map"
HTML_NAME = "海淀小学高德互动地图.html"
PORT = 8765
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}/{urllib.request.pathname2url(HTML_NAME)}"


def healthy():
    try:
        with urllib.request.urlopen(URL, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def port_is_taken():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((HOST, PORT)) == 0


class ReusableThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    if not (ROOT / HTML_NAME).exists():
        raise SystemExit(f"Missing map HTML: {ROOT / HTML_NAME}")

    if healthy():
        print(URL)
        webbrowser.open(URL)
        return

    if port_is_taken():
        raise SystemExit(
            f"Port {PORT} is already in use but did not return the map page. "
            "Stop the stale process or change PORT in scripts/serve_amap_map.py."
        )

    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=ROOT, **kwargs)
    with ReusableThreadingTCPServer((HOST, PORT), handler) as server:
        print(URL)
        webbrowser.open(URL)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
            sys.exit(0)


if __name__ == "__main__":
    main()
