import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = "outputs/school_district/海淀小学对应小区与租金评价_初版.xlsx";
const renderDir = "outputs/school_district/rendered";

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

await fs.mkdir(renderDir, { recursive: true });

for (const item of [
  { sheetName: "小学-招生范围", range: "A1:Q10", file: "schools.png" },
  { sheetName: "小区明细", range: "A1:H25", file: "communities.png" },
  { sheetName: "来源与限制", range: "A1:B9", file: "sources.png" },
]) {
  const blob = await workbook.render({ sheetName: item.sheetName, range: item.range, scale: 1 });
  await fs.writeFile(`${renderDir}/${item.file}`, Buffer.from(await blob.arrayBuffer()));
  console.log(`rendered ${item.sheetName}`);
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);
