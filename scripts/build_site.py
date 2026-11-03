#!/usr/bin/env python3
"""Samler alle klassifikationer til site/data.json og site/index.html.

Brug:  python scripts/build_site.py
Input:  data/classification/*.csv  (én fil pr. institution, med CFQT-kolonner)
        data/reference.json        (CFQT content map, områder, niveauer, institutioner)
Output: site/data.json, site/index.html (data indlejret), site/artifact.html
"""
import csv, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ref = json.loads((ROOT / "data/reference.json").read_text(encoding="utf-8"))
valid_subs = {s for d in ref["cfqt"]["domains"].values() for s in d["subdomains"]}
valid_levels = set(ref["cfqt"]["levels"])
# CFQT-underdomæner vises altid i numerisk rækkefølge (1.1, 1.2, …, 2.1); det primære underdomæne gemmes separat
skey = lambda s: tuple(int(x) for x in s.split("."))
sort_subs = lambda xs: sorted(dict.fromkeys(xs), key=skey)

courses, unmapped = [], 0
for f in sorted((ROOT / "data/classification").glob("*.csv")):
    with f.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inst = ref["institutions"][r["institution"]]
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
NAV = [("Education", [("index", "index.html", "Coverage"), ("triangle", "triangle.html", "Triangle"),
                      ("students", "students.html", "Study paths"), ("planner", "planner.html", "Course finder")]),
       ("Research", [("people", "people.html", "Educators"), ("groups", "groups.html", "Groups")])]
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

# Trekant-siden (CFQT proficiency triangle) bygges af de samme data.
ttpl = (ROOT / "site/triangle_template.html").read_text(encoding="utf-8")
tbody = chrome(ttpl.replace("/*DATA*/", json.dumps(out, ensure_ascii=False).replace("</", "<\\/")), "triangle")
tpage = page.split("<body>\n")[0] + "<body>\n" + tbody + "\n</body>\n</html>\n"
(ROOT / "site/triangle.html").write_text(tpage, encoding="utf-8")
(ROOT / "site/triangle_artifact.html").write_text(tbody, encoding="utf-8")

# Studiestier (den studerendes trekant) bygges af kurserne + data/programmes.json.
sout = {**out, "programmes": programmes}
stpl = (ROOT / "site/students_template.html").read_text(encoding="utf-8")
sbody = chrome(stpl.replace("/*DATA*/", json.dumps(sout, ensure_ascii=False).replace("</", "<\\/")), "students")
(ROOT / "site/students.html").write_text(page.split("<body>\n")[0] + "<body>\n" + sbody + "\n</body>\n</html>\n", encoding="utf-8")
(ROOT / "site/students_artifact.html").write_text(sbody, encoding="utf-8")
# Kursusfinder (den studerendes søgning) bygges af de samme data.
ptpl = (ROOT / "site/planner_template.html").read_text(encoding="utf-8")
pbody = chrome(ptpl.replace("/*DATA*/", json.dumps({**out, "profiles": programmes["reference_profiles"]}, ensure_ascii=False).replace("</", "<\\/")), "planner")
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
pout = {"reference": ref, "people": plist, "units": units}
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

