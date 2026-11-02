#!/usr/bin/env python3
"""Indfører CFQT-skønnene (scripts/cfqt_estimates.txt) i data/classification/*.csv.
Fjerner de gamle kolonner relevance og track og tilføjer CFQT-kolonnerne."""
import csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
est = {}
for line in (ROOT / "scripts/cfqt_estimates.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    inst, code, subs, p1, p2, p3 = (line.split("|") + [""] * 6)[:6]
    s = [x for x in subs.split(";") if x]
    est[(inst, code)] = {"cfqt_primary": s[0] if s else "", "cfqt_secondary": ";".join(s[1:]),
                         "prof_I": p1, "prof_II": p2, "prof_III": p3}
NOTES = {  # danske noter fra første runde -> engelsk
    "samme indhold som FY845": "Same content as FY845",
    "MSc in Quantum Computing": "MSc in Quantum Computing",
    "godkendt som ph.d.-kursus": "Approved as PhD course",
    "Civilingeniør i Fysik og Teknologi": "MSc in Engineering Physics",
    "ren matematik": "Pure mathematics",
    "vurderet på titel": "",
    "samme pensum som Eksperimentel kvanteoptik 1": "Same syllabus as Experimental Quantum Optics 1",
    "gymnasierettet; kvanteforsøg indgår": "Aimed at upper-secondary teaching; includes quantum experiments",
    "post-kvantekryptografi indgår": "Includes post-quantum cryptography",
    "phdcourses.dk; september 2026": "phdcourses.dk; September 2026",
    "phdcourses.dk; ph.d.-skolen ved TEK; ingen dato angivet": "phdcourses.dk; PhD School, Faculty of Engineering; no date given",
    "phdcourses.dk; februar 2027": "phdcourses.dk; February 2027",
    "phdcourses.dk; december 2026": "phdcourses.dk; December 2026",
}
def en_note(n):
    if not n:
        return ""
    if n in NOTES:
        return NOTES[n]
    n = n.replace("også ", "also ").replace(" og ", " and ").replace("projekt", "project")
    return n
missing = []
for f in sorted((ROOT / "data/classification").glob("*.csv")):
    rows = list(csv.DictReader(f.open(encoding="utf-8")))
    hdr = [h for h in rows[0].keys() if h not in ("relevance", "track")]
    i = hdr.index("dept") + 1
    hdr[i:i] = ["cfqt_primary", "cfqt_secondary", "prof_I", "prof_II", "prof_III", "cfqt_status"]
    for r in rows:
        e = est.get((r["institution"], r["code"]))
        if not e:
            missing.append((r["institution"], r["code"]))
            e = {"cfqt_primary": "", "cfqt_secondary": "", "prof_I": "", "prof_II": "", "prof_III": ""}
        r.update(e)
        r["cfqt_status"] = "estimated"
        r["note"] = en_note(r.get("note", ""))
        r["language"] = {"Danish or English": "Danish or English"}.get(r["language"], r["language"])
    with f.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
print("Uden skøn:", missing or "ingen")
