# Sources

Everything on [map.danishquantumacademy.dk](https://map.danishquantumacademy.dk) comes from **public web pages that anyone can read without logging in**: university course catalogues, curricula and programme pages, the universities' public research portals, the research groups' own websites, and the CFQT framework. No intranets, student or staff systems behind a login, paid databases, or private documents have been used.

The full list, one row per page, is in [`data/sources.csv`](data/sources.csv) (columns: category, institution, url, what it was used for, data file). It is generated from the data files by `scripts/list_sources.py`, so it changes when the data change. The table below summarises it.

## How the pages were read

- **Course catalogues and curricula** were read in an ordinary web browser or through the public data feed that the catalogue page itself uses (AU's course catalogue loads its course data from `kursuskatalog.au.dk/api/courses/`, which is open to anyone). Curricula published as PDF were read from the universities' public study-regulation pages.
- **Research portals** (DTU Orbit, the University of Copenhagen research portal, AU Pure, SDU Find Researcher, AAU VBN) were read in an ordinary browser. Their list pages sit behind bot protection, so they are not harvested automatically.
- **Research groups' news, events, grants and positions** are read automatically every Monday by `scripts/fetch_group_feeds.py` from the public pages listed as "Research group feed (weekly)". The script identifies itself as `DQA-map/1.0` with a link to the map.
- **Only professional information** is kept: names, positions, units, research topics, research output titles and the courses people teach. No e-mail addresses, phone numbers, photos, CV details or birth dates are stored in this repository or shown on the map. Group photos and long texts are not copied; summaries are written by Danish Quantum Academy, with at most a short quote and a link to the source.

## Notes on particular sources

- **University of Copenhagen courses** come from [kucourses.dk](https://kucourses.dk), a public, student-run mirror of KU's course catalogue, because kurser.ku.dk could not be reached on 2 November 2026. The data should be checked against kurser.ku.dk.
- **SDU study plans** were opened from the public MitSDU programme pages ("Uddannelsens forløb"), which link to the public study regulations on odin.sdu.dk.
- **Search engines** were used only to find the official pages; no information is taken from search results.
- **Survey contacts.** For the European Quantum Academy survey, the names and work e-mail addresses of course responsibles were taken from the same public course pages and are kept in a separate private repository. They are not published.

## Summary by source


### Framework

| Site | Pages |
|---|---:|
| doi.org | 1 |

### Course catalogue

| Site | Pages |
|---|---:|
| kurser.dtu.dk | 100 |
| kursuskatalog.au.dk | 56 |
| kucourses.dk | 49 |
| moduler.aau.dk | 38 |
| odinlister.sdu.dk | 38 |
| odin.sdu.dk | 9 |
| phdcourses.dk | 6 |
| uvm.dk | 2 |
| tidsskrift.dk | 1 |

### Upper secondary

| Site | Pages |
|---|---:|
| uddannelsesstatistik.dk | 1 |
| uvm.dk | 1 |

### Timetable and prerequisites

| Site | Pages |
|---|---:|
| kucourses.dk | 1 |
| kurser.dtu.dk | 1 |
| kursuskatalog.au.dk | 1 |
| moduler.aau.dk | 1 |
| odin.sdu.dk | 1 |

### Programme and curriculum

| Site | Pages |
|---|---:|
| kurser.dtu.dk | 15 |
| odin.sdu.dk | 7 |
| www.ku.dk | 6 |
| bachelor.au.dk | 3 |
| mitsdu.dk | 2 |
| studieordninger.aau.dk | 2 |
| www.dtu.dk | 2 |
| kucourses.dk | 1 |
| kursuskatalog.au.dk | 1 |
| moduler.aau.dk | 1 |
| studerende.au.dk | 1 |
| studies.ku.dk | 1 |

### Educator profile

| Site | Pages |
|---|---:|
| orbit.dtu.dk | 118 |
| researchprofiles.ku.dk | 56 |
| portal.findresearcher.sdu.dk | 47 |
| pure.au.dk | 41 |
| vbn.aau.dk | 15 |

### Educator output and PhD projects

| Site | Pages |
|---|---:|
| orbit.dtu.dk | 386 |
| researchprofiles.ku.dk | 98 |
| portal.findresearcher.sdu.dk | 81 |
| pure.au.dk | 72 |
| vbn.aau.dk | 30 |

### Educator supervised PhD theses

| Site | Pages |
|---|---:|
| orbit.dtu.dk | 118 |
| portal.findresearcher.sdu.dk | 108 |
| researchprofiles.ku.dk | 88 |
| vbn.aau.dk | 73 |

### Educator research output (OpenAlex)

| Site | Pages |
|---|---:|
| openalex.org | 345 |

### Unit page

| Site | Pages |
|---|---:|
| orbit.dtu.dk | 75 |
| vbn.aau.dk | 25 |
| portal.findresearcher.sdu.dk | 20 |
| www.sdu.dk | 17 |
| electro.dtu.dk | 16 |
| researchprofiles.ku.dk | 16 |
| pure.au.dk | 10 |
| www.nanolab.dtu.dk | 9 |
| physics.dtu.dk | 8 |
| www.healthtech.dtu.dk | 8 |
| nbi.ku.dk | 5 |
| www.compute.dtu.dk | 4 |
| www.kemi.dtu.dk | 4 |
| phys.au.dk | 3 |
| www.space.dtu.dk | 3 |
| di.ku.dk | 2 |
| www.bioengineering.dtu.dk | 2 |
| www.energy.dtu.dk | 2 |
| www.math.aau.dk | 2 |
| cbqs.ku.dk | 1 |
| cfin.au.dk | 1 |
| chem.au.dk | 1 |
| diku.dk | 1 |
| ece.au.dk | 1 |
| engtech.dtu.dk | 1 |
| es.aau.dk | 1 |
| inano.au.dk | 1 |
| microbes.dtu.dk | 1 |
| mpe.au.dk | 1 |
| nano.ku.dk | 1 |
| nanophoton.dtu.dk | 1 |
| nbia.nbi.ku.dk | 1 |
| nqcp.ku.dk | 1 |
| qdev.nbi.ku.dk | 1 |
| quantum.dtu.dk | 1 |
| quantumforlife.ku.dk | 1 |
| www.bigq.fysik.dtu.dk | 1 |
| www.bio.aau.dk | 1 |
| www.bio.ku.dk | 1 |
| www.classique.aau.dk | 1 |
| www.cmc.aau.dk | 1 |
| www.cs.aau.dk | 1 |
| www.cs.au.dk | 1 |
| www.fysik.dtu.dk | 1 |
| www.ind.ku.dk | 1 |
| www.ki.ku.dk | 1 |
| www.math.ku.dk | 1 |
| www.mp.aau.dk | 1 |
| www.nbi.ku.dk | 1 |
| www.qmath.ku.dk | 1 |
| www.spoc.dtu.dk | 1 |
| www1.bio.ku.dk | 1 |

### Workshops and public outreach

| Site | Pages |
|---|---:|
| nbi.ku.dk | 4 |
| phys.au.dk | 3 |
| nqcp.ku.dk | 1 |
| sites.google.com | 1 |
| www.sdu.dk | 1 |

### Research group

| Site | Pages |
|---|---:|
| researchprofiles.ku.dk | 98 |
| orbit.dtu.dk | 85 |
| vbn.aau.dk | 41 |
| portal.findresearcher.sdu.dk | 34 |
| www.sdu.dk | 2 |
| employment.ku.dk | 1 |
| international.au.dk | 1 |
| nqcp.ku.dk | 1 |
| phys.au.dk | 1 |
| physics.dtu.dk | 1 |
| pure.au.dk | 1 |
| www.classique.aau.dk | 1 |
| www.dtu.dk | 1 |
| www.vacancies.aau.dk | 1 |

### Research group feed (weekly)

| Site | Pages |
|---|---:|
| phys.au.dk | 2 |
| www.sdu.dk | 2 |
| nqcp.ku.dk | 1 |
| orbit.dtu.dk | 1 |
| physics.dtu.dk | 1 |
| researchprofiles.ku.dk | 1 |
| vbn.aau.dk | 1 |

## Access check

The workflow "Check sources" opened 138 pages (up to three per site) from a GitHub server, without login or cookies. Result, in [`data/sources_check.csv`](data/sources_check.csv): **111 public, 0 behind a login**, 3 bot-protected and 24 not reachable.

- *Bot-protected* pages (the AU research portal) show a Cloudflare challenge to scripts but open normally in a browser without logging in.
- *Not reachable* are mostly University of Copenhagen web servers (ku.dk), which do not answer requests from GitHub's servers; they open normally in a browser without logging in. The rest were outdated links to unit websites, which have been removed (the map links to the research-portal page instead).



Total: 2577 pages from 75 sites. All were publicly accessible without login when they were read (2–3 November 2026; group feeds weekly).
