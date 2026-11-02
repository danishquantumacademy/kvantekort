// DTU kursushøster – køres i browserkonsollen på https://kurser.dtu.dk/
// (siden er JavaScript-renderet og blokerer mange servere, så høstningen sker i browseren).
//
// 1. Åbn https://kurser.dtu.dk/search i Chrome
// 2. Indsæt hele scriptet i DevTools-konsollen
// 3. Når det er færdigt, downloades dtu_courses.json automatisk
//
// Output: én række pr. (niveau, kursuskode) med titel, sprog, ECTS, skema, institut,
// dansk titel, kursusformål (uddrag) og nøgleordstællinger til kvanterelevans.

(async () => {
  const LEVELS = { BSC: 'BSc', MSC: 'MSc', PHD: 'PhD' };
  const STRONG = /quantum|qubit|kvante|entangl|superposition|schr[öo]dinger|wave ?function|bell inequal|post-quantum/gi;
  const MEDIUM = /hamiltonian|\bspin|photon|coheren|superconduct|tunnel|density functional|\bdft\b|band structure|electronic structure|atomic|laser|cryptograph|semiconductor|nanofab|cryogen|optic/gi;

  const rows = [];
  for (const [key, label] of Object.entries(LEVELS)) {
    const html = await fetch(`/search?CourseCode=&SearchKeyword=&CourseType=DTU_${key}&TeachingLanguage=`).then(r => r.text());
    const doc = new DOMParser().parseFromString(html, 'text/html');
    let dept = '';
    for (const tr of doc.querySelectorAll('tr')) {
      const a = tr.querySelector('a[href^="/course/"]');
      if (!a) {
        const m = (tr.textContent || '').trim().match(/^(\d{2} .+)$/m);
        if (m) dept = m[1].trim();
        continue;
      }
      const m = a.textContent.trim().match(/^(\w+)\s*-\s*(.+)$/);
      const meta = (tr.querySelector('small')?.textContent || '').replace(/\s+/g, ' ').trim().split('|').map(s => s.trim());
      rows.push({
        institution: 'DTU', level: label,
        code: m ? m[1] : '', title: m ? m[2] : a.textContent.trim(),
        language: meta[0] || '', ects: parseFloat(meta[1]) || null, schedule: meta[3] || '',
        department: dept, url: `https://kurser.dtu.dk/course/${m ? m[1] : ''}`,
      });
    }
  }

  const codes = [...new Set(rows.map(r => r.code))];
  const det = {};
  let i = 0;
  const worker = async () => {
    while (i < codes.length) {
      const c = codes[i++];
      try {
        const html = await fetch('/course/' + c).then(r => r.text());
        const d = new DOMParser().parseFromString(html, 'text/html');
        const t = (d.body.textContent || '').replace(/\s+/g, ' ');
        const a = t.indexOf('General course objectives'), b = t.lastIndexOf('Last updated');
        const body = a >= 0 ? t.slice(a, b > a ? b : undefined) : t;
        const s = (body.match(STRONG) || []).map(x => x.toLowerCase());
        const m = (body.match(MEDIUM) || []).map(x => x.toLowerCase());
        det[c] = {
          title_da: (t.match(/Danish title\s*(.*?)\s*Language of instruction/) || [])[1] || '',
          kw_strong: s.length, kw_medium: m.length,
          kw_terms: [...new Set([...s, ...m])].join(';'),
          objective: body.replace('General course objectives', '').slice(0, 400).trim(),
        };
      } catch (e) { det[c] = { error: String(e) }; }
    }
  };
  await Promise.all(Array.from({ length: 8 }, worker));

  const out = rows.map(r => ({ ...r, ...det[r.code], harvested: new Date().toISOString().slice(0, 10) }));
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  const link = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'dtu_courses.json' });
  link.click();
  console.log(`Høstet ${out.length} rækker (${codes.length} unikke kurser)`);
})();
