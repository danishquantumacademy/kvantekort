#!/usr/bin/env python3
"""Harvests the research output (2021 onwards) and the supervised PhD theses of every educator.
Research output comes from OpenAlex (openalex.org, open bibliographic data), matched on the educator's name and
university, because the portals' publication lists sit behind a bot check. Supervised PhD theses come from the
"Supervised work" tab of the universities' public research portals (Pure), read with a real browser (Playwright).
Runs in GitHub Actions (workflow "Harvest research output").

Usage:  python scripts/harvest_research.py INST [INST ...]     (DTU KU AU SDU AAU)
Output: data/people/research_outputs/<inst>.tsv
        columns: name, kind (O = research output, S = supervised PhD thesis), year, type, title, path
        plus one line per educator with kind "-" giving the profile path that was used (or MISS)
"""
import asyncio, csv, json, pathlib, re, sys, time, unicodedata, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = {"DTU": "https://orbit.dtu.dk", "KU": "https://researchprofiles.ku.dk", "AU": "https://pure.au.dk/portal",
        "SDU": "https://portal.findresearcher.sdu.dk", "AAU": "https://vbn.aau.dk"}
FROM = 2021
import os
DEBUG = os.environ.get("DEBUG")
LIMIT = int(os.environ.get("LIMIT", "0"))
OUT = ROOT / "data/people/research_outputs"

ROR = {"DTU": "04qtj9h94", "KU": "035b05819", "AU": "01aj84f44", "SDU": "03yrrjy16", "AAU": "04m5j1k67"}
UA = {"User-Agent": "DQA-map/1.0 (+https://map.danishquantumacademy.dk)"}

def oa(url):
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                time.sleep(0.25)
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print("  openalex retry", type(e).__name__, getattr(e, "code", ""), flush=True); time.sleep(min(90, 5 * 2 ** attempt))
    raise RuntimeError("OpenAlex not reachable: " + url)

TRANS = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "å": "a", "Å": "a", "ß": "ss", "ł": "l", "đ": "d"})
def norm(s):
    s = unicodedata.normalize("NFKD", s.translate(TRANS)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s).split()

def same_person(name, cand):
    a, b = norm(name), norm(cand)
    if not a or not b: return False
    if a == b: return True
    # same last name and same first name (or first initial when one side is abbreviated)
    return a[-1] == b[-1] and (a[0] == b[0] or (len(b[0]) == 1 and a[0][0] == b[0]) or (len(a[0]) == 1 and b[0][0] == a[0]))

def openalex_outputs(inst, name):
    q = urllib.parse.quote(name)
    res = oa(f"https://api.openalex.org/authors?search={q}&filter=affiliations.institution.ror:https://ror.org/{ROR[inst]}&per-page=25&select=id,display_name,display_name_alternatives,works_count")
    ids = [a["id"].rsplit("/", 1)[-1] for a in res.get("results", [])
           if a.get("works_count") and any(same_person(name, n) for n in [a["display_name"], *(a.get("display_name_alternatives") or [])])][:4]
    out, seen = [], set()
    # several matching author records (common names): keep only works with an author at this university
    inst_f = f",institutions.ror:https://ror.org/{ROR[inst]}" if len(ids) > 1 else ""
    for aid in ids:
        cursor = "*"
        while cursor:
            r = oa(f"https://api.openalex.org/works?filter=author.id:{aid},publication_year:>{FROM - 1}{inst_f}&per-page=200&cursor={cursor}&select=id,title,publication_year,type,doi")
            for w in r.get("results", []):
                t = (w.get("title") or "").strip()
                if not t or w["id"] in seen: continue
                seen.add(w["id"])
                out.append({"title": re.sub(r"<[^>]+>", "", t), "year": str(w.get("publication_year") or ""), "type": w.get("type") or "",
                            "url": w.get("doi") or w["id"]})
            cursor = r.get("meta", {}).get("next_cursor") if r.get("results") else None
            time.sleep(0.15)
    return ids, out

def educators(inst):
    rows = []
    for ln in (ROOT / f"data/people/{inst.lower()}.txt").read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"): continue
        f = ln.split("||")
        path = f[-1].strip() if f[-1].strip().startswith("/") else ""
        rows.append((f[0].strip(), path))
    return rows

# Reads one listing page in the page itself: title, year, type and link of each item.
JS_LIST = r"""() => [...document.querySelectorAll('main h3')].map(h => {
  const li = h.closest('li') || h.parentElement.parentElement; const t = li.innerText || '';
  const a = h.querySelector('a'); const y = (t.match(/\b(19|20)\d\d\b/) || [''])[0];
  const typ = ((t.match(/Research output: ([^\n]*)/) || t.match(/Forskningsoutput: ([^\n]*)/) || ['', ''])[1] || '').replace(/\s*›\s*/g, ' > ');
  return {title: h.innerText.trim(), year: y, type: typ, href: a ? a.getAttribute('href') : ''};
}).filter(x => x.title && !/^\\d{4}$/.test(x.title))"""

async def goto(page, url):
    for attempt in range(3):
        try:
            r = await page.goto(url, wait_until="load", timeout=60000)
            # wait out a bot check ("Just a moment" / "Et øjeblik")
            for _ in range(20):
                t = await page.title()
                if not re.search(r"moment|øjeblik|attention", t, re.I): break
                await page.wait_for_timeout(1500)
            # a bot check may reload the page; wait until the listing (or an empty-result text) is there
            try:
                await page.wait_for_selector("main h3", timeout=15000)
            except Exception:  # noqa: BLE001
                pass
            await page.wait_for_timeout(600)
            if re.search(r"moment|øjeblik|attention", await page.title(), re.I):
                await page.wait_for_timeout(8000)
            return r.status if r else 0
        except Exception as e:  # noqa: BLE001
            print("  retry", url, type(e).__name__, flush=True)
            await page.wait_for_timeout(3000)
    return 0

async def find_au(page, name):
    q = urllib.parse.quote(name)
    await goto(page, f"{BASE['AU']}/en/persons/?search={q}")
    hrefs = await page.evaluate("() => [...document.querySelectorAll('main h3 a')].map(a => [a.innerText.trim(), a.getAttribute('href')])")
    norm = lambda s: re.sub(r"[^a-zæøå]", "", s.lower())
    for t, h in hrefs:
        if norm(t) == norm(name): return urllib.parse.urlparse(h).path
    return urllib.parse.urlparse(hrefs[0][1]).path if hrefs else ""

async def listing(page, url, stop_year=FROM):
    items, seen = [], set()
    for p in range(0, 30):
        st = await goto(page, url + (f"?page={p}" if p else ""))
        if DEBUG: print("   status", st, page.url, await page.title(), flush=True)
        if st >= 400 and p == 0:
            st = await goto(page, url.rstrip("/"))
            if DEBUG: print("   status (no slash)", st, page.url, flush=True)
        if st >= 400: break
        got = await page.evaluate(JS_LIST)
        if DEBUG: print("   ", url, p, len(got), got[:2], flush=True)
        if not got and p == 0:  # second chance after a bot check
            await page.wait_for_timeout(5000); await goto(page, url); got = await page.evaluate(JS_LIST)
        new = [g for g in got if (g["title"], g["year"]) not in seen]
        if not new: break
        for g in new: seen.add((g["title"], g["year"]))
        items += new
        ys = [int(g["year"]) for g in new if g["year"]]
        if ys and max(ys) < stop_year: break
    return items

async def run(inst):
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        ctx = await br.new_context(locale="en-GB", user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        page = await ctx.new_page()
        for name, path in educators(inst)[:LIMIT or None]:
            if not path:
                rows.append([name, "-", "", "", "", "MISS"])
                ids, outs = openalex_outputs(inst, name)
                rows.append([name, "A", "", "", "", " ".join(ids)])
                rows += [[name, "O", o["year"], o["type"], o["title"], o["url"]] for o in outs if o["year"] and int(o["year"]) >= FROM]
                print(inst, name, "no portal path;", len(outs), "outputs from OpenAlex", flush=True); continue
            base = ("https://pure.au.dk" + (path if path.startswith("/portal") else "/portal" + path)) if inst == "AU" else BASE[inst] + path
            rows.append([name, "-", "", "", "", "AU portal search" if inst == "AU" else path])  # AU profile paths contain e-mail addresses
            ids, outs = openalex_outputs(inst, name)
            rows.append([name, "A", "", "", "", " ".join(ids)])
            for o in outs:
                if o["year"] and int(o["year"]) >= FROM:
                    rows.append([name, "O", o["year"], o["type"], o["title"], o["url"]])
            sup = await listing(page, base + "supervised/", stop_year=0) if inst not in ("AU", "DTU") else []  # DTU Orbit has no supervised tab
            for o in sup:
                if "dissertation" in o["type"].lower() or "thesis" in o["type"].lower() or "ph.d" in o["type"].lower() or "phd" in o["type"].lower():
                    rows.append([name, "S", o["year"], o["type"], o["title"], urllib.parse.urlparse(o["href"]).path])
            print(inst, name, len([r for r in rows if r[0] == name and r[1] == "O"]), "outputs,",
                  len([r for r in rows if r[0] == name and r[1] == "S"]), "theses", flush=True)
        await br.close()
    with (OUT / f"{inst.lower()}.tsv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t"); w.writerow(["name", "kind", "year", "type", "title", "path"]); w.writerows(rows)

def fill_missing(inst):
    """Re-reads OpenAlex for educators whose author record was not found (e.g. after rate limiting); keeps the rest."""
    f = OUT / f"{inst.lower()}.tsv"
    rows = list(csv.reader(f.open(encoding="utf-8"), delimiter="\t"))
    head, body = rows[0], rows[1:]
    missing = [r[0] for r in body if r[1] == "A" and not r[5].strip()]
    out = []
    for r in body:
        if r[0] in missing and r[1] in ("A", "O"): continue
        out.append(r)
        if r[0] in missing and r[1] == "-":
            ids, outs = openalex_outputs(inst, r[0])
            out.append([r[0], "A", "", "", "", " ".join(ids)])
            out += [[r[0], "O", o["year"], o["type"], o["title"], o["url"]] for o in outs if o["year"] and int(o["year"]) >= FROM]
            print(inst, r[0], len(ids), "author records,", len(outs), "outputs", flush=True)
    with f.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t"); w.writerow(head); w.writerows(out)

def harvest_groups():
    """Research output since FROM for the members of the five research groups (data/groups/<key>.txt), from OpenAlex.
    Technical and administrative staff are left out. Output: data/groups/research_outputs/<key>.tsv"""
    cfg = json.loads((ROOT / "data/groups/groups.json").read_text(encoding="utf-8"))["groups"]
    gout = ROOT / "data/groups/research_outputs"; gout.mkdir(parents=True, exist_ok=True)
    skip = re.compile(r"administrat|secretar|technician|lab(oratory)? (manager|engineer|technician)|coordinator|officer|communication|\bhr\b|finance|project manager|student assistant|teaching assistant|it[- ]", re.I)
    limited = False
    for g in cfg:
        rows = []
        f_out = gout / f"{g['key']}.tsv"
        done = {}  # resume: keep members already read (author record found or none exists)
        if f_out.exists():
            for r in csv.reader(f_out.open(encoding="utf-8"), delimiter="\t"):
                done.setdefault(r[0], []).append(r)
        for ln in (ROOT / "data/groups" / f"{g['key']}.txt").read_text(encoding="utf-8").splitlines():
            if not ln.startswith("P||"): continue
            f = (ln.split("||") + [""] * 6)
            name, role = f[1].strip(), f[2].strip()
            if skip.search(role): rows.append([name, "-", "", "", "", "skipped: " + role]); continue
            prev = done.get(name, [])
            if any(r[1] == "A" and r[5] != "RATE-LIMITED" for r in prev):
                rows += prev; continue
            if limited:
                rows.append([name, "A", "", "", "", "RATE-LIMITED"]); continue
            try:
                ids, outs = openalex_outputs(g["institution"], name)
            except RuntimeError:
                limited = True; print("OpenAlex rate limit reached; the rest is left for the next run", flush=True)
                rows.append([name, "A", "", "", "", "RATE-LIMITED"]); continue
            rows.append([name, "A", "", "", "", " ".join(ids)])
            rows += [[name, "O", o["year"], o["type"], o["title"], o["url"]] for o in outs if o["year"] and int(o["year"]) >= FROM]
            print(g["key"], name, len(ids), "author records,", len(outs), "outputs", flush=True)
        with f_out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, delimiter="\t"); w.writerow(["name", "kind", "year", "type", "title", "path"]); w.writerows(rows)

def harvest_industry():
    """Research output since FROM of the companies in data/industry/organisations.txt (those with a CVR number), from OpenAlex:
    the matching institution record, the number of works, the Danish universities they publish with, and work titles.
    Output: data/industry/openalex.json (companies already found are kept; the rest is tried again on the next run)."""
    outp = ROOT / "data/industry/openalex.json"
    data = json.loads(outp.read_text(encoding="utf-8")) if outp.exists() else {}
    for ln in (ROOT / "data/industry/organisations.txt").read_text(encoding="utf-8").splitlines():
        if ln.startswith("#") or not ln.strip(): continue
        f = ln.split("|")
        name, cvr = f[0], f[6]
        if not cvr or name in data: continue
        base = re.sub(r"\s*\(.*?\)|\b(ApS|A/S|P/S|Inc)\b\.?", "", name).strip()
        try:
            res = oa(f"https://api.openalex.org/institutions?search={urllib.parse.quote(base)}&filter=country_code:DK&per-page=10&select=id,display_name,type,works_count")
        except RuntimeError:
            print("OpenAlex rate limit reached; the rest is left for the next run", flush=True); break
        cand = [r for r in res.get("results", []) if norm(r["display_name"])[:2] == norm(base)[:2] or norm(base)[0] in norm(r["display_name"])]
        cand = [r for r in cand if r.get("type") in ("company", "facility", "nonprofit", "other", None)] or cand
        if not cand:
            data[name] = {"id": "", "works": 0}; print("industry", name, "no OpenAlex record", flush=True); continue
        inst = cand[0]["id"].rsplit("/", 1)[-1]
        try:
            g = oa(f"https://api.openalex.org/works?filter=institutions.id:{inst},publication_year:>{FROM - 1}&group_by=authorships.institutions.lineage")
            w = oa(f"https://api.openalex.org/works?filter=institutions.id:{inst},publication_year:>{FROM - 1}&per-page=100&select=title,publication_year,doi,id&sort=publication_year:desc")
        except RuntimeError:
            print("OpenAlex rate limit reached; the rest is left for the next run", flush=True); break
        co = {}
        for grp in g.get("group_by", []):
            key = grp.get("key", "").rsplit("/", 1)[-1]
            co[key] = {"name": grp.get("key_display_name", ""), "count": grp.get("count", 0)}
        data[name] = {"id": inst, "display": cand[0]["display_name"], "works": w.get("meta", {}).get("count", 0),
                      "co": sorted(({"id": k, **v} for k, v in co.items() if k != inst), key=lambda x: -x["count"])[:25],
                      "titles": [[x.get("publication_year"), re.sub(r"<[^>]+>", "", x.get("title") or ""), x.get("doi") or x["id"]] for x in w.get("results", []) if x.get("title")]}
        print("industry", name, inst, data[name]["works"], "works", flush=True)
        outp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    outp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    if "--industry" in sys.argv:
        harvest_industry(); sys.exit()
    if "--groups" in sys.argv:
        harvest_groups(); sys.exit()
    if os.environ.get("ONLY_MISSING"):
        for i in sys.argv[1:]: fill_missing(i.upper())
        sys.exit()
    for i in sys.argv[1:] or BASE: asyncio.run(run(i.upper()))
