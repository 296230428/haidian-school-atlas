import fs from "node:fs/promises";
import { chromium } from "playwright";

const browser = await chromium.launch({
  headless: true,
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const page = await browser.newPage({
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
});
await page.goto("https://m.xqfhp.com/aid/7195/", { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(2000);
const html = await page.content();
await fs.writeFile("outputs/ranking_data/xqfhp_playwright_7195.html", html);
console.log(await page.title());
console.log(html.slice(0, 500));
await browser.close();
