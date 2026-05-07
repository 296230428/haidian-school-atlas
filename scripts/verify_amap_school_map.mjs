import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { chromium } from "playwright";

const rootDir = path.resolve("outputs/amap_map");
const htmlName = "海淀小学高德互动地图.html";
const htmlPath = path.join(rootDir, htmlName);
const screenshotPath = path.join(rootDir, "海淀小学高德地图标注.png");

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".js") return "application/javascript; charset=utf-8";
  return "application/octet-stream";
}

function startServer() {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url || "/", "http://127.0.0.1");
      const pathname = decodeURIComponent(url.pathname === "/" ? `/${htmlName}` : url.pathname);
      const resolved = path.resolve(rootDir, pathname.slice(1));
      if (!resolved.startsWith(rootDir)) {
        res.writeHead(403);
        res.end("Forbidden");
        return;
      }
      const data = await fs.readFile(resolved);
      res.writeHead(200, { "content-type": contentType(resolved) });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({ server, port: address.port });
    });
  });
}

await fs.access(htmlPath);
const { server, port } = await startServer();
const consoleLines = [];
let browser;

try {
  browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 920 } });
  page.on("console", (msg) => {
    const text = msg.text();
    if (/amap|高德|error|security|key|referer/i.test(text)) {
      consoleLines.push(`[${msg.type()}] ${text}`);
    }
  });
  page.on("pageerror", (error) => consoleLines.push(`[pageerror] ${error.message}`));

  const url = `http://127.0.0.1:${port}/${encodeURIComponent(htmlName)}`;
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForFunction(() => window.__AMAP_READY === true, { timeout: 45000 });
  await page.waitForSelector(".marker-wrap", { timeout: 30000 });
  await page.waitForTimeout(3000);

  const markerCount = await page.evaluate(() => window.__AMAP_MARKERS?.length || 0);
  if (markerCount !== 89) {
    throw new Error(`expected 89 markers, got ${markerCount}`);
  }

  const markerClick = await page.evaluate(() => {
    const visibleMarkers = Array.from(document.querySelectorAll(".marker-wrap")).filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.left >= 360 && rect.left <= 1440 && rect.top >= 0 && rect.top <= 920;
    });
    const marker = visibleMarkers[0];
    if (!marker) {
      const sample = Array.from(document.querySelectorAll(".marker-wrap")).slice(0, 8).map((node) => {
        const rect = node.getBoundingClientRect();
        return { left: Math.round(rect.left), top: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height) };
      });
      const first = window.__AMAP_MARKERS?.[0]?.marker?.getPosition?.();
      const center = window.__AMAP_MAP?.getCenter?.();
      const firstPixel = first && window.__AMAP_MAP?.lngLatToContainer ? window.__AMAP_MAP.lngLatToContainer(first) : null;
      const centerPixel = center && window.__AMAP_MAP?.lngLatToContainer ? window.__AMAP_MAP.lngLatToContainer(center) : null;
      return {
        visibleMarkers: 0,
        clicked: false,
        sample,
        firstPosition: first ? [first.lng, first.lat] : null,
        center: center ? [center.lng, center.lat] : null,
        firstPixel: firstPixel ? [firstPixel.x, firstPixel.y] : null,
        centerPixel: centerPixel ? [centerPixel.x, centerPixel.y] : null,
        zoom: window.__AMAP_MAP?.getZoom?.(),
      };
    }
    const rect = marker.getBoundingClientRect();
    return {
      visibleMarkers: visibleMarkers.length,
      clicked: true,
      x: Math.round(rect.left + rect.width / 2),
      y: Math.round(rect.top + rect.height / 2),
    };
  });
  if (!markerClick.clicked) {
    throw new Error(`no visible marker was available for click verification; info=${JSON.stringify(markerClick)}`);
  }
  await page.mouse.click(markerClick.x, markerClick.y);
  await page.waitForSelector(".detail.open h2", { timeout: 10000 });
  const detailTitle = await page.locator(".detail.open h2").innerText();
  if (!detailTitle) {
    throw new Error("detail panel opened without a title");
  }
  await page.evaluate(() => document.getElementById("detail").classList.remove("open"));
  await page.waitForFunction(() => !document.getElementById("detail").classList.contains("open"), { timeout: 5000 });
  await page.waitForTimeout(1000);

  const markerRects = await page.evaluate(() => Array.from(document.querySelectorAll(".marker-wrap"))
    .map((node) => {
      const rect = node.getBoundingClientRect();
      return { left: Math.round(rect.left), top: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height) };
    }));
  const mapView = await page.evaluate(() => {
    const center = window.__AMAP_MAP?.getCenter?.();
    return {
      zoom: window.__AMAP_MAP?.getZoom?.(),
      center: center ? [center.lng, center.lat] : null,
    };
  });
  const visibleMarkerRects = markerRects
    .filter((rect) => rect.width > 0 && rect.height > 0 && rect.left >= 360 && rect.left <= 1440 && rect.top >= 0 && rect.top <= 920)
    .slice(0, 10);
  if (visibleMarkerRects.length === 0) {
    throw new Error(`markers are present in DOM but not visible in the screenshot viewport; map=${JSON.stringify(mapView)} sample=${JSON.stringify(markerRects.slice(0, 8))}`);
  }
  await page.screenshot({ path: screenshotPath, fullPage: false, timeout: 60000 });
  await fs.access(screenshotPath);
  console.log(JSON.stringify({ markerCount, detailTitle, visibleMarkerRects, screenshotPath }, null, 2));
} catch (error) {
  console.error(JSON.stringify({ error: error.message, consoleLines: consoleLines.slice(-20) }, null, 2));
  throw error;
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
