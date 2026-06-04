"""为海淀幼儿园招生名录中的园所地址做高德地理编码（GCJ02）。

读取:    outputs/kindergarten/data/kindergarten_rows.json
缓存:    outputs/kindergarten/data/kindergarten_geocodes.json

使用方法:

    export AMAP_KEY=你的高德 Web 服务 Key   # 不是 Web JS API Key
    python3 scripts/geocode_kindergartens.py

如果只想跑一个小范围测试，加 --limit N。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs/kindergarten/data/kindergarten_rows.json"
CACHE = ROOT / "outputs/kindergarten/data/kindergarten_geocodes.json"


def load_env_local() -> None:
    env_path = ROOT / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def amap_geocode(address: str, key: str) -> dict | None:
    params = urlencode(
        {"key": key, "address": address, "city": "北京", "output": "JSON"}
    )
    url = f"https://restapi.amap.com/v3/geocode/geo?{params}"
    req = Request(
        url,
        headers={
            "User-Agent": "Codex haidian kindergarten map (local)",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"_error": str(exc)}
    if data.get("status") != "1":
        return {"_error": f"status={data.get('status')} info={data.get('info')}"}
    geocodes = data.get("geocodes") or []
    if not geocodes:
        return None
    best = geocodes[0]
    location = best.get("location", "")
    if "," not in location:
        return None
    lon_str, lat_str = location.split(",", 1)
    return {
        "lat": float(lat_str),
        "lon": float(lon_str),
        "formatted_address": best.get("formatted_address", ""),
        "level": best.get("level", ""),
        "adcode": best.get("adcode", ""),
        "district": best.get("district", ""),
        "source": "AMap/restapi.geocode",
        "raw_query": address,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 条 (0=全部)")
    parser.add_argument("--sleep", type=float, default=0.2, help="每次请求间隔秒")
    args = parser.parse_args()

    load_env_local()
    key = os.environ.get("AMAP_KEY")
    if not key or "your_amap" in key:
        print("缺少 AMAP_KEY，请配置高德 Web 服务 Key", file=sys.stderr)
        return 2

    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    rows = payload["rows"]
    if args.limit > 0:
        rows = rows[: args.limit]

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    matched = 0
    for idx, row in enumerate(rows, 1):
        name = row["园所名称"]
        address = row["地址信息"]
        if name in cache and cache[name].get("lat") and cache[name].get("lon"):
            matched += 1
            print(f"{idx:03d}/{len(rows)} cached {name}")
            continue

        queries = [
            f"{address} {name}",
            address,
            f"海淀区{address}" if not address.startswith("海淀区") else address,
            name,
        ]
        seen: set[str] = set()
        found: dict | None = None
        last_error: str | None = None
        for q in queries:
            if q in seen:
                continue
            seen.add(q)
            result = amap_geocode(q, key)
            time.sleep(args.sleep)
            if result is None:
                continue
            if result.get("_error"):
                last_error = result["_error"]
                continue
            found = result
            break

        cache[name] = {
            "园所名称": name,
            "街道": row["街道"],
            "园所性质": row["园所性质"],
            "地址信息": address,
            "招生咨询联系人": row["招生咨询联系人"],
            "招生咨询时间": row["招生咨询时间"],
            **(
                found
                if found
                else {
                    "lat": None,
                    "lon": None,
                    "source": "未匹配",
                    "error": last_error,
                }
            ),
        }
        if found:
            matched += 1
        CACHE.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        status = "ok" if found else "missing"
        print(f"{idx:03d}/{len(rows)} {status} {name}")

    print(f"matched {matched}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
