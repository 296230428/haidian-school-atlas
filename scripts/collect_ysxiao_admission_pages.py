import gzip
import json
import re
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


OUT = Path("outputs/school_district/data/ysxiao_admission_pages.json")
HTML_DIR = Path("outputs/school_district/html")


def fetch(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    with urlopen(req, timeout=20) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data.decode("utf-8", "ignore")


def clean_title(title: str) -> str:
    title = re.sub(r"<[^>]+>", "", title)
    title = title.replace("&nbsp;", " ").strip()
    return title


def parse_page(article_id: int, html: str):
    title_match = re.search(r"<title>(.*?)</title>", html, re.S)
    title = clean_title(title_match.group(1)) if title_match else ""
    if "2025年海淀区" not in title or "招生简章" not in title:
        return None
    if not any(token in title for token in ["小学", "学校"]):
        return None
    image_urls = sorted(set(re.findall(r"https://cdn\.ysxiao\.cn/zixunzhan/[^\"'\\\s<>]+", html)))
    # The admission notice image is usually the large article image; filter out site logo/banner/sidebar assets.
    candidate_images = [
        u
        for u in image_urls
        if not any(
            bad in u
            for bad in [
                "logo",
                "1920",
                "120",
                "二维码",
                "图标",
                "客服",
                "微信",
                "政策发布",
                "入学政策收藏查询",
                "升学资讯",
                "北京中考",
                "北京高考",
                "教育地图",
                "教育专题",
            ]
        )
    ]
    school = title
    school = re.sub(r"^.*?海淀区", "", school)
    school = re.sub(r"2025年|招生简章|小学登记入学通知|登记入学通知|发布.*$", "", school)
    school = school.replace("2025", "").strip(" ：:-_")
    return {
        "article_id": article_id,
        "title": title,
        "school_name_from_title": school,
        "url": f"https://www.ysxiao.cn/zhongdianxiaoxue/{article_id}.html",
        "candidate_images": candidate_images,
        "all_image_count": len(image_urls),
    }


def main():
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for article_id in range(212730, 212930):
        url = f"https://www.ysxiao.cn/zhongdianxiaoxue/{article_id}.html"
        try:
            html = fetch(url)
        except URLError as exc:
            print(f"fail {article_id}: {exc}")
            continue
        (HTML_DIR / f"{article_id}.html").write_text(html, encoding="utf-8")
        parsed = parse_page(article_id, html)
        if parsed:
            results.append(parsed)
            print(parsed["article_id"], parsed["school_name_from_title"], len(parsed["candidate_images"]))
        time.sleep(0.15)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {OUT} rows={len(results)}")


if __name__ == "__main__":
    main()
