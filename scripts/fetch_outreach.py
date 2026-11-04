#!/usr/bin/env python3
"""Reads the event calendars of the Niels Bohr Institute (KU) and the Department of Physics and Astronomy (AU)
and keeps the public events about quantum physics and technology (public outreach).

Usage:  python scripts/fetch_outreach.py      (runs weekly in GitHub Actions, workflow "Byg og publicér Kvantekort")
Output: data/outreach/calendar.json  {sources: {url: {status, read}}, items: [...]}
Items are kept once found, so the file builds a history; a source that does not answer keeps its last items.
An event counts when its title or text is on the CFQT content map (scripts/cfqt_classify.py) and it is
marked as open to the public (public lecture, open house, for everyone, upper-secondary students, ...).
"""
import datetime as dt, json, pathlib, re, sys
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cfqt_classify import classify  # noqa: E402
from fetch_group_feeds import get, find_date, clean, generic_list, soup  # noqa: E402

OUT = ROOT / "data/outreach/calendar.json"
SOURCES = [
    {"provider": "KU", "kind": "rss", "url": "https://nbi.ku.dk/english/kalender/?get_rss=1"},
    {"provider": "KU", "kind": "rss", "url": "https://nbi.ku.dk/kalender/?get_rss=1"},
    {"provider": "AU", "kind": "list", "url": "https://phys.au.dk/aktuelt/arrangementer"},
    {"provider": "AU", "kind": "list", "url": "https://phys.au.dk/en/news/events"},
]
PUBLIC = re.compile(r"\b(public|offentlig\w*|popular|populærvidensk\w*|for (alle|everyone|all)|open (house|lab|day)|åbent? hus|"
                    r"folkeuniversitet\w*|gymnasie\w*|high[- ]school|skoleelever|students? from upper|outreach|kulturnat\w*|"
                    r"science (show|festival|café|cafe)|videnskabsfestival|forskningens døgn|festival|museum|foredrag|lecture for)\b", re.I)
NOT_PUBLIC = re.compile(r"(\b(seminar|colloqui\w*|defen[cs]e|forsvar\w*|journal club|group meeting|retreat|annual meeting|thesis|afhandling|ph\.?d\.?)\b|ph\.?d\.?-)", re.I)


def level(subs):
    """Public events reach A2 Literacy in the area of their main topic and A1 Awareness in other areas."""
    area = lambda s: "I" if s.split(".")[0] in ("1", "2") or s in ("5.1", "5.4", "5.5") else ("III" if s.split(".")[0] == "8" or s in ("5.6", "6.7", "7.4", "7.6") else "II")
    prof = {}
    for i, s in enumerate(subs):
        a = area(s)
        if a not in prof: prof[a] = "A2" if i == 0 else "A1"
    return prof


def from_rss(xml):
    root = ET.fromstring(xml)
    out = []
    for it in root.iter("item"):
        title = clean(it.findtext("title")); link = clean(it.findtext("link"))
        desc = clean(re.sub(r"<[^>]+>", " ", it.findtext("description") or ""))
        d = find_date(desc) or find_date(title)
        out.append({"title": title, "url": link, "text": desc[:400], "date": d.isoformat() if d else ""})
    return out


def keep(item, fetch_page=False):
    text = item["title"] + " " + item.get("text", "")
    subs = classify(item["title"]) or classify(text)
    if not subs: return None
    if NOT_PUBLIC.search(item["title"]): return None
    if not PUBLIC.search(text) and fetch_page:
        try:
            page = clean(soup(get(item["url"])).get_text(" "))[:4000]
            text += " " + page
        except Exception:  # noqa: BLE001
            pass
    if not PUBLIC.search(text): return None
    return subs


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"sources": {}, "items": []}
    items = {x["url"] + "|" + x["title"]: x for x in old.get("items", []) if not NOT_PUBLIC.search(x["title"])}
    sources = old.get("sources", {})
    today = dt.date.today().isoformat()
    for src in SOURCES:
        try:
            raw = get(src["url"])
            found = from_rss(raw) if src["kind"] == "rss" else generic_list(raw, src["url"])
            n = 0
            for it in found:
                subs = keep(it, fetch_page=src["kind"] == "list")
                if not subs: continue
                key = it["url"] + "|" + it["title"]
                items[key] = {"kind": "O", "provider": src["provider"], "date": it.get("date", ""), "title": it["title"], "url": it["url"],
                              "subs": subs, "prof": level(subs), "source": src["url"], "found": items.get(key, {}).get("found", today)}
                n += 1
            sources[src["url"]] = {"status": "read", "read": today, "events": len(found), "kept": n}
            print("read", src["url"], len(found), "events,", n, "public quantum events")
        except Exception as e:  # noqa: BLE001
            prev = sources.get(src["url"], {})
            sources[src["url"]] = {**prev, "status": f"not reachable ({type(e).__name__})", "tried": today}
            print("failed", src["url"], type(e).__name__, e)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"sources": sources, "items": sorted(items.values(), key=lambda x: x.get("date", ""), reverse=True)},
                              ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
