#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猫眼专业版《欢迎来龙餐馆》预售及点映总票房抓取
GitHub Actions 每小时整点运行，结果追加到 maoyan_presale.csv
"""
import csv
import json
import os
import re
import sys
import urllib.request
import http.cookiejar
from datetime import datetime, timedelta

MOVIE_ID = "1462628"
MOVIE_NAME = "欢迎来龙餐馆"
RELEASE_DATE = "20260811"
BASE = "https://piaofang.maoyan.com"
UA_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

CSV_PATH = os.path.join(os.getcwd(), "maoyan_presale.csv")


def build_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get(opener, url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_presale():
    opener = build_opener()
    page_headers = {
        "User-Agent": UA_IPHONE,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "identity",
    }
    page_url = f"{BASE}/i/imovie/{MOVIE_ID}/premiere"
    html = get(opener, page_url, page_headers)
    m = re.search(r'name="csrf" content="([^"]+)"', html)
    if not m:
        raise RuntimeError("无法获取 csrf")
    csrf = m.group(1)

    api_headers = {
        "User-Agent": UA_IPHONE,
        "uid": csrf,
        "Referer": page_url,
        "Origin": BASE,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "identity",
    }
    api_url = f"{BASE}/i/api/movie/getBoxShow?movieId={MOVIE_ID}&boxLevel=1"
    text = get(opener, api_url, api_headers)
    data = json.loads(text)
    rows = [r for day in data["data"]["boxDatas"] for r in day if isinstance(r, dict)]

    point = sum(r["box"] for r in rows if r.get("releaseInfo") == "点映")
    first = sum(r["box"] for r in rows if str(r.get("showDate")) == RELEASE_DATE)
    total = point + first

    detail = {}
    for r in rows:
        d = str(r.get("showDate"))
        if r.get("box", 0) > 0 and d <= RELEASE_DATE:
            detail[d] = {"票房(元)": r["box"], "场次": r.get("showCount"), "人次": r.get("viewCountDesc")}
    return total, point, first, detail


def main():
    now = datetime.utcnow() + timedelta(hours=8)  # 北京时间
    try:
        total, point, first, detail = fetch_presale()
        line = {
            "时间": now.strftime("%Y-%m-%d %H:%M:%S"),
            "预售及点映总票房(元)": total,
            "合计(万)": round(total / 10000, 2),
            "点映预售(元)": point,
            "首日预售(元)": first,
            "分日明细": json.dumps(detail, ensure_ascii=False),
        }
        is_new = not os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(line.keys()))
            if is_new:
                w.writeheader()
            w.writerow(line)
        print(f"[{line['时间']}] {MOVIE_NAME} 总票房: {line['合计(万)']} 万 -> OK")
        return 0
    except Exception as e:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 抓取失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
