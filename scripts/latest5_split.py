#!/usr/bin/env python3
"""Write data/groups/pubcheck/<key>_latest5.tsv for several groups from one classification run.

Usage: python3 scripts/latest5_split.py <classes.txt> <map.txt> <portal name> <key> [<key> ...]
classes.txt: "portal slug|cfqt subdomains or -|basis" per output; map.txt: "member:slug,slug,..." (newest first).
Each member is written to the file of every listed group they belong to (data/groups/<key>.txt)."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
cls = {}
for l in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if l.strip():
        s, c, b = l.split("|", 2); cls[s] = (c, b)
mp = {}
for l in pathlib.Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    if l.strip():
        n, s = l.split(":", 1); mp[n] = s.split(",")
portal = sys.argv[3]
for key in sys.argv[4:]:
    names = [l.split("||")[1] for l in (ROOT / f"data/groups/{key}.txt").read_text(encoding="utf-8").splitlines() if l.startswith("P||")]
    rows = [f"{n}\t{s}\t{cls[s][0]}\t{cls[s][1]}" for n in names for s in mp.get(n, [])]
    head = (f"# The five newest research outputs on each {key} member's {portal} profile, classified on the CFQT content map\n"
            "# from the title and abstract in the portal (read and classified by Danish Quantum Academy, 11 November 2026).\n"
            "# '-' = outside the CFQT content map. First subdomain = main topic.\nmember\tportal path\tcfqt\tbasis\n")
    (ROOT / f"data/groups/pubcheck/{key}_latest5.tsv").write_text(head + "\n".join(rows) + "\n", encoding="utf-8")
    print(key, len(rows))
