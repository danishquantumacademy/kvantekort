#!/usr/bin/env python3
"""Reads DeiC's quantum news list (https://www.deic.dk/da/news/all?dept=154) and keeps the newest items in
data/events/deic_news.json for the events page. Each news URL carries its date (/da/news/YYYY-MM-DD/slug).
If the page cannot be read or no items are found, the last known list is kept.  Runs every Monday in GitHub Actions."""
import datetime as dt, json, pathlib, re, sys, urllib.request
from html import unescape

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/events/deic_news.json"
SRC = "https://www.deic.dk/da/news/all?dept=154"
UA = "Mozilla/5.0 (compatible; DQA-map/1.0; +https://map.danishquantumacademy.dk)"
LINK = re.compile(r'<a[^>]+href="((?:https://www\.deic\.dk)?/da/news/(\d{4}-\d\d-\d\d)/[^"#?]+)"[^>]*>(.*?)</a>', re.S | re.I)

def read(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    items, seen = [], set()
    try:
        for page in range(3):
            html = read(SRC + (f"&page={page}" if page else ""))
            for href, date, inner in LINK.findall(html):
                title = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
                url = href if href.startswith("http") else "https://www.deic.dk" + href
                if len(title) < 12 or url in seen: continue
                seen.add(url); items.append({"date": date, "title": title, "url": url})
    except Exception as e:  # keep the last list
        print("DeiC news not read:", e); return
    if not items:
        print("DeiC news: no items found; keeping the last list"); return
    # keep older items that dropped off the three pages
    for x in old.get("items", []):
        if x["url"] not in seen: items.append(x)
    items.sort(key=lambda x: x["date"], reverse=True)
    OUT.write_text(json.dumps({"source": SRC, "read": dt.date.today().isoformat(), "items": items[:40]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DeiC news:", len(items), "items")

if __name__ == "__main__":
    main()
