import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = "outputs/ranking_data/海淀义务教育学校排行数据.xlsx";
const renderDir = "outputs/ranking_data/rendered";

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

await fs.mkdir(renderDir, { recursive: true });

const checks = [
  { sheetName: "排行数据", range: "A1:O25", file: "ranking.png" },
  { sheetName: "评分说明", range: "A1:B12", file: "methodology.png" },
  { sheetName: "来源", range: "A1:C6", file: "sources.png" },
];

for (const check of checks) {
  const rendered = await workbook.render({
    sheetName: check.sheetName,
    range: check.range,
    scale: 1,
  });
  await fs.writeFile(`${renderDir}/${check.file}`, Buffer.from(await rendered.arrayBuffer()));
  console.log(`rendered ${check.sheetName} ${check.range}`);
}

const sample = await workbook.inspect({
  kind: "table",
  range: "评分说明!A1:B12",
  include: "values",
  tableMaxRows: 12,
  tableMaxCols: 2,
});
console.log(sample.ndjson);
