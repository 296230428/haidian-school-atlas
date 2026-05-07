import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputPath = "outputs/ranking_data/ranking_rows.json";
const outputDir = "outputs/ranking_data";
const outputPath = `${outputDir}/海淀义务教育学校排行数据.xlsx`;

const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
const workbook = Workbook.create();

const ranking = workbook.worksheets.add("排行数据");
const methodology = workbook.worksheets.add("评分说明");
const sources = workbook.worksheets.add("来源");

const headers = [
  "综合排名",
  "学校名称",
  "办学层次",
  "办学类型",
  "学校地址",
  "网上评价摘要",
  "民间等级/梯队",
  "等级分",
  "口碑评价分",
  "入学难度",
  "入学难度分",
  "学区热度参考",
  "综合热度分",
  "依据说明",
  "来源",
];

const values = [
  headers,
  ...payload.rows.map((row) => headers.map((header) => row[header] ?? "")),
];
ranking.getRange(`A1:O${values.length}`).values = values;

methodology.getRange("A1:B12").values = [
  ["项目", "说明"],
  ["定位", "非官方排名，用于初筛和横向比较，不替代教委政策、学校招生简章或实地考察。"],
  ["综合热度分", payload.generated_note],
  ["口碑评价分", "来自公开网页的学校梯队、口碑描述、集团/分校品牌外溢，并结合学区热度微调。"],
  ["等级分", "一流一类/一流二类/二流一类/二流二类、中学梯队等映射为 0-100 分。未收录学校保守记为 D 档。"],
  ["入学难度分", "用热门程度、学区房/派位风险、民办派位、分校/新校成熟度等估算，代表需求热度和不确定性，不代表个人录取概率。"],
  ["小学入学规则", "海淀小学以登记入学为主，单校划片与多校划片相结合；民办报名超额实行派位。"],
  ["初中入学规则", "包含九年一贯制直升、按比例对口直升、公办登记入学、公办寄宿、民办、派位等路径。"],
  ["政策风险", "六年一学位、九年一贯制九年一学位、新购房多校划片、2020年后新建校多校划片等政策会影响实际入学确定性。"],
  ["来源口径", "优先官方政策和官方名录；学校等级/评价采用公开家长信息网站资料，已在来源表列出 URL。"],
  ["排序", "主表按综合热度分降序、等级分降序、入学难度分降序排列。"],
  ["更新时间", "根据 2026-04-25 检索结果整理；未确认到 2026 年海淀官方入学意见发布时，采用 2025 年官方政策作为最新可核验政策依据。"],
];

const sourceRows = [
  ["来源键", "标题", "URL"],
  ...Object.entries(payload.sources).map(([key, source]) => [key, source.title, source.url]),
];
sources.getRange(`A1:C${sourceRows.length}`).values = sourceRows;

const widths = [72, 240, 100, 76, 320, 430, 126, 72, 88, 78, 90, 116, 96, 330, 140];
for (let i = 0; i < widths.length; i += 1) {
  ranking.getRange(`${String.fromCharCode(65 + i)}:${String.fromCharCode(65 + i)}`).format = {
    columnWidthPx: widths[i],
  };
}

methodology.getRange("A:A").format = { columnWidthPx: 130 };
methodology.getRange("B:B").format = { columnWidthPx: 760 };
sources.getRange("A:A").format = { columnWidthPx: 130 };
sources.getRange("B:B").format = { columnWidthPx: 520 };
sources.getRange("C:C").format = { columnWidthPx: 640 };

ranking.getRange(`A1:O${values.length}`).format = {
  verticalAlignment: "top",
  wrapText: true,
};
methodology.getRange("A1:B12").format = {
  verticalAlignment: "top",
  wrapText: true,
};
sources.getRange(`A1:C${sourceRows.length}`).format = {
  verticalAlignment: "top",
  wrapText: true,
};

ranking.getRange("A1:O1").format = {
  fill: { color: "#d9eaf7" },
  font: { color: "#000000", bold: true },
  verticalAlignment: "middle",
  wrapText: true,
};

methodology.getRange("A1:B1").format = {
  fill: { color: "#e2f0d9" },
  font: { color: "#000000", bold: true },
  verticalAlignment: "middle",
  wrapText: true,
};

sources.getRange("A1:C1").format = {
  fill: { color: "#e4dfec" },
  font: { color: "#000000", bold: true },
  verticalAlignment: "middle",
  wrapText: true,
};

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const inspect = await workbook.inspect({
  kind: "table",
  range: "排行数据!A1:O12",
  include: "values",
  tableMaxRows: 12,
  tableMaxCols: 15,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

console.log(`saved ${outputPath}`);
