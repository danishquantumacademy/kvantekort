#!/usr/bin/env python3
"""Apply the CFQT reverse check (data/review/cfqt_check.tsv) to data/classification/*.csv
and scripts/cfqt_estimates.txt.

Each row of the review file is one course: key (INST:code), the verdict per assigned subdomain
(Ja = the course description covers two or more of the subdomain's CFQT topics, Delvist = one,
Nej = none), the new subdomains (empty = keep, "-" = no CFQT match, remove from the map) and a note.

When the new subdomains drop every subdomain of a proficiency area, that area's level is cleared.
When they add an area that none of the old subdomains belonged to, the level is set to the course's lowest
existing level (or a default by study level), and the change is printed for a manual look.
"""
import csv, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
DEFAULT = {"BSc": "A2", "MSc": "B1", "PhD": "B2", "STX": "A1", "HTX": "A1"}

def area(sub):
    if sub.startswith("1.") or sub in ("5.1", "5.4", "5.5"):
        return "I"
    if sub.startswith("8.") or sub in ("5.6", "6.7", "7.4", "7.6"):
        return "III"
    return "II"

review = {}
with (ROOT / "data/review/cfqt_check.tsv").open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        new = r["new_codes"].strip()
        if new and new != "-" and len(new.split(";")) > 3:
            sys.exit(f"More than three subdomains for {r['course']}")
        review[r["course"]] = new

changed, removed, levels_set = [], [], []
for f in sorted((ROOT / "data/classification").glob("*.csv")):
    rows = list(csv.DictReader(f.open(encoding="utf-8")))
    hdr = list(rows[0].keys())
    for r in rows:
        key = f"{r['institution']}:{r['code']}"
        if key not in review:
            continue
        r["cfqt_status"] = "checked"
        new = review[key]
        if not new:
            continue
        old = [s for s in [r["cfqt_primary"], *r["cfqt_secondary"].split(";")] if s]
        if new == "-":
            r["cfqt_primary"] = r["cfqt_secondary"] = r["prof_I"] = r["prof_II"] = r["prof_III"] = ""
            removed.append(key)
            continue
        subs = new.split(";")
        r["cfqt_primary"], r["cfqt_secondary"] = subs[0], ";".join(subs[1:])
        have = [r[f"prof_{a}"] for a in ("I", "II", "III") if r[f"prof_{a}"]]
        for a in ("I", "II", "III"):
            k = f"prof_{a}"
            if not any(area(s) == a for s in subs):
                r[k] = ""
            elif not r[k] and not any(area(s) == a for s in old):
                r[k] = min(have, key=LEVELS.index) if have else DEFAULT.get(r["level"], "A2")
                levels_set.append(f"{key} {a}={r[k]}")
        changed.append(f"{key}: {';'.join(old)} -> {new}")
    with f.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, lineterminator="\n")
        w.writeheader(); w.writerows(rows)

# keep scripts/cfqt_estimates.txt (the first-round estimates) in step with the classification files
cls = {}
for f in (ROOT / "data/classification").glob("*.csv"):
    for r in csv.DictReader(f.open(encoding="utf-8")):
        cls[(r["institution"], r["code"])] = r
est = ROOT / "scripts/cfqt_estimates.txt"
out = []
for line in est.read_text(encoding="utf-8").splitlines():
    if line.strip() and not line.startswith("#"):
        inst, code = line.split("|")[:2]
        r = cls.get((inst, code))
        if r and f"{inst}:{code}" in review and review[f"{inst}:{code}"]:
            subs = ";".join(s for s in [r["cfqt_primary"], *r["cfqt_secondary"].split(";")] if s) or "-"
            line = "|".join([inst, code, subs, r["prof_I"], r["prof_II"], r["prof_III"]])
    out.append(line)
est.write_text("\n".join(out) + "\n", encoding="utf-8")

print(f"{len(review)} courses checked, {len(changed)} reclassified, {len(removed)} removed")
print("\n".join(changed))
print("Removed:", ", ".join(removed))
print("Levels set for new areas:", ", ".join(levels_set) or "none")
