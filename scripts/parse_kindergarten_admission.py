"""解析海淀教育委员会发布的 2026 年小班招生名录 HTML，输出结构化数据。

来源页面: https://www.bjhdedu.cn/zxfw/yey/tzgg/202605/t20260529_92822.html
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_HTML = ROOT / "outputs/kindergarten/raw/2026_haidian_kindergarten_admission.html"
OUT_JSON = ROOT / "outputs/kindergarten/data/kindergarten_rows.json"
SOURCE_URL = "https://www.bjhdedu.cn/zxfw/yey/tzgg/202605/t20260529_92822.html"


def _clean(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\u2002", " ").replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_html(raw: str) -> list[dict]:
    rows = re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", raw)
    records: list[dict] = []
    current_street = ""
    seq = 0
    for row in rows:
        cells = [_clean(c) for c in re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)]
        if not cells:
            continue
        if cells[:1] == ["序号"]:
            continue
        if not cells[0].isdigit():
            continue
        seq += 1
        if len(cells) == 7:
            _, street, name, nature, address, contacts, hours = cells
            current_street = street
        elif len(cells) == 6:
            _, name, nature, address, contacts, hours = cells
            street = current_street
        else:
            continue
        contact_lines = _split_lines(contacts)
        records.append(
            {
                "序号": seq,
                "街道": street,
                "园所名称": name,
                "园所性质": nature,
                "地址信息": address,
                "招生咨询联系人": "；".join(contact_lines) if contact_lines else contacts,
                "招生咨询联系人列表": contact_lines,
                "招生咨询时间": " ".join(_split_lines(hours)),
            }
        )
    return records


def main() -> None:
    raw = RAW_HTML.read_text(encoding="utf-8", errors="ignore")
    records = parse_html(raw)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_url": SOURCE_URL,
        "title": "2026年海淀区幼儿园小班招生名录",
        "issued_by": "北京市海淀区教育委员会",
        "issued_at": "2026-05-29",
        "count": len(records),
        "rows": records,
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    streets: dict[str, int] = {}
    for r in records:
        streets[r["街道"]] = streets.get(r["街道"], 0) + 1
    print(f"parsed {len(records)} kindergartens across {len(streets)} streets")
    for s, n in sorted(streets.items(), key=lambda x: -x[1]):
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()
