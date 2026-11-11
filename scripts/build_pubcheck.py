#!/usr/bin/env python3
"""Publication check: compares each group member's research output since 2021 on the university research
profile (the official one) with ORCID and OpenAlex.

Input:  data/groups/pubcheck/<key>_raw.txt   written from the browser harvest (scrapers/pubcheck_browser.js)
        data/groups/pubcheck/<key>_mismatch.txt  works OpenAlex attached to the wrong person (checked by hand)
Output: data/groups/pubcheck/<key>.json      {read, w: [[title, year, type, openalex id]], p: [member ...]}

Raw format: a line "W", one line per work "title year type [openalex-id] non-research-flag", a line "P",
then one line per member "name|portal slug|orcid|orcid source (p=portal, o=openalex)|openalex author|
name shared in OpenAlex|no portal profile|items", items being "<work index><sources>" with p=portal,
o=ORCID, a=OpenAlex. Status per member and work: profile (on the university profile), elsewhere (only in
ORCID/OpenAlex), excluded (editorials, letters, data, code) or mismatch (another person).
The check is run once a semester, or when a researcher asks, since profiles change only when people update them.
"""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "data/groups/pubcheck"
RX = re.compile(r"^(.*) (\d{4}|0) ([A-Z])(?: (\d+))? ([01])$")
READ = {"qmath": "2026-11-11"}


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def build(key):
    lines = (DIR / f"{key}_raw.txt").read_text(encoding="utf-8").split("\n")
    i = lines.index("P")
    W = []
    for w in lines[1:i]:
        t, y, ty, oa, nr = RX.match(w).groups()
        W.append({"t": t, "y": int(y), "ty": ty, "oa": oa or "", "nr": int(nr)})
    mm = DIR / f"{key}_mismatch.txt"
    mismatch = {int(x) for x in mm.read_text().split() if x.isdigit()} if mm.exists() else set()
    people = []
    for line in filter(str.strip, lines[i + 1:]):
        n, slug, orc, osrc, oaid, amb, nop, items = line.split("|")
        its = {}
        for it in filter(None, items.split(",")):
            m = re.match(r"(\d+)([poa]+)", it)
            its[int(m[1])] = set(m[2])
        # a short title (as some ORCID records give it) is merged into the full title of the same work
        for a in sorted(its, key=lambda k: len(W[k]["t"])):
            na = norm(W[a]["t"])
            if len(na.split()) < 2:
                continue
            for b in list(its):
                if b != a and a in its and len(W[b]["t"]) > len(W[a]["t"]) and norm(W[b]["t"]).startswith(na) \
                        and (W[a]["y"] == 0 or abs(W[a]["y"] - W[b]["y"]) <= 1):
                    its[b] |= its.pop(a)
                    break
        rows = []
        for k, f in its.items():
            st = "mismatch" if k in mismatch else "excluded" if W[k]["nr"] else "profile" if "p" in f else "elsewhere"
            rows.append([k, "".join(s for s in "poa" if s in f), st])
        rows.sort(key=lambda r: (-W[r[0]]["y"], W[r[0]]["t"]))
        people.append({"n": n, "slug": slug, "orcid": orc, "osrc": osrc, "oa": oaid, "amb": int(amb), "noportal": int(nop), "rows": rows})
    used = sorted({r[0] for p in people for r in p["rows"]})
    remap = {k: j for j, k in enumerate(used)}
    for p in people:
        p["rows"] = [[remap[k], f, s] for k, f, s in p["rows"]]
        for s in ("profile", "elsewhere"):
            p["n_" + s] = sum(1 for r in p["rows"] if r[2] == s)
    out = {"read": READ.get(key, ""), "w": [[W[k]["t"], W[k]["y"], W[k]["ty"], W[k]["oa"]] for k in used], "p": people}
    (DIR / f"{key}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(key, len(people), "members,", len(used), "works")


if __name__ == "__main__":
    for f in sorted(DIR.glob("*_raw.txt")) if len(sys.argv) < 2 else [DIR / f"{k}_raw.txt" for k in sys.argv[1:]]:
        build(f.name[:-8])
