import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

const htmlPath = path.resolve("outputs/interactive_map/海淀小学互动地图.html");
const screenshotPath = path.resolve("outputs/interactive_map/preview.png");

const browser = await chromium.launch({
  headless: true,
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } });
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "domcontentloaded" });
await page.waitForSelector(".marker");

const markerCount = await page.locator(".marker").count();
if (markerCount !== 89) {
  throw new Error(`expected 89 markers, got ${markerCount}`);
}

await page.locator(".marker").first().click();
await page.waitForSelector(".detail.open");
const detailTitle = await page.locator(".detail.open h2").innerText();
if (!detailTitle) {
  throw new Error("detail panel opened without a title");
}
await page.waitForTimeout(350);

await page.screenshot({ path: screenshotPath, fullPage: false });
await browser.close();

await fs.access(htmlPath);
await fs.access(screenshotPath);
console.log(JSON.stringify({ markerCount, detailTitle, screenshotPath }, null, 2));
