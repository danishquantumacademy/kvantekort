// Ph.d.-kursushøster – køres i browserkonsollen på https://phdcourses.dk/
// Paginerer universitetets kursusliste (10 pr. side) og henter hver kursusside.
// Beholder kurser med dato i 2026/27 eller uden dato, ekskl. arkiverede "(Gl. ...)"-kurser.
(async () => {
  const UNI = { 4: 'DTU', 6: 'KU', 7: 'SDU', 8: 'AAU', 10: 'AU' };
  const STRONG = /quantum|qubit|kvante|entangl|superposition|schr[öo]dinger|wave ?function|bell inequal|post-quantum/gi;
  const MEDIUM = /hamiltonian|\bspin|photon|coheren|superconduct|tunnel|density functional|\bdft\b|band structure|electronic structure|\batom|laser|cryptograph|semiconductor|nanofab|cryogen|optic|plasmon|polariton/gi;
  const list = {};
  for (const [id, uni] of Object.entries(UNI)) {
    for (let p = 1; p < 400; p++) {
      const d = new DOMParser().parseFromString(await fetch(`/?page=${p}&currentUniversityId=${id}&currentPhdschoolId=0&currentSearchWord=`).then(r => r.text()), 'text/html');
      const rows = [...d.querySelectorAll('a[href*="/Course/"]')];
      let added = 0;
      for (const a of rows) { const k = a.getAttribute('href').split('/').pop(); if (list[k]) continue; const td = [...a.closest('tr').children].map(c => c.textContent.trim()); list[k] = { id: k, institution: uni, place: td[1], date: td[2], ects: td[3] }; added++; }
      if (!added || ![...d.querySelectorAll('a')].some(a => /Next/.test(a.textContent))) break;
    }
  }
  const ids = Object.keys(list).filter(k => /202[67]/.test(list[k].date) || list[k].date === '-');
  let i = 0;
  await Promise.all(Array.from({ length: 10 }, async () => {
    while (i < ids.length) {
      const k = ids[i++], r = list[k];
      try {
        const d = new DOMParser().parseFromString(await fetch('/Course/' + k).then(x => x.text()), 'text/html');
        d.querySelectorAll('script,style').forEach(e => e.remove());
        const x = d.body.textContent.replace(/\s+/g, ' ');
        const s = (x.match(STRONG) || []).map(z => z.toLowerCase()), m = (x.match(MEDIUM) || []).map(z => z.toLowerCase());
        Object.assign(r, { kw_strong: s.length, kw_medium: m.length, kw_terms: [...new Set([...s, ...m])], url: `https://phdcourses.dk/Course/${k}`, text: x.slice(0, 1500) });
      } catch (e) { /* spring over */ }
    }
  }));
  const out = ids.map(k => list[k]).filter(r => !/\(gl\.|gl\. nat/i.test(r.text || ''));
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'phdcourses.json' }).click();
  console.log(`Høstet ${out.length} aktuelle ph.d.-kurser`);
})();
