#!/usr/bin/env python3
"""Split one combined compact harvest into data/groups/pubcheck/harvest/<key>.txt by group membership.
Usage: python3 scripts/harvest_split.py <combined.txt> "<header comment>" <key> [<key> ...]"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
blocks, cur = {}, None
for l in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if l.startswith("#M|"):
        cur = l.split("|")[1]; blocks[cur] = [l]
    elif cur and l.strip() and not l.startswith("# "):
        blocks[cur].append(l)
for key in sys.argv[3:]:
    names = [l.split("||")[1] for l in (ROOT / f"data/groups/{key}.txt").read_text(encoding="utf-8").splitlines() if l.startswith("P||")]
    out = [f"# {key}, {sys.argv[2]}"] + [x for n in names if n in blocks for x in blocks[n]]
    (ROOT / f"data/groups/pubcheck/harvest/{key}.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(key, sum(n in blocks for n in names), "of", len(names))
