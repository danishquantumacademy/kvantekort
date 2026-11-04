#!/usr/bin/env python3
"""Samler alle klassifikationer til site/data.json og site/index.html.

Brug:  python scripts/build_site.py
Input:  data/classification/*.csv  (én fil pr. institution, med CFQT-kolonner)
        data/reference.json        (CFQT content map, områder, niveauer, institutioner)
Output: site/data.json, site/index.html (data indlejret), site/artifact.html
"""
import csv, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
ref = json.loads((ROOT / "data/reference.json").read_text(encoding="utf-8"))
valid_subs = {s for d in ref["cfqt"]["domains"].values() for s in d["subdomains"]}
valid_levels = set(ref["cfqt"]["levels"])
# CFQT-underdomæner vises altid i numerisk rækkefølge (1.1, 1.2, …, 2.1); det primære underdomæne gemmes separat
skey = lambda s: tuple(int(x) for x in s.split("."))
sort_subs = lambda xs: sorted(dict.fromkeys(xs), key=skey)

# CFQT-underdomæner for ph.d.- og postdoc-projekter, slået op på titel (data/projects/cfqt_projects.txt)
ptkey = lambda t: re.sub(r"\s+", " ", t).strip().lower()
PROJ_CFQT, OUT_CFQT = {}, {}
for line in (ROOT / "data/projects/cfqt_projects.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"): continue
    out_line = line.startswith("OUT|")
    t, subs = (line[4:] if out_line else line).rsplit("|", 1)
    subs = [] if subs.strip() == "-" else [x for x in subs.split(";") if x]
    bad = [x for x in subs if x not in valid_subs]
    if bad: raise SystemExit(f"Ugyldig CFQT {bad} for projekt {t}")
    (OUT_CFQT if out_line else PROJ_CFQT)[ptkey(t)] = subs   # første underdomæne er det primære

courses, unmapped = [], 0
for f in sorted((ROOT / "data/classification").glob("*.csv")):
    with f.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inst = {**ref["institutions"], **ref.get("schools", {})}[r["institution"]]
            subs = [s for s in [r["cfqt_primary"], *r["cfqt_secondary"].split(";")] if s]
            bad = [s for s in subs if s not in valid_subs] + [p for p in (r["prof_I"], r["prof_II"], r["prof_III"]) if p and p not in valid_levels]
            if bad:
                raise SystemExit(f"Ugyldig CFQT-værdi {bad} i {f.name}: {r['code']}")
            if not subs:
                unmapped += 1
                continue  # intet CFQT-match: vises ikke på siden
            courses.append({
                "institution": r["institution"], "level": r["level"], "code": r["code"], "title": r["title"],
                "language": r["language"], "ects": float(r["ects"]) if r["ects"] else None,
                "dept_name": inst.get("departments", {}).get(r["dept"], r["dept"]),
                "subs": sort_subs(subs), "primary": subs[0], "domain": subs[0].split(".")[0],
                "prof": {k: r[f"prof_{k}"] for k in ("I", "II", "III") if r[f"prof_{k}"]},
                "status": r.get("cfqt_status", "estimated"),
                "kw_strong": int(r["kw_strong"] or 0), "kw_medium": int(r["kw_medium"] or 0),
                "note": r.get("note", ""),
                "url": r.get("url") or inst.get("course_url", "").format_map({**r, "ref": r.get("ref") or r["code"]}),
            })

# Skema og forudsætninger for kandidatkurser (data/schedule/<inst>.txt): code|semester|period|slot|prerequisites
sched = {}
for f in sorted((ROOT / "data/schedule").glob("*.txt")):
    inst = f.stem.upper()
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        code, sem, per, slot, pre = (line.split("|") + [""] * 5)[:5]
        if sem not in {"E", "F", "EF", "Jan", "Jun", "Aug"} or per not in {"S", "H1", "H2", "3w"}:
            raise SystemExit(f"Ugyldig skemalinje i {f.name}: {line}")
        sched[(inst, code)] = {"sem": sem, "per": per, "slot": slot, "pre": [x for x in pre.split(";") if x and x != code]}
missing = []
for c in courses:
    if (c["institution"], c["code"]) in sched:
        c["sched"] = sched[(c["institution"], c["code"])]
    elif c["level"] == "MSc":
        missing.append(f'{c["institution"]} {c["code"]}')
if missing:
    print("Advarsel: kandidatkurser uden skemadata:", ", ".join(missing))

programmes = json.loads((ROOT / "data/programmes.json").read_text(encoding="utf-8"))
known = {(c["institution"], c["code"]) for c in courses}
for prog in programmes["programmes"]:
    for x in prog["courses"]:
        if (x["inst"], x["code"]) not in known:
            raise SystemExit(f"Studiesti {prog['id']}: kurset {x['inst']} {x['code']} findes ikke blandt de kortlagte kurser")
out = {"reference": ref, "courses": courses, "unmapped": unmapped}

# ---- Fælles sidehoved, navigation, "How to read"-bokse og sidefod for alle sider ----
NAV = [("Education", [("index", "index.html", "Proficiency"), ("planner", "planner.html", "Study planner")]),
       ("Research", [("people", "people.html", "Educators"), ("groups", "groups.html", "Groups")]),
       ("Industry", [("industry", "industry.html", "Industry")])]
SHARED_CSS = """
/* shared site chrome: navigation, how-to-read boxes, footer */
nav.site{display:grid;gap:8px;padding-bottom:12px;border-bottom:1px solid var(--line);font:500 13.5px var(--body)}
nav.site .nt{display:flex;justify-content:space-between;align-items:center;gap:12px}
nav.site .brand{font:600 11.5px var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--muted);text-decoration:none}
nav.site .brand:hover{color:var(--accent)}
nav.site .nb{display:flex;flex-wrap:wrap;gap:4px 28px}
nav.site .ng{display:flex;flex-wrap:wrap;align-items:center;gap:2px}
nav.site .nl{font:600 10.5px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-right:4px}
nav.site a.p{color:var(--fg);text-decoration:none;padding:5px 9px;border-radius:7px;white-space:nowrap}
nav.site a.p:hover{background:var(--chip)}
nav.site a.p[aria-current=page]{background:var(--accent);color:var(--surface)}
nav.site a:focus-visible,details.howto>summary:focus-visible,details.fold>summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
details.howto{border:1px solid var(--line);border-radius:10px;background:var(--surface);max-width:100%}
details.howto>summary{cursor:pointer;padding:9px 14px;font:600 14px var(--body);color:var(--accent);list-style:none;display:flex;gap:8px;align-items:center}
details.howto>summary::-webkit-details-marker,details.fold>summary::-webkit-details-marker{display:none}
details.howto>summary::before,details.fold>summary::before{content:"\\203A";font:700 20px/1 var(--body);width:12px;text-align:center;transition:transform .15s;flex:none;color:var(--accent)}
details.howto[open]>summary::before,details.fold[open]>summary::before{transform:rotate(90deg)}
details.howto .hb{padding:2px 16px 16px;display:grid;gap:10px;font-size:13.5px;line-height:1.5;color:var(--muted)}
details.howto .hb p{margin:0;max-width:86ch}
details.howto .hb b{color:var(--fg)}
footer .site-foot{display:flex;flex-wrap:wrap;gap:6px 16px}
footer .site-foot a{color:var(--accent)}
@media (max-width:640px){nav.site .bx{display:none}nav.site{font-size:13px}nav.site a.p{padding:4px 7px}nav.site .nb{gap:2px 16px}nav.site .nl{width:100%;margin:2px 0 0}}
"""


def chrome(html, key):
    links = "".join(
        f'<div class="ng"><span class="nl">{grp}</span>' + "".join(
            f'<a class="p" href="{href}"' + (' aria-current="page"' if k == key else "") + f">{label}</a>" for k, href, label in items) + "</div>"
        for grp, items in NAV)
    nav = ('<nav class="site" aria-label="Site"><div class="nt"><a class="brand" href="index.html">Danish Quantum Academy<span class="bx"> · Quantum education and research map</span></a>'
           '<a class="p" href="about.html"' + (' aria-current="page"' if key == "about" else "") + f'>About the data</a></div><div class="nb">{links}</div></nav>')
    foot = ('<p class="site-foot"><span>Published by <a href="https://danishquantumacademy.dk">Danish Quantum Academy</a> for the European Quantum Academy (Northern European Regional Quantum Academy).</span>'
            '<a href="about.html">About the data and methods</a><a href="https://github.com/danishquantumacademy/kvantekort">Data and code on GitHub</a></p>')
    assert "<!--SITENAV-->" in html and "<!--SITEFOOT-->" in html, key
    return html.replace("<!--SITENAV-->", nav).replace("<!--SITEFOOT-->", foot).replace("</style>", SHARED_CSS + "</style>", 1)

(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site/data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

# Selvstændig side: data indlejres, så index.html virker både på GitHub Pages og lokalt.
tpl = (ROOT / "site/template.html").read_text(encoding="utf-8")
body = chrome(tpl.replace("/*DATA*/", json.dumps(out, ensure_ascii=False).replace("</", "<\\/")), "index")
page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
(ROOT / "site/index.html").write_text(page, encoding="utf-8")
(ROOT / "site/artifact.html").write_text(body, encoding="utf-8")  # til claude.ai-preview

# Trekant-siden er lagt sammen med forsiden; triangle.html sender videre og bevarer parametre og anker.
(ROOT / "site/triangle.html").write_text(
    '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Danish Quantum Education Map</title>'
    '<meta http-equiv="refresh" content="0; url=index.html">'
    '<script>location.replace("index.html"+location.search+location.hash)</script></head>'
    '<body><p>The proficiency triangle is now on the <a href="index.html">front page</a>.</p></body></html>\n', encoding="utf-8")
(ROOT / "site/triangle_artifact.html").unlink(missing_ok=True)

# Studiestier (den studerendes trekant) bygges af kurserne + data/programmes.json.
# Study paths er lagt sammen med kursusfinderen i planner.html; students.html sender videre og bevarer parametre.
(ROOT / "site/students.html").write_text(
    '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Quantum Study Planner</title>'
    '<meta http-equiv="refresh" content="0; url=planner.html">'
    '<script>location.replace("planner.html"+location.search+location.hash)</script></head>'
    '<body><p>Study paths are now part of the <a href="planner.html">Study planner</a>.</p></body></html>\n', encoding="utf-8")
(ROOT / "site/students_artifact.html").unlink(missing_ok=True)
# Kursusfinder (den studerendes søgning) bygges af de samme data.
ptpl = (ROOT / "site/planner_template.html").read_text(encoding="utf-8")
pbody = chrome(ptpl.replace("/*DATA*/", json.dumps({**out, "profiles": programmes["reference_profiles"], "programmes": programmes}, ensure_ascii=False).replace("</", "<\\/")), "planner")
(ROOT / "site/planner.html").write_text(page.split("<body>\n")[0] + "<body>\n" + pbody + "\n</body>\n</html>\n", encoding="utf-8")
(ROOT / "site/planner_artifact.html").write_text(pbody, encoding="utf-8")
# Undervisere og forskning (people.html): portaldata + forskningsfokus + hvem underviser hvad.
import re
from urllib.parse import quote
PORTAL = {"DTU": "https://orbit.dtu.dk", "KU": "https://researchprofiles.ku.dk", "AU": "https://pure.au.dk",
          "SDU": "https://portal.findresearcher.sdu.dk", "AAU": "https://vbn.aau.dk"}
def level_of(title):
    t = title.lower()
    if not t: return "Not stated"
    first = t.split("/")[0]
    for key, lv in (("associate professor", "Associate Professor"), ("assistant professor", "Assistant Professor"),
                    ("tenure track", "Assistant Professor"), ("professor", "Professor"), ("senior researcher", "Senior Researcher"),
                    ("postdoc", "Postdoc"), ("post.doc", "Postdoc"), ("researcher", "Researcher")):
        if key in first: return lv
    for key, lv in (("associate professor", "Associate Professor"), ("professor", "Professor")):
        if key in t: return lv
    return "Other staff"
def roles_of(title):
    r = []
    for key, lab in (("head of department", "Head of department"), ("deputy head of department", "Deputy head of department"),
                     ("head of section", "Head of section"), ("section leader", "Head of section"), ("head of sections", "Head of section"),
                     ("groupleader", "Group leader"), ("group leader", "Group leader"), ("deputy director", "Deputy director"), ("chair", "Chair")):
        if key in title.lower() and lab not in r: r.append(lab)
    return r
people = {}
for f in sorted((ROOT / "data/people").glob("*.txt")):
    inst = f.stem.upper()
    if inst not in PORTAL: continue
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"): continue
        x = line.split("||")
        name = x[0]
        if len(x) < 3:
            people[(inst, name)] = {"institution": inst, "name": name, "found": False}; continue
        if inst == "DTU": title, units, concepts, path, pubs, centres = x[1], x[2], x[3], x[4], "", ""
        elif inst == "KU": title, units, centres, pubs, path, concepts = x[1], x[2], x[3], x[4], x[5], ""
        elif inst == "AU": title, units, concepts, pubs, path, centres = x[1], x[2], x[3], x[4], "", ""
        else: title, units, concepts, pubs, path, centres = x[1], x[2], x[3], x[4], x[5], ""
        url = PORTAL[inst] + path if path else f'{PORTAL[inst]}/portal/en/persons/?search={quote(chr(34) + name + chr(34))}'
        people[(inst, name)] = {"institution": inst, "name": name, "found": True, "title": title, "level": level_of(title), "roles": roles_of(title),
                                "units": [u for u in units.split(" > ") if u], "centres": [c for c in centres.split("; ") if c],
                                "concepts": [c for c in concepts.split(", ") if c], "outputs": [o for o in pubs.split(" ¦ ") if o], "url": url}
for line in (ROOT / "data/people/research.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"): continue
    inst, name, focus, subs = line.split("|")
    bad = [s for s in subs.split(";") if s and s not in valid_subs]
    if bad: raise SystemExit(f"Ugyldig CFQT-underdomæne {bad} for {name}")
    p = people.setdefault((inst, name), {"institution": inst, "name": name, "found": False})
    p["focus"], p["subs"] = focus, sort_subs(s for s in subs.split(";") if s)
# Seneste forskningsoutput (med link) og igangværende ph.d.-projekter med underviseren som hovedvejleder,
# høstet fra forskningsportalerne (data/people/harvest/<inst>*.txt). Linjer: TYPE|navn-indeks|år|type|slug|titel,
# hvor slug "=N" betyder de første N tegn af titlens slug (Pure danner adressen ud fra titlen).
import unicodedata
def pure_slug(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(ch for ch in t if not 0x300 <= ord(ch) <= 0x36F)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")
PUB_BASE = {"DTU": "https://orbit.dtu.dk/en/", "KU": "https://researchprofiles.ku.dk/en/", "AU": "https://pure.au.dk/portal/en/",
            "SDU": "https://portal.findresearcher.sdu.dk/en/", "AAU": "https://vbn.aau.dk/en/"}
TYPE_NAME = {"Article/newspaper": "Article", "Contribution to book/anthology/report/proceeding": "Proceedings",
             "Contribution to book/anthology/report/conference proceeding": "Proceedings", "Working paper/Preprint": "Preprint",
             "Conference without publisher/journal": "Conference", "Book/report": "Report"}
HARVEST_SKIP = {("SDU", "Shan Shan")}  # portalprofilen matcher ikke personen
n_out = n_phd = 0
for inst in PUB_BASE:
    names = []
    for f in sorted((ROOT / "data/people/harvest").glob(f"{inst.lower()}*.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("NAMES:"):
                names = line[6:].split(";"); continue
            if not line.strip() or line.startswith("#"): continue
            kind, idx, year, typ, slug, title = line.split("|", 5)
            name = names[int(idx)]
            if (inst, name) in HARVEST_SKIP or (inst, name) not in people: continue
            if slug.startswith("="):
                slug = pure_slug(title)[:int(slug[1:])]
            url = PUB_BASE[inst] + ("publications/" if kind == "O" else "projects/") + slug + "/"
            pp = people[(inst, name)]
            if kind == "O":
                pp.setdefault("latest", []).append({"title": title, "url": url, "year": year, "type": TYPE_NAME.get(typ, typ)}); n_out += 1
            elif kind == "J":
                pp.setdefault("phd", []).append({"title": title, "url": url, "period": year, "type": typ, "subs": PROJ_CFQT.get(ptkey(title))}); n_phd += 1
print(f"harvest: {n_out} seneste output, {n_phd} ph.d.-projekter som hovedvejleder")
# en underviser registreret ved ét universitet, men ansat ved et andet (fx en KU-forsker på et DTU-kursus)
for (inst, name), p in list(people.items()):
    if not p.get("found"):
        other = next((q for (i2, n2), q in people.items() if n2 == name and i2 != inst and q.get("found")), None)
        if other: p.update({k: v for k, v in other.items() if k != "institution"}); p["employer"] = other["institution"]
mapped = {(c["institution"], c["code"]): c for c in courses}
for r in csv.DictReader((ROOT / "data/people/teaching.csv").open(encoding="utf-8")):
    p = people.setdefault((r["institution"], r["name"]), {"institution": r["institution"], "name": r["name"], "found": False})
    c = mapped.get((r["institution"], r["code"]))
    p.setdefault("courses", []).append({"institution": r["institution"], "code": r["code"], "title": r["title"], "level": r["level"], "role": r["role"],
                                        "subs": c["subs"] if c else [], "primary": c["primary"] if c else "", "url": c["url"] if c else "", "mapped": bool(c), "prof": c["prof"] if c else {}})
# saml personer, der underviser ved et andet universitet end deres ansættelsessted, under ansættelsesstedet
for key, p in list(people.items()):
    if p.get("employer") and (p["employer"], p["name"]) in people:
        people[(p["employer"], p["name"])].setdefault("courses", []).extend(p.get("courses", []))
        del people[key]
plist = sorted(people.values(), key=lambda p: (p["institution"], p["name"]))
# landingssider for institutter, sektioner, grupper og centre (data/people/units.txt)
from urllib.parse import urlparse
units = {}
rows = [l.split("|") for l in (ROOT / "data/people/units.txt").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
dept_sites = {(i, w) for i, n, pu, w in rows if w and re.search(r"Department|Institute|National Centre", n)}
for inst, name, portal, web in rows:
    trivial = web and urlparse(web).path.strip("/") in ("", "english", "en")
    is_dept = bool(re.search(r"Department|Institute|National Centre", name))
    weak = (not web) or (not is_dept and ((inst, web) in dept_sites or trivial))
    units.setdefault(inst, {})[name] = portal if (weak and portal) else (web or portal)
# Oversigt over ph.d.- og postdoc-projekter på CFQT-kortet: undervisernes ph.d.-projekter som hovedvejleder og gruppernes ph.d.-studerende og postdocs
proj_list, seen_p = [], set()
for pp in plist:
    for j in pp.get("phd", []):
        k = ("phd", ptkey(j["title"]))
        if k in seen_p: continue
        seen_p.add(k); proj_list.append({"kind": "phd", "inst": pp["institution"], "title": j["title"], "url": j["url"], "subs": j.get("subs"), "basis": "project", "who": pp["name"]})
for g in json.loads((ROOT / "data/groups/groups.json").read_text(encoding="utf-8"))["groups"]:
    for line in (ROOT / "data/groups" / f"{g['key']}.txt").read_text(encoding="utf-8").splitlines():
        if not line.startswith("P||"): continue
        f = (line.split("||") + [""] * 6)
        role = f[2]
        if not re.search(r"phd|ph\.d|postdoc|post-doc", role, re.I): continue
        kind = "postdoc" if re.search(r"postdoc|post-doc", role, re.I) else "phd"
        proj = re.sub(r"\s*\[.*?\]\s*$", "", f[4]).strip(); outp = re.sub(r"\s*\(20\d\d\)\s*$", "", f[5]).strip()
        if proj:
            k = (kind, ptkey(proj))
            if k in seen_p: continue
            seen_p.add(k); proj_list.append({"kind": kind, "inst": g["institution"], "title": proj, "subs": PROJ_CFQT.get(ptkey(proj)), "basis": "project", "group": g["short"]})
        elif outp:
            proj_list.append({"kind": kind, "inst": g["institution"], "title": outp, "subs": OUT_CFQT.get(ptkey(outp)), "basis": "output", "group": g["short"]})
        else:
            proj_list.append({"kind": kind, "inst": g["institution"], "title": "", "subs": None, "basis": "none", "group": g["short"]})
unmapped_p = [x["title"] for x in proj_list if x["title"] and x["subs"] is None]
if unmapped_p: print("advarsel: projekter uden CFQT-vurdering:", len(unmapped_p), unmapped_p[:5])
print(f"projekter: {len(proj_list)} ph.d./postdoc, {sum(1 for x in proj_list if x['subs'])} på CFQT-kortet")
# Niveau i CFQT-trekanten for et forskningsprojekt: hovedemnets område på C2 (forskningsniveau, "Innovation"),
# andre områder, som underdomænerne berører, på C1. Område efter underdomæne:
# I Quantum concepts: 1, 2, 5.1, 5.4, 5.5 · II HW & SW engineering: 3, 4, 5.2, 5.3, 6.1-6.6, 7.1-7.3, 7.5
# III Applications & strategies: 5.6, 6.7, 7.4, 7.6, 8
def sub_area(x):
    d = x.split(".")[0]
    if d in ("1", "2") or x in ("5.1", "5.4", "5.5"): return "I"
    if d == "8" or x in ("5.6", "6.7", "7.4", "7.6"): return "III"
    return "II"
for x in proj_list:
    if x["subs"]:
        areas = [sub_area(t) for t in x["subs"]]
        x["prof"] = {a: ("C2" if a == areas[0] else "C1") for a in dict.fromkeys(areas)}
# Research proficiency of each educator: research profile, research output 2021 onwards and supervised PhD theses
# (data/people/research_outputs/*.tsv, harvested by scripts/harvest_research.py), tagged with CFQT subdomains by
# scripts/cfqt_classify.py. Ongoing PhD projects as main supervisor (DTU Orbit) count as supervision.
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from cfqt_classify import classify
RP_FROM = 2021
SKIP_TYPE = re.compile(r"^(editorial|erratum|retraction|paratext|peer-review|letter|other|dataset|libguides|supplementary-materials)$|editorial|preface|foreword|review of|book review|comment/debate|letter to the editor|erratum|corrigend|newspaper|blog|interview|anthology editing|editor", re.I)
rp_rows = {}
for f in sorted((ROOT / "data/people/research_outputs").glob("*.tsv")):
    for r in csv.DictReader(f.open(encoding="utf-8"), delimiter="\t"):
        rp_rows.setdefault((f.stem.upper(), r["name"]), []).append(r)
RP_SITE = {"DTU": "https://orbit.dtu.dk", "KU": "https://researchprofiles.ku.dk", "AU": "https://pure.au.dk",
           "SDU": "https://portal.findresearcher.sdu.dk", "AAU": "https://vbn.aau.dk"}
n_rp = [0, 0, 0, 0]
for pp in plist:
    rows = rp_rows.get((pp["institution"], pp["name"]))
    if not pp.get("found"): continue
    items, seen, no, nm, ns = [], set(), 0, 0, 0
    if pp.get("subs"):
        items.append(["P", 0, ";".join(pp["subs"]), pp.get("focus") or "Research profile", ""])
    for r in rows or []:
        if r["kind"] not in ("O", "S") or not r["year"].isdigit() or int(r["year"]) < RP_FROM: continue
        if r["kind"] == "O" and SKIP_TYPE.search(r["type"]): continue
        k = (r["kind"], re.sub(r"\W", "", r["title"].lower()))
        if k in seen: continue
        seen.add(k)
        subs = classify(r["title"])
        url = r["path"] if r["path"].startswith("http") else (RP_SITE[pp["institution"]] + r["path"]) if r["path"].startswith("/") else ""
        if r["kind"] == "O": no += 1; nm += bool(subs)
        else: ns += 1
        if subs: items.append([r["kind"], int(r["year"]), ";".join(subs), r["title"], url])
    for j in pp.get("phd", []):
        k = ("S", re.sub(r"\W", "", j["title"].lower()))
        if k in seen: continue
        seen.add(k); ns += 1
        if j.get("subs"): items.append(["S", 0, ";".join(j["subs"]), j["title"], j["url"]])
    pp["rp"] = {"no": no, "nm": nm, "ns": ns, "it": items}
    n_rp[0] += 1; n_rp[1] += no; n_rp[2] += nm; n_rp[3] += ns
print(f"research proficiency: {n_rp[0]} educators, {n_rp[1]} outputs since {RP_FROM} ({n_rp[2]} on the CFQT map), {n_rp[3]} supervised PhD theses/projects")
pout = {"reference": ref, "people": plist, "units": units, "projects": proj_list, "rp_from": RP_FROM}
pt = (ROOT / "site/people_template.html").read_text(encoding="utf-8")
pbody2 = chrome(pt.replace("/*DATA*/", json.dumps(pout, ensure_ascii=False).replace("</", "<\\/")), "people")
(ROOT / "site/people.html").write_text(page.split("<body>\n")[0] + "<body>\n" + pbody2 + "\n</body>\n</html>\n", encoding="utf-8")
(ROOT / "site/people_artifact.html").write_text(pbody2, encoding="utf-8")
print(f"people: {len(plist)} undervisere, {sum(1 for p in plist if p.get('found'))} med portalprofil")
# Forskningsgrupper (groups.html): kuraterede beskrivelser + portaldata + ugentlige feeds + tilknyttede kurser.
gcfg = json.loads((ROOT / "data/groups/groups.json").read_text(encoding="utf-8"))
feeds = json.loads((ROOT / "data/groups/feeds.json").read_text(encoding="utf-8")) if (ROOT / "data/groups/feeds.json").exists() else {"groups": {}}
def member_cat(role):
    r = role.lower()
    if re.search(r"affiliate|external", r): return "Affiliates and external"
    if re.search(r"phd", r): return "PhD students"
    if re.search(r"professor|group leader|centre leader|executive director", r): return "Faculty"
    if re.search(r"postdoc|researcher|research consultant|senior consultant|special consultant|research assistant|scientist|specialist|academic staff", r): return "Researchers and postdocs"
    return "Technical and administrative staff" if r else "Other members"
import unicodedata
def nkey(n):
    t = unicodedata.normalize("NFD", n).encode("ascii", "ignore").decode().lower().replace(".", " ").split()
    return (t[0], t[-1]) if t else ("", "")
pmap = {(p["institution"], nkey(p["name"])): p for p in plist}
# research proficiency of the group members: research output since 2021 from OpenAlex (data/groups/research_outputs),
# the member's current project and, for educators, the evidence on the Educators page
sys.path.insert(0, str(ROOT / "scripts"))
from cfqt_classify import classify as _cls
def _ar(x):
    d = x.split(".")[0]
    return "I" if d in ("1", "2") or x in ("5.1", "5.4", "5.5") else ("III" if d == "8" or x in ("5.6", "6.7", "7.4", "7.6") else "II")
def levels_of(sublists):
    mains = [_ar(s[0]) for s in sublists]; touch = [set(map(_ar, s)) for s in sublists]; out = {}
    for a in ("I", "II", "III"):
        m = mains.count(a); sec = sum(1 for mm, t in zip(mains, touch) if a in t and mm != a)
        lv = "C2" if m >= 3 else "C1" if (m >= 1 or sec >= 2) else "B2" if sec == 1 else ""
        if lv: out[a] = lv
    return out
gres = {}
for f in sorted((ROOT / "data/groups/research_outputs").glob("*.tsv")) if (ROOT / "data/groups/research_outputs").exists() else []:
    for r in csv.DictReader(f.open(encoding="utf-8"), delimiter="\t"):
        gres.setdefault((f.stem, r["name"]), []).append(r)
groups_out = []
for g in gcfg["groups"]:
    txt = (ROOT / f"data/groups/{g['key']}.txt").read_text(encoding="utf-8")
    members, pubs, projects, press, acts, prizes, events = [], [], [], [], [], [], []
    for line in txt.splitlines():
        if not line.strip() or line.startswith("#"): continue
        f = line.split("||")
        if f[0] == "P":
            name, role, path, proj, out_ = (f + [""] * 6)[1:6]
            per = re.search(r"\[(.*?)\]", proj)
            years = re.findall(r"(20\d\d)", per[1]) if per else []
            pp = pmap.get((g["institution"], nkey(name)))
            members.append({"name": name, "role": role, "cat": member_cat(role), "url": (g["portal_base"] + path) if path else "",
                            "project": re.sub(r"\s*\[.*?\]\s*$", "", proj), "project_years": "–".join(years[:2]),
                            "output": out_, "subs": pp.get("subs", []) if pp else [], "teacher": bool(pp)})
            ev, seen = [], set()
            for r in gres.get((g["key"], name), []):
                if r["kind"] != "O" or not r["year"].isdigit() or int(r["year"]) < 2021 or SKIP_TYPE.search(r["type"]): continue
                k = re.sub(r"\W", "", r["title"].lower())
                if k in seen: continue
                seen.add(k); sb = _cls(r["title"])
                if sb: ev.append(sb)
            ptitle = members[-1]["project"]
            if ptitle and _cls(ptitle): ev.append(_cls(ptitle))
            if pp and pp.get("rp"):
                for x in pp["rp"]["it"]:
                    k = re.sub(r"\W", "", x[3].lower())
                    if k not in seen: seen.add(k); ev.append(x[2].split(";"))
            harvested = any(r["kind"] == "A" and r["path"].strip() != "RATE-LIMITED" for r in gres.get((g["key"], name), []))
            members[-1].update({"rl": levels_of(ev), "nev": len(ev), "nout": sum(1 for r in gres.get((g["key"], name), []) if r["kind"] == "O"), "harv": harvested})
        elif f[0] == "PUBS": pubs.append({"title": f[1], "url": (g["portal_base"] + f[2]) if f[2] else "", "cite": f[3] if len(f) > 3 else ""})
        elif f[0] == "PROJ": projects.append({"title": f[1], "url": (g["portal_base"] + f[2]) if f[2] else "", "people": f[3], "period": f[4], "funder": f[5], "type": f[6] if len(f) > 6 else ""})
        elif f[0] == "PRESS": press.append({"date": f[1], "title": f[2], "url": g["portal_base"] + f[3]})
        elif f[0] == "ACT": acts.append({"date": f[1], "title": f[2], "url": g["portal_base"] + f[3]})
        elif f[0] == "PRIZE": prizes.append({"date": f[1], "title": f[2], "url": g["portal_base"] + f[3]})
        elif f[0] == "EVENT": events.append({"date": f[1], "title": f[2]})
    bad = [s for s in g["cfqt"] if s not in valid_subs]
    if bad: raise SystemExit(f"Ugyldig CFQT i gruppe {g['key']}: {bad}")
    # tilknyttede kurser: undervisere, der er medlem af gruppen eller hører til gruppens enhed
    names = {nkey(m["name"]) for m in members}
    crs = {}
    for p in plist:
        if p["institution"] != g["institution"] and p.get("employer") != g["institution"]: continue
        if nkey(p["name"]) in names or any(u in g.get("teacher_units", []) for u in p.get("units", []) + p.get("centres", [])):
            for c in p.get("courses", []):
                k = (c["institution"], c["code"])
                crs.setdefault(k, {**{x: c[x] for x in ("institution", "code", "title", "level", "url", "subs", "primary", "mapped") if x in c}, "teachers": []})
                crs[k]["teachers"].append({"name": p["name"], "role": c["role"]})
    groups_out.append({**{k: v for k, v in g.items() if k != "feeds"}, "cfqt": sort_subs(g["cfqt"]), "members": members, "pubs": pubs, "projects": projects,
                       "press": press, "acts": acts, "prizes": prizes, "static_events": events,
                       "courses": sorted(crs.values(), key=lambda c: (c["level"] != "MSc", c["code"])),
                       "feed": feeds.get("groups", {}).get(g["key"], {})})
gout = {"reference": ref, "groups": groups_out, "feeds_generated": feeds.get("generated", ""), "harvested": "2026-11-02"}
gt = (ROOT / "site/groups_template.html").read_text(encoding="utf-8")
gbody = chrome(gt.replace("/*DATA*/", json.dumps(gout, ensure_ascii=False).replace("</", "<\\/")), "groups")
(ROOT / "site/groups.html").write_text(page.split("<body>\n")[0] + "<body>\n" + gbody + "\n</body>\n</html>\n", encoding="utf-8")
(ROOT / "site/groups_artifact.html").write_text(gbody, encoding="utf-8")
print(f"groups: {len(groups_out)} grupper, {sum(len(g['members']) for g in groups_out)} medlemmer")
print(f"site: {len(courses)} kurser med CFQT-match, {unmapped} uden match (vises ikke)")

# Om data (about.html): kilder og metoder for alle sider samlet ét sted.
aout = {"reference": ref, "unmapped": unmapped, "n_courses": len(courses), "groups_harvested": gout["harvested"], "feeds_generated": gout["feeds_generated"]}
at = (ROOT / "site/about_template.html").read_text(encoding="utf-8")
abody = chrome(at.replace("/*DATA*/", json.dumps(aout, ensure_ascii=False).replace("</", "<\\/")), "about")
(ROOT / "site/about.html").write_text(page.split("<body>\n")[0] + "<body>\n" + abody + "\n</body>\n</html>\n", encoding="utf-8")
(ROOT / "site/about_artifact.html").write_text(abody, encoding="utf-8")

# Kildeliste (SOURCES.md og data/sources.csv) følger data.
import subprocess, sys
subprocess.run([sys.executable, str(ROOT / "scripts/list_sources.py")], check=True)

# Forsiden får ph.d.- og postdoc-projekterne med (små trekanter pr. universitet) og bygges derfor igen til sidst.
out["projects"] = [{k: x[k] for k in ("kind", "inst", "prof", "basis", "title", "url", "subs", "who", "group") if k in x} for x in proj_list]
# Quantum industry (industry.html): Danish Quantum Ecosystem Map, CVR, OpenAlex, job ads
REGION_CITY = {"Aarhus": "Central Denmark", "Lystrup": "Central Denmark", "Odense": "Southern Denmark", "Fredericia": "Southern Denmark",
               "Aalborg": "North Denmark", "Roskilde": "Zealand"}
def region_of(city, postcode=""):
    if city in REGION_CITY: return REGION_CITY[city]
    pc = int(postcode) if postcode.isdigit() else 0
    if pc:
        if pc < 3700: return "Capital Region"
        if pc < 5000: return "Zealand"
        if pc < 7300: return "Southern Denmark"
        if pc < 9000: return "Central Denmark"
        return "North Denmark"
    return "Capital Region"
cvr = {}
for ln in (ROOT / "data/industry/cvr.txt").read_text(encoding="utf-8").splitlines():
    if ln.startswith("#") or not ln.strip(): continue
    c, nm, start, place, code, status = ln.split("|")
    cvr[c] = {"start": start, "postcode": place.split()[0], "code": code, "status": status}
oa_ind = json.loads((ROOT / "data/industry/openalex.json").read_text(encoding="utf-8")) if (ROOT / "data/industry/openalex.json").exists() else {}
jobsd = json.loads((ROOT / "data/industry/jobs.json").read_text(encoding="utf-8")) if (ROOT / "data/industry/jobs.json").exists() else {"items": [], "sources": {}}
jobs = jobsd.get("items", [])
UNI_RX = re.compile(r"University|Universit|Technical University of Denmark|Niels Bohr", re.I)
orgs = []
for ln in (ROOT / "data/industry/organisations.txt").read_text(encoding="utf-8").splitlines():
    if ln.startswith("#") or not ln.strip(): continue
    f = ln.split("|")
    name, cat, apps, role, summ, city, c, subs, l1, l2, l3, spin = f
    cv = cvr.get(c, {})
    o = {"name": name, "category": cat, "apps": apps, "role": role, "summary": summ, "city": city, "cvr": c, "start": cv.get("start", ""),
         "region": region_of(city, cv.get("postcode", "")), "subs": subs.split(";") if subs else [],
         "prof": {a: l for a, l in zip(("I", "II", "III"), (l1, l2, l3)) if l}, "spinout": spin}
    oa = oa_ind.get(name)
    if oa and oa.get("works"):
        o["oa"] = {"works": oa["works"], "unis": [x for x in oa.get("co", []) if UNI_RX.search(x["name"]) and re.search(r"Denmark|Copenhagen|Aarhus|Aalborg|Southern|DTU", x["name"])][:4]}
    key = re.sub(r"\W", "", re.sub(r"\b(ApS|A/S|P/S|Inc)\b", "", name.split("(")[0]).lower())[:10]
    o["jobs"] = sum(1 for j in jobs if j.get("technical") and key and key in re.sub(r"\W", "", (j.get("employer") or "").lower()))
    orgs.append(o)
coverage = {d: {"courses": 0, "research": 0, "orgs": 0, "jobs": 0} for d in ref["cfqt"]["domains"]}
for c in courses:
    for d in {s.split(".")[0] for s in c.get("subs", [])}: coverage[d]["courses"] += 1
for pp in plist:
    if pp.get("rp"):
        for d in {s.split(".")[0] for x in pp["rp"]["it"] for s in x[2].split(";")}: coverage[d]["research"] += 1
for o in orgs:
    for d in {s.split(".")[0] for s in o["subs"]}: coverage[d]["orgs"] += 1
for j in jobs:
    if j.get("technical") and not j.get("academic"):
        for d in {s.split(".")[0] for s in j.get("subs", [])}: coverage[d]["jobs"] += 1
jobs_read = max((v.get("read", "") for v in jobsd.get("sources", {}).values()), default="")
iout = {"reference": ref, "orgs": orgs, "jobs": [{k: j.get(k) for k in ("title", "employer", "place", "url", "first", "last", "academic", "subs", "level", "prof", "technical")} for j in jobs],
        "coverage": coverage, "jobs_read": jobs_read}
it_ = (ROOT / "site/industry_template.html").read_text(encoding="utf-8")
ibody = chrome(it_.replace("/*DATA*/", json.dumps(iout, ensure_ascii=False).replace("</", "<\\/")), "industry")
(ROOT / "site/industry.html").write_text(page.split("<body>\n")[0] + "<body>\n" + ibody + "\n</body>\n</html>\n", encoding="utf-8")
(ROOT / "site/industry_artifact.html").write_text(ibody, encoding="utf-8")
print(f"industry: {len(orgs)} organisations, {sum(1 for j in jobs if j.get('technical') and not j.get('academic'))} technical job ads")
out["industry"] = [{"name": o["name"], "role": o["role"], "city": o["city"], "subs": o["subs"], "prof": o["prof"], "summary": o["summary"]} for o in orgs if o["prof"]]
out["jobs"] = [{"title": j["title"], "employer": j.get("employer", ""), "url": j["url"], "subs": j.get("subs", []), "prof": j.get("prof", {}), "first": j.get("first", "")} for j in jobs if j.get("technical") and not j.get("academic")]
# Research of the educators on the front page: one item per educator, at their level in each proficiency area
def _area(x):
    d = x.split(".")[0]
    return "I" if d in ("1", "2") or x in ("5.1", "5.4", "5.5") else ("III" if d == "8" or x in ("5.6", "6.7", "7.4", "7.6") else "II")
res_list = []
for pp in plist:
    rp = pp.get("rp")
    if not rp or not rp["it"]: continue
    mains = [_area(x[2].split(";")[0]) for x in rp["it"]]
    touch = [set(map(_area, x[2].split(";"))) for x in rp["it"]]
    prof = {}
    for a in ("I", "II", "III"):
        m = mains.count(a); sec = sum(1 for mm, t in zip(mains, touch) if a in t and mm != a)
        lv = "C2" if m >= 3 else "C1" if (m >= 1 or sec >= 2) else "B2" if sec == 1 else ""
        if lv: prof[a] = lv
    if not prof: continue
    w = {}
    for x in rp["it"]:
        for i, sub in enumerate(x[2].split(";")): w[sub] = w.get(sub, 0) + (1 if i == 0 else 0.5)
    subs = sorted(w, key=lambda k: -w[k])[:3]
    res_list.append({"inst": pp["institution"], "name": pp["name"], "level": pp.get("level", ""), "unit": ([u for u in pp.get("units", [])] or [""])[-1],
                     "prof": prof, "subs": subs, "n": len(rp["it"])})
out["research"] = res_list
# Workshops (W) and public outreach (O): hand-made list (data/outreach/activities.txt) and public quantum events
# from the NBI and AU calendars (data/outreach/calendar.json, scripts/fetch_outreach.py, weekly)
outreach = []
for ln in (ROOT / "data/outreach/activities.txt").read_text(encoding="utf-8").splitlines():
    if not ln.strip() or ln.startswith("#"): continue
    kind, prov, years, title, aud, subs, l1, l2, l3, url = ln.split("|")
    prof = {a: l for a, l in zip(("I", "II", "III"), (l1, l2, l3)) if l}
    outreach.append({"kind": kind, "provider": prov, "years": years.replace(";", ", "), "title": title, "audience": aud,
                     "subs": subs.split(";"), "prof": prof, "url": url})
cal = ROOT / "data/outreach/calendar.json"
if cal.exists():
    for x in json.loads(cal.read_text(encoding="utf-8")).get("items", []):
        outreach.append({"kind": "O", "provider": x["provider"], "years": (x.get("date") or x.get("found", ""))[:10], "title": x["title"],
                         "audience": "public event (calendar)", "subs": x["subs"], "prof": x["prof"], "url": x["url"]})
out["outreach"] = outreach
body = chrome(tpl.replace("/*DATA*/", json.dumps(out, ensure_ascii=False).replace("</", "<\\/")), "index")
page = page.split("<body>\n")[0] + "<body>\n" + body + "\n</body>\n</html>\n"
(ROOT / "site/index.html").write_text(page, encoding="utf-8")
(ROOT / "site/artifact.html").write_text(body, encoding="utf-8")

