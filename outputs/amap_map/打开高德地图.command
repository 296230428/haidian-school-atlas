#!/bin/zsh
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"

cd "$ROOT"
"$PY" scripts/build_amap_school_map.py || exit $?
exec "$PY" scripts/serve_amap_map.py
