import html
import io
import json
import math
from pathlib import Path

from PIL import Image


GEOCODES = Path("outputs/map/primary_school_geocodes.json")
DISTRICT_DATA = Path("outputs/school_district/data/school_district_dataset.json")
TILE_DIR = Path("outputs/map/tiles")
OUT_DIR = Path("outputs/interactive_map")
BACKGROUND = OUT_DIR / "haidian_school_map_base.png"
HTML_OUT = OUT_DIR / "海淀小学互动地图.html"

ZOOM = 12
TILE_SIZE = 256
PAD_TILES = 1
MAP_W = 2200
MAP_H = 1500

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


def latlon_to_world(lat, lon, z=ZOOM):
    lat_rad = math.radians(lat)
    n = 2**z * TILE_SIZE
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def tile_path(x, y, z=ZOOM):
    return TILE_DIR / f"{z}_{x}_{y}.png"


def marker_class(rank):
    if rank <= 15:
        return "rank-top"
    if rank <= 45:
        return "rank-mid"
    return "rank-base"


def short_name(name):
    return (
        name.replace("北京市海淀区", "")
        .replace("北京", "")
        .replace("附属", "附")
        .replace("小学", "小")
    )


def read_data():
    geocodes = json.loads(GEOCODES.read_text(encoding="utf-8"))
    district = json.loads(DISTRICT_DATA.read_text(encoding="utf-8"))
    community_by_school = {}
    for row in district["community_rows"]:
        community_by_school.setdefault(row["学校名称"], []).append(row)

    schools = []
    for row in district["detail_rows"]:
        name = row["学校名称"]
        geo = geocodes.get(name, {})
        lat = geo.get("lat")
        lon = geo.get("lon")
        precision = "OSM地理编码"
        if not lat or not lon:
            lat, lon = MANUAL[name]
            precision = "按地址近似补点"
        rank = int(row["综合排名"])
        merged = {
            **geo,
            **row,
            "lat": float(lat),
            "lon": float(lon),
            "定位方式": precision,
            "markerClass": marker_class(rank),
            "shortName": short_name(name),
            "communityRows": community_by_school.get(name, []),
        }
        schools.append(merged)
    return sorted(schools, key=lambda item: int(item["综合排名"]))


def build_background(schools):
    min_lat = min(p["lat"] for p in schools) - 0.012
    max_lat = max(p["lat"] for p in schools) + 0.012
    min_lon = min(p["lon"] for p in schools) - 0.018
    max_lon = max(p["lon"] for p in schools) + 0.018

    x0, y1 = latlon_to_world(min_lat, min_lon)
    x1, y0 = latlon_to_world(max_lat, max_lon)
    world_left, world_right = min(x0, x1), max(x0, x1)
    world_top, world_bottom = min(y0, y1), max(y0, y1)
    tx0 = math.floor(world_left / TILE_SIZE) - PAD_TILES
    tx1 = math.ceil(world_right / TILE_SIZE) + PAD_TILES
    ty0 = math.floor(world_top / TILE_SIZE) - PAD_TILES
    ty1 = math.ceil(world_bottom / TILE_SIZE) + PAD_TILES

    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * TILE_SIZE, (ty1 - ty0 + 1) * TILE_SIZE), (238, 238, 238))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            path = tile_path(tx, ty)
            if path.exists():
                tile = Image.open(path).convert("RGB")
            else:
                tile = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (238, 238, 238))
            mosaic.paste(tile, ((tx - tx0) * TILE_SIZE, (ty - ty0) * TILE_SIZE))

    crop = mosaic.crop(
        (
            int(world_left - tx0 * TILE_SIZE),
            int(world_top - ty0 * TILE_SIZE),
            int(world_right - tx0 * TILE_SIZE),
            int(world_bottom - ty0 * TILE_SIZE),
        )
    ).resize((MAP_W, MAP_H), Image.Resampling.LANCZOS)
    crop.save(BACKGROUND)

    for item in schools:
        x, y = latlon_to_world(item["lat"], item["lon"])
        item["xPct"] = round((x - world_left) / (world_right - world_left) * 100, 5)
        item["yPct"] = round((y - world_top) / (world_bottom - world_top) * 100, 5)


def page_template(schools):
    data_json = json.dumps(schools, ensure_ascii=False)
    region_options = sorted({s.get("地址片区", "") for s in schools if s.get("地址片区")})
    region_options_html = "\n".join(f'<option value="{html.escape(r)}">{html.escape(r)}</option>' for r in region_options)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>海淀小学互动地图</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; color: #1f2933; background: #eef2f5; }}
    .app {{ display: grid; grid-template-columns: 360px 1fr; min-height: 100vh; }}
    .sidebar {{ background: #ffffff; border-right: 1px solid #d8dee6; display: flex; flex-direction: column; min-width: 0; }}
    .header {{ padding: 18px 18px 12px; border-bottom: 1px solid #e3e8ef; }}
    .header h1 {{ margin: 0 0 8px; font-size: 20px; line-height: 1.25; }}
    .summary {{ margin: 0; color: #627081; font-size: 13px; line-height: 1.5; }}
    .filters {{ padding: 12px 14px; display: grid; gap: 8px; border-bottom: 1px solid #e3e8ef; }}
    input, select {{ width: 100%; height: 36px; border: 1px solid #cbd5df; border-radius: 6px; padding: 0 10px; font-size: 14px; background: #fff; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; padding: 10px 14px; border-bottom: 1px solid #e3e8ef; }}
    .stat {{ background: #f3f6f9; border: 1px solid #e0e6ed; border-radius: 6px; padding: 8px; }}
    .stat strong {{ display: block; font-size: 18px; line-height: 1; }}
    .stat span {{ display: block; margin-top: 5px; color: #677789; font-size: 12px; }}
    .school-list {{ overflow: auto; padding: 8px; flex: 1; }}
    .school-item {{ width: 100%; display: grid; grid-template-columns: 34px 1fr; gap: 9px; padding: 10px; border: 1px solid transparent; border-radius: 7px; background: transparent; text-align: left; cursor: pointer; }}
    .school-item:hover, .school-item.active {{ background: #eef6ff; border-color: #b7d7f4; }}
    .rank {{ width: 30px; height: 30px; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 13px; }}
    .rank-top {{ background: #c73f3f; }}
    .rank-mid {{ background: #d9822b; }}
    .rank-base {{ background: #2f6fb0; }}
    .school-name {{ font-size: 14px; font-weight: 650; line-height: 1.35; }}
    .school-meta {{ margin-top: 4px; color: #6b7888; font-size: 12px; line-height: 1.45; }}
    .map-shell {{ position: relative; overflow: hidden; min-width: 0; background: #dce4ea; }}
    .map-toolbar {{ position: absolute; top: 14px; left: 14px; z-index: 4; display: flex; gap: 8px; align-items: center; }}
    .tool-button {{ border: 1px solid #bac7d5; background: rgba(255,255,255,.96); border-radius: 6px; height: 34px; min-width: 34px; padding: 0 10px; font-size: 14px; cursor: pointer; box-shadow: 0 2px 8px rgba(28,39,53,.12); }}
    .legend {{ position: absolute; left: 14px; bottom: 14px; z-index: 4; background: rgba(255,255,255,.96); border: 1px solid #cfd8e3; border-radius: 7px; padding: 10px 12px; display: grid; gap: 8px; font-size: 12px; box-shadow: 0 2px 12px rgba(28,39,53,.14); }}
    .legend-row {{ display: flex; align-items: center; gap: 8px; white-space: nowrap; }}
    .dot {{ width: 12px; height: 12px; border-radius: 999px; display: inline-block; }}
    .map-stage {{ position: absolute; inset: 0; overflow: auto; cursor: grab; }}
    .map-stage.dragging {{ cursor: grabbing; }}
    .map-content {{ position: relative; width: {MAP_W}px; height: {MAP_H}px; transform-origin: 0 0; background: url("haidian_school_map_base.png") center / 100% 100% no-repeat; }}
    .marker {{ position: absolute; transform: translate(-50%, -50%); width: 22px; height: 22px; border: 2px solid #fff; border-radius: 999px 999px 999px 2px; rotate: -45deg; box-shadow: 0 2px 8px rgba(0,0,0,.28); cursor: pointer; z-index: 2; }}
    .marker::after {{ content: ""; position: absolute; inset: 5px; background: #fff; border-radius: 999px; }}
    .marker.approx {{ border-color: #1f2933; }}
    .marker.approx::before {{ content: ""; position: absolute; width: 14px; height: 2px; background: #fff; left: 2px; top: 8px; rotate: 45deg; z-index: 2; }}
    .marker.hidden {{ display: none; }}
    .marker.selected {{ width: 30px; height: 30px; z-index: 5; outline: 3px solid rgba(255,255,255,.7); }}
    .marker-label {{ position: absolute; transform: translate(11px, -28px); rotate: 45deg; padding: 2px 6px; border-radius: 5px; background: rgba(255,255,255,.95); border: 1px solid #cbd5df; color: #17202a; font-size: 12px; line-height: 18px; white-space: nowrap; pointer-events: none; box-shadow: 0 1px 5px rgba(0,0,0,.12); }}
    .detail {{ position: absolute; top: 0; right: 0; z-index: 6; width: min(520px, 92vw); height: 100%; background: #fff; border-left: 1px solid #d1d9e3; box-shadow: -12px 0 28px rgba(27,38,52,.16); transform: translateX(100%); transition: transform .18s ease; display: flex; flex-direction: column; }}
    .detail.open {{ transform: translateX(0); }}
    .detail-head {{ padding: 18px 20px 14px; border-bottom: 1px solid #e4e9f0; }}
    .detail-head h2 {{ margin: 0; font-size: 20px; line-height: 1.35; }}
    .detail-actions {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 10px; }}
    .tagline {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .tag {{ display: inline-flex; align-items: center; min-height: 24px; padding: 0 8px; border-radius: 999px; background: #eef3f8; color: #44556a; font-size: 12px; }}
    .close {{ border: 0; background: #eef2f5; border-radius: 6px; width: 32px; height: 32px; cursor: pointer; font-size: 18px; }}
    .detail-body {{ overflow: auto; padding: 16px 20px 28px; }}
    .section {{ margin-bottom: 18px; }}
    .section h3 {{ margin: 0 0 8px; font-size: 14px; color: #304256; }}
    .kv {{ display: grid; grid-template-columns: 116px 1fr; gap: 8px 12px; font-size: 13px; line-height: 1.5; }}
    .kv div:nth-child(odd) {{ color: #66778a; }}
    .long-text {{ white-space: pre-wrap; max-height: 260px; overflow: auto; padding: 10px; background: #f7f9fb; border: 1px solid #e0e6ee; border-radius: 6px; font-size: 12px; line-height: 1.6; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{ padding: 5px 8px; border: 1px solid #d8e1eb; background: #f8fafc; border-radius: 999px; font-size: 12px; }}
    a {{ color: #1b66a9; word-break: break-all; }}
    @media (max-width: 900px) {{
      .app {{ grid-template-columns: 1fr; grid-template-rows: 42vh 58vh; }}
      .sidebar {{ order: 2; border-right: 0; border-top: 1px solid #d8dee6; }}
      .map-shell {{ order: 1; }}
      .school-list {{ max-height: none; }}
    }}
  </style>
</head>
<body>
  <main class="app">
    <aside class="sidebar">
      <div class="header">
        <h1>海淀小学互动地图</h1>
        <p class="summary">点击地图标注或左侧学校，查看表格中的完整详情。招生范围来自 OCR，需人工复核。</p>
      </div>
      <div class="filters">
        <input id="search" type="search" placeholder="搜索学校、地址、片区、小区">
        <select id="region"><option value="">全部地址片区</option>{region_options_html}</select>
        <select id="difficulty"><option value="">全部入学难度</option><option>极高</option><option>高</option><option>中</option><option>一般</option></select>
      </div>
      <div class="stats">
        <div class="stat"><strong id="shownCount">89</strong><span>当前显示</span></div>
        <div class="stat"><strong>89</strong><span>小学总数</span></div>
        <div class="stat"><strong>28</strong><span>近似补点</span></div>
      </div>
      <div id="list" class="school-list"></div>
    </aside>
    <section class="map-shell">
      <div class="map-toolbar">
        <button id="zoomIn" class="tool-button" type="button">+</button>
        <button id="zoomOut" class="tool-button" type="button">-</button>
        <button id="resetView" class="tool-button" type="button">重置</button>
      </div>
      <div class="legend">
        <div class="legend-row"><span class="dot rank-top"></span>排名 1-15</div>
        <div class="legend-row"><span class="dot rank-mid"></span>排名 16-45</div>
        <div class="legend-row"><span class="dot rank-base"></span>排名 46-89</div>
        <div class="legend-row"><span class="dot" style="border:2px solid #1f2933;background:#fff"></span>按地址近似补点</div>
      </div>
      <div id="stage" class="map-stage">
        <div id="map" class="map-content"></div>
      </div>
      <article id="detail" class="detail" aria-live="polite"></article>
    </section>
  </main>
  <script>
    const SCHOOLS = {data_json};
    const $ = (id) => document.getElementById(id);
    const map = $("map");
    const stage = $("stage");
    const list = $("list");
    const detail = $("detail");
    let scale = 1;
    let selected = null;

    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]));
    const link = (url, label = url) => url ? `<a href="${{escapeHtml(url)}}" target="_blank" rel="noreferrer">${{escapeHtml(label)}}</a>` : "";
    const splitItems = (value) => String(value || "").split("；").map((x) => x.trim()).filter(Boolean);

    function setScale(next) {{
      scale = Math.max(0.55, Math.min(2.3, next));
      map.style.transform = `scale(${{scale}})`;
      map.style.width = `{MAP_W}px`;
      map.style.height = `{MAP_H}px`;
      stage.style.setProperty("--scale", scale);
    }}

    function rankText(school) {{
      return `#${{school["综合排名"]}} · ${{school["地址片区"] || "未分片区"}}`;
    }}

    function matches(school) {{
      const q = $("search").value.trim().toLowerCase();
      const region = $("region").value;
      const difficulty = $("difficulty").value;
      const haystack = [
        school["学校名称"], school["学校地址"], school["地址片区"], school["疑似小区/居住区"],
        school["招生范围OCR原文"], school["入学难度"], school["民间等级/梯队"]
      ].join(" ").toLowerCase();
      return (!q || haystack.includes(q)) && (!region || school["地址片区"] === region) && (!difficulty || school["入学难度"] === difficulty);
    }}

    function renderMarkers() {{
      map.innerHTML = "";
      SCHOOLS.forEach((school) => {{
        const marker = document.createElement("button");
        marker.type = "button";
        marker.className = `marker ${{school.markerClass}} ${{school["定位方式"] === "按地址近似补点" ? "approx" : ""}}`;
        marker.style.left = `${{school.xPct}}%`;
        marker.style.top = `${{school.yPct}}%`;
        marker.title = `${{school["学校名称"]}} ${{rankText(school)}}`;
        marker.dataset.name = school["学校名称"];
        if (Number(school["综合排名"]) <= 18) {{
          const label = document.createElement("span");
          label.className = "marker-label";
          label.textContent = `${{school["综合排名"]}}. ${{school.shortName}}`;
          marker.appendChild(label);
        }}
        marker.addEventListener("click", () => openDetail(school["学校名称"]));
        map.appendChild(marker);
      }});
    }}

    function renderList() {{
      const visible = SCHOOLS.filter(matches);
      $("shownCount").textContent = visible.length;
      list.innerHTML = visible.map((school) => `
        <button class="school-item ${{selected === school["学校名称"] ? "active" : ""}}" type="button" data-name="${{escapeHtml(school["学校名称"])}}">
          <span class="rank ${{school.markerClass}}">${{school["综合排名"]}}</span>
          <span>
            <span class="school-name">${{escapeHtml(school["学校名称"])}}</span>
            <span class="school-meta">${{escapeHtml(school["地址片区"] || "")}} · ${{escapeHtml(school["入学难度"] || "入学难度待补")}}<br>${{escapeHtml(school["学校地址"] || "")}}</span>
          </span>
        </button>
      `).join("");
      list.querySelectorAll(".school-item").forEach((node) => node.addEventListener("click", () => openDetail(node.dataset.name)));
      document.querySelectorAll(".marker").forEach((node) => {{
        const school = SCHOOLS.find((item) => item["学校名称"] === node.dataset.name);
        node.classList.toggle("hidden", !school || !matches(school));
        node.classList.toggle("selected", selected === node.dataset.name);
      }});
    }}

    function detailKv(rows) {{
      return `<div class="kv">${{rows.map(([k, v]) => `<div>${{escapeHtml(k)}}</div><div>${{v || ""}}</div>`).join("")}}</div>`;
    }}

    function openDetail(name) {{
      const school = SCHOOLS.find((item) => item["学校名称"] === name);
      if (!school) return;
      selected = name;
      renderList();
      const marker = document.querySelector(`.marker[data-name="${{CSS.escape(name)}}"]`);
      if (marker) {{
        const markerX = Number(school.xPct) / 100 * {MAP_W} * scale;
        const markerY = Number(school.yPct) / 100 * {MAP_H} * scale;
        stage.scrollTo({{
          left: Math.max(0, markerX - stage.clientWidth / 2),
          top: Math.max(0, markerY - stage.clientHeight / 2),
          behavior: "smooth",
        }});
      }}
      const communities = splitItems(school["疑似小区/居住区"]);
      detail.className = "detail open";
      detail.innerHTML = `
        <div class="detail-head">
          <h2>${{escapeHtml(school["学校名称"])}}</h2>
          <div class="detail-actions">
            <div class="tagline">
              <span class="tag">排名 ${{escapeHtml(school["综合排名"])}}</span>
              <span class="tag">${{escapeHtml(school["地址片区"] || "未分片区")}}</span>
              <span class="tag">${{escapeHtml(school["定位方式"])}}</span>
            </div>
            <button class="close" type="button" aria-label="关闭详情">×</button>
          </div>
        </div>
        <div class="detail-body">
          <section class="section">
            <h3>学校信息</h3>
            ${{detailKv([
              ["学校地址", escapeHtml(school["学校地址"])],
              ["综合热度分", escapeHtml(school["综合热度分"] || "")],
              ["民间等级/梯队", escapeHtml(school["民间等级/梯队"] || "")],
              ["入学难度", escapeHtml(school["入学难度"] || "")],
              ["经纬度", `${{school.lat.toFixed(6)}}, ${{school.lon.toFixed(6)}}`],
              ["地理来源", escapeHtml(school.source || school["定位方式"])],
            ])}}
          </section>
          <section class="section">
            <h3>招生与来源</h3>
            ${{detailKv([
              ["匹配简章", escapeHtml(school["招生简章匹配名称"])],
              ["匹配分", escapeHtml(school["匹配分"])],
              ["简章网页", link(school["招生简章URL"], "打开招生简章")],
              ["简章图片", link(school["招生简章图片URL"], "打开原图")],
              ["教育政策", link(school["教育官网政策来源"], "海淀教育政策")],
              ["学校名录", link(school["教育官网名录来源"], "海淀学校名录")],
            ])}}
          </section>
          <section class="section">
            <h3>疑似小区/居住区</h3>
            <div class="chips">${{communities.length ? communities.map((x) => `<span class="chip">${{escapeHtml(x)}}</span>`).join("") : "<span class='school-meta'>暂无自动抽取结果，需人工复核 OCR 原文。</span>"}}</div>
          </section>
          <section class="section">
            <h3>租金与评价字段</h3>
            ${{detailKv([
              ["小区评价", escapeHtml(school["小区评价"] || "未自动补充")],
              ["平均房租", escapeHtml(school["平均房租"] || "未自动补充")],
              ["房租来源", escapeHtml(school["房租来源"] || "")],
            ])}}
          </section>
          <section class="section">
            <h3>招生范围 OCR 原文</h3>
            <div class="long-text">${{escapeHtml(school["招生范围OCR原文"] || "")}}</div>
          </section>
          <section class="section">
            <h3>备注</h3>
            <div class="long-text">${{escapeHtml(school["备注"] || "")}}</div>
          </section>
        </div>
      `;
      detail.querySelector(".close").addEventListener("click", () => detail.classList.remove("open"));
    }}

    function initPan() {{
      let isDown = false;
      let startX = 0;
      let startY = 0;
      let left = 0;
      let top = 0;
      stage.addEventListener("mousedown", (event) => {{
        if (event.target.closest(".marker")) return;
        isDown = true;
        stage.classList.add("dragging");
        startX = event.clientX;
        startY = event.clientY;
        left = stage.scrollLeft;
        top = stage.scrollTop;
      }});
      window.addEventListener("mousemove", (event) => {{
        if (!isDown) return;
        stage.scrollLeft = left - (event.clientX - startX);
        stage.scrollTop = top - (event.clientY - startY);
      }});
      window.addEventListener("mouseup", () => {{
        isDown = false;
        stage.classList.remove("dragging");
      }});
    }}

    ["search", "region", "difficulty"].forEach((id) => $(id).addEventListener("input", renderList));
    $("zoomIn").addEventListener("click", () => setScale(scale + 0.15));
    $("zoomOut").addEventListener("click", () => setScale(scale - 0.15));
    $("resetView").addEventListener("click", () => {{ setScale(1); stage.scrollTo({{ left: 500, top: 330, behavior: "smooth" }}); }});
    renderMarkers();
    renderList();
    initPan();
    setScale(1);
    requestAnimationFrame(() => stage.scrollTo(500, 330));
  </script>
</body>
</html>
"""


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    schools = read_data()
    build_background(schools)
    HTML_OUT.write_text(page_template(schools), encoding="utf-8")
    approx = sum(1 for item in schools if item["定位方式"] == "按地址近似补点")
    print(json.dumps({"schools": len(schools), "approx": approx, "html": str(HTML_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
