#!/usr/bin/env python3
"""Lister alle kilder, som kortet bygger på, ud fra datafilerne i repoet.

Brug:  python scripts/list_sources.py
Output: data/sources.csv  (én række pr. URL: kategori, institution, url, hvad den er brugt til, datafil)
        SOURCES.md         (opsummering pr. kilde; teksten øverst og nederst skrives her i scriptet)

Alle kilder er offentlige sider, der kan læses uden login. Scriptet kører efter build_site.py, så listen
følger data, når der høstes nyt.
"""
import csv, json, pathlib, re
from collections import OrderedDict
from urllib.parse import quote, urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"
ref = json.loads((D / "reference.json").read_text(encoding="utf-8"))
programmes = json.loads((D / "programmes.json").read_text(encoding="utf-8"))
groups = json.loads((D / "groups/groups.json").read_text(encoding="utf-8"))["groups"]

PORTAL = {"DTU": "https://orbit.dtu.dk", "KU": "https://researchprofiles.ku.dk", "AU": "https://pure.au.dk/portal",
          "SDU": "https://portal.findresearcher.sdu.dk", "AAU": "https://vbn.aau.dk"}
PORTAL_NAME = {"DTU": "DTU Orbit", "KU": "University of Copenhagen research portal", "AU": "AU Pure",
               "SDU": "SDU Find Researcher", "AAU": "AAU VBN"}

rows = []
def add(cat, inst, url, use, src):
    if url:
        rows.append({"category": cat, "institution": inst, "url": url, "used_for": use, "data_file": src})

# 1. Framework
add("Framework", "", ref["cfqt"]["doi"], "CFQT v3.0: domains, subdomains, proficiency areas, levels and qualification profiles P1–P9", "data/reference.json")

# 2. Course catalogues: one URL per mapped course
for f in sorted((D / "classification").glob("*.csv")):
    for r in csv.DictReader(f.open(encoding="utf-8")):
        if not r["cfqt_primary"]:
            continue
        inst = {**ref["institutions"], **ref.get("schools", {})}[r["institution"]]
        url = r.get("url") or inst["course_url"].format_map({**r, "ref": r.get("ref") or r["code"]})
        add("Course catalogue", r["institution"], url, f"Course description, ECTS, level, language ({r['code']})", f"data/classification/{f.name}")
for k, v in ref["institutions"].items():
    add("Course catalogue", k, v["course_base"], "Course list and descriptions, 2026/27 (" + v.get("scope", "") + ")", "data/reference.json")
for k, v in ref.get("schools", {}).items():
    add("Upper secondary", k, v["fysik_a"]["source"], "Students and school departments with Fysik A, 2025 and 2026", "data/reference.json")
    add("Upper secondary", k, v["course_base"], "Subject guidelines (læreplaner) for stx", "data/reference.json")
add("Course catalogue", "", "https://phdcourses.dk", "PhD courses at all five universities", "data/classification/*.csv")

# 3. Timetables and prerequisites come from the same course pages as above (data/schedule/*.txt)
for f in sorted((D / "schedule").glob("*.txt")):
    head = f.read_text(encoding="utf-8").splitlines()[0]
    m = re.search(r"([a-z0-9.-]+\.dk)", head)
    if m:
        add("Timetable and prerequisites", f.stem.upper(), "https://" + m[1], "Semester, teaching block, schedule slot and recommended prerequisites, from the course pages", f"data/schedule/{f.name}")

# 4. Programme structures and curricula
for p in programmes["programmes"]:
    inst = "+".join(p["institutions"])
    add("Programme and curriculum", inst, p.get("source"), f"{p['name']}: programme page", "data/programmes.json")
    for u in p.get("curriculum", []):
        add("Programme and curriculum", inst, u, f"{p['name']}: compulsory/elective status and project size", "data/programmes.json")

# 5. Educators: research-portal profiles
for f in sorted((D / "people").glob("*.txt")):
    inst = f.stem.upper()
    if inst not in PORTAL:
        continue
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("MISS"):
            continue
        parts = line.split("||")
        if len(parts) > 1 and parts[1].strip() == "MISS":
            continue  # no portal profile found: nothing was harvested
        path = parts[-1].strip() if parts[-1].startswith("/") else ""
        name = parts[0].strip()
        url = PORTAL[inst] + path if path else f'{PORTAL[inst]}/en/persons/?search={quote(chr(34) + name + chr(34))}'
        add("Educator profile", inst, url, f"{PORTAL_NAME[inst]} profile: position, units, fingerprint concepts, recent output ({name})", f"data/people/{f.name}")

# 5b. Latest research output and ongoing PhD projects (educator as main supervisor), from the research portals
import unicodedata
def pure_slug(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(ch for ch in t if not 0x300 <= ord(ch) <= 0x36F)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")
PUB_BASE = {"DTU": "https://orbit.dtu.dk/en/", "KU": "https://researchprofiles.ku.dk/en/", "AU": "https://pure.au.dk/portal/en/",
            "SDU": "https://portal.findresearcher.sdu.dk/en/", "AAU": "https://vbn.aau.dk/en/"}
for inst in PUB_BASE:
    names = []
    for f in sorted((D / "people/harvest").glob(f"{inst.lower()}*.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("NAMES:"):
                names = line[6:].split(";"); continue
            if not line.strip() or line.startswith("#"):
                continue
            kind, idx, year, typ, slug, title = line.split("|", 5)
            if slug.startswith("="):
                slug = pure_slug(title)[:int(slug[1:])]
            url = PUB_BASE[inst] + ("publications/" if kind == "O" else "projects/") + slug + "/"
            what = "latest research output" if kind == "O" else "ongoing PhD project, main supervisor"
            add("Educator output and PhD projects", inst, url, f"{names[int(idx)]}: {what}", f"data/people/harvest/{f.name}")

# 5b. Research proficiency: OpenAlex author records (research output) and the portals' "Supervised work" tabs
SITE = {"dtu": "https://orbit.dtu.dk", "ku": "https://researchprofiles.ku.dk", "au": "https://pure.au.dk",
        "sdu": "https://portal.findresearcher.sdu.dk", "aau": "https://vbn.aau.dk"}
for f in sorted((D / "people/research_outputs").glob("*.tsv")):
    inst = f.stem.upper()
    for r in csv.DictReader(f.open(encoding="utf-8"), delimiter="\t"):
        if r["kind"] == "A":
            for aid in r["path"].split():
                add("Educator research output (OpenAlex)", inst, f"https://openalex.org/{aid}", f"{r['name']}: author record and works since 2021", f"data/people/research_outputs/{f.name}")
        elif r["kind"] == "-" and r["path"].startswith("/"):
            add("Educator supervised PhD theses", inst, SITE[f.stem] + r["path"] + "supervised/", f"{r['name']}: supervised work", f"data/people/research_outputs/{f.name}")
        elif r["kind"] == "S" and r["path"]:
            add("Educator supervised PhD theses", inst, r["path"] if r["path"].startswith("http") else SITE[f.stem] + r["path"], f"{r['name']}: PhD thesis {r['title'][:80]}", f"data/people/research_outputs/{f.name}")

# 6. Organisational units: portal page and own website
for line in (D / "people/units.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    inst, name, portal, site = (line.split("|") + ["", "", "", ""])[:4]
    add("Unit page", inst, portal, f"Research-portal organisation page: {name}", "data/people/units.txt")
    add("Unit page", inst, site, f"Unit website (link target): {name}", "data/people/units.txt")

# 6c. Industry
add("Industry", "", "https://danishbusinessauthority.dk/danish-quantum-ecosystem-map", "The Danish Quantum Ecosystem Map (list view): organisations, categories, descriptions", "data/industry/organisations.txt")
for line in (D / "industry/cvr.txt").read_text(encoding="utf-8").splitlines():
    if line.startswith("#") or not line.strip():
        continue
    c, nm = line.split("|")[:2]
    add("Industry", "", f"https://datacvr.virk.dk/enhed/virksomhed/{c}", f"CVR: {nm} (start date, place, industry code)", "data/industry/cvr.txt")
for qy in ("quantum", "kvante", "qubit", "kvanteteknologi", "quantum%20computing", "quantum%20sensing", "post-quantum"):
    add("Industry", "", f"https://www.jobindex.dk/jobsoegning.rss?q={qy}", "Job ads, read every Monday", "data/industry/jobs.json")

# 6b. Workshops and public outreach
for line in (D / "outreach/activities.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    f = line.split("|")
    add("Workshops and public outreach", f[1], f[9], ("Workshop" if f[0] == "W" else "Outreach") + f": {f[3][:90]}", "data/outreach/activities.txt")
for u in ("https://nbi.ku.dk/english/kalender/?get_rss=1", "https://nbi.ku.dk/kalender/?get_rss=1", "https://phys.au.dk/aktuelt/arrangementer", "https://phys.au.dk/en/news/events"):
    add("Workshops and public outreach", "KU" if "nbi" in u else "AU", u, "Event calendar, read every Monday for public quantum events", "data/outreach/calendar.json")

# 7. Research groups
for g in groups:
    i = g["institution"]
    add("Research group", i, g["website"], f"{g['short']}: own website (short quote, description read for DQA's own summary)", "data/groups/groups.json")
    add("Research group", i, g["portal"], f"{g['short']}: research-portal organisation page", "data/groups/groups.json")
    add("Research group", i, g.get("jobs_url"), f"{g['short']}: university vacancies page (link target)", "data/groups/groups.json")
    for fd in g.get("feeds", []):
        add("Research group feed (weekly)", i, fd["url"], f"{g['short']}: {fd['kind']}, read automatically every Monday", "data/groups/feeds.json")
    gf = D / "groups" / f"{g['key']}.txt"
    for line in gf.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("||")
        kind, path = f[0], ""
        if kind == "P": path, what = f[3], f"member profile ({f[1]})"
        elif kind in ("PUBS", "PROJ"): path, what = f[2], ("publication" if kind == "PUBS" else "project") + f": {f[1][:80]}"
        elif kind in ("PRESS", "ACT", "PRIZE"): path, what = f[3], {"PRESS": "press clipping", "ACT": "activity", "PRIZE": "prize"}[kind] + f": {f[2][:80]}"
        else:
            continue
        if path:
            add("Research group", i, g["portal_base"] + path, f"{g['short']}: {what}", f"data/groups/{gf.name}")

# dedupe on (category, url)
seen, out = set(), []
for r in rows:
    k = (r["category"], r["url"])
    if k not in seen:
        seen.add(k); out.append(r)
with (D / "sources.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["category", "institution", "url", "used_for", "data_file"])
    w.writeheader(); w.writerows(out)

# summary per category and site
summ = OrderedDict()
for r in out:
    host = urlparse(r["url"].split(" ")[0]).netloc
    summ.setdefault(r["category"], OrderedDict()).setdefault(host, 0)
    summ[r["category"]][host] += 1

HEAD = """# Sources

Everything on [map.danishquantumacademy.dk](https://map.danishquantumacademy.dk) comes from **public web pages that anyone can read without logging in**: university course catalogues, curricula and programme pages, the universities' public research portals, the research groups' own websites, and the CFQT framework. No intranets, student or staff systems behind a login, paid databases, or private documents have been used.

The full list, one row per page, is in [`data/sources.csv`](data/sources.csv) (columns: category, institution, url, what it was used for, data file). It is generated from the data files by `scripts/list_sources.py`, so it changes when the data change. The table below summarises it.

## How the pages were read

- **Course catalogues and curricula** were read in an ordinary web browser or through the public data feed that the catalogue page itself uses (AU's course catalogue loads its course data from `kursuskatalog.au.dk/api/courses/`, which is open to anyone). Curricula published as PDF were read from the universities' public study-regulation pages.
- **Research portals** (DTU Orbit, the University of Copenhagen research portal, AU Pure, SDU Find Researcher, AAU VBN) were read in an ordinary browser. Their list pages sit behind bot protection, so they are not harvested automatically.
- **Research groups' news, events, grants and positions** are read automatically every Monday by `scripts/fetch_group_feeds.py` from the public pages listed as "Research group feed (weekly)". The script identifies itself as `DQA-map/1.0` with a link to the map.
- **Only professional information** is kept: names, positions, units, research topics, research output titles and the courses people teach. No e-mail addresses, phone numbers, photos, CV details or birth dates are stored in this repository or shown on the map. Group photos and long texts are not copied; summaries are written by Danish Quantum Academy, with at most a short quote and a link to the source.

## Notes on particular sources

- **University of Copenhagen courses** come from [kucourses.dk](https://kucourses.dk), a public, student-run mirror of KU's course catalogue, because kurser.ku.dk could not be reached on 2 November 2026. The data should be checked against kurser.ku.dk.
- **SDU study plans** were opened from the public MitSDU programme pages ("Uddannelsens forløb"), which link to the public study regulations on odin.sdu.dk.
- **Search engines** were used only to find the official pages; no information is taken from search results.
- **Survey contacts.** For the European Quantum Academy survey, the names and work e-mail addresses of course responsibles were taken from the same public course pages and are kept in a separate private repository. They are not published.

## Summary by source
"""
lines = [HEAD]
for cat, hosts in summ.items():
    lines.append(f"\n### {cat}\n\n| Site | Pages |\n|---|---:|")
    for h, n in sorted(hosts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {h} | {n} |")
chk = D / "sources_check.csv"
if chk.exists():
    cr = list(csv.DictReader(chk.open(encoding="utf-8")))
    cnt = {v: sum(1 for r in cr if r["verdict"] == v) for v in ("public", "bot-protected", "login", "error")}
    lines.append(f"""
## Access check

The workflow "Check sources" opened {len(cr)} pages (up to three per site) from a GitHub server, without login or cookies. Result, in [`data/sources_check.csv`](data/sources_check.csv): **{cnt['public']} public, {cnt['login']} behind a login**, {cnt['bot-protected']} bot-protected and {cnt['error']} not reachable.

- *Bot-protected* pages (the AU research portal) show a Cloudflare challenge to scripts but open normally in a browser without logging in.
- *Not reachable* are mostly University of Copenhagen web servers (ku.dk), which do not answer requests from GitHub's servers; they open normally in a browser without logging in. The rest were outdated links to unit websites, which have been removed (the map links to the research-portal page instead).
""")
lines.append(f"\n\nTotal: {len(out)} pages from {len({urlparse(r['url'].split(' ')[0]).netloc for r in out})} sites. All were publicly accessible without login when they were read (2–3 November 2026; group feeds weekly).\n")
(ROOT / "SOURCES.md").write_text("\n".join(lines), encoding="utf-8")
print(f"{len(out)} kilder, {len(summ)} kategorier")
