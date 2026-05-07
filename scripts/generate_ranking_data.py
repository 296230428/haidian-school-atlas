import json
import re
from pathlib import Path

import pandas as pd


INPUT = Path("/Users/wh/Downloads/P020250514380056001058.xlsx")
OUT = Path("outputs/ranking_data/ranking_rows.json")

SOURCES = {
    "official_list": {
        "title": "海淀区教育委员会：2024-2025学年度海淀区义务教育学校名录",
        "url": "https://zyk.bjhd.gov.cn/sjkf/jyzy/202505/t20250509_4768788.shtml",
    },
    "policy": {
        "title": "海淀教育：2025年义务教育阶段入学工作的实施意见",
        "url": "https://www.bjhdedu.cn/gongkai/tzgg/202504/t20250423_79349.html",
    },
    "primary_tier": {
        "title": "北京小升初信息网：2024年海淀幼升小热门学校一览，附部分小学口碑介绍",
        "url": "https://www.xscxx.com/rdgz/rmtj/202410212370.html",
    },
    "district_tier": {
        "title": "北京中考信息网：2024版海淀学区梯队排名",
        "url": "https://www.zhongkaobj.cn/zhongkao/zixun/202502068931.html",
    },
    "middle_tier": {
        "title": "北京小升初信息网：2025年海淀区中学新排名及录取分数线解析",
        "url": "https://www.xscxx.com/xiaoshengchu/hdqxsc/202503159987.html",
    },
}


def norm(name: str) -> str:
    s = str(name)
    for token in ["北京市海淀区", "北京市", "北京", "中国"]:
        s = s.replace(token, "")
    s = s.replace("附属", "附")
    s = s.replace("实验学校", "实验")
    s = s.replace("学校", "")
    s = s.replace("小学部", "")
    s = s.replace("中心", "")
    s = s.replace("第一", "一").replace("第二", "二").replace("第三", "三").replace("第四", "四")
    return re.sub(r"\s+", "", s)


PRIMARY_TIERS = {
    "一流一类": [
        "中关村第三小学",
        "中关村第一小学",
        "中关村第二小学",
        "中国人民大学附属小学",
        "中国人民大学附属中学实验小学",
    ],
    "一流二类": [
        "北京市海淀区实验小学",
        "北京市海淀区五一小学",
        "北京市海淀区上地实验小学",
        "北京市海淀区翠微小学",
        "北京石油学院附属小学",
        "北京师范大学实验小学",
        "北京大学附属小学",
    ],
    "二流一类": [
        "北京林业大学附属小学",
        "北京科技大学附属小学",
        "北京理工大学附属小学",
        "北京市海淀区中关村第四小学",
        "北京市海淀区万泉小学",
        "北京市海淀区七一小学",
        "北京航空航天大学附属小学",
        "中国农业科学院附属小学",
        "北京医科大学附属小学",
        "北京市海淀区第二实验小学",
        "清华大学附属小学",
    ],
    "二流二类": [
        "北京市海淀区玉泉小学",
        "北京市海淀区羊坊店中心小学",
        "北京市海淀区羊坊店第四小学",
        "北京市海淀区太平路小学",
        "北京市第二十中学附属育鹰小学",
        "首都师范大学附属小学",
        "北京市海淀区永泰小学",
        "北京交通大学附属小学",
        "首都师范大学附属中学育鸿学校",
        "北京市海淀区实验小学九一分校",
        "首都师范大学附属花园小学",
        "北京市海淀区双榆树中心小学",
        "北京市海淀区双榆树第一小学",
        "北京市海淀区西苑小学",
        "北京市海淀区民族小学",
        "北京市海淀区红英小学",
        "北京市海淀区教科院培英未来实验小学",
        "北京市海淀区北安河中心小学",
        "北京教育学院附属海淀实验小学",
        "北京市海淀区前进小学",
        "北京市海淀区六一小学",
        "北京外国语大学附属小学",
    ],
}

TIER_SCORES = {
    "一流一类": 96,
    "一流二类": 88,
    "二流一类": 78,
    "二流二类": 68,
    "集团/分校参考": 72,
    "中学第一梯队": 94,
    "中学第二梯队": 84,
    "中学第三梯队": 76,
    "未收录": 58,
}

PRIMARY_REVIEW = {
    "北京市海淀区中关村第三小学": "顶级牛小，竞赛和师资口碑强，但竞争激烈、课业管理严格。",
    "中国人民大学附属小学": "人大附体系品牌成熟，活动丰富，成绩口碑突出，择校成本较高。",
    "北京市海淀区中关村第一小学": "教学节奏稳、基础扎实、师资口碑好，家长评价性价比较高。",
    "北京市海淀区中关村第二小学": "教学水平较高，素质教育和乐团特色有口碑。",
    "北京市海淀区上地实验小学": "上升较快，校风口碑不错，竞赛氛围和小升初压力较强。",
    "北京市海淀区实验小学": "规模大、学风好，是海淀传统强校之一。",
    "北京市海淀区翠微小学": "老师负责、竞赛获奖多，素质教育口碑较好。",
    "北京石油学院附属小学": "海淀重点校口碑，作业压力相对适中，兴趣班和英语特色较明显。",
    "北京市海淀区万泉小学": "抓得较紧，学习氛围浓，周边教育资源密集。",
    "北京市海淀区七一小学": "素质教育与课外活动口碑较好，奥数成绩有一定认可度。",
    "北京市海淀区太平路小学": "有对口直升十一学校机会，升学通路受到关注。",
    "北京市海淀区西苑小学": "有对口直升101中学机会，升学通路带来热度。",
    "北京市第二十中学附属育鹰小学": "育鹰小学在海淀二流二类名单中，家长关注度中等偏上。",
}

MIDDLE_TIERS = {
    "中学第一梯队": [
        "北京市十一学校龙樾实验中学",
    ],
    "中学第二梯队": [
        "北京十一晋元中学",
        "北京市十一学校一分校",
        "北京市上地实验学校",
        "北京交通大学附属中学实验学校",
    ],
    "中学第三梯队": [
        "北京航空航天大学实验学校分校",
        "北京市第二十中学附属实验学校",
        "北大附中西三旗学校",
        "首都师范大学附属中学育鸿学校",
    ],
}

GROUP_BRANDS = [
    ("中关村第三小学", 84),
    ("中关村第一小学", 82),
    ("中关村第二小学", 80),
    ("中国人民大学附属小学", 78),
    ("清华大学附属小学", 78),
    ("北京大学附属小学", 78),
    ("北京市海淀区翠微小学", 72),
    ("北京市海淀区五一", 72),
    ("北京石油学院附属", 70),
    ("北京市海淀区实验小学", 70),
    ("北京师范大学", 70),
    ("首都师范大学附属中学", 70),
    ("北京市十一学校", 82),
    ("北京十一", 82),
    ("北大附中", 76),
    ("北京市第二十中学", 70),
]

AREA_RULES = [
    ("中关村", "第一梯队学区", 6),
    ("上地", "第一梯队学区", 6),
    ("万柳", "第一梯队学区", 6),
    ("万泉", "第二梯队学区", 3),
    ("八里庄", "第二梯队学区", 3),
    ("羊坊店", "第二梯队学区", 3),
    ("翠微", "第二梯队学区", 3),
    ("四季青", "第三梯队学区", 1),
    ("永定路", "第三梯队学区", 1),
    ("玉泉", "第三梯队学区", 1),
    ("五一", "第三梯队学区", 1),
    ("西三旗", "第三梯队学区", 1),
    ("温泉", "谨慎选择学区", -2),
    ("苏家坨", "谨慎选择学区", -2),
    ("清河", "谨慎选择学区", -2),
    ("西北旺", "谨慎选择学区", -2),
    ("永丰", "谨慎选择学区", -2),
    ("北安河", "谨慎选择学区", -2),
    ("肖家河", "谨慎选择学区", -2),
]


def exact_primary_tier(name: str):
    n = norm(name)
    for tier, names in PRIMARY_TIERS.items():
        if n in {norm(x) for x in names}:
            return tier
    return None


def exact_middle_tier(name: str):
    n = norm(name)
    for tier, names in MIDDLE_TIERS.items():
        if n in {norm(x) for x in names}:
            return tier
    return None


def infer_area(name: str, addr: str):
    text = f"{name}{addr}"
    for key, label, bonus in AREA_RULES:
        if key in text:
            return label, bonus
    return "未明确", 0


def infer_group_score(name: str):
    for key, score in GROUP_BRANDS:
        if key in name:
            return score
    return None


def difficulty_label(score: float):
    if score >= 90:
        return "极高"
    if score >= 80:
        return "高"
    if score >= 70:
        return "中高"
    if score >= 60:
        return "中"
    return "相对低"


def grade_label(score: float):
    if score >= 92:
        return "S"
    if score >= 84:
        return "A"
    if score >= 74:
        return "B"
    if score >= 64:
        return "C"
    return "D"


def main():
    df = pd.read_excel(INPUT, sheet_name="义务教育学校名录", header=1).dropna(how="all")
    rows = []
    for _, r in df.iterrows():
        name = str(r["学校名称"]).strip()
        level = str(r["办学层次"]).strip()
        kind = str(r["办学类型"]).strip()
        addr = str(r["学校地址"]).strip()

        tier = exact_primary_tier(name) if "小学" in level else None
        middle_tier = exact_middle_tier(name) if level != "小学" else None
        evidence = []
        source_keys = ["official_list", "policy"]

        if tier:
            tier_label = tier
            base = TIER_SCORES[tier]
            evidence.append(f"小学梯队收录：{tier}")
            source_keys.append("primary_tier")
        elif middle_tier:
            tier_label = middle_tier
            base = TIER_SCORES[middle_tier]
            evidence.append(f"中学录取/梯队参考：{middle_tier}")
            source_keys.append("middle_tier")
        else:
            group_score = infer_group_score(name)
            if group_score:
                tier_label = "集团/分校参考"
                base = group_score
                evidence.append("按同名教育集团/分校口碑折减估算")
                source_keys.append("primary_tier")
            else:
                tier_label = "未收录"
                base = TIER_SCORES["未收录"]
                evidence.append("未在本次检索到的公开梯队清单中直接收录")

        area_label, area_bonus = infer_area(name, addr)
        if area_label != "未明确":
            evidence.append(f"所在片区参考：{area_label}")
            source_keys.append("district_tier")

        eval_score = max(45, min(100, base + area_bonus))
        tier_score = max(45, min(100, TIER_SCORES.get(tier_label, base)))

        difficulty = tier_score
        if "一流一类" in tier_label or "中学第一梯队" in tier_label:
            difficulty += 2
        if area_label == "第一梯队学区":
            difficulty += 4
        elif area_label == "第二梯队学区":
            difficulty += 2
        elif area_label == "谨慎选择学区":
            difficulty -= 3
        if "分校" in name or "科学城" in name or "未来" in name or "新馨" in name:
            difficulty -= 4
        if kind == "民办":
            difficulty = max(55, difficulty - 8)
        difficulty = max(45, min(100, difficulty))

        # 综合热度：口碑评价与梯队权重更高，入学难度作为需求热度代理。
        composite = round(eval_score * 0.45 + tier_score * 0.35 + difficulty * 0.20, 1)

        review = PRIMARY_REVIEW.get(name)
        if not review:
            if tier_label == "集团/分校参考":
                review = "集团校或分校具备品牌外溢，但校区成熟度、派位与生源结构需单独核实。"
            elif tier_label == "未收录":
                review = "公开口碑资料有限，建议结合学校开放日、招生简章和学区派位结果复核。"
            elif "中学" in tier_label:
                review = "按中考录取分数线/区排名和集团资源作中学段评价参考。"
            else:
                review = "公开梯队清单收录，具备一定家长关注度和口碑基础。"

        rows.append(
            {
                "学校名称": name,
                "办学层次": level,
                "办学类型": kind,
                "学校地址": addr,
                "网上评价摘要": review,
                "民间等级/梯队": tier_label,
                "等级分": round(tier_score, 1),
                "口碑评价分": round(eval_score, 1),
                "入学难度": difficulty_label(difficulty),
                "入学难度分": round(difficulty, 1),
                "学区热度参考": area_label,
                "综合热度分": composite,
                "依据说明": "；".join(evidence),
                "来源": "；".join(dict.fromkeys(source_keys)),
            }
        )

    rows.sort(key=lambda x: (-x["综合热度分"], -x["等级分"], -x["入学难度分"], x["学校名称"]))
    for i, row in enumerate(rows, 1):
        row["综合排名"] = i

    payload = {
        "generated_note": "非官方排名。综合热度分=口碑评价分45%+等级分35%+入学难度分20%；入学难度是需求热度/录取不确定性代理，不代表必然录取概率。",
        "sources": SOURCES,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
