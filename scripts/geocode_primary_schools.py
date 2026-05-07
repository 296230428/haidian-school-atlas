import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


INPUT = Path("outputs/ranking_data/ranking_rows.json")
CACHE = Path("outputs/map/primary_school_geocodes.json")


def valid_beijing(result):
    try:
        lat = float(result["lat"])
        lon = float(result["lon"])
    except Exception:
        return False
    return 39.75 <= lat <= 40.25 and 115.85 <= lon <= 116.75


def request_json(url):
    req = Request(
        url,
        headers={
            "User-Agent": "Codex local school map generation contact: local-user",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.3",
        },
    )
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode(query):
    params = urlencode({"format": "jsonv2", "limit": 5, "q": query})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    data = request_json(url)
    for item in data:
        if valid_beijing(item):
            return {
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "display_name": item.get("display_name", ""),
                "class": item.get("class", ""),
                "type": item.get("type", ""),
                "query": query,
                "source": "Nominatim/OpenStreetMap",
            }
    return None


def main():
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    schools = [r for r in payload["rows"] if r["办学层次"] == "小学"]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    for idx, row in enumerate(schools, 1):
        name = row["学校名称"]
        if name in cache and cache[name].get("lat") and cache[name].get("lon"):
            print(f"{idx:02d}/{len(schools)} cached {name}")
            continue

        queries = [
            name,
            f"{name} 海淀区 北京",
            row["学校地址"],
            f"{name} {row['学校地址']}",
        ]
        found = None
        for q in queries:
            try:
                found = geocode(q)
            except Exception as exc:
                found = None
                print(f"query failed: {q}: {exc}")
            time.sleep(1.1)
            if found:
                break

        cache[name] = {
            "学校名称": name,
            "学校地址": row["学校地址"],
            "综合排名": row["综合排名"],
            "综合热度分": row["综合热度分"],
            "民间等级/梯队": row["民间等级/梯队"],
            "入学难度": row["入学难度"],
            **(found or {"lat": None, "lon": None, "source": "未匹配"}),
        }
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "ok" if found else "missing"
        print(f"{idx:02d}/{len(schools)} {status} {name}")

    matched = sum(1 for item in cache.values() if item.get("lat") and item.get("lon"))
    print(f"matched {matched}/{len(schools)}")


if __name__ == "__main__":
    main()
