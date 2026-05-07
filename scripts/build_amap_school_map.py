import html
import json
import math
import os
from pathlib import Path


GEOCODES = Path("outputs/map/primary_school_geocodes.json")
DISTRICT_DATA = Path("outputs/school_district/data/school_district_dataset.json")
OUT_DIR = Path("outputs/amap_map")
HTML_OUT = OUT_DIR / "海淀小学高德互动地图.html"

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


def transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def transform_lon(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lat, lon):
    a = 6378245.0
    ee = 0.00669342162296594323
    dlat = transform_lat(lon - 105.0, lat - 35.0)
    dlon = transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrt_magic * math.cos(radlat) * math.pi)
    return lat + dlat, lon + dlon


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
        precision = "OSM地理编码转高德坐标"
        if not lat or not lon:
            lat, lon = MANUAL[name]
            precision = "按地址近似补点转高德坐标"
        gcj_lat, gcj_lon = wgs84_to_gcj02(float(lat), float(lon))
        rank = int(row["综合排名"])
        schools.append(
            {
                **geo,
                **row,
                "wgs84Lat": float(lat),
                "wgs84Lon": float(lon),
                "lat": round(gcj_lat, 7),
                "lon": round(gcj_lon, 7),
                "定位方式": precision,
                "markerClass": marker_class(rank),
                "shortName": short_name(name),
                "communityRows": community_by_school.get(name, []),
            }
        )
    return sorted(schools, key=lambda item: int(item["综合排名"]))


def page_template(schools, amap_key, security_code):
    data_json = json.dumps(schools, ensure_ascii=False)
    regions = sorted({s.get("地址片区", "") for s in schools if s.get("地址片区")})
    region_options = "\n".join(f'<option value="{html.escape(r)}">{html.escape(r)}</option>' for r in regions)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>海淀小学高德互动地图</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; color: #1f2933; background: #eef2f5; }}
    .app {{ display: grid; grid-template-columns: 360px 1fr; height: 100vh; min-height: 720px; overflow: hidden; }}
    .sidebar {{ background: #fff; border-right: 1px solid #d8dee6; display: flex; flex-direction: column; min-width: 0; min-height: 0; z-index: 3; }}
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
    .rank-top, .marker-pin.rank-top {{ background: #c73f3f; }}
    .rank-mid, .marker-pin.rank-mid {{ background: #d9822b; }}
    .rank-base, .marker-pin.rank-base {{ background: #2f6fb0; }}
    .school-name {{ font-size: 14px; font-weight: 650; line-height: 1.35; }}
    .school-meta {{ display: block; margin-top: 4px; color: #6b7888; font-size: 12px; line-height: 1.45; }}
    .map-shell {{ position: relative; min-width: 0; min-height: 0; overflow: hidden; }}
    #map {{ position: absolute; inset: 0; }}
    .legend {{ position: absolute; left: 14px; bottom: 24px; z-index: 4; background: rgba(255,255,255,.96); border: 1px solid #cfd8e3; border-radius: 7px; padding: 10px 12px; display: grid; gap: 8px; font-size: 12px; box-shadow: 0 2px 12px rgba(28,39,53,.14); }}
    .legend-row {{ display: flex; align-items: center; gap: 8px; white-space: nowrap; }}
    .dot {{ width: 12px; height: 12px; border-radius: 999px; display: inline-block; }}
    .marker-wrap {{ position: relative; width: 24px; height: 34px; cursor: pointer; }}
    .marker-pin {{ position: absolute; left: 0; top: 0; width: 24px; height: 24px; border: 2px solid #fff; border-radius: 999px 999px 999px 2px; transform: rotate(-45deg); box-shadow: 0 2px 8px rgba(0,0,0,.28); }}
    .marker-pin::after {{ content: ""; position: absolute; inset: 5px; background: #fff; border-radius: 999px; }}
    .marker-pin.approx {{ border-color: #111827; }}
    .marker-label {{ position: absolute; left: 22px; top: -4px; padding: 2px 6px; border-radius: 5px; background: rgba(255,255,255,.96); border: 1px solid #cbd5df; color: #17202a; font-size: 12px; line-height: 18px; white-space: nowrap; pointer-events: none; box-shadow: 0 1px 5px rgba(0,0,0,.12); }}
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
    .loading {{ position: absolute; inset: 0; z-index: 10; display: grid; place-items: center; background: #eef2f5; color: #344456; font-size: 15px; }}
    .loading.hidden {{ display: none; }}
    a {{ color: #1b66a9; word-break: break-all; }}
    @media (max-width: 900px) {{
      .app {{ grid-template-columns: 1fr; grid-template-rows: 44vh 56vh; }}
      .sidebar {{ order: 2; border-right: 0; border-top: 1px solid #d8dee6; }}
      .map-shell {{ order: 1; }}
    }}
  </style>
  <script>
    window._AMapSecurityConfig = {{ securityJsCode: "{html.escape(security_code)}" }};
  </script>
  <script src="https://webapi.amap.com/loader.js"></script>
</head>
<body>
  <main class="app">
    <aside class="sidebar">
      <div class="header">
        <h1>海淀小学高德互动地图</h1>
        <p class="summary">高德地图底图。点击标注或左侧学校查看完整详情；招生范围来自 OCR，需人工复核。</p>
      </div>
      <div class="filters">
        <input id="search" type="search" placeholder="搜索学校、地址、片区、小区">
        <select id="region"><option value="">全部地址片区</option>{region_options}</select>
        <select id="difficulty"><option value="">全部入学难度</option><option>极高</option><option>高</option><option>中</option><option>一般</option><option>相对低</option></select>
      </div>
      <div class="stats">
        <div class="stat"><strong id="shownCount">89</strong><span>当前显示</span></div>
        <div class="stat"><strong>89</strong><span>小学总数</span></div>
        <div class="stat"><strong>28</strong><span>近似补点</span></div>
      </div>
      <div id="list" class="school-list"></div>
    </aside>
    <section class="map-shell">
      <div id="map"></div>
      <div id="loading" class="loading">正在加载高德地图...</div>
      <div class="legend">
        <div class="legend-row"><span class="dot rank-top"></span>排名 1-15</div>
        <div class="legend-row"><span class="dot rank-mid"></span>排名 16-45</div>
        <div class="legend-row"><span class="dot rank-base"></span>排名 46-89</div>
        <div class="legend-row"><span class="dot" style="border:2px solid #111827;background:#fff"></span>按地址近似补点</div>
      </div>
      <article id="detail" class="detail" aria-live="polite"></article>
    </section>
  </main>
  <script>
    const SCHOOLS = {data_json};
    const AMAP_KEY = "{html.escape(amap_key)}";
    const $ = (id) => document.getElementById(id);
    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]));
    const link = (url, label = url) => url ? `<a href="${{escapeHtml(url)}}" target="_blank" rel="noreferrer">${{escapeHtml(label)}}</a>` : "";
    const splitItems = (value) => String(value || "").split("；").map((x) => x.trim()).filter(Boolean);
    let amap = null;
    let markers = [];
    let selected = null;

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

    function detailKv(rows) {{
      return `<div class="kv">${{rows.map(([k, v]) => `<div>${{escapeHtml(k)}}</div><div>${{v || ""}}</div>`).join("")}}</div>`;
    }}

    function renderList() {{
      const visible = SCHOOLS.filter(matches);
      $("shownCount").textContent = visible.length;
      $("list").innerHTML = visible.map((school) => `
        <button class="school-item ${{selected === school["学校名称"] ? "active" : ""}}" type="button" data-name="${{escapeHtml(school["学校名称"])}}">
          <span class="rank ${{school.markerClass}}">${{school["综合排名"]}}</span>
          <span>
            <span class="school-name">${{escapeHtml(school["学校名称"])}}</span>
            <span class="school-meta">${{escapeHtml(school["地址片区"] || "")}} · ${{escapeHtml(school["入学难度"] || "入学难度待补")}}<br>${{escapeHtml(school["学校地址"] || "")}}</span>
          </span>
        </button>
      `).join("");
      $("list").querySelectorAll(".school-item").forEach((node) => node.addEventListener("click", () => openDetail(node.dataset.name, true)));
      if (markers.length) {{
        markers.forEach((entry) => {{
          const shouldShow = matches(entry.school);
          if (shouldShow !== entry.visible) {{
            shouldShow ? entry.marker.show() : entry.marker.hide();
            entry.visible = shouldShow;
          }}
        }});
      }}
    }}

    function openDetail(name, moveMap = false) {{
      const school = SCHOOLS.find((item) => item["学校名称"] === name);
      if (!school) return;
      selected = name;
      renderList();
      if (moveMap && amap) amap.setZoomAndCenter(Math.max(amap.getZoom(), 13), [school.lon, school.lat]);
      const communities = splitItems(school["疑似小区/居住区"]);
      const detail = $("detail");
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
          <section class="section"><h3>学校信息</h3>
            ${{detailKv([
              ["学校地址", escapeHtml(school["学校地址"])],
              ["综合热度分", escapeHtml(school["综合热度分"] || "")],
              ["民间等级/梯队", escapeHtml(school["民间等级/梯队"] || "")],
              ["入学难度", escapeHtml(school["入学难度"] || "")],
              ["高德坐标", `${{school.lon.toFixed(6)}}, ${{school.lat.toFixed(6)}}`],
              ["定位来源", escapeHtml(school["定位方式"])],
            ])}}
          </section>
          <section class="section"><h3>招生与来源</h3>
            ${{detailKv([
              ["匹配简章", escapeHtml(school["招生简章匹配名称"])],
              ["匹配分", escapeHtml(school["匹配分"])],
              ["简章网页", link(school["招生简章URL"], "打开招生简章")],
              ["简章图片", link(school["招生简章图片URL"], "打开原图")],
              ["教育政策", link(school["教育官网政策来源"], "海淀教育政策")],
              ["学校名录", link(school["教育官网名录来源"], "海淀学校名录")],
            ])}}
          </section>
          <section class="section"><h3>疑似小区/居住区</h3>
            <div class="chips">${{communities.length ? communities.map((x) => `<span class="chip">${{escapeHtml(x)}}</span>`).join("") : "<span class='school-meta'>暂无自动抽取结果，需人工复核 OCR 原文。</span>"}}</div>
          </section>
          <section class="section"><h3>租金与评价字段</h3>
            ${{detailKv([
              ["小区评价", escapeHtml(school["小区评价"] || "未自动补充")],
              ["平均房租", escapeHtml(school["平均房租"] || "未自动补充")],
              ["房租来源", escapeHtml(school["房租来源"] || "")],
            ])}}
          </section>
          <section class="section"><h3>招生范围 OCR 原文</h3><div class="long-text">${{escapeHtml(school["招生范围OCR原文"] || "")}}</div></section>
          <section class="section"><h3>备注</h3><div class="long-text">${{escapeHtml(school["备注"] || "")}}</div></section>
        </div>
      `;
      detail.querySelector(".close").addEventListener("click", () => detail.classList.remove("open"));
    }}

    function markerContent(school) {{
      const label = Number(school["综合排名"]) <= 18 ? `<span class="marker-label">${{school["综合排名"]}}. ${{escapeHtml(school.shortName)}}</span>` : "";
      const approx = school["定位方式"].includes("近似") ? "approx" : "";
      return `<div class="marker-wrap" data-name="${{escapeHtml(school["学校名称"])}}"><div class="marker-pin ${{school.markerClass}} ${{approx}}"></div>${{label}}</div>`;
    }}

    async function init() {{
      const AMap = await AMapLoader.load({{ key: AMAP_KEY, version: "2.0" }});
      amap = new AMap.Map("map", {{
        zoom: 12,
        center: [116.305, 39.985],
        viewMode: "2D",
        mapStyle: "amap://styles/normal",
      }});
      window.__AMAP_MAP = amap;
      markers = SCHOOLS.map((school) => {{
        const marker = new AMap.Marker({{
          position: [school.lon, school.lat],
          content: markerContent(school),
          offset: new AMap.Pixel(-12, -34),
          title: school["学校名称"],
        }});
        marker.on("click", () => openDetail(school["学校名称"], false));
        return {{ school, marker, visible: true }};
      }});
      window.__AMAP_MARKERS = markers;
      amap.add(markers.map((entry) => entry.marker));
      amap.setZoomAndCenter(11, [116.285, 39.985]);
      amap.on("complete", () => $("loading").classList.add("hidden"));
      renderList();
      $("loading").classList.add("hidden");
      window.__AMAP_READY = true;
    }}

    ["search", "region", "difficulty"].forEach((id) => $(id).addEventListener("input", renderList));
    document.addEventListener("click", (event) => {{
      const marker = event.target.closest(".marker-wrap");
      if (marker && marker.dataset.name) openDetail(marker.dataset.name, false);
    }});
    init().catch((error) => {{
      $("loading").textContent = "高德地图加载失败，请检查 Key、安全密钥、Referer 白名单或网络。";
      console.error(error);
    }});
  </script>
</body>
</html>
"""


def main():
    amap_key = os.environ.get("AMAP_KEY", "").strip()
    security_code = os.environ.get("AMAP_SECURITY_CODE", "").strip()
    if not amap_key or not security_code:
        raise SystemExit("AMAP_KEY and AMAP_SECURITY_CODE are required")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    schools = read_data()
    HTML_OUT.write_text(page_template(schools, amap_key, security_code), encoding="utf-8")
    approx = sum(1 for item in schools if "近似" in item["定位方式"])
    print(json.dumps({"schools": len(schools), "approx": approx, "html": str(HTML_OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
