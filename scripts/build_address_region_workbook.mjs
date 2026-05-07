import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const input = "outputs/ranking_data/address_regions.json";
const outputDir = "outputs/ranking_data";
const outputPath = `${outputDir}/海淀义务教育学校排行数据_按地址片区.xlsx`;

const payload = JSON.parse(await fs.readFile(input, "utf8"));
const workbook = Workbook.create();

const detail = workbook.worksheets.add("按地址片区");
const summary = workbook.worksheets.add("片区汇总");
const rules = workbook.worksheets.add("划分规则");

function colName(index) {
  let n = index + 1;
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function writeSheet(sheet, headers, rows) {
  const values = [headers, ...rows.map((row) => headers.map((header) => row[header] ?? ""))];
  const lastCol = colName(headers.length - 1);
  sheet.getRange(`A1:${lastCol}${values.length}`).values = values;
  sheet.getRange(`A1:${lastCol}${values.length}`).format = {
    verticalAlignment: "top",
    wrapText: true,
  };
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: { color: "#d9eaf7" },
    font: { color: "#000000", bold: true },
    verticalAlignment: "middle",
    wrapText: true,
  };
  return values.length;
}

const detailRows = payload.detail_rows;
const summaryRows = payload.summary_rows;
writeSheet(detail, payload.detail_headers, detailRows);
writeSheet(summary, payload.summary_headers, summaryRows);

const ruleHeaders = ["地址片区", "方位片区", "关键词"];
const noteRows = [
  ["说明", payload.note, ""],
  ["输出口径", "主表按“地址片区、综合排名、学校名称”排序；片区汇总按学校数量和平均综合热度分排序。", ""],
  ["", "", ""],
  ...payload.rules.map((rule) => ruleHeaders.map((h) => rule[h] ?? "")),
];
rules.getRange(`A1:C${noteRows.length}`).values = noteRows;
rules.getRange(`A1:C${noteRows.length}`).format = { verticalAlignment: "top", wrapText: true };
rules.getRange("A4:C4").format = {
  fill: { color: "#e2f0d9" },
  font: { bold: true },
  verticalAlignment: "middle",
  wrapText: true,
};

const detailWidths = [
  72, 240, 100, 76, 320, 145, 90, 300, 420, 126, 72, 88, 78, 90, 116, 96, 330, 140,
];
for (let i = 0; i < detailWidths.length; i += 1) {
  const col = colName(i);
  detail.getRange(`${col}:${col}`).format = { columnWidthPx: detailWidths[i] };
}

const summaryWidths = [160, 90, 80, 80, 130, 110, 100, 85];
for (let i = 0; i < summaryWidths.length; i += 1) {
  const col = colName(i);
  summary.getRange(`${col}:${col}`).format = { columnWidthPx: summaryWidths[i] };
}
rules.getRange("A:A").format = { columnWidthPx: 170 };
rules.getRange("B:B").format = { columnWidthPx: 110 };
rules.getRange("C:C").format = { columnWidthPx: 850 };

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const detailCheck = await workbook.inspect({
  kind: "table",
  range: "按地址片区!A1:R12",
  include: "values",
  tableMaxRows: 12,
  tableMaxCols: 18,
});
console.log(detailCheck.ndjson);

const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "片区汇总!A1:H16",
  include: "values",
  tableMaxRows: 16,
  tableMaxCols: 8,
});
console.log(summaryCheck.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);
console.log(`saved ${outputPath}`);
