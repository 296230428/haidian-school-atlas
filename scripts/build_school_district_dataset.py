import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


RANKING = Path("outputs/ranking_data/海淀义务教育学校排行数据_按地址片区.xlsx")
PAGES = Path("outputs/school_district/data/admission_images.json")
OCR_DIR = Path("outputs/school_district/ocr")
OUT = Path("outputs/school_district/data/school_district_dataset.json")


OFFICIAL_POLICY = "https://www.bjhdedu.cn/gongkai/tzgg/202504/t20250423_79349.html"
OFFICIAL_LIST = "https://zyk.bjhd.gov.cn/sjkf/jyzy/202505/t20250509_4768788.shtml"


def norm(s: str) -> str:
    s = str(s)
    s = s.replace("_北京幼升小网", "")
    s = s.replace("2025年", "").replace("招生简章", "")
    for a, b in [
        ("中国人民大学", "人大"),
        ("北京航空航天大学", "北航"),
        ("北京理工大学", "北理"),
        ("北京交通大学", "交大"),
        ("首都师范大学", "首师大"),
        ("北京市第二十中学", "二十中"),
        ("北京石油学院", "石油学院"),
    ]:
        s = s.replace(a, b)
    for token in ["北京市", "海淀区", "北京", "小学部", "校区", "学校", "实验", "附属", "附中", "附小", "教育集团", "_北京幼升小网"]:
        s = s.replace(token, "")
    s = s.replace("第一", "一").replace("第二", "二").replace("第三", "三").replace("第四", "四")
    s = re.sub(r"[（）()·\s_-]", "", s)
    return s


def score(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0
    if na in nb or nb in na:
        return 0.92 + min(len(na), len(nb)) / max(len(na), len(nb)) * 0.08
    return SequenceMatcher(None, na, nb).ratio()


def read_ocr(article_id):
    path = OCR_DIR / f"{article_id}.txt"
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def extract_scope_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if x]
    joined = "\n".join(lines)
    start_markers = ["入 学 登记 范围", "招生范围", "服务范围", "入学登记范围", "登记范围", "范围"]
    end_markers = ["招生计划", "办理入学", "办理 入 学", "材料", "通知书", "咨询电话", "入 学 通知"]
    start = 0
    for marker in start_markers:
        idx = joined.find(marker)
        if idx >= 0:
            start = idx
            break
    end = len(joined)
    for marker in end_markers:
        idx = joined.find(marker, start + 20)
        if idx >= 0:
            end = min(end, idx)
    scope = joined[start:end].strip()
    # Keep the useful part bounded.
    if len(scope) > 1200:
        scope = scope[:1200] + "..."
    return scope


def extract_communities(scope: str) -> list[str]:
    clean = re.sub(r"\s+", "", scope)
    token_re = re.compile(r"[^，。、；;:：|\\/\[\]【】（）()《》\n]+")
    suffix_re = re.compile(
        r"(小区|家园|花园|公寓|嘉园|园区|园|号院|院|号楼|楼|里|庄|村|平房|大院|宿舍|居民区|居民楼|社区|[一二三四五六七八九十]区)$"
    )
    road_re = re.compile(r".{1,24}(街|路|巷|条).{0,12}(号|院|楼)$")
    bad_words = [
        "时间",
        "登记",
        "地点",
        "材料",
        "通知",
        "范围",
        "计划",
        "对象",
        "政策",
        "招生",
        "咨询",
        "电话",
        "上午",
        "下午",
        "学校",
        "校区",
    ]
    candidates = []
    last_area_prefix = ""
    for raw in token_re.findall(clean):
        item = re.sub(r"^[0-9一二三四五六七八九十]+[.、．]", "", raw)
        item = item.strip("-—甲乙丙丁 ")
        if not item:
            continue
        if re.fullmatch(r"[一二三四五六七八九十]区", item) and last_area_prefix:
            item = f"{last_area_prefix}{item}"
        elif re.search(r"(.{1,12})[一二三四五六七八九十]区$", item):
            last_area_prefix = re.sub(r"[一二三四五六七八九十]区$", "", item)

        if len(item) > 34:
            for match in re.findall(
                r"[\u4e00-\u9fa5A-Za-z0-9甲乙丙丁\-—]{1,28}(?:小区|家园|花园|公寓|嘉园|园区|园|号院|院|号楼|楼|里|庄|村|平房|大院|宿舍|居民区|居民楼|社区|[一二三四五六七八九十]区)",
                item,
            ):
                if not any(bad in match for bad in bad_words):
                    candidates.append(match)
            continue

        if (suffix_re.search(item) or road_re.match(item)) and not any(bad in item for bad in bad_words):
            candidates.append(item)
    seen = []
    for item in candidates:
        if len(item) >= 2 and item not in seen:
            seen.append(item)
    return seen[:30]


def quality_flag(text: str, scope: str, communities: list[str]) -> str:
    if not text:
        return "未OCR"
    if len(scope) < 20:
        return "低：未定位范围段"
    if len(communities) < 1:
        return "中：需人工复核"
    return "中：OCR自动抽取，需人工复核"


def main():
    schools = pd.read_excel(RANKING, sheet_name="按地址片区")
    schools = schools[schools["办学层次"] == "小学"].copy()
    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    for page in pages:
        page["ocr_text"] = read_ocr(page["article_id"])
        page["scope_text"] = extract_scope_text(page["ocr_text"])
        page["communities"] = extract_communities(page["scope_text"])

    detail_rows = []
    for _, school in schools.iterrows():
        name = str(school["学校名称"])
        best = max(pages, key=lambda p: score(name, p["school_name_from_title"]))
        best_score = score(name, best["school_name_from_title"])
        matched = best if best_score >= 0.58 else None
        scope_text = matched["scope_text"] if matched else ""
        communities = matched["communities"] if matched else []
        detail_rows.append(
            {
                "学校名称": name,
                "综合排名": int(school["综合排名"]),
                "地址片区": school.get("地址片区", ""),
                "学校地址": school.get("学校地址", ""),
                "招生简章匹配名称": matched["school_name_from_title"] if matched else "",
                "匹配分": round(best_score, 2),
                "招生简章URL": matched["url"] if matched else "",
                "招生简章图片URL": matched["imageUrl"] if matched else "",
                "招生范围OCR原文": scope_text,
                "疑似小区/居住区": "；".join(communities),
                "OCR质量": quality_flag(matched["ocr_text"] if matched else "", scope_text, communities),
                "教育官网政策来源": OFFICIAL_POLICY,
                "教育官网名录来源": OFFICIAL_LIST,
                "小区评价": "",
                "平均房租": "",
                "房租来源": "未自动补充：需按疑似小区名逐项检索房产平台",
                "备注": "招生范围来自招生简章图片OCR，需以学校/教委当年正式通知为准；租金和评价不属于教育官网信息。",
            }
        )

    community_rows = []
    for row in detail_rows:
        for community in [x for x in row["疑似小区/居住区"].split("；") if x]:
            community_rows.append(
                {
                    "学校名称": row["学校名称"],
                    "小区/居住区": community,
                    "地址片区": row["地址片区"],
                    "招生简章URL": row["招生简章URL"],
                    "OCR质量": row["OCR质量"],
                    "小区评价": "",
                    "平均房租": "",
                    "房租来源": "待检索",
                }
            )

    payload = {
        "detail_rows": detail_rows,
        "community_rows": community_rows,
        "summary": {
            "primary_school_count": len(detail_rows),
            "matched_admission_notice_count": sum(1 for r in detail_rows if r["招生简章URL"]),
            "community_row_count": len(community_rows),
            "note": "当前版本完成招生简章图片抓取与 OCR 抽取；小区评价/平均房租字段已预留，需逐小区从房产平台补充。",
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    missing = [r["学校名称"] for r in detail_rows if not r["招生简章URL"]]
    if missing:
        print("missing", missing)


if __name__ == "__main__":
    main()
