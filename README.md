# Danish Quantum Education Map

Mapping of quantum technology education at Danish universities, published at **[map.danishquantumacademy.dk](https://map.danishquantumacademy.dk)** by [Danish Quantum Academy](https://danishquantumacademy.dk) as part of the mapping task of the European Quantum Academy (Northern European Regional Quantum Academy).

Every course is described with the terms of the **European Competence Framework for Quantum Technologies (CFQT) v3.0** (F. Greinert and R. Müller, QUCATS, April 2025, [doi:10.2759/8917117](https://doi.org/10.2759/8917117), CC BY 4.0):

- **Content map:** up to three CFQT subdomains per course (e.g. `2.3` Solid-state physics, `5.5` Quantum algorithms). The first is the primary subdomain.
- **Proficiency levels:** the level (A1 Awareness to C2 Innovation) the course brings students to in each proficiency area it addresses: (I) Quantum concepts, (II) QT hardware & software engineering, (III) QT applications & strategies. An empty level means the course gives no QT-specific proficiency in that area, which is typical for enabling technologies such as classical optics or nanofabrication.

All assignments are **first estimates** (`cfqt_status = estimated`) made from the course descriptions, study level and workload. They will be validated with the course responsibles through the European Quantum Academy survey.

## Repository structure

```
data/
  programmes.json           # study paths through MSc and BSc programmes, with curriculum sources (student-perspective triangles)
  reference.json            # CFQT content map (8 domains, 42 subdomains), areas, levels; institutions and totals
  raw/<inst>_courses.json   # full harvest (all courses), produced by the scrapers
  classification/<inst>.csv # quantum-relevant courses with CFQT subdomains and proficiency levels
  projects/cfqt_projects.txt # CFQT subdomains of PhD and postdoc projects, by title (supervised PhD projects and group members)
  classification/gym.csv    # physics A at upper secondary school (stx/htx): core content and Kvant21, valid for all schools of each type;
                            # school counts and Fysik A statistics are under "schools" in reference.json
  schedule/<inst>.txt       # MSc courses: semester, teaching block, weekly schedule slot, prerequisite course codes
  people/<inst>.txt         # educators: position, organisational units, portal fingerprint / recent outputs (research portals)
  people/research.txt       # research focus per educator with CFQT subdomains (written by DQA)
  people/teaching.csv       # who teaches which course and in which role (no contact data)
  people/units.txt          # landing pages of departments, sections, groups and centres
  groups/groups.json        # research groups on groups.html: summary, CFQT tags, links, feed sources
  groups/<key>.txt          # members, publications and portal projects per group (harvested with a browser)
  groups/feeds.json         # news, events, grants and positions (updated weekly by GitHub Actions)
scrapers/
  dtu_browser.js            # kurser.dtu.dk (run in the browser console)
  au_browser.js             # kursuskatalog.au.dk via the catalogue's own API
  sdu_browser.js            # SDU's ODIN: iterates code prefixes + Faculty of Engineering curricula
  aau_browser.js            # moduler.aau.dk: broad search + every module page for 2026/27
  phdcourses_browser.js     # PhD courses from the national portal phdcourses.dk
  ku_kurser_browser.js      # kurser.ku.dk: every SCIENCE course page for 2026/27 (check and quantum search)
  ku_kucourses_browser.js   # KU SCIENCE courses via kucourses.dk (first round, while kurser.ku.dk was down)
scripts/
  cfqt_estimates.txt        # the CFQT estimate per course (source of truth for the first round)
  apply_cfqt.py             # writes the estimates into data/classification/*.csv
  build_site.py             # builds site/data.json and site/index.html (data embedded)
site/
  template.html             # front page: proficiency triangle per university, CFQT content map, coverage table and course list (index.html);
                            # triangle.html only redirects here, so old links keep working
  planner_template.html     # study planner: programme path and profile, electives from interests, comparison, timetable (planner.html);
                            # students.html only redirects here
  people_template.html      # research behind the courses: educators, units, research and course fit (people.html)
  groups_template.html      # research group profiles: members, publications, projects, news, events, positions, courses (groups.html)
  about_template.html       # about the data: scope, sources and methods for all pages (about.html)
                            # build_site.py adds the shared navigation, how-to-read styling and footer to every page
  index.html                # generated; served by GitHub Pages
  CNAME                     # map.danishquantumacademy.dk
.github/workflows/pages.yml # builds and publishes the site on every push to main
```

Harvested data and expert judgement are kept apart: scrapers only write to `data/raw/`, while the CFQT assignments in `data/classification/` are curated and changed through pull requests, so every change has a history.


## Sources

Everything on the map comes from public web pages that can be read without logging in. [`SOURCES.md`](SOURCES.md) explains which kinds of pages were used and how, and [`data/sources.csv`](data/sources.csv) lists every page, one row per URL. Both are generated from the data files by `scripts/list_sources.py` (run by `build_site.py`). The workflow "Check sources" opens up to three pages per site anonymously and records in `data/sources_check.csv` whether each is public, bot-protected or behind a login.

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
| KU (SCIENCE only) | 969 courses on [kurser.ku.dk](https://kurser.ku.dk), 2026/27 (first round via the mirror kucourses.dk, checked against kurser.ku.dk on 10 November 2026) + PhD courses | 55 |

304 courses analysed; 290 match the CFQT content map and are shown on the site. PhD courses for AU, SDU, AAU and KU come from [phdcourses.dk](https://phdcourses.dk); DTU's from its own course base.

## Schedule data

`data/schedule/<inst>.txt` holds one line per MSc course: `code|semester|period|slot|prerequisites`, harvested from the course catalogues for 2026/27. The course finder uses it to order courses and flag timetable clashes.

- `semester`: `E` autumn, `F` spring, `EF` both, or a 3-week period `Jan`, `Jun`, `Aug`.
- `period`: `S` whole semester, `H1`/`H2` first/second half (KU blocks 1–4, AU quarters, SDU quarters), `3w` for 3-week courses.
- `slot`: the weekly schedule slot where the university has one: DTU modules (e.g. `F3A`, Tuesday 8–12) and KU schedule groups (`A`, `B`, `C`). AU, SDU and AAU publish no comparable slots in their catalogues.
- `prerequisites`: course codes named under recommended or academic prerequisites; where a course is named only by title, the code was added by hand (noted in the file header).

## Educators and research

`data/people/` describes the educators named in the course catalogues, from the universities' research portals (DTU Orbit, KU research portal, AU Pure, SDU Find Researcher, AAU VBN): position, department, section or group, centres, the portal's automatic fingerprint concepts and recent research output titles. Only professional information is kept; no e-mail addresses, phone numbers or CV details. `research.txt` adds a short research focus and the CFQT subdomains it touches, written by Danish Quantum Academy from that data. `people.html` compares those subdomains with the subdomains of each course the educator teaches.

`data/people/harvest/<inst>*.txt` holds each educator's latest research output and the ongoing PhD projects they supervise as main supervisor, harvested from the research portals with a browser. Lines are `O|person|year|type|slug|title` (output) or `J|person|period|type|slug|title` (PhD project), where `person` indexes the `NAMES:` line and `slug=N` means the first N characters of the title's slug, which is how the portals build the address. `people.html` lists them with links and places every educator on a CFQT map of their research.

## Research groups (pilot)

`groups.html` profiles one research group per university: QPIT (DTU), NQCP (KU), CCQ (AU), POLIMA (SDU) and Classique (AAU). Summaries and CFQT tags in `data/groups/groups.json` are written by Danish Quantum Academy; only a short quote is taken from each group's own page, and the groups' images are not reused. Members (including PhD students), positions, current projects, recent output and portal projects are in `data/groups/<key>.txt`; the member and project lists in the research portals sit behind bot protection, so they are refreshed by hand with a browser.

`scripts/fetch_group_feeds.py` runs every Monday in the Pages workflow (and on manual runs). It reads the groups' news and event pages and the research-portal front pages, sorts items into news, events, grants and positions, and writes `data/groups/feeds.json`. If a source cannot be read, the last known items from that source are kept and the page says so. To add a group, add an entry to `groups.json` with its feed URLs and a `<key>.txt` file.

## Update workflow

1. **Harvest:** run the institution's scraper and save the file in `data/raw/`.
2. **Screen:** courses with keyword hits or quantum-related titles are candidates.
3. **Map:** add or edit the line in `scripts/cfqt_estimates.txt` and run `python scripts/apply_cfqt.py`, or edit `data/classification/<inst>.csv` directly.
4. **Build:** `python scripts/build_site.py`. GitHub Actions does this automatically on push.

Contact data for course responsibles is kept in a separate private repository and is never published here.
