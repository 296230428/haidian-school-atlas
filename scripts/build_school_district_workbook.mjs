import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const payload = JSON.parse(await fs.readFile("outputs/school_district/data/school_district_dataset.json", "utf8"));
const outputDir = "outputs/school_district";
const outputPath = `${outputDir}/海淀小学对应小区与租金评价_初版.xlsx`;

const workbook = Workbook.create();
const schools = workbook.worksheets.add("小学-招生范围");
const communities = workbook.worksheets.add("小区明细");
const sources = workbook.worksheets.add("来源与限制");

function colName(i) {
  let n = i + 1;
  let s = "";
  while (n) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function write(sheet, rows, headers) {
  const values = [headers, ...rows.map((row) => headers.map((h) => row[h] ?? ""))];
  const last = colName(headers.length - 1);
  sheet.getRange(`A1:${last}${values.length}`).values = values;
  sheet.getRange(`A1:${last}${values.length}`).format = { verticalAlignment: "top", wrapText: true };
  sheet.getRange(`A1:${last}1`).format = {
    fill: { color: "#d9eaf7" },
    font: { bold: true },
    verticalAlignment: "middle",
    wrapText: true,
  };
}

const schoolHeaders = [
  "学校名称",
  "综合排名",
  "地址片区",
  "学校地址",
  "招生简章匹配名称",
  "匹配分",
  "招生简章URL",
  "招生简章图片URL",
  "疑似小区/居住区",
  "招生范围OCR原文",
  "OCR质量",
  "小区评价",
  "平均房租",
  "房租来源",
  "教育官网政策来源",
  "教育官网名录来源",
  "备注",
];
const communityHeaders = [
  "学校名称",
  "小区/居住区",
  "地址片区",
  "招生简章URL",
  "OCR质量",
  "小区评价",
  "平均房租",
  "房租来源",
];

write(schools, payload.detail_rows, schoolHeaders);
write(communities, payload.community_rows, communityHeaders);

const sourceRows = [
  ["项目", "说明"],
  ["教育官网政策", "海淀区 2025 年义务教育阶段入学工作的实施意见，用于确认入学政策口径。"],
  ["教育官网学校名录", "海淀区 2024-2025 学年度义务教育学校名录，用于确认学校范围。"],
  ["招生范围来源", "逐校招生简章图片来自北京幼升小网转载的 2025 年海淀区小学招生简章；已保留原网页和图片 URL。"],
  ["OCR限制", "招生范围图片经 Tesseract OCR 自动识别，表格和楼号存在错字/漏字风险；已保留 OCR 原文并标注需人工复核。"],
  ["房租/评价限制", "小区评价和平均房租不属于教育官网信息。本版先预留字段，未批量填入房产平台租金，避免把未核验数据写入结果。"],
  ["覆盖情况", `小学 ${payload.summary.primary_school_count} 所；匹配招生简章 ${payload.summary.matched_admission_notice_count} 所；自动拆出的疑似小区/居住区记录 ${payload.summary.community_row_count} 条。`],
  ["官方政策 URL", "https://www.bjhdedu.cn/gongkai/tzgg/202504/t20250423_79349.html"],
  ["官方名录 URL", "https://zyk.bjhd.gov.cn/sjkf/jyzy/202505/t20250509_4768788.shtml"],
];
sources.getRange(`A1:B${sourceRows.length}`).values = sourceRows;
sources.getRange(`A1:B${sourceRows.length}`).format = { verticalAlignment: "top", wrapText: true };
sources.getRange("A1:B1").format = { fill: { color: "#e2f0d9" }, font: { bold: true } };

const schoolWidths = [240, 75, 140, 260, 220, 70, 360, 360, 420, 620, 160, 240, 120, 240, 360, 360, 420];
schoolWidths.forEach((w, i) => {
  const c = colName(i);
  schools.getRange(`${c}:${c}`).format = { columnWidthPx: w };
});
const communityWidths = [240, 260, 140, 360, 160, 240, 120, 220];
communityWidths.forEach((w, i) => {
  const c = colName(i);
  communities.getRange(`${c}:${c}`).format = { columnWidthPx: w };
});
sources.getRange("A:A").format = { columnWidthPx: 150 };
sources.getRange("B:B").format = { columnWidthPx: 850 };

await fs.mkdir(outputDir, { recursive: true });
const blob = await SpreadsheetFile.exportXlsx(workbook);
await blob.save(outputPath);

const check = await workbook.inspect({
  kind: "table",
  range: "小学-招生范围!A1:Q8",
  include: "values",
  tableMaxRows: 8,
  tableMaxCols: 17,
});
console.log(check.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);
console.log(`saved ${outputPath}`);
