import fs from "node:fs/promises";
import path from "node:path";

const pages = JSON.parse(await fs.readFile("outputs/school_district/data/ysxiao_admission_pages.json", "utf8"));
const outDir = "outputs/school_district/admission_images";
await fs.mkdir(outDir, { recursive: true });

function chooseImage(row) {
  const candidates = (row.candidate_images || []).filter(
    (u) =>
      ![
        "大号0",
        "1697598294427",
        "722-98",
        "1920",
        "logo",
        "二维码",
        "图标",
      ].some((bad) => u.includes(bad)),
  );
  return (
    candidates.find((u) => /\/174\d+.*image\.(png|jpg|jpeg)$/i.test(u)) ||
    candidates.find((u) => /\/174\d+.*\.(png|jpg|jpeg)$/i.test(u)) ||
    candidates.find((u) => /image\.(png|jpg|jpeg)$/i.test(u)) ||
    candidates[0] ||
    ""
  );
}

const results = [];
for (const row of pages) {
  const imageUrl = chooseImage(row);
  const ext = imageUrl.split("?")[0].split(".").pop() || "png";
  const file = path.join(outDir, `${row.article_id}.${ext.replace(/[^a-zA-Z0-9]/g, "")}`);
  let status = "missing";
  if (imageUrl) {
    try {
      const res = await fetch(imageUrl, { headers: { "User-Agent": "Mozilla/5.0" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const buf = Buffer.from(await res.arrayBuffer());
      await fs.writeFile(file, buf);
      status = "downloaded";
    } catch (err) {
      status = `failed: ${err.message}`;
    }
  }
  results.push({ ...row, imageUrl, localImage: file, downloadStatus: status });
  console.log(row.article_id, status, row.school_name_from_title);
}

await fs.writeFile("outputs/school_district/data/admission_images.json", JSON.stringify(results, null, 2));
