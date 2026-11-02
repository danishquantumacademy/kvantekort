# Danish Quantum Education Map

Mapping of quantum technology education at Danish universities, published at **[map.danishquantumacademy.dk](https://map.danishquantumacademy.dk)** by [Danish Quantum Academy](https://danishquantumacademy.dk) as part of the mapping task of the European Quantum Academy (Northern European Regional Quantum Academy).

Every course is described with the terms of the **European Competence Framework for Quantum Technologies (CFQT) v3.0** (F. Greinert and R. Müller, QUCATS, April 2025, [doi:10.2759/8917117](https://doi.org/10.2759/8917117), CC BY 4.0):

- **Content map:** up to three CFQT subdomains per course (e.g. `2.3` Solid-state physics, `5.5` Quantum algorithms). The first is the primary subdomain.
- **Proficiency levels:** the level (A1 Awareness to C2 Innovation) the course brings students to in each proficiency area it addresses: (I) Quantum concepts, (II) QT hardware & software engineering, (III) QT applications & strategies. An empty level means the course gives no QT-specific proficiency in that area, which is typical for enabling technologies such as classical optics or nanofabrication.

All assignments are **first estimates** (`cfqt_status = estimated`) made from the course descriptions, study level and workload. They will be validated with the course responsibles through the European Quantum Academy survey.

## Repository structure

```
data/
  programmes.json           # study paths through MSc programmes (student-perspective triangles)
  reference.json            # CFQT content map (8 domains, 42 subdomains), areas, levels; institutions and totals
  raw/<inst>_courses.json   # full harvest (all courses), produced by the scrapers
  classification/<inst>.csv # quantum-relevant courses with CFQT subdomains and proficiency levels
  schedule/<inst>.txt       # MSc courses: semester, teaching block, weekly schedule slot, prerequisite course codes
scrapers/
  dtu_browser.js            # kurser.dtu.dk (run in the browser console)
  au_browser.js             # kursuskatalog.au.dk via the catalogue's own API
  sdu_browser.js            # SDU's ODIN: iterates code prefixes + Faculty of Engineering curricula
  aau_browser.js            # moduler.aau.dk: broad search + every module page for 2026/27
  phdcourses_browser.js     # PhD courses from the national portal phdcourses.dk
  ku_kucourses_browser.js   # KU SCIENCE courses via kucourses.dk (temporary source)
scripts/
  cfqt_estimates.txt        # the CFQT estimate per course (source of truth for the first round)
  apply_cfqt.py             # writes the estimates into data/classification/*.csv
  build_site.py             # builds site/data.json and site/index.html (data embedded)
site/
  template.html             # coverage matrix and course list (index.html)
  triangle_template.html    # CFQT proficiency triangle per university (triangle.html)
  students_template.html    # study path profiles per MSc programme (students.html)
  planner_template.html     # course finder: interests -> three MSc course plans (planner.html)
  index.html                # generated; served by GitHub Pages
  CNAME                     # map.danishquantumacademy.dk
.github/workflows/pages.yml # builds and publishes the site on every push to main
```

Harvested data and expert judgement are kept apart: scrapers only write to `data/raw/`, while the CFQT assignments in `data/classification/` are curated and changed through pull requests, so every change has a history.

## CSV columns

`institution, level, code, [ref,] [url,] title, language, ects, dept, cfqt_primary, cfqt_secondary, prof_I, prof_II, prof_III, cfqt_status, kw_strong, kw_medium, note`

- `cfqt_primary`: primary CFQT subdomain; `cfqt_secondary`: further subdomains separated by `;`. Courses with no subdomain have no meaningful CFQT match and are not shown on the site.
- `prof_I`, `prof_II`, `prof_III`: proficiency level `A1`–`C2`, or empty.
- `cfqt_status`: `estimated` (first round) or `confirmed` (validated by the course responsible).
- `kw_strong`, `kw_medium`: keyword counts in the course description (quantum terms / related technical terms).
- `level`: `BSc`, `MSc`, `PhD`, `Diplom` (Bachelor of Engineering) or `Master` (professional master).
- `url` overrides the institution's link template; `ref` is used where the course page is addressed by an internal id (AU).

## Status (2 November 2026)

| Institution | Harvest | Mapped courses |
|---|---|---|
| DTU | 1,274 course rows, all levels, 2026/27 | 102 |
| AU | 1,554 unique courses, Natural + Technical Sciences | 58 |
| SDU | Active course descriptions, Faculty of Science + Faculty of Engineering (Physics and Technology, Electronics) | 52 |
| AAU | 6,841 modules; Engineering & Science + IT & Design: 1,947 unique titles | 37 |
| KU (SCIENCE only) | 862 BSc/MSc courses via [kucourses.dk](https://kucourses.dk) (student-run mirror; kurser.ku.dk was unavailable) + PhD courses | 55 |

304 courses analysed; 290 match the CFQT content map and are shown on the site. PhD courses for AU, SDU, AAU and KU come from [phdcourses.dk](https://phdcourses.dk); DTU's from its own course base.

## Schedule data

`data/schedule/<inst>.txt` holds one line per MSc course: `code|semester|period|slot|prerequisites`, harvested from the course catalogues for 2026/27. The course finder uses it to order courses and flag timetable clashes.

- `semester`: `E` autumn, `F` spring, `EF` both, or a 3-week period `Jan`, `Jun`, `Aug`.
- `period`: `S` whole semester, `H1`/`H2` first/second half (KU blocks 1–4, AU quarters, SDU quarters), `3w` for 3-week courses.
- `slot`: the weekly schedule slot where the university has one: DTU modules (e.g. `F3A`, Tuesday 8–12) and KU schedule groups (`A`, `B`, `C`). AU, SDU and AAU publish no comparable slots in their catalogues.
- `prerequisites`: course codes named under recommended or academic prerequisites; where a course is named only by title, the code was added by hand (noted in the file header).

## Update workflow

1. **Harvest:** run the institution's scraper and save the file in `data/raw/`.
2. **Screen:** courses with keyword hits or quantum-related titles are candidates.
3. **Map:** add or edit the line in `scripts/cfqt_estimates.txt` and run `python scripts/apply_cfqt.py`, or edit `data/classification/<inst>.csv` directly.
4. **Build:** `python scripts/build_site.py`. GitHub Actions does this automatically on push.

Contact data for course responsibles is kept in a separate private repository and is never published here.
