import io
import json
import math
import time
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


GEOCODES = Path("outputs/map/primary_school_geocodes.json")
OUT = Path("outputs/map/海淀小学地图标注.png")
TILE_DIR = Path("outputs/map/tiles")

MANUAL = {
    "北京市海淀区中关村第三小学": (39.9758, 116.2992),
    "中国人民大学附属中学实验小学": (39.9802, 116.3265),
    "北京师范大学实验小学": (39.9598, 116.3658),
    "中国农业科学院附属小学": (39.9556, 116.3223),
    "北京市海淀区中关村第一小学科学城分校": (40.0502, 116.1691),
    "北京市海淀区中关村第二小学西山分校": (39.9669, 116.2418),
    "北京医科大学附属小学": (39.9822, 116.3569),
    "北京航空航天大学附属小学": (39.9818, 116.3483),
    "中国人民大学附属小学亮甲店分校": (39.9385, 116.2738),
    "中国人民大学附属小学银燕分校": (39.9677, 116.2812),
    "首都师范大学附属中学第一小学": (39.9322, 116.2912),
    "清华大学附属小学清河分校": (40.0362, 116.3339),
    "北京市海淀区五一未来实验小学": (39.9090, 116.2637),
    "北京市海淀区实验小学紫竹分校": (39.9445, 116.3072),
    "北京交通大学附属小学": (39.9522, 116.3448),
    "北京外国语大学附属小学": (39.9498, 116.3206),
    "北京市第二十中学附属育鹰小学": (40.0402, 116.3337),
    "首都师范大学附属花园小学": (39.9391, 116.3078),
    "北京市海淀区实验小学九一分校": (39.9810, 116.3532),
    "北京市海淀区教科院培英未来实验小学": (39.9059, 116.2682),
    "北京市海淀区教师进修学校附属实验小学": (39.9582, 116.2540),
    "北京市海淀区翠湖小学": (40.0872, 116.1576),
    "北京市海淀区航天图强小学": (39.9062, 116.2648),
    "北京邮电大学附属小学": (39.9617, 116.3590),
    "首都师范大学实验小学": (39.9408, 116.3324),
    "首都师范大学附属定慧里小学": (39.9286, 116.2768),
    "北京市海淀区教科院台头未来实验小学": (40.0918, 116.0914),
    "北京市海淀区第二实验小学安宁分校": (40.0416, 116.3445),
}

LABEL_TOP_N = 28
ZOOM = 12
TILE_SIZE = 256
PAD_TILES = 1
MAP_W, MAP_H = 2200, 1500
SIDE_W = 620
CANVAS_W, CANVAS_H = MAP_W + SIDE_W, MAP_H


def font(size, bold=False):
    choices = [
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ]
    for path in choices:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE = font(36, True)
F_SUB = font(20)
F_TEXT = font(18)
F_SMALL = font(15)
F_LABEL = font(16, True)


def latlon_to_world(lat, lon, z=ZOOM):
    lat_rad = math.radians(lat)
    n = 2**z * TILE_SIZE
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def world_to_latlon(x, y, z=ZOOM):
    n = 2**z * TILE_SIZE
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    return math.degrees(lat_rad), lon


def tile_url(x, y, z=ZOOM):
    return f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"


def fetch_tile(x, y, z=ZOOM):
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    path = TILE_DIR / f"{z}_{x}_{y}.png"
    if path.exists():
        return Image.open(path).convert("RGB")
    req = Request(tile_url(x, y, z), headers={"User-Agent": "Codex local school map rendering"})
    with urlopen(req, timeout=20) as resp:
        data = resp.read()
    path.write_bytes(data)
    time.sleep(0.15)
    return Image.open(io.BytesIO(data)).convert("RGB")


def marker_color(rank):
    if rank <= 15:
        return (206, 58, 58)
    if rank <= 45:
        return (238, 151, 42)
    return (55, 126, 184)


def text_box(draw, xy, text, fill, outline=(255, 255, 255)):
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=F_LABEL)
    pad_x, pad_y = 5, 3
    rect = (bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y)
    draw.rounded_rectangle(rect, radius=4, fill=(255, 255, 255, 230), outline=fill, width=1)
    draw.text((x, y), text, font=F_LABEL, fill=fill)


def main():
    data = json.loads(GEOCODES.read_text(encoding="utf-8"))
    points = []
    for item in data.values():
        name = item["学校名称"]
        lat, lon = item.get("lat"), item.get("lon")
        source = item.get("source", "")
        precision = "OSM"
        if not lat or not lon:
            lat, lon = MANUAL[name]
            precision = "地址近似"
        points.append({**item, "lat": float(lat), "lon": float(lon), "precision": precision, "source": source})

    min_lat = min(p["lat"] for p in points) - 0.012
    max_lat = max(p["lat"] for p in points) + 0.012
    min_lon = min(p["lon"] for p in points) - 0.018
    max_lon = max(p["lon"] for p in points) + 0.018

    x0, y1 = latlon_to_world(min_lat, min_lon)
    x1, y0 = latlon_to_world(max_lat, max_lon)
    tx0 = math.floor(min(x0, x1) / TILE_SIZE) - PAD_TILES
    tx1 = math.ceil(max(x0, x1) / TILE_SIZE) + PAD_TILES
    ty0 = math.floor(min(y0, y1) / TILE_SIZE) - PAD_TILES
    ty1 = math.ceil(max(y0, y1) / TILE_SIZE) + PAD_TILES

    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * TILE_SIZE, (ty1 - ty0 + 1) * TILE_SIZE), (244, 244, 244))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            try:
                tile = fetch_tile(tx, ty)
            except Exception:
                tile = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (238, 238, 238))
            mosaic.paste(tile, ((tx - tx0) * TILE_SIZE, (ty - ty0) * TILE_SIZE))

    # Crop to data bounds and resize into the fixed map panel.
    crop_left = int(min(x0, x1) - tx0 * TILE_SIZE)
    crop_top = int(min(y0, y1) - ty0 * TILE_SIZE)
    crop_right = int(max(x0, x1) - tx0 * TILE_SIZE)
    crop_bottom = int(max(y0, y1) - ty0 * TILE_SIZE)
    crop = mosaic.crop((crop_left, crop_top, crop_right, crop_bottom)).resize((MAP_W, MAP_H), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), (248, 249, 250))
    canvas.paste(crop, (0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, MAP_W - 1, MAP_H - 1), outline=(120, 120, 120), width=2)

    def project(lat, lon):
        x, y = latlon_to_world(lat, lon)
        px = (x - min(x0, x1)) / (max(x0, x1) - min(x0, x1)) * MAP_W
        py = (y - min(y0, y1)) / (max(y0, y1) - min(y0, y1)) * MAP_H
        return int(px), int(py)

    # Draw lower ranked first so stronger markers stay visible.
    for p in sorted(points, key=lambda row: row["综合排名"], reverse=True):
        x, y = project(p["lat"], p["lon"])
        rank = int(p["综合排名"])
        r = 12 if rank <= 15 else 9 if rank <= 45 else 7
        color = marker_color(rank)
        outline = (30, 30, 30) if p["precision"] == "OSM" else (255, 255, 255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color + (220,), outline=outline + (255,), width=2)
        if p["precision"] != "OSM":
            draw.line((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 220), width=2)

    label_offsets = [(10, -24), (10, 8), (-140, -24), (-140, 8), (14, -2)]
    used = []
    for p in sorted(points, key=lambda row: row["综合排名"])[:LABEL_TOP_N]:
        x, y = project(p["lat"], p["lon"])
        text = f"{int(p['综合排名'])}.{p['学校名称'].replace('北京市海淀区', '').replace('北京', '')}"
        color = marker_color(int(p["综合排名"]))
        placed = False
        for dx, dy in label_offsets:
            bbox = draw.textbbox((x + dx, y + dy), text, font=F_LABEL)
            padded = (bbox[0] - 6, bbox[1] - 4, bbox[2] + 6, bbox[3] + 4)
            if all(padded[2] < u[0] or padded[0] > u[2] or padded[3] < u[1] or padded[1] > u[3] for u in used):
                draw.line((x, y, x + dx, y + dy + 8), fill=color + (190,), width=2)
                text_box(draw, (x + dx, y + dy), text, color)
                used.append(padded)
                placed = True
                break
        if not placed:
            draw.text((x + 8, y + 8), str(int(p["综合排名"])), font=F_SMALL, fill=(20, 20, 20))

    side_x = MAP_W
    draw.rectangle((side_x, 0, CANVAS_W, CANVAS_H), fill=(255, 255, 255, 245))
    draw.text((side_x + 32, 28), "海淀区小学地图标注", font=F_TITLE, fill=(32, 42, 54))
    draw.text((side_x + 32, 82), "仅保留原表“办学层次=小学”的 89 所学校", font=F_SUB, fill=(70, 80, 92))
    draw.text((side_x + 32, 112), "点位来自 OSM 地理编码；白叉为按地址近似补点。", font=F_SUB, fill=(70, 80, 92))

    legend_y = 165
    for label, color in [
        ("综合排名 1-15", (206, 58, 58)),
        ("综合排名 16-45", (238, 151, 42)),
        ("综合排名 46-89", (55, 126, 184)),
    ]:
        draw.ellipse((side_x + 36, legend_y - 8, side_x + 56, legend_y + 12), fill=color + (230,), outline=(40, 40, 40), width=1)
        draw.text((side_x + 70, legend_y - 12), label, font=F_TEXT, fill=(40, 40, 40))
        legend_y += 34
    draw.line((side_x + 38, legend_y - 5, side_x + 56, legend_y + 13), fill=(255, 255, 255), width=3)
    draw.ellipse((side_x + 36, legend_y - 8, side_x + 56, legend_y + 12), outline=(80, 80, 80), width=2)
    draw.text((side_x + 70, legend_y - 12), "地址近似补点", font=F_TEXT, fill=(40, 40, 40))

    top = sorted(points, key=lambda row: row["综合排名"])[:20]
    y = 315
    draw.text((side_x + 32, y), "前 20 名", font=font(24, True), fill=(32, 42, 54))
    y += 42
    for p in top:
        name = p["学校名称"].replace("北京市海淀区", "").replace("北京", "")
        if len(name) > 17:
            name = name[:16] + "…"
        line = f"{int(p['综合排名']):>2}. {name}"
        draw.text((side_x + 36, y), line, font=F_TEXT, fill=marker_color(int(p["综合排名"])))
        y += 30

    precise = sum(1 for p in points if p["precision"] == "OSM")
    approx = len(points) - precise
    note_y = CANVAS_H - 150
    draw.line((side_x + 32, note_y - 18, CANVAS_W - 32, note_y - 18), fill=(220, 225, 230), width=1)
    draw.text((side_x + 32, note_y), f"标注数量：{len(points)} 所小学", font=F_TEXT, fill=(40, 40, 40))
    draw.text((side_x + 32, note_y + 30), f"OSM 命中：{precise}；地址近似：{approx}", font=F_TEXT, fill=(40, 40, 40))
    draw.text((side_x + 32, note_y + 60), "底图 © OpenStreetMap contributors", font=F_SMALL, fill=(95, 105, 115))
    draw.text((side_x + 32, note_y + 85), "生成日期：2026-04-25", font=F_SMALL, fill=(95, 105, 115))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT)
    print(f"saved {OUT}")
    print(f"points={len(points)} precise={precise} approximate={approx}")


if __name__ == "__main__":
    main()
