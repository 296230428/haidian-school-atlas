import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import { createWorker } from "tesseract.js";

const rows = JSON.parse(await fs.readFile("outputs/school_district/data/admission_images.json", "utf8"));
const outDir = "outputs/school_district/ocr";
const prepDir = "outputs/school_district/ocr_prepared";
await fs.mkdir(outDir, { recursive: true });
await fs.mkdir(prepDir, { recursive: true });

const start = Number(process.argv[2] || 0);
const limit = Number(process.argv[3] || rows.length);
const selected = rows.slice(start, start + limit);

const worker = await createWorker("chi_sim+eng", 1, {
  logger: (m) => {
    if (m.status && m.progress !== undefined) {
      process.stderr.write(`${m.status} ${(m.progress * 100).toFixed(0)}%\r`);
    }
  },
});

for (const row of selected) {
  const outText = path.join(outDir, `${row.article_id}.txt`);
  try {
    await fs.access(outText);
    console.log(`cached ${row.article_id} ${row.school_name_from_title}`);
    continue;
  } catch {}

  try {
    await fs.access(row.localImage);
  } catch {
    console.log(`skip missing image ${row.article_id} ${row.school_name_from_title}`);
    continue;
  }

  const meta = await sharp(row.localImage).metadata();
  const cropHeight = Math.round(meta.height * 0.72);
  const prep = path.join(prepDir, `${row.article_id}.png`);
  await sharp(row.localImage)
    .extract({ left: 0, top: 0, width: meta.width, height: cropHeight })
    .grayscale()
    .normalize()
    .resize({ width: Math.min(1400, Math.round(meta.width * 1.35)), withoutEnlargement: false })
    .png()
    .toFile(prep);

  const { data } = await worker.recognize(prep);
  await fs.writeFile(outText, data.text, "utf8");
  console.log(`ocr ${row.article_id} ${row.school_name_from_title}`);
}

await worker.terminate();
