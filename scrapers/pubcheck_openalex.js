// Publication check, step 2 (run in a tab on https://api.openalex.org/ after the portal step of pubcheck_browser.js).
// window.name holds the portal result: [{n, p, o, pubs: [[hash, date, "type nr", slug, title], ...]}, ...].
// For each member: the OpenAlex author from the ORCID iD, or else from a name search restricted to the institution
// (ambiguous when more than one author matches); works from 2021 on; the public ORCID record.
// Output (window.DUMP) is the harvest format read by scripts/pubcheck_import.py.
window.thash = t => { t = t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/<[^>]+>/g, '').replace(/[^a-z0-9]/g, '').slice(0, 50); let x = 0x811C9DC5; for (const c of new TextEncoder().encode(t)) { x = Math.imul(x ^ c, 0x01000193) >>> 0 } return x.toString(36) };
window.sleep = ms => new Promise(s => setTimeout(s, ms));
const OATY = { article: 'J 0', preprint: 'P 0', 'book-chapter': 'C 0', book: 'B 0', dissertation: 'T 0', review: 'J 0', letter: 'L 0', report: 'P 0' };
const ORTY = { 'journal-article': 'J 0', preprint: 'P 0', 'conference-paper': 'R 0', 'book-chapter': 'C 0', book: 'B 0', 'dissertation-thesis': 'T 0', 'working-paper': 'P 0', report: 'P 0' };
const clean = t => t.replace(/<[^>]+>/g, '').replace(/[|\n\r]+/g, ' ').replace(/\s+/g, ' ').trim();
window.oaPhase = async (R, inst) => {
  const out = [];
  for (const r of R) {
    let aid = '', amb = 0;
    try {
      if (r.o) { const a = await fetch('https://api.openalex.org/authors/orcid:' + r.o); if (a.ok) aid = (await a.json()).id.split('/').pop() }
      if (!aid) {
        const s = await (await fetch(`https://api.openalex.org/authors?search=${encodeURIComponent(r.n)}&filter=affiliations.institution.id:${inst}&per-page=5`)).json();
        if (s.results.length) { aid = s.results[0].id.split('/').pop(); amb = s.results.length > 1 ? 1 : 0 }
      }
    } catch (e) { }
    const oa = {}, orc = {};
    if (aid) {
      let cur = '*';
      while (cur) {
        const j = await (await fetch(`https://api.openalex.org/works?filter=author.id:${aid},from_publication_date:2021-01-01&per-page=200&cursor=${cur}&select=id,title,publication_date,type`)).json();
        for (const w of j.results) if (w.title) { const h = thash(w.title); if (!oa[h]) oa[h] = { t: clean(w.title), d: w.publication_date || '', ty: OATY[w.type] || 'D 1', id: w.id.split('/W').pop() } }
        cur = j.meta.next_cursor; if (!j.results.length) break;
        await sleep(120);
      }
    }
    if (r.o) {
      try {
        const o = await (await fetch(`https://pub.orcid.org/v3.0/${r.o}/works`, { headers: { Accept: 'application/json' } })).json();
        for (const g of o.group) { const s = g['work-summary'][0]; const y = s['publication-date'] && s['publication-date'].year ? +s['publication-date'].year.value : 0; if (y < 2021) continue; const t = clean(s.title.title.value); const h = thash(t); if (!orc[h]) orc[h] = { t, d: String(y), ty: ORTY[s.type] || 'D 1' } }
      } catch (e) { }
    }
    const L = [`#M|${r.n}|${r.p}|${r.o}|${aid.replace(/^A/, '')}|${amb}`], seen = new Set();
    for (const p of r.pubs) { if (seen.has(p[0])) continue; seen.add(p[0]); L.push(['p', p[0], p[1], p[2], p[3], (oa[p[0]] || {}).id || '', (orc[p[0]] ? 'o' : '') + (oa[p[0]] ? 'a' : ''), p[4]].join('|')) }
    for (const h of new Set([...Object.keys(oa), ...Object.keys(orc)])) {
      if (seen.has(h)) continue; seen.add(h);
      const w = oa[h] || orc[h];
      L.push(['e', h, (oa[h] || {}).d || w.d, w.ty, '', (oa[h] || {}).id || '', (orc[h] ? 'o' : '') + (oa[h] ? 'a' : ''), w.t].join('|'));
    }
    out.push(L.join('\n'));
    await sleep(150);
  }
  window.DUMP = out.join('\n');
  return out.length;
};
