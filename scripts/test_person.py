#!/usr/bin/env python3
"""TEST: builds site/test/molmer.html, a research proficiency triangle for one researcher (not linked from the site)."""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
ref = json.loads((ROOT / "data/reference.json").read_text(encoding="utf-8"))["cfqt"]
items = []
for ln in (ROOT / "data/people/test_molmer.txt").read_text(encoding="utf-8").splitlines():
    if not ln.strip() or ln.startswith("#"): continue
    k, y, s, t = ln.split("|", 3)
    items.append({"k": k, "y": int(y), "subs": [] if s == "x" else s.split(";"), "t": t})
tpl = (ROOT / "site/template.html").read_text(encoding="utf-8")
root_css = tpl[tpl.index(":root{"):tpl.index("*{box-sizing")]
data = {"cfqt": {k: ref[k] for k in ("areas", "levels", "level_by_area", "domains", "doi")}, "items": items}
page = (ROOT / "scripts/test_person_template.html").read_text(encoding="utf-8")
page = page.replace("/*ROOTCSS*/", root_css).replace("/*DATA*/", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
(ROOT / "site/test/molmer.html").write_text(page, encoding="utf-8")
print(len(items), "items")
