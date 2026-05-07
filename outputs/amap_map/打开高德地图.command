#!/bin/zsh
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"

cd "$ROOT"
exec "$PY" scripts/serve_amap_map.py
