import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = "outputs/ranking_data/海淀义务教育学校排行数据_按地址片区.xlsx";
const renderDir = "outputs/ranking_data/rendered_address_regions";

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

await fs.mkdir(renderDir, { recursive: true });

for (const item of [
  { sheetName: "按地址片区", range: "A1:R18", file: "detail.png" },
  { sheetName: "片区汇总", range: "A1:H16", file: "summary.png" },
  { sheetName: "划分规则", range: "A1:C19", file: "rules.png" },
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
