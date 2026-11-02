// AAU modulhøster – køres i browserkonsollen på https://moduler.aau.dk/
// Søgningen "a" returnerer hele kataloget (alle år); vi beholder 2026/27 og henter hver modulside.
// Faktaboksen er en tabel (etiket/værdi). Kun ENG- og TECH-fakulteterne beholdes. Tager ca. 8 min.
(async () => {
  const YEAR = '2026-2027';
  const KEEP = /Ingeniør- og Naturvidenskabelige|Engineering and Science|Tekniske Fakultet for IT|Technical Faculty of IT/;
  const STRONG = /quantum|qubit|kvante|entangl|sammenfiltr|superposition|schr[öo]dinger|wave ?function|bølgefunktion|bell inequal|post-quantum/gi;
  const MEDIUM = /hamiltonian|\bspin|photon|foton|coheren|kohæren|superconduct|superled|tunnel|density functional|\bdft\b|band structure|båndstruktur|electronic structure|elektronstruktur|\batom|laser|cryptograph|kryptogra|semiconductor|halvleder|nanofab|cryogen|optic|optik|plasmon|polariton/gi;
  const levelFromProg = p => /ph\.?\s?d/i.test(p) ? 'PhD' : /Diplomingeniør|Bachelor of Engineering/i.test(p) ? 'Diplom' : /^Bachelor|Bachelor of Science|bacheloruddannelse/i.test(p) ? 'BSc' : /Kandidat|Master of Science|civilingeniør/i.test(p) ? 'MSc' : /^Master/i.test(p) ? 'Master' : '';
  const levelFromCode = c => { const m = c.match(/-([BKD])\d/) || c.match(/([BKD])\d[KP]\d+$/); return m ? ({ B: 'BSc', K: 'MSc', D: 'Diplom' })[m[1]] : 'Ukendt'; };
  const html = await fetch('/search?Term=a').then(r => r.text());
  const hrefs = [...new Set(html.match(new RegExp(`/course/${YEAR}/[^"'?#\\s<>]+`, 'g')) || [])];
  const out = []; let i = 0;
  await Promise.all(Array.from({ length: 12 }, async () => {
    while (i < hrefs.length) {
      const h = hrefs[i++];
      try {
        const d = new DOMParser().parseFromString(await fetch(h).then(r => r.text()), 'text/html');
        const facts = {};
        d.querySelectorAll('tr').forEach(tr => { const c = tr.children; if (c.length >= 2) { const k = c[0].textContent.replace(/\s+/g, ' ').trim(); if (!(k in facts)) facts[k] = c[1].textContent.replace(/\s+/g, ' ').trim(); } });
        const faculty = facts['Faculty'] || facts['Fakultet'] || '';
        if (!KEEP.test(faculty)) continue;
        d.querySelectorAll('script,style').forEach(e => e.remove());
        const x = d.body.textContent.replace(/\s+/g, ' ');
        const a = x.search(/Content, progress|Indhold, forløb/), b = x.search(/Name of exam|Prøvens navn/);
        const body = x.slice(a > 0 ? a : 0, b > a ? b : undefined);
        const s = (body.match(STRONG) || []).map(z => z.toLowerCase()), m = (body.match(MEDIUM) || []).map(z => z.toLowerCase());
        const code = h.split('/').pop(); const prog = facts['Education owner'] || facts['Uddannelsesejer'] || '';
        const title = [...d.querySelectorAll('h1')].map(e => e.textContent.trim()).find(t => t && t !== 'AAU Moduler' && !/^\d{4}\/\d{4}$/.test(t)) || '';
        out.push({ institution: 'AAU', code, title, title_da: facts['Danish title'] || '', level: levelFromProg(prog) || levelFromCode(code),
          module_type: facts['Module type'] || facts['Modultype'] || '', ects: parseFloat(facts['ECTS']) || null,
          language: facts['Language of instruction'] || facts['Undervisningssprog'] || '', programme: prog,
          department: facts['Department'] || facts['Institut'] || '', faculty,
          kw_strong: s.length, kw_medium: m.length, kw_terms: [...new Set([...s, ...m])], objective: body.slice(0, 400),
          url: 'https://moduler.aau.dk' + h, harvested: new Date().toISOString().slice(0, 10) });
      } catch (e) { /* spring over */ }
    }
  }));
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'aau_courses.json' }).click();
  console.log(`Høstet ${out.length} AAU-moduler (ENG + TECH)`);
})();
