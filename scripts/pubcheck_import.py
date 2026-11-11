#!/usr/bin/env python3
"""Turn a browser harvest (scrapers/pubcheck_browser.js, harvestDump) into the publication-check input files
data/groups/pubcheck/<key>_raw.txt and <key>_portal.txt, which scripts/build_pubcheck.py reads.

Usage: python3 scripts/pubcheck_import.py <key> <harvest.txt>

Harvest format, one block per member:
  #M|name|portal path|orcid|openalex author id|name shared in OpenAlex (0/1)
  p|hash|date|type nr|portal slug|openalex id|sources|title     research output on the university profile
  e|hash|date|type nr||openalex id|sources|title                 found only in ORCID (o) and/or OpenAlex (a)
  #N|on profile|found only elsewhere                              (compact harvest) counts of research outputs since 2021;
                                                                 the p lines are then only the newest outputs on the profile
In a compact harvest the path may be written "~slug", the type without nr, and the portal slug as "=" when it is the slugified title.
type: J journal article, L letter, R proceedings, P preprint, C book chapter, B book, T thesis, D other;
nr = 1 for editorials, comments, news pieces, data sets and other non-research items.
"""
import pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_pubcheck import thash, slugify

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "data/groups/pubcheck"


def main(key, src, read_date):
    W, byh, people, portal = [], {}, [], []

    def idx(t, y, ty, oa, nr):
        h = thash(t)
        if h not in byh:
            W.append(f"{t} {y or 0} {ty}{' ' + oa if oa else ''} {nr}")
            byh[h] = len(W) - 1
        return byh[h]

    cur, seen_t = None, {}
    for line in pathlib.Path(src).read_text(encoding="utf-8").splitlines():
        if line.startswith("#M|"):
            _, n, path, orc, oaid, amb = (line.split("|") + [""] * 6)[:6]
            path = "/en/persons/" + path[1:] + "/" if path.startswith("~") else path  # compact harvest: "~slug"
            slug = path.rstrip("/").split("/persons/")[-1] if path else ""
            cur = {"n": n, "slug": slug, "orc": orc, "oa": oaid, "amb": amb or "0", "items": [], "p": [], "cnt": ""}
            people.append(cur)
        elif cur and line.startswith("#N|"):
            cur["cnt"] = "/".join(line.split("|")[1:3])
        elif cur and line[:2] in ("p|", "e|"):
            kind, h, d, tn, sl, oa, src_, t = line.split("|", 7)
            t = t or seen_t.get(h, "")  # compact harvest: a repeated work may leave the title out
            seen_t.setdefault(h, t)
            ty, nr = (tn.split() + ["0"])[:2]
            y = d[:4] if d[:4].isdigit() else 0
            k = idx(t, y, ty, oa, nr)
            if kind == "p":
                if sl == "=" and h != thash(t): sl = slugify(t)
                cur["items"].append(f"{k}p{''.join(c for c in 'oa' if c in src_)}")
                cur["p"].append(f"p {thash(t)} {d or '-'} {'=' if sl == slugify(t) else sl}")
            else:
                cur["items"].append(f"{k}{''.join(c for c in 'oa' if c in src_) or 'a'}")
    raw = ["W", *W, "P"]
    for p in people:
        osrc = "p" if p["orc"] else ""
        raw.append("|".join([p["n"], p["slug"], p["orc"], osrc, p["oa"], p["amb"], "0" if p["slug"] else "1", ",".join(p["items"])] + ([p["cnt"]] if p["cnt"] else [])))
    (DIR / f"{key}_raw.txt").write_text("\n".join(raw) + "\n", encoding="utf-8")
    head = [f"# {key} members' research output since 2021 on their university research profiles, read {read_date}.",
            "# \"#name|portal slug|orcid|openalex author\" then one line per output: \"p <title hash> <date> <portal path or = >\".",
            "# Title hash and \"=\" as in scripts/build_pubcheck.py."]
    for p in people:
        head.append(f"#{p['n']}|{p['slug']}|{p['orc']}|{p['oa']}")
        head += p["p"]
    (DIR / f"{key}_portal.txt").write_text("\n".join(head) + "\n", encoding="utf-8")
    print(key, len(people), "members,", len(W), "works")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
