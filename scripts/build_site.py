#!/usr/bin/env python3
"""Samler alle klassifikationer til site/data.json, som hjemmesiden læser.

Brug:  python scripts/build_site.py
Input:  data/classification/*.csv  (én fil pr. institution)
        data/reference.json        (relevansniveauer, spor, institutioner)
Output: site/data.json
"""
import csv, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ref = json.loads((ROOT / "data/reference.json").read_text(encoding="utf-8"))

courses = []
for f in sorted((ROOT / "data/classification").glob("*.csv")):
    with f.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inst = ref["institutions"][r["institution"]]
            r["ects"] = float(r["ects"]) if r["ects"] else None
            r["relevance"] = int(r["relevance"])
            r["kw_strong"] = int(r["kw_strong"] or 0)
            r["kw_medium"] = int(r["kw_medium"] or 0)
            r["dept_name"] = inst.get("departments", {}).get(r["dept"], r["dept"])
            r["url"] = inst.get("course_url", "").format_map({**r, "ref": r.get("ref") or r["code"]})
            courses.append(r)

out = {"reference": ref, "courses": courses}
(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site/data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

# Selvstændig side: data indlejres, så index.html virker både på GitHub Pages og lokalt.
tpl = (ROOT / "site/template.html").read_text(encoding="utf-8")
body = tpl.replace("/*DATA*/", json.dumps(out, ensure_ascii=False).replace("</", "<\\/"))
page = "<!doctype html>\n<html lang=\"da\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n</head>\n<body>\n" + body + "\n</body>\n</html>\n"
(ROOT / "site/index.html").write_text(page, encoding="utf-8")
(ROOT / "site/artifact.html").write_text(body, encoding="utf-8")  # til claude.ai-preview
print(f"site/data.json + index.html: {len(courses)} klassificerede kurser")
