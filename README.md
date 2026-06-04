# Haidian School Atlas / 海淀学区地图集

这个项目整理了海淀小学排行、地址片区、招生范围 OCR、小区匹配和地图标注相关的数据处理脚本与本地可视化页面。

## 功能

- 生成小学排行与地址片区数据表
- 整理招生简章 OCR、疑似小区/居住区、租金评价字段
- 生成离线静态地图图片和本地互动地图
- 生成高德地图版本的互动页面和截图
- 生成 2026 年海淀幼儿园招生名录数据集和高德互动地图

## 目录

```text
scripts/                  数据采集、清洗、制表、地图生成与验证脚本
outputs/ranking_data/      排行与地址片区数据
outputs/school_district/   招生范围、小区匹配和租金评价数据
outputs/map/               静态地图标注输出
outputs/interactive_map/   不依赖高德 Key 的本地互动地图
outputs/amap_map/          高德地图页面、截图和本地启动脚本
outputs/kindergarten/      海淀幼儿园招生名录数据、原文 HTML 和导出 Excel
```

## 快速开始

安装 Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

高德地图页面需要你自己的 Web JS API Key：

```bash
cp .env.example .env.local
export AMAP_KEY="你的高德 Web JS API Key"
export AMAP_SECURITY_CODE="你的安全密钥 securityJsCode"
python3 scripts/build_amap_school_map.py
python3 scripts/serve_amap_map.py
```

然后打开脚本输出的本地地址。不要直接用 `file://` 打开高德页面，高德底图可能因域名校验不显示。

macOS 也可以双击：

```text
outputs/amap_map/打开高德地图.command
```

生成幼儿园互动地图：

```bash
python3 scripts/parse_kindergarten_admission.py     # 解析官网 HTML，输出 JSON
python3 scripts/build_kindergarten_workbook.py      # 导出 Excel（园所明细 + 街道汇总）
python3 scripts/build_amap_kindergarten_map.py      # 生成高德互动地图 HTML
python3 scripts/serve_amap_map.py kindergarten      # 本地启动并打开幼儿园页面
```

幼儿园页面用浏览器端的 `AMap.Geocoder` 把每个园所地址换算成 GCJ02 坐标，
结果会缓存到浏览器 `localStorage`，复访无需再次解析。
原始数据来源：[海淀教育委员会 · 2026 年海淀区幼儿园小班招生名录](https://www.bjhdedu.cn/zxfw/yey/tzgg/202605/t20260529_92822.html)。

## 数据重建

常用命令：

```bash
python3 scripts/generate_ranking_data.py
node scripts/build_ranking_workbook.mjs
python3 scripts/prepare_address_regions.py
node scripts/build_address_region_workbook.mjs
python3 scripts/build_school_district_dataset.py
node scripts/build_school_district_workbook.mjs
python3 scripts/build_interactive_school_map.py
```

部分 Node 脚本使用 Codex 工作区内的 `@oai/artifact-tool` 来写入和校验 Excel 文件；在普通开源环境里，可以直接使用已生成的 `.xlsx` 输出，或将这些脚本替换为 `openpyxl`/`xlsx` 实现。

## 开源注意事项

- 不要提交 `.env.local`、真实高德 Key 或包含真实 Key 的 `outputs/amap_map/海淀小学高德互动地图.html`。
- 同样，包含真实 Key 的 `outputs/amap_map/海淀幼儿园高德互动地图.html` 也不要提交。
- 招生图片、缓存网页、OCR 中间文件默认忽略，避免发布第三方原始内容。
- 排行、片区、小区匹配和租金字段是研究整理结果，正式使用前需要人工复核官方来源。
- 幼儿园招生名录是海淀教育委员会发布的公开数据，发布日期为 2026-05-29，正式使用前请回到原文核对。

## 许可证

代码使用 MIT License。第三方地图、网页、数据和图片遵循各自来源的许可与使用条款。
