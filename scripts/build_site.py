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
                "subs": subs, "domain": subs[0].split(".")[0],
                "prof": {k: r[f"prof_{k}"] for k in ("I", "II", "III") if r[f"prof_{k}"]},
                "status": r.get("cfqt_status", "estimated"),
                "kw_strong": int(r["kw_strong"] or 0), "kw_medium": int(r["kw_medium"] or 0),
                "note": r.get("note", ""),
                "url": r.get("url") or inst.get("course_url", "").format_map({**r, "ref": r.get("ref") or r["code"]}),
            })

out = {"reference": ref, "courses": courses, "unmapped": unmapped}
(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site/data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

# Selvstændig side: data indlejres, så index.html virker både på GitHub Pages og lokalt.
tpl = (ROOT / "site/template.html").read_text(encoding="utf-8")
body = tpl.replace("/*DATA*/", json.dumps(out, ensure_ascii=False).replace("</", "<\\/"))
page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
(ROOT / "site/index.html").write_text(page, encoding="utf-8")
(ROOT / "site/artifact.html").write_text(body, encoding="utf-8")  # til claude.ai-preview
print(f"site: {len(courses)} kurser med CFQT-match, {unmapped} uden match (vises ikke)")
