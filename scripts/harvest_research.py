#!/usr/bin/env python3
"""Harvests the research output (2021 onwards) and the supervised PhD theses of every educator from the
universities' public research portals (Pure). Runs in GitHub Actions (workflow "Harvest research output"),
because the portals cannot be reached from everywhere. Uses a real browser (Playwright), since some portals
show a bot check before the page.

Usage:  python scripts/harvest_research.py INST [INST ...]     (DTU KU AU SDU AAU)
Output: data/people/research_outputs/<inst>.tsv
        columns: name, kind (O = research output, S = supervised PhD thesis), year, type, title, path
        plus one line per educator with kind "-" giving the profile path that was used (or MISS)
"""
import asyncio, csv, pathlib, re, sys, urllib.parse
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = {"DTU": "https://orbit.dtu.dk", "KU": "https://researchprofiles.ku.dk", "AU": "https://pure.au.dk/portal",
        "SDU": "https://portal.findresearcher.sdu.dk", "AAU": "https://vbn.aau.dk"}
FROM = 2021
import os
DEBUG = os.environ.get("DEBUG")
LIMIT = int(os.environ.get("LIMIT", "0"))
OUT = ROOT / "data/people/research_outputs"

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
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        ctx = await br.new_context(locale="en-GB", user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        page = await ctx.new_page()
        for name, path in educators(inst)[:LIMIT or None]:
            if inst == "AU" and not path:
                path = await find_au(page, name)
                if path and not path.endswith("/"): path += "/"
            if not path:
                rows.append([name, "-", "", "", "", "MISS"]); print(inst, name, "MISS", flush=True); continue
            base = ("https://pure.au.dk" + (path if path.startswith("/portal") else "/portal" + path)) if inst == "AU" else BASE[inst] + path
            rows.append([name, "-", "", "", "", "AU portal search" if inst == "AU" else path])  # AU profile paths contain e-mail addresses
            outs = await listing(page, base + "publications/")
            for o in outs:
                if o["year"] and int(o["year"]) >= FROM:
                    rows.append([name, "O", o["year"], o["type"], o["title"], urllib.parse.urlparse(o["href"]).path])
            sup = await listing(page, base + "supervised/", stop_year=0)
            for o in sup:
                if "dissertation" in o["type"].lower() or "thesis" in o["type"].lower() or "ph.d" in o["type"].lower() or "phd" in o["type"].lower():
                    rows.append([name, "S", o["year"], o["type"], o["title"], urllib.parse.urlparse(o["href"]).path])
            print(inst, name, len([r for r in rows if r[0] == name and r[1] == "O"]), "outputs,",
                  len([r for r in rows if r[0] == name and r[1] == "S"]), "theses", flush=True)
        await br.close()
    with (OUT / f"{inst.lower()}.tsv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t"); w.writerow(["name", "kind", "year", "type", "title", "path"]); w.writerows(rows)

if __name__ == "__main__":
    for i in sys.argv[1:] or BASE: asyncio.run(run(i.upper()))
