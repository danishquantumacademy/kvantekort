// Publication check, browser part (run once a semester, or when a researcher asks).
// Used for QMATH on 11 November 2026. Output goes to data/groups/pubcheck/<key>_raw.txt; scripts/build_pubcheck.py does the rest.
// Only public, professional information is read: profile path, ORCID iD and research output titles. No e-mail or phone.
//
// Step 1 – on researchprofiles.ku.dk (the portal's bot check must have passed in this tab).
//   M = [[name, profile path or ""], ...] from data/groups/<key>.txt (administrative staff left out).
//   For each member: find the profile by name if no path is known, read /publications/?page=N until output
//   from before 2021 appears, and take the ORCID link on the profile.
async function portal(M) {
  const nz = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z ]/g, '');
  const dp = h => new DOMParser().parseFromString(h, 'text/html');
  async function find(name) {
    const parts = nz(name).split(' '), last = parts.at(-1), first = parts[0];
    for (const q of [name, last]) {
      const d = dp(await (await fetch('/en/persons/?search=' + encodeURIComponent(q))).text());
      const a = [...d.querySelectorAll('.result-container h3 a')].find(a => { const t = nz(a.textContent); return t.split(' ').includes(last) && t.startsWith(first) });
      if (a) return new URL(a.href, location.origin).pathname;
    }
    return '';
  }
  const out = [];
  for (const [name, known] of M) {
    const r = { n: name, p: known || await find(name), o: '', pubs: [] };
    if (r.p) {
      r.p = r.p.replace(/\/$/, '') + '/';
      for (let page = 0, done = false; !done && page < 8; page++) {
        const d = dp(await (await fetch(r.p + 'publications/?page=' + page)).text());
        if (page === 0) { const o = d.querySelector('a[href*="orcid.org/"]'); if (o) r.o = o.href.split('orcid.org/')[1].replace(/\/$/, '') }
        const res = [...d.querySelectorAll('.result-container')]; if (!res.length) break;
        for (const x of res) {
          const a = x.querySelector('h3 a'); if (!a) continue;
          const t = x.textContent.replace(/\s+/g, ' '), after = t.slice(t.indexOf(a.textContent.trim().slice(-20)) + 20);
          const y = (after.match(/,\s(?:\d{1,2}\s)?(?:[A-Z][a-z]{2,8}\.?\s)?((?:19|20)\d\d)\b/) || ['', ''])[1];
          if (y && +y < 2021) { done = true; break }
          const ty = (t.match(/Research output: (.*?)(?= Open Access| File| \d+ Downloads|$)/) || ['', ''])[1].split(' › ');
          r.pubs.push([y, a.textContent.trim(), ty[1] || ty[0], ty[2] || '']);
        }
      }
    }
    out.push(r);
  }
  window.name = 'DQA' + JSON.stringify(out); // survives the move to api.openalex.org in the same tab
  return out.length;
}
// Step 2 – navigate the same tab to https://api.openalex.org/ (the portal's security policy blocks other hosts).
//   For each member: the OpenAlex author from the ORCID iD, or from the name when it gives one author;
//   works from 2021 on (/works?filter=author.id:A…,from_publication_date:2021-01-01), and the ORCID record
//   (https://pub.orcid.org/v3.0/<iD>/works). Works are matched by title; editorials, society letters,
//   corrections, newspaper pieces, data sets and code are flagged as non-research. The result is written in the
//   raw format described in scripts/build_pubcheck.py.
