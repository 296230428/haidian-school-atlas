import json
import re
from pathlib import Path

import pandas as pd


INPUT = Path("outputs/ranking_data/海淀义务教育学校排行数据.xlsx")
OUT = Path("outputs/ranking_data/address_regions.json")


REGION_RULES = [
    ("西北旺/永丰片区", "北部", ["西北旺", "永丰", "亮甲店村", "山水小区", "英润路", "唐家岭", "正林街", "安河家园", "菊园"]),
    ("上地/西二旗片区", "北部", ["上地", "西二旗", "智学苑", "信息路", "文龙家园", "龙樾", "清华东路4号"]),
    ("清河/西三旗片区", "东北部", ["清河", "西三旗", "安宁庄", "永泰", "宝盛", "建材城", "观澳园", "回龙观", "翡丽铂庭", "朱房路"]),
    ("学院路/花园路片区", "东部", ["学院路", "花园路", "蓟门", "王庄路", "学清路", "月泉路", "北京航空航天大学", "北京科技大学", "北京石油学院", "清华东路35号", "新外大街", "北三环西路", "建安西路"]),
    ("中关村/海淀片区", "中北部", ["中关村", "知春里", "太阳园", "科春", "北京大学燕东园", "清华大学30号", "圆明园西路", "清华大学", "圆明园"]),
    ("万柳/万泉河片区", "中部", ["万柳", "万泉", "芙蓉南街", "万泉庄", "蓝靛厂", "火器营", "厢红旗"]),
    ("双榆树/人大-北理片区", "中东部", ["双榆树", "中关村南大街5号", "中关村南大街12号", "人大", "北理", "花园路甲3号"]),
    ("紫竹院/万寿寺片区", "中南部", ["紫竹", "万寿寺", "魏公村", "民族", "后黑寺", "二里沟", "新街口外大街", "红联北村", "花园村"]),
    ("羊坊店/翠微片区", "南部", ["羊坊店", "翠微", "北蜂窝", "交大东路", "北蜂窝路", "复兴路24号", "莲花池西路"]),
    ("八里庄/定慧寺片区", "西南部", ["八里庄", "定慧", "田村", "金沟河", "亮甲店1号", "西三环北路107号", "恩济里", "通汇路"]),
    ("永定路/玉泉路片区", "西南部", ["永定路", "玉泉", "采石路", "正大南路", "太平路", "金沟河路", "复兴路14号"]),
    ("香山/四季青片区", "西部", ["香山", "四季青", "正白旗", "黑塔村", "门头村", "厢红旗19号"]),
    ("温泉/苏家坨片区", "西北部", ["温泉", "苏家坨", "台头", "聂各庄", "小营村", "正林街安河家园", "向山路", "凤仪佳苑", "白水洼"]),
    ("北安河片区", "西北部", ["北安河", "环谷园"]),
    ("肖家河/西苑片区", "西部", ["肖家河", "西苑", "培星", "韩家川", "王庄1号"]),
]


def explicit_town_or_street(address: str) -> str:
    match = re.search(r"海淀区([^号\d]{2,12}?(?:镇|街道))", address)
    return match.group(1) if match else ""


def classify(address: str, name: str):
    text = f"{address} {name}"
    explicit = explicit_town_or_street(address)
    for region, direction, keywords in REGION_RULES:
        for keyword in keywords:
            if keyword in text:
                basis = f"匹配地址关键词：{keyword}"
                if explicit:
                    basis = f"{basis}；地址含：{explicit}"
                return region, direction, basis

    if explicit:
        if "镇" in explicit:
            return f"{explicit}片区", "西北部", f"地址含：{explicit}"
        return f"{explicit}片区", "未明确", f"地址含：{explicit}"
    return "未明确片区", "未明确", "地址缺少可识别片区关键词"


def main():
    df = pd.read_excel(INPUT, sheet_name="排行数据")
    region_info = df.apply(lambda r: classify(str(r["学校地址"]), str(r["学校名称"])), axis=1)
    df.insert(5, "地址片区", [x[0] for x in region_info])
    df.insert(6, "方位片区", [x[1] for x in region_info])
    df.insert(7, "片区依据", [x[2] for x in region_info])

    detail = df.sort_values(["地址片区", "综合排名", "学校名称"], ascending=[True, True, True])
    summary = (
        df.groupby(["地址片区", "方位片区"], as_index=False)
        .agg(
            学校数量=("学校名称", "count"),
            小学数量=("办学层次", lambda s: int((s == "小学").sum())),
            初中及九年一贯制数量=("办学层次", lambda s: int((s != "小学").sum())),
            平均综合热度分=("综合热度分", "mean"),
            最高综合排名=("综合排名", "min"),
            S_A档数量=("等级分", lambda s: int((s >= 84).sum())),
        )
        .sort_values(["学校数量", "平均综合热度分"], ascending=[False, False])
    )
    summary["平均综合热度分"] = summary["平均综合热度分"].round(1)

    payload = {
        "detail_headers": detail.columns.tolist(),
        "detail_rows": detail.where(pd.notnull(detail), "").to_dict(orient="records"),
        "summary_headers": summary.columns.tolist(),
        "summary_rows": summary.where(pd.notnull(summary), "").to_dict(orient="records"),
        "rules": [
            {
                "地址片区": region,
                "方位片区": direction,
                "关键词": "、".join(keywords),
            }
            for region, direction, keywords in REGION_RULES
        ],
        "note": "地址片区按学校地址中的街镇、道路、小区或地标关键词划分；这是地址分组，不等同于官方入学学区或划片范围。",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} detail={len(detail)} summary={len(summary)}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
