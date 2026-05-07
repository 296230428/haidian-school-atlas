import { createWorker } from "tesseract.js";

const imagePath = process.argv[2];
if (!imagePath) {
  console.error("usage: node ocr_with_tesseract.mjs <image>");
  process.exit(2);
}

const worker = await createWorker("chi_sim+eng", 1, {
  logger: (m) => {
    if (m.status && m.progress !== undefined) {
      process.stderr.write(`${m.status} ${(m.progress * 100).toFixed(0)}%\r`);
    }
  },
});
const { data } = await worker.recognize(imagePath);
await worker.terminate();
console.log(data.text);
