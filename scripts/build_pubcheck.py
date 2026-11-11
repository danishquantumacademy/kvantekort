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
import difflib, json, pathlib, re, sys, unicodedata
ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "data/groups/pubcheck"
RX = re.compile(r"^(.*) (\d{4}|0) ([A-Z])(?: (\d+))? ([01])$")
READ = {}  # date of the last portal run, from the first header line of <key>_portal.txt


def thash(t):
    """Short title key shared with the browser script: FNV-1a of the first 50 letters/digits, base 36."""
    t = re.sub("[\u0300-\u036f]", "", unicodedata.normalize("NFD", t)).lower()
    t = re.sub(r"[^a-z0-9]", "", re.sub(r"<[^>]+>", "", t))[:50]
    x = 0x811C9DC5
    for c in t.encode():
        x = ((x ^ c) * 0x01000193) & 0xFFFFFFFF
    d, out = "0123456789abcdefghijklmnopqrstuvwxyz", ""
    while True:
        x, r = divmod(x, 36); out = d[r] + out
        if not x: return out


def slugify(t):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", t.lower()))[:64].rstrip("-")


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def similar(a, b):
    a, b = norm(a).split(), norm(b).split()
    if not a or not b:
        return False
    if [w for w in a if w.isdigit() or w in ("i", "ii", "iii", "part")] != [w for w in b if w.isdigit() or w in ("i", "ii", "iii", "part")]:
        return False  # a numbered part or sequel is another work
    return difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() >= 0.85


def build(key):
    lines = (DIR / f"{key}_raw.txt").read_text(encoding="utf-8").split("\n")
    i = lines.index("P")
    W = []
    for w in lines[1:i]:
        t, y, ty, oa, nr = RX.match(w).groups()
        W.append({"t": t, "y": int(y), "ty": ty, "oa": oa or "", "nr": int(nr)})
    byhash_pre = {}
    for k, w in enumerate(W):
        byhash_pre.setdefault(thash(w["t"]), []).append(k)
    # second-run portal file (dates and portal paths); replaces the portal flags of the raw file when present
    portal = {}
    pf = DIR / f"{key}_portal.txt"
    if pf.exists():
        cur = None
        for line in pf.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") and "|" in line:
                cur = line[1:].split("|")[0]; portal[cur] = []
            elif line.startswith("p ") and cur:
                _, h, d, sl = (line.split(" ") + ["", "", "", ""])[:4]
                portal[cur].append((h, "" if d == "-" else d, sl))
    for w in W:
        w["d"] = str(w["y"]) if w["y"] else ""; w["ax"] = ""
    # arXiv run (control source): "x <hash> <arXiv id>" for a work already known, "X|title|date|arXiv id|category" for a new one
    arxiv, same, n_known = {}, {}, len(W)
    af = DIR / f"{key}_arxiv.txt"
    if af.exists():
        cur = None
        for line in af.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") and "|" not in line and not line.startswith("# "):
                cur = line[1:]; arxiv[cur] = []
            elif cur and line.startswith("x "):
                _, h, aid = line.split(" ")[:3]; arxiv[cur].append((h, None, aid, None))
            elif line.startswith("=|"):
                _, a, b = line.split("|")[:3]; same[norm(a)] = norm(b)
            elif cur and line.startswith("X|"):
                _, t, d, aid, cat = line.split("|")[:5]
                arxiv[cur].append((thash(t), d, aid, t))
    mm = DIR / f"{key}_mismatch.txt"
    mismatch = {int(x) for x in mm.read_text().split() if x.isdigit()} if mm.exists() else set()
    people, line_cnt = [], {}
    for line in filter(str.strip, lines[i + 1:]):
        n, slug, orc, osrc, oaid, amb, nop, items, *cnt = line.split("|")  # cnt: "profile/elsewhere" from a compact harvest
        its = {}
        for it in filter(None, items.split(",")):
            m = re.match(r"(\d+)([poax]+)", it)
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
        slugs, sdate = {}, {}
        if n in portal:
            for k in its: its[k].discard("p")
            for h, d, sl in portal[n]:
                ks = byhash_pre.get(h)
                if not ks:
                    print("  new portal output not in the raw file:", n, h); continue
                # the work with this title the member already has, else the first one with it
                k = next((k for k in ks if k in its), ks[0])
                its.setdefault(k, set()).add("p")
                if d and d > W[k]["d"]: W[k]["d"] = d  # newest version (a preprint and its article share one entry)
                if k not in slugs or d >= sdate.get(k, ""):  # link to the newest version
                    slugs[k] = slugify(W[k]["t"]) if sl == "=" else sl; sdate[k] = d
        for h, d, aid, t in arxiv.get(n, []):
            ks = byhash_pre.get(h, [])
            if t is not None and not ks:
                # a new arXiv title: the member's own work with a near-identical title (other spelling, preprint title) is the same work
                k = next((k for k in its if k < n_known and (similar(t, W[k]["t"]) or same.get(norm(t)) == norm(W[k]["t"]))), None)
                if k is None:
                    W.append({"t": t, "y": int(d[:4]), "ty": "P", "oa": "", "nr": 0, "d": d, "ax": aid})
                    k = len(W) - 1; byhash_pre[h] = [k]
                else:
                    print("  arXiv title merged:", n, "|", t, "->", W[k]["t"])
                ks = [k]
            if not ks: continue
            k = next((k for k in ks if k in its), ks[0])
            its.setdefault(k, set()).add("x")
            if not W[k]["ax"]: W[k]["ax"] = aid
            if d and d > W[k]["d"] and "p" not in its[k]: W[k]["d"] = d
        rows = []
        for k, f in its.items():
            st = "mismatch" if k in mismatch else "excluded" if W[k]["nr"] else "profile" if "p" in f else "elsewhere"
            rows.append([k, "".join(s for s in "poax" if s in f), st] + ([slugs[k]] if k in slugs else []))
        rows.sort(key=lambda r: (W[r[0]]["d"] or "0"), reverse=True)
        people.append({"n": n, "slug": slug, "orcid": orc, "osrc": osrc, "oa": oaid, "amb": int(amb), "noportal": int(nop), "rows": rows, "cnt": cnt[0] if cnt else ""})
        if cnt: line_cnt[n] = cnt[0]
    used = sorted({r[0] for p in people for r in p["rows"]})
    remap = {k: j for j, k in enumerate(used)}
    for p in people:
        p["rows"] = [[remap[r[0]]] + r[1:] for r in p["rows"]]
        for s in ("profile", "elsewhere"):
            p["n_" + s] = sum(1 for r in p["rows"] if r[2] == s)
        if p.pop("cnt"):  # compact harvest: only the newest outputs are listed, the counts come from the harvest
            p["n_profile"], p["n_elsewhere"] = map(int, line_cnt[p["n"]].split("/"))
    m = re.search(r"read (\d{1,2} \w+ \d{4}|\d{4}-\d{2}-\d{2})", pf.read_text(encoding="utf-8").split("\n", 1)[0]) if pf.exists() else None
    import datetime
    rd = (datetime.datetime.strptime(m[1], "%d %B %Y").strftime("%Y-%m-%d") if m and not m[1][:4].isdigit() else m[1] if m else "")
    out = {"read": READ.get(key, rd), "w": [[W[k]["t"], W[k]["y"], W[k]["ty"], W[k]["oa"], W[k]["d"], W[k]["ax"]] for k in used], "p": people}
    (DIR / f"{key}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(key, len(people), "members,", len(used), "works")


if __name__ == "__main__":
    for f in sorted(DIR.glob("*_raw.txt")) if len(sys.argv) < 2 else [DIR / f"{k}_raw.txt" for k in sys.argv[1:]]:
        build(f.name[:-8])
