// kurser.ku.dk – KU's official course catalogue, Faculty of SCIENCE, volume 2026/2027.
// Run in the browser console on a kurser.ku.dk search page that lists all SCIENCE courses, e.g.
//   https://kurser.ku.dk/search?programme=&volume=2026/2027&searchText=&faculty=FACULTY_0005
// (the page lists 969 courses). Used on 10 November 2026 to check the courses first read from the
// mirror kucourses.dk and to search every course page again for quantum content.
// Only public course information is read: title, ECTS, language, level, course coordinators (names only).
(async () => {
  const c = s => (s || '').replace(/\s+/g, ' ').trim();
  const all = [...document.querySelectorAll('a[href*="/course/"]')].map(a => {
    const tds = [...a.closest('tr').querySelectorAll('td')].map(t => c(t.textContent));
    return { href: a.getAttribute('href'), title: c(a.textContent), level: tds[3] || '', lang: tds[5] || '' };
  });
  const QUANTUM = /quantum|kvante|qubit|entangle|superposition|schrödinger|hilbert space|bell inequalit|photon statistic|superconduct|post-quantum|kvantemekan/gi;
  const rows = [];
  let i = 0;
  await Promise.all(Array.from({ length: 6 }, async () => {
    while (i < all.length) {
      const x = all[i++];
      const d = new DOMParser().parseFromString(await (await fetch(x.href)).text(), 'text/html');
      const text = c((d.querySelector('main') || d.body).textContent);
      const info = {};
      [...d.querySelectorAll('dt')].forEach(dt => { const k = c(dt.textContent); if (!(k in info)) info[k] = c(dt.nextElementSibling?.textContent); });
      const coord = ((text.match(/(?:Course Coordinators?|Kursusansvarlige?)\s*(.*?)\s*(?:Saved on|Gemt den)/) || [])[1] || '')
        .replace(/\([^)]*\)/g, ';').replace(/(Phone|Telefon):?\s*[\d ]+/g, '').replace(/(Lecturers|Undervisere|These two).*/, '')
        .replace(/\s*;\s*/g, '; ').replace(/;\s*$/, '');  // names only, e-mail addresses removed
      const hits = (text.match(QUANTUM) || []).length;
      rows.push([x.href.split('/')[2].toUpperCase(), x.level, x.title, (info['Credit'] || info['Point'] || '').replace(' ECTS', ''),
                 info['Language'] || info['Sprog'] || '', coord, hits].join('\t'));
    }
  }));
  console.log('code\tlevel\ttitle\tects\tlanguage\tcoordinators\tquantum_terms\n' + rows.join('\n'));
})();
