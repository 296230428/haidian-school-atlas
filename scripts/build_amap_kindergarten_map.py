"""根据 outputs/kindergarten/data/kindergarten_rows.json 生成
海淀幼儿园招生地图（高德 Web JS API 版）。

使用方法:

    export AMAP_KEY="你的高德 Web JS API Key"
    export AMAP_SECURITY_CODE="你的安全密钥 securityJsCode"
    python3 scripts/build_amap_kindergarten_map.py
    python3 scripts/serve_amap_map.py    # 顺便也会暴露幼儿园页面

页面会用浏览器端的 AMap.Geocoder 把每个园所地址换成 GCJ02 坐标，
并把结果缓存在 localStorage 里，重复访问无需重新请求。
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs/kindergarten/data/kindergarten_rows.json"
OUT_DIR = ROOT / "outputs/amap_map"
HTML_OUT = OUT_DIR / "海淀幼儿园高德互动地图.html"

PLACEHOLDERS = {
    "your_amap_web_js_api_key",
    "your_amap_security_jscode",
    "你的高德 Web JS API Key",
    "你的安全密钥 securityJsCode",
    "你的 securityJsCode",
}

NATURE_CLASS = {
    "公办(教育部门办)": "nature-edu",
    "公办(单位办)": "nature-unit",
    "民办(普惠)": "nature-pubpriv",
    "民办(非普惠)": "nature-priv",
}

NATURE_COLOR = {
    "nature-edu": "#c73f3f",      # 公办（教育部门办）红
    "nature-unit": "#2f6fb0",     # 公办（单位办）蓝
    "nature-pubpriv": "#2f9f6b",  # 民办普惠 绿
    "nature-priv": "#d9822b",     # 民办非普惠 橙
}


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def load_amap_config():
    local_values = parse_env_file(ROOT / ".env.local")
    amap_key = os.environ.get("AMAP_KEY", local_values.get("AMAP_KEY", "")).strip()
    security_code = os.environ.get(
        "AMAP_SECURITY_CODE", local_values.get("AMAP_SECURITY_CODE", "")
    ).strip()
    return amap_key, security_code


def validate(amap_key: str, security_code: str) -> None:
    missing = []
    if not amap_key or amap_key in PLACEHOLDERS:
        missing.append("AMAP_KEY")
    if not security_code or security_code in PLACEHOLDERS:
        missing.append("AMAP_SECURITY_CODE")
    if missing:
        raise SystemExit(
            "Missing valid AMap credentials: "
            + ", ".join(missing)
            + ". Put real values in .env.local or export them before running this script."
        )


def short_name(name: str) -> str:
    return (
        name.replace("北京市海淀区", "")
        .replace("北京市", "")
        .replace("北京", "")
        .replace("幼儿园", "幼")
        .replace("幼稚园", "幼")
    )


def build_records(rows: list[dict]) -> list[dict]:
    records = []
    for row in rows:
        nature = row.get("园所性质", "")
        nature_class = NATURE_CLASS.get(nature, "nature-priv")
        records.append(
            {
                "序号": row["序号"],
                "园所名称": row["园所名称"],
                "园所简称": short_name(row["园所名称"]),
                "街道": row["街道"],
                "园所性质": nature,
                "natureClass": nature_class,
                "地址信息": row["地址信息"],
                "地理编码地址": (
                    row["地址信息"]
                    if row["地址信息"].startswith("北京")
                    else f"北京市{row['地址信息']}"
                ),
                "招生咨询联系人": row["招生咨询联系人"],
                "招生咨询联系人列表": row.get("招生咨询联系人列表", []),
                "招生咨询时间": row["招生咨询时间"],
            }
        )
    return records


def page_template(records, source_meta, amap_key, security_code) -> str:
    streets = sorted({r["街道"] for r in records})
    natures = sorted({r["园所性质"] for r in records})
    street_options = "".join(
        f"<option value=\"{html.escape(s)}\">{html.escape(s)}</option>" for s in streets
    )
    nature_options = "".join(
        f"<option value=\"{html.escape(n)}\">{html.escape(n)}</option>" for n in natures
    )
    nature_legend = "".join(
        f'<div class="legend-row"><span class="dot" style="background:{NATURE_COLOR[NATURE_CLASS[n]]}"></span>{html.escape(n)}</div>'
        for n in natures
        if n in NATURE_CLASS
    )
    data_json = json.dumps(records, ensure_ascii=False)
    meta_json = json.dumps(source_meta, ensure_ascii=False)
    counts = {n: sum(1 for r in records if r["园所性质"] == n) for n in natures}
    counts_json = json.dumps(counts, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>海淀幼儿园 2026 招生互动地图</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body, html {{ margin: 0; height: 100%; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #1c2735; }}
  .app {{ display: grid; grid-template-columns: 360px 1fr; height: 100vh; }}
  .sidebar {{ display: flex; flex-direction: column; border-right: 1px solid #d8dee6; background: #fff; min-height: 0; }}
  .header {{ padding: 16px 18px 12px; border-bottom: 1px solid #e3e8ef; }}
  .header h1 {{ margin: 0; font-size: 18px; line-height: 1.3; }}
  .summary {{ margin: 6px 0 0; color: #5d6e80; font-size: 12px; line-height: 1.6; }}
  .summary a {{ color: #1b66a9; }}
  .filters {{ display: grid; gap: 8px; padding: 10px 14px; border-bottom: 1px solid #e3e8ef; }}
  input, select {{ width: 100%; height: 34px; border: 1px solid #cbd5df; border-radius: 6px; padding: 0 10px; font-size: 13px; background: #fff; }}
  .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; padding: 10px 14px; border-bottom: 1px solid #e3e8ef; }}
  .stat {{ background: #f3f6f9; border: 1px solid #e0e6ed; border-radius: 6px; padding: 8px; }}
  .stat strong {{ display: block; font-size: 17px; line-height: 1; }}
  .stat span {{ display: block; margin-top: 4px; color: #677789; font-size: 11px; }}
  .geo-progress {{ padding: 8px 14px; border-bottom: 1px solid #e3e8ef; font-size: 12px; color: #607389; }}
  .geo-progress.done {{ color: #2e7d4f; }}
  .geo-progress.error {{ color: #b15151; }}
  .school-list {{ overflow: auto; padding: 6px; flex: 1; }}
  .school-item {{ width: 100%; display: grid; grid-template-columns: 30px 1fr; gap: 9px; padding: 8px; border: 1px solid transparent; border-radius: 6px; background: transparent; text-align: left; cursor: pointer; }}
  .school-item:hover, .school-item.active {{ background: #eef6ff; border-color: #b7d7f4; }}
  .badge {{ width: 26px; height: 26px; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 11px; }}
  .nature-edu, .marker-pin.nature-edu {{ background: {NATURE_COLOR['nature-edu']}; }}
  .nature-unit, .marker-pin.nature-unit {{ background: {NATURE_COLOR['nature-unit']}; }}
  .nature-pubpriv, .marker-pin.nature-pubpriv {{ background: {NATURE_COLOR['nature-pubpriv']}; }}
  .nature-priv, .marker-pin.nature-priv {{ background: {NATURE_COLOR['nature-priv']}; }}
  .school-name {{ font-size: 13px; font-weight: 650; line-height: 1.4; }}
  .school-meta {{ display: block; margin-top: 3px; color: #6b7888; font-size: 11px; line-height: 1.45; }}
  .map-shell {{ position: relative; min-width: 0; min-height: 0; overflow: hidden; }}
  #map {{ position: absolute; inset: 0; }}
  .legend {{ position: absolute; left: 14px; bottom: 24px; z-index: 4; background: rgba(255,255,255,.96); border: 1px solid #cfd8e3; border-radius: 7px; padding: 10px 12px; display: grid; gap: 6px; font-size: 12px; box-shadow: 0 2px 12px rgba(28,39,53,.14); }}
  .legend-row {{ display: flex; align-items: center; gap: 8px; white-space: nowrap; }}
  .dot {{ width: 12px; height: 12px; border-radius: 999px; display: inline-block; }}
  .marker-wrap {{ position: relative; width: 22px; height: 30px; cursor: pointer; }}
  .marker-pin {{ position: absolute; left: 0; top: 0; width: 22px; height: 22px; border: 2px solid #fff; border-radius: 999px 999px 999px 2px; transform: rotate(-45deg); box-shadow: 0 2px 8px rgba(0,0,0,.28); }}
  .marker-pin::after {{ content: ""; position: absolute; inset: 5px; background: #fff; border-radius: 999px; }}
  .detail {{ position: absolute; top: 0; right: 0; z-index: 6; width: min(480px, 92vw); height: 100%; background: #fff; border-left: 1px solid #d1d9e3; box-shadow: -12px 0 28px rgba(27,38,52,.16); transform: translateX(100%); transition: transform .18s ease; display: flex; flex-direction: column; }}
  .detail.open {{ transform: translateX(0); }}
  .detail-head {{ padding: 16px 20px 12px; border-bottom: 1px solid #e4e9f0; }}
  .detail-head h2 {{ margin: 0; font-size: 18px; line-height: 1.4; }}
  .detail-actions {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 10px; }}
  .tagline {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .tag {{ display: inline-flex; align-items: center; min-height: 22px; padding: 0 8px; border-radius: 999px; background: #eef3f8; color: #44556a; font-size: 12px; }}
  .close {{ border: 0; background: #eef2f5; border-radius: 6px; width: 30px; height: 30px; cursor: pointer; font-size: 18px; }}
  .detail-body {{ overflow: auto; padding: 14px 20px 24px; }}
  .section {{ margin-bottom: 16px; }}
  .section h3 {{ margin: 0 0 8px; font-size: 13px; color: #304256; }}
  .kv {{ display: grid; grid-template-columns: 96px 1fr; gap: 6px 12px; font-size: 13px; line-height: 1.5; }}
  .kv div:nth-child(odd) {{ color: #66778a; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{ padding: 5px 8px; border: 1px solid #d8e1eb; background: #f8fafc; border-radius: 999px; font-size: 12px; }}
  .loading {{ position: absolute; inset: 0; z-index: 10; display: grid; place-items: center; background: #eef2f5; color: #344456; font-size: 15px; }}
  .loading.error {{ padding: 24px; text-align: center; line-height: 1.7; color: #8a2f2f; }}
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
      <h1>海淀幼儿园 2026 招生地图</h1>
      <p class="summary">数据来源：<a href="{html.escape(source_meta['source_url'])}" target="_blank" rel="noreferrer">海淀教育委员会 · 2026 年海淀区幼儿园小班招生名录</a>。坐标由浏览器端高德 Geocoder 实时换算，结果缓存在 localStorage。</p>
    </div>
    <div class="filters">
      <input id="search" type="search" placeholder="搜索园所、街道、地址、电话" />
      <select id="street"><option value="">全部街道/镇</option>{street_options}</select>
      <select id="nature"><option value="">全部园所性质</option>{nature_options}</select>
    </div>
    <div class="stats">
      <div class="stat"><strong id="shownCount">0</strong><span>当前显示</span></div>
      <div class="stat"><strong id="totalCount">0</strong><span>园所总数</span></div>
      <div class="stat"><strong id="locatedCount">0</strong><span>已定位</span></div>
    </div>
    <div id="geoStatus" class="geo-progress">坐标准备中…</div>
    <div id="list" class="school-list"></div>
  </aside>
  <section class="map-shell">
    <div id="map"></div>
    <div id="loading" class="loading">正在加载高德地图...</div>
    <div class="legend">{nature_legend}<div class="legend-row" style="margin-top:4px;border-top:1px solid #e6ebf2;padding-top:6px;"><button id="clearCache" type="button" style="border:1px solid #cbd5df;background:#fff;border-radius:5px;padding:3px 8px;font-size:12px;cursor:pointer;">清空坐标缓存并重新解析</button></div></div>
    <article id="detail" class="detail" aria-live="polite"></article>
  </section>
</main>
<script>
  const KINDERGARTENS = {data_json};
  const SOURCE_META = {meta_json};
  const NATURE_COUNTS = {counts_json};
  const AMAP_KEY = "{html.escape(amap_key)}";
  const STORAGE_KEY = "haidian-kindergarten-geo-v1";
  const STORAGE_VERSION = 2;

  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]));

  let amap = null;
  let AMapNs = null;
  let geocoder = null;
  let placeSearch = null;
  let districtPolygon = null;
  let markers = [];
  let selected = null;

  function loadCache() {{
    try {{
      const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");
      if (!raw || raw._v !== STORAGE_VERSION) return {{ _v: STORAGE_VERSION }};
      return raw;
    }} catch (e) {{
      return {{ _v: STORAGE_VERSION }};
    }}
  }}
  function saveCache(cache) {{
    try {{
      cache._v = STORAGE_VERSION;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
    }}
    catch (e) {{}}
  }}

  function matches(item) {{
    const q = $("search").value.trim().toLowerCase();
    const street = $("street").value;
    const nature = $("nature").value;
    const haystack = [item["园所名称"], item["街道"], item["地址信息"], item["招生咨询联系人"], item["招生咨询时间"], item["园所性质"]].join(" ").toLowerCase();
    return (!q || haystack.includes(q)) && (!street || item["街道"] === street) && (!nature || item["园所性质"] === nature);
  }}

  function detailKv(rows) {{
    return `<div class="kv">${{rows.map(([k, v]) => `<div>${{escapeHtml(k)}}</div><div>${{v || ""}}</div>`).join("")}}</div>`;
  }}

  function renderList() {{
    const visible = KINDERGARTENS.filter(matches);
    $("shownCount").textContent = visible.length;
    $("list").innerHTML = visible.map((item) => `
      <button class="school-item ${{selected === item["园所名称"] ? "active" : ""}}" type="button" data-name="${{escapeHtml(item["园所名称"])}}">
        <span class="badge ${{item.natureClass}}">${{escapeHtml(item["园所性质"].includes("公办") ? "公" : "民")}}</span>
        <span>
          <span class="school-name">${{escapeHtml(item["园所名称"])}}</span>
          <span class="school-meta">${{escapeHtml(item["街道"])}} · ${{escapeHtml(item["园所性质"])}}<br>${{escapeHtml(item["地址信息"])}}</span>
        </span>
      </button>
    `).join("");
    $("list").querySelectorAll(".school-item").forEach((node) => node.addEventListener("click", () => openDetail(node.dataset.name, true)));
    if (markers.length) {{
      markers.forEach((entry) => {{
        const shouldShow = entry.located && matches(entry.item);
        if (shouldShow !== entry.visible) {{
          shouldShow ? entry.marker.show() : entry.marker.hide();
          entry.visible = shouldShow;
        }}
      }});
    }}
  }}

  function openDetail(name, moveMap = false) {{
    const item = KINDERGARTENS.find((x) => x["园所名称"] === name);
    if (!item) return;
    selected = name;
    renderList();
    if (moveMap && amap && item.lon && item.lat) amap.setZoomAndCenter(Math.max(amap.getZoom(), 14), [item.lon, item.lat]);
    const detail = $("detail");
    const contacts = (item["招生咨询联系人列表"] || []).filter(Boolean);
    detail.className = "detail open";
    detail.innerHTML = `
      <div class="detail-head">
        <h2>${{escapeHtml(item["园所名称"])}}</h2>
        <div class="detail-actions">
          <div class="tagline">
            <span class="tag">${{escapeHtml(item["街道"])}}</span>
            <span class="tag">${{escapeHtml(item["园所性质"])}}</span>
            ${{item.lon && item.lat ? `<span class="tag">已定位</span>` : `<span class="tag">未定位</span>`}}
          </div>
          <button class="close" type="button" aria-label="关闭详情">×</button>
        </div>
      </div>
      <div class="detail-body">
        <section class="section"><h3>基本信息</h3>
          ${{detailKv([
            ["地址", escapeHtml(item["地址信息"])],
            ["园所性质", escapeHtml(item["园所性质"])],
            ["所在街道", escapeHtml(item["街道"])],
            ["高德坐标", item.lon && item.lat ? `${{item.lon.toFixed(6)}}, ${{item.lat.toFixed(6)}}` : "（待解析）"],
            ["定位来源", escapeHtml(item.geoSource || "—")],
          ])}}
        </section>
        <section class="section"><h3>招生咨询</h3>
          ${{detailKv([
            ["联系电话", contacts.length ? contacts.map((x) => `<div>${{escapeHtml(x)}}</div>`).join("") : escapeHtml(item["招生咨询联系人"])],
            ["咨询时间", escapeHtml(item["招生咨询时间"])],
          ])}}
        </section>
        <section class="section"><h3>原始名录</h3>
          ${{detailKv([
            ["序号", escapeHtml(item["序号"])],
            ["发布机构", escapeHtml(SOURCE_META["issued_by"])],
            ["发布日期", escapeHtml(SOURCE_META["issued_at"])],
            ["数据原文", `<a href="${{escapeHtml(SOURCE_META["source_url"])}}" target="_blank" rel="noreferrer">海淀教育网通知公告</a>`],
          ])}}
        </section>
      </div>
    `;
    detail.querySelector(".close").addEventListener("click", () => detail.classList.remove("open"));
  }}

  function markerContent(item) {{
    return `<div class="marker-wrap" data-name="${{escapeHtml(item["园所名称"])}}" title="${{escapeHtml(item["园所名称"])}}"><div class="marker-pin ${{item.natureClass}}"></div></div>`;
  }}

  function placeMarker(item) {{
    if (!AMapNs || !amap || !item.lon || !item.lat) return;
    const marker = new AMapNs.Marker({{
      position: [item.lon, item.lat],
      content: markerContent(item),
      offset: new AMapNs.Pixel(-11, -30),
      title: item["园所名称"],
    }});
    marker.on("click", () => openDetail(item["园所名称"], false));
    markers.push({{ item, marker, visible: true, located: true }});
    amap.add(marker);
  }}

  // 高德 Geocoder 在没匹配到精确门牌/POI 时，会兜底到「街道/区/省」级别
  // —— 这种粒度的坐标是街道甚至全市中心，落到地图上会偏几公里。
  // 这里只接受门牌号、道路、兴趣点（含 POI 类）和小区类的结果。
  const ACCEPT_LEVELS = new Set([
    "门牌号", "兴趣点", "兴趣点类", "热点商圈", "道路", "道路交叉口",
    "热点门牌号", "公交线路", "热点设施", "POI", "建筑物",
  ]);
  // 海淀区的大致包围盒：经度 116.05–116.45，纬度 39.85–40.18
  const HD_BBOX = {{ lonMin: 116.04, lonMax: 116.48, latMin: 39.83, latMax: 40.20 }};
  function inHaidian(lon, lat) {{
    return lon >= HD_BBOX.lonMin && lon <= HD_BBOX.lonMax && lat >= HD_BBOX.latMin && lat <= HD_BBOX.latMax;
  }}

  function placeSearchOne(keyword) {{
    return new Promise((resolve) => {{
      if (!placeSearch || !keyword) return resolve(null);
      placeSearch.search(keyword, (status, result) => {{
        if (status !== "complete" || !result || !result.poiList || !result.poiList.pois || !result.poiList.pois.length) {{
          resolve(null); return;
        }}
        const poi = result.poiList.pois.find((p) => p.location && inHaidian(p.location.lng, p.location.lat)) || null;
        if (!poi) {{ resolve(null); return; }}
        resolve({{
          lon: poi.location.lng,
          lat: poi.location.lat,
          level: poi.type || "POI",
          formatted: poi.address || poi.name || "",
          geoSource: "AMap.PlaceSearch",
        }});
      }});
    }});
  }}

  function geocoderOne(query) {{
    return new Promise((resolve) => {{
      if (!geocoder || !query) return resolve(null);
      geocoder.getLocation(query, (status, result) => {{
        if (status !== "complete" || !result.geocodes || !result.geocodes.length) {{ resolve(null); return; }}
        const g = result.geocodes[0];
        const loc = g.location;
        if (!loc || typeof loc.lng !== "number" || typeof loc.lat !== "number") {{ resolve(null); return; }}
        const level = g.level || "";
        if (!ACCEPT_LEVELS.has(level)) {{ resolve({{ _rejected: level, lon: loc.lng, lat: loc.lat }}); return; }}
        if (!inHaidian(loc.lng, loc.lat)) {{ resolve({{ _rejected: "海淀区外" }}); return; }}
        resolve({{
          lon: loc.lng, lat: loc.lat, level,
          formatted: g.formattedAddress || "",
          geoSource: "AMap.Geocoder",
        }});
      }});
    }});
  }}

  async function geocodeOne(item) {{
    // 1) 先用园所名称做 POI 搜索：幼儿园在高德地图上大多有 POI
    const poiQueries = [
      `海淀区 ${{item["园所名称"]}}`,
      item["园所名称"],
    ];
    for (const q of poiQueries) {{
      const r = await placeSearchOne(q);
      if (r) return r;
    }}
    // 2) 再用「地址 + 园名」走精确地理编码
    const geoQueries = [
      `${{item["地理编码地址"]}} ${{item["园所名称"]}}`,
      item["地理编码地址"],
      item["地址信息"],
    ];
    let lastReject = null;
    for (const q of geoQueries) {{
      const r = await geocoderOne(q);
      if (r && !r._rejected) return r;
      if (r && r._rejected) lastReject = r._rejected;
    }}
    return lastReject ? {{ _rejected: lastReject }} : null;
  }}

  async function geocodeAll() {{
    const cache = loadCache();
    let located = 0;
    for (const item of KINDERGARTENS) {{
      const cached = cache[item["园所名称"]];
      if (cached && cached.lon && cached.lat) {{
        item.lon = cached.lon;
        item.lat = cached.lat;
        item.geoSource = cached.geoSource || "缓存";
        located += 1;
        placeMarker(item);
      }}
    }}
    $("locatedCount").textContent = located;
    renderList();

    const pending = KINDERGARTENS.filter((it) => !it.lon || !it.lat);
    if (!pending.length) {{
      $("geoStatus").className = "geo-progress done";
      $("geoStatus").textContent = `全部 ${{KINDERGARTENS.length}} 个园所均已使用缓存定位。`;
      return;
    }}

    let done = 0;
    let failed = 0;
    let rejected = 0;
    $("geoStatus").textContent = `坐标解析中 0 / ${{pending.length}}…`;
    for (const item of pending) {{
      const result = await geocodeOne(item);
      done += 1;
      if (result && !result._rejected) {{
        item.lon = result.lon;
        item.lat = result.lat;
        item.geoSource = result.geoSource + (result.level ? `（${{result.level}}）` : "");
        cache[item["园所名称"]] = {{
          lon: result.lon, lat: result.lat,
          geoSource: item.geoSource, formatted: result.formatted, level: result.level || "",
        }};
        located += 1;
        placeMarker(item);
        $("locatedCount").textContent = located;
      }} else {{
        if (result && result._rejected) {{
          rejected += 1;
          item.geoSource = `已跳过（${{result._rejected}}级兜底）`;
        }} else {{
          failed += 1;
        }}
      }}
      if (done % 5 === 0 || done === pending.length) {{
        saveCache(cache);
        renderList();
      }}
      $("geoStatus").textContent = `坐标解析中 ${{done}} / ${{pending.length}}（失败 ${{failed}}，跳过粗粒度 ${{rejected}}）`;
      // light throttle to be friendly to the JS API quota
      await new Promise((r) => setTimeout(r, 80));
    }}
    saveCache(cache);
    renderList();
    const dropped = failed + rejected;
    $("geoStatus").className = dropped ? "geo-progress error" : "geo-progress done";
    $("geoStatus").textContent = dropped
      ? `定位完成：成功 ${{located}} / ${{KINDERGARTENS.length}}；跳过粗粒度兜底 ${{rejected}}，未匹配 ${{failed}}。`
      : `定位完成：${{located}} / ${{KINDERGARTENS.length}}。`;
  }}

  async function init() {{
    $("totalCount").textContent = KINDERGARTENS.length;
    if (!window.AMapLoader) throw new Error("高德 Loader 未加载，请检查网络是否能访问 https://webapi.amap.com/loader.js。");
    AMapNs = await AMapLoader.load({{ key: AMAP_KEY, version: "2.0", plugins: ["AMap.Geocoder", "AMap.PlaceSearch"] }});
    amap = new AMapNs.Map("map", {{
      zoom: 11,
      center: [116.305, 39.985],
      viewMode: "2D",
      mapStyle: "amap://styles/normal",
    }});
    geocoder = new AMapNs.Geocoder({{ city: "010", extensions: "all" }});
    placeSearch = new AMapNs.PlaceSearch({{
      city: "北京",
      citylimit: true,
      pageSize: 5,
      pageIndex: 1,
      type: "科教文化服务;教育培训服务;幼儿园",
    }});
    amap.on("complete", () => $("loading").classList.add("hidden"));
    $("loading").classList.add("hidden");
    renderList();
    geocodeAll().catch((err) => {{
      console.error(err);
      $("geoStatus").className = "geo-progress error";
      $("geoStatus").textContent = `坐标解析失败：${{err && err.message || err}}`;
    }});
  }}

  ["search", "street", "nature"].forEach((id) => $(id).addEventListener("input", renderList));
  document.addEventListener("click", (event) => {{
    const m = event.target.closest(".marker-wrap");
    if (m && m.dataset.name) openDetail(m.dataset.name, false);
  }});
  $("clearCache").addEventListener("click", () => {{
    try {{ localStorage.removeItem(STORAGE_KEY); }} catch (e) {{}}
    location.reload();
  }});
  init().catch((error) => {{
    $("loading").classList.add("error");
    $("loading").innerHTML = `高德地图加载失败。<br>请检查 Key、安全密钥、Referer 白名单或网络。<br><small>${{escapeHtml(error?.message || error)}}</small>`;
    console.error(error);
  }});
</script>
</body>
</html>
"""


def main() -> None:
    amap_key, security_code = load_amap_config()
    validate(amap_key, security_code)
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    records = build_records(payload["rows"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(
        page_template(
            records,
            {
                "source_url": payload["source_url"],
                "title": payload["title"],
                "issued_by": payload["issued_by"],
                "issued_at": payload["issued_at"],
            },
            amap_key,
            security_code,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"kindergartens": len(records), "html": str(HTML_OUT)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
