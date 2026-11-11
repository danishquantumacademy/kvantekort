#!/usr/bin/env python3
"""Henter nyheder, events, bevillinger, stillinger og seneste publikationer for forskningsgrupperne.

Brug:  python scripts/fetch_group_feeds.py            (kører i GitHub Actions hver uge)
Input:  data/groups/groups.json  (feeds pr. gruppe)
Output: data/groups/feeds.json   (opdateres kun for kilder, der svarer; ellers beholdes sidste kendte data)

Kilder, der kræver en browser (Cloudflare-beskyttede lister i forskningsportalerne), høstes ikke her;
medlemmer, publikationslister og projekter ligger i data/groups/<key>.txt og opdateres manuelt.
"""
import datetime as dt, json, pathlib, re, sys, urllib.request
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    sys.exit("pip install beautifulsoup4 lxml")

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "data/groups/groups.json").read_text(encoding="utf-8"))
OUT = ROOT / "data/groups/feeds.json"
UA = "Mozilla/5.0 (compatible; DQA-map/1.0; +https://map.danishquantumacademy.dk)"
TODAY = dt.date.today()

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
MONTHS.update({m: i for i, m in enumerate(["januar", "februar", "marts", "april", "maj", "juni", "juli", "august", "september", "oktober", "november", "december"], 1)})
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9
MON = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_RES = [
    (re.compile(r"\b(20\d\d)\.(\d{1,2})\.(\d{1,2})\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),  # 2026.10.30 (math.ku.dk)
    (re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(20\d\d)\b"), lambda m: (int(m[3]), int(m[2]), int(m[1]))),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b"), lambda m: (int(m[3]), int(m[2]), int(m[1]))),
    (re.compile(r"\b(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\.?\s+(" + MON + r")\.?,?\s+(20\d\d)\b", re.I), lambda m: (int(m[3]), MONTHS[m[2].lower()], int(m[1]))),
    (re.compile(r"\b(" + MON + r")\.?\s+(\d{1,2}),?\s+(20\d\d)\b", re.I), lambda m: (int(m[3]), MONTHS[m[1].lower()], int(m[2]))),
]
GRANT = re.compile(r"(\bgrant(s|ed)?\b|\bawarded\b|\breceives?\b.{0,80}\b(million|mio\.?|DKK|EUR|kr\.)|\bbevilling|\bbevilget|\bERC (Starting|Consolidator|Advanced|Synergy|Proof)|Sk[lł]odowska-Curie|Villum (Investigator|Young Investigator|Experiment)|\b\d+(\.\d+)? ?(million|mio\.?) ?(DKK|kr|EUR|euro))", re.I)
JOB = re.compile(r"\b(vacanc\w*|position[s]? (?:in|at|available|open)|open position|phd position|postdoc(?:toral)? position|we are hiring|ledig\w* stilling|stillingsopslag|apply now)\b", re.I)
PRIZE = re.compile(r"\b(prize|award(ed|s)?|medal|pris(en)?|elected (as )?fellow|fellow of the)\b", re.I)
EVENT = re.compile(r"\b(seminar|colloquium|workshop|conference|symposium|summer school|defen[cs]e|lecture|hackathon|hack|talk|meeting|retreat)\b", re.I)


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def find_date(text):
    for rx, f in DATE_RES:
        m = rx.search(text)
        if m:
            try:
                y, mo, d = f(m)
                return dt.date(y, mo, d)
            except ValueError:
                continue
    return None


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def soup(html):
    s = BeautifulSoup(html, "lxml")
    for t in s(["script", "style", "nav", "header", "footer", "noscript"]):
        t.decompose()
    return s


def generic_list(html, base):
    """Elementer med både et link og en dato (nyhedslister, eventlister) i CMS'er som au.dk og sdu.dk."""
    s = soup(html)
    main = s.find("main") or s.find(id=re.compile("content", re.I)) or s.body or s
    items, seen = [], set()
    for el in main.find_all(["li", "article", "div"]):
        a = el.find("a", href=True)
        if not a:
            continue
        txt = clean(el.get_text(" "))
        if len(txt) > 600 or len(txt) < 12 or re.search(r"\b(Revideret|Revised|Senest opdateret|Last updated)\b", txt):
            continue
        date = find_date(txt)
        if not date:
            continue
        # det inderste element med både link og dato vinder
        inner = [c for c in el.find_all(["li", "article", "div"]) if c.find("a", href=True) and find_date(clean(c.get_text(" ")))]
        if inner:
            continue
        href = urljoin(base, a["href"])
        title = clean(a.get("title") or (el.find(["h2", "h3", "h4"]) or a).get_text(" "))
        if len(title) < 6 or href in seen or re.fullmatch(r"(read more|læs mere|show all|see all)", title, re.I):
            continue
        seen.add(href)
        rest = clean(txt.replace(title, "", 1))
        rest = re.sub(r"(Read more|Read article|Læs mere)\s*$", "", rest).strip()
        items.append({"date": date.isoformat(), "title": title, "url": href, "text": rest[:220]})
    return items


def dated_lines(html, base):
    """Sider, hvor events står som en dato-linje efterfulgt af en titel-linje (fx QPIT's eventside)."""
    s = soup(html)
    main = s.find("main") or s.body or s
    lines = [clean(x) for x in main.get_text("\n").split("\n")]
    lines = [x for x in lines if x and x != ","]
    items = []
    for i, ln in enumerate(lines[:-1]):
        if len(ln) <= 40 and find_date(ln) and re.match(r"^\d", ln):
            title = lines[i + 1]
            if find_date(title):
                continue
            extra = lines[i + 2] if i + 2 < len(lines) and len(lines[i + 2]) < 120 and not find_date(lines[i + 2]) else ""
            items.append({"date": find_date(ln).isoformat(), "title": title + (" " + extra if extra.startswith(",") else ""), "url": base, "text": ln})
    return items


def pure_overview(html, base):
    """Seneste forskningsoutput og presseomtale fra en Pure-organisationsside (forsiden er ikke Cloudflare-beskyttet)."""
    s = soup(html)
    out = []
    for r in s.select(".rendering_researchoutput, .rendering_clipping, [class*='rendering_contributiontojournal']"):
        t = r.select_one(".title")
        a = r.select_one(".title a, a.link")
        if not t:
            continue
        txt = clean(r.get_text(" "))
        date = find_date(txt)
        year = re.search(r"\b(20\d\d)\b", txt)
        kind = "press" if "clipping" in " ".join(r.get("class", [])) else "output"
        out.append({"date": date.isoformat() if date else (year[1] + "-01-01" if year else ""), "title": clean(t.get_text(" ")),
                    "url": urljoin(base, a["href"]) if a and a.get("href") else base, "text": "", "kind": kind})
    return out


def call_deadlines(html, base):
    """Jobsider uden liste, hvor ansøgningsrunder står som tekst: 'The deadline for the next PhD call is November 1, 2026.'
    efterfulgt af et afsnit med link til opslaget (fx QMATH). Alle runder returneres med fristen i 'deadline';
    siden viser kun dem, hvis frist ikke er overskredet."""
    s = soup(html)
    main = s.find("main") or s.body or s
    els = main.find_all(["p", "li", "h2", "h3", "h4"])
    items = []
    for i, el in enumerate(els):
        txt = clean(el.get_text(" "))
        m = re.search(r"deadline for the (?:next )?(.{2,40}?) call is (.{6,30}?\d{4})", txt, re.I)
        if not m:
            continue
        d = find_date(m[2])
        if not d:
            continue
        a = el.find("a", href=True) or next((x.find("a", href=True) for x in els[i + 1:i + 3] if x.find("a", href=True)), None)
        title = clean(a.get_text(" ")) if a and len(clean(a.get_text(" "))) > 6 else f"{m[1]} call"
        items.append({"date": d.isoformat(), "deadline": d.isoformat(), "title": title, "url": urljoin(base, a["href"]) if a else base,
                      "text": f"Application deadline · {m[1]} call"})
    return items


PARSERS = {"generic_list": generic_list, "dated_lines": dated_lines, "pure_overview": pure_overview, "call_deadlines": call_deadlines}


def classify(item, kind):
    t = item["title"] + " " + item.get("text", "")
    if item.get("kind") == "output":
        return "outputs"
    if item.get("kind") == "press":
        return "news"
    if kind == "jobs" or JOB.search(item["title"]):
        return "jobs"
    if kind == "events":
        return "events"
    if GRANT.search(t) or PRIZE.search(t):
        return "grants"
    return "news"


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"groups": {}}
    result = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "groups": {}}
    for g in CFG["groups"]:
        prev = old.get("groups", {}).get(g["key"], {})
        rec = {"news": [], "events": [], "grants": [], "jobs": [], "outputs": [], "sources": []}
        for f in g.get("feeds", []):
            status = {"url": f["url"], "kind": f["kind"]}
            try:
                items = PARSERS[f["type"]](get(f["url"]), f["url"])
                if not items:
                    raise ValueError("no items found")
                for it in items:
                    rec[classify(it, f["kind"])].append(it)
                status.update(ok=True, n=len(items), checked=result["generated"])
            except Exception as e:  # kilde nede eller ændret: behold sidste kendte data for denne kilde
                status.update(ok=False, error=str(e)[:160], checked=result["generated"])
                for k in ("news", "events", "grants", "jobs", "outputs"):
                    rec[k] += [x for x in prev.get(k, []) if x.get("source") == f["url"]]
            for k in ("news", "events", "grants", "jobs", "outputs"):
                for x in rec[k]:
                    x.setdefault("source", f["url"])
            rec["sources"].append(status)
        for k in ("news", "events", "grants", "jobs", "outputs"):
            uniq = {x["url"] + x["title"]: x for x in rec[k]}
            rec[k] = sorted(uniq.values(), key=lambda x: x.get("date", ""), reverse=True)[:12]
        result["groups"][g["key"]] = rec
        print(g["key"], {k: len(v) for k, v in rec.items() if k != "sources"}, [s.get("ok") for s in rec["sources"]])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
