#!/usr/bin/env python3
"""Reads job ads about quantum technology in Denmark and maps the demand on the CFQT proficiency triangle.

Usage:  python scripts/fetch_jobs.py      (runs weekly in GitHub Actions, workflow "Byg og publicér Kvantekort")
Source: Jobindex search feeds (public RSS) for quantum terms.
Output: data/industry/jobs.json  {sources: {...}, items: [...]}; ads are kept with first and last date seen,
        so the file builds a history of the demand. Only the job title, employer, place, date and link are kept.

Each ad gets CFQT subdomains from its title and text (scripts/cfqt_classify.py) and a demanded level:
  research roles (scientist, researcher, principal, PhD) C2; senior and specialist engineering roles C1;
  engineers and developers B2; technicians, operators and assistants B1; business, sales and other roles A2.
The main topic's area gets that level, other areas it touches one level lower.
Ads from universities and other public research institutions are marked as academic and kept apart.
"""
import datetime as dt, json, pathlib, re, sys, urllib.parse
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cfqt_classify import classify  # noqa: E402
from fetch_group_feeds import get, clean, soup  # noqa: E402

OUT = ROOT / "data/industry/jobs.json"
QUERIES = ["quantum", "kvante", "qubit", "kvanteteknologi", "quantum computing", "quantum sensing", "post-quantum"]
FEED = "https://www.jobindex.dk/jobsoegning.rss?q={}"
QUANT = re.compile(r"quantum|kvante|qubit|cryo|photonic|superconduct|post-quantum|qkd|nanofab", re.I)
ACADEMIC = re.compile(r"universit|DTU\b|Danmarks Tekniske|Niels Bohr|Institut|Institute|\bKU\b|\bAU\b|\bSDU\b|\bAAU\b|Hospital|Region ", re.I)
LV = ["A1", "A2", "B1", "B2", "C1", "C2"]


def area(s):
    d = s.split(".")[0]
    return "I" if d in ("1", "2") or s in ("5.1", "5.4", "5.5") else ("III" if d == "8" or s in ("5.6", "6.7", "7.4", "7.6") else "II")


def demanded(title):
    t = title.lower()
    if re.search(r"scientist|researcher|research engineer|principal|phd|ph\.d|postdoc|r&d lead|research lead", t): return "C2"
    if re.search(r"senior|lead|specialist|architect|staff |expert|manager.*(engineering|r&d)|head of", t): return "C1"
    if re.search(r"engineer|developer|ingeniør|udvikler|programmer|designer|physicist|fysiker", t): return "B2"
    if re.search(r"technician|tekniker|operator|assistant|assistent|student|intern|praktikant|laborant", t): return "B1"
    return "A2"


def profile(subs, lvl):
    prof = {}
    for i, s in enumerate(subs):
        a = area(s)
        if a in prof: continue
        prof[a] = lvl if i == 0 else LV[max(0, LV.index(lvl) - 1)]
    return prof


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"sources": {}, "items": []}
    items = {x["url"]: x for x in old.get("items", [])}
    sources = old.get("sources", {})
    today = dt.date.today().isoformat()
    for q in QUERIES:
        url = FEED.format(urllib.parse.quote(q))
        try:
            root = ET.fromstring(get(url).encode("latin-1", "replace"))
            n = kept = 0
            for it in root.iter("item"):
                n += 1
                raw_title = clean(it.findtext("title")); link = clean(it.findtext("link")).split("?")[0]
                desc_html = it.findtext("description") or ""
                s = soup(desc_html)
                place = clean((s.select_one(".jix_robotjob--area") or s.select_one(".jobad-element-area") or s).get_text(" "))[:60] if s else ""
                text = clean(s.get_text(" "))[:1500] if s else ""
                title, _, employer = raw_title.rpartition(", ")
                if not title: title, employer = raw_title, ""
                pub = it.findtext("pubDate") or ""
                if not QUANT.search(raw_title + " " + text): continue
                subs = classify(title) or classify(title + " " + text[:600])
                lvl = demanded(title)
                tech = bool(subs) and lvl != "A2"
                rec = items.get(link, {"first": today})
                rec.update({"title": title, "employer": employer, "place": place, "url": link, "last": today,
                            "academic": bool(ACADEMIC.search(employer)), "subs": subs, "level": lvl if subs else "",
                            "prof": profile(subs, lvl) if subs else {}, "technical": tech, "query": rec.get("query", q)})
                items[link] = rec; kept += 1
            sources[url] = {"status": "read", "read": today, "ads": n, "kept": kept}
            print("read", url, n, "ads,", kept, "about quantum technology")
        except Exception as e:  # noqa: BLE001
            sources[url] = {**sources.get(url, {}), "status": f"not reachable ({type(e).__name__})", "tried": today}
            print("failed", url, type(e).__name__, e)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"sources": sources, "items": sorted(items.values(), key=lambda x: x.get("last", ""), reverse=True)},
                              ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
