# Kvantekort Danmark

Kortlægning af kvanteområdet i Danmark – uddannelse, forskning, innovation og erhverv.
Første fase: kvanterelevante kurser på de fem universiteter med kvanteaktivitet (DTU, KU, AU, SDU, AAU).

Hjemmesiden (`site/index.html`) viser hvert kursus på et af tre relevansniveauer:

| Niveau | Navn | Betydning |
|---|---|---|
| 1 | Kerne | Kurset handler primært om kvantefysik, kvanteinformation eller kvanteteknologi |
| 2 | Kvantebaseret | Kvantemekanik er bærende fundament (faststof, elektronstruktur, kvantekemi, fotonik) |
| 3 | Perifer | Understøttende fag (klassisk fotonik, nanofab, kryptografi) eller kun nævnt |
| 0 | Ikke relevant | Ingen eller tilfældige nøgleordstræf (vises kun i totaler) |

Hvert kursus har desuden et **fagspor** (`QT`, `QC`, `QM`, `MAT`, `PHO`, `FAB`, `CRY`, `SEN`), defineret i `data/reference.json`.

## Struktur

```
data/
  reference.json            # relevansniveauer, fagspor, institutioner, totaler
  raw/<inst>_courses.json   # rå høst (alle kurser) – genereres af scraperne
  classification/<inst>.csv # kvanterelevante kurser med niveau og spor (redigeres manuelt)
scrapers/
  dtu_browser.js            # høster kurser.dtu.dk i browserkonsollen
scripts/
  build_site.py             # samler classification/*.csv → site/data.json + site/index.html
site/
  template.html             # hjemmesidens skabelon
  index.html                # genereret, data indlejret (serveres af GitHub Pages)
.github/workflows/pages.yml # bygger og publicerer siden ved push til main
```

**Princip:** rå høst og menneskelig vurdering holdes adskilt. Scraperne overskriver kun `data/raw/`; klassifikationerne i `data/classification/` er kuraterede og ændres via pull requests, så hver vurdering har en historik og kan diskuteres.

## Arbejdsgang

1. **Høst** – kør institutionens scraper (for DTU: åbn kurser.dtu.dk, indsæt `scrapers/dtu_browser.js` i konsollen). Gem filen i `data/raw/`.
2. **Forslag** – kurser med nøgleordstræf (`kw_strong > 0` eller `kw_medium ≥ 2`) eller kvanterelaterede titler er kandidater.
3. **Vurdering** – sæt `relevance` og `track` i `data/classification/<inst>.csv`. Tilføj `note`, hvis vurderingen kun bygger på titlen.
4. **Byg** – `python scripts/build_site.py`. GitHub Actions gør det automatisk ved push.

## Ny institution

1. Tilføj institutionen i `data/reference.json` (navn, kursusbase, `course_url`-skabelon, totaler, institutkoder).
2. Skriv `scrapers/<inst>.*` der leverer samme felter som DTU-høsten.
3. Opret `data/classification/<inst>.csv` med samme kolonner.

## CSV-kolonner

`institution, level, code, title, language, ects, dept, relevance, track, kw_strong, kw_medium, note`

## Status

| Institution | Høstet | Klassificeret |
|---|---|---|
| DTU | 2026-11-02 (1.274 kursusrækker, 2026/27) | 102 relevante (20 kerne, 23 kvantebaseret, 59 perifere) |
| KU, AU, SDU, AAU | – | – |

Vedligeholdes af Dansk Fysisk Selskab.
