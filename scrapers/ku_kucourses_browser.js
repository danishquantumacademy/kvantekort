// KU SCIENCE harvester via kucourses.dk (student-run mirror of kurser.ku.dk). Run in the browser console on https://kucourses.dk/
// The site stores course overviews in IndexedDB (KUCoursesDB/courses); full course data is served as SvelteKit
// __data.json per course in "devalue" format, decoded below. Temporary source while kurser.ku.dk is unavailable.
(async () => {
  const STRONG = /quantum|qubit|kvante|entangl|sammenfiltr|superposition|schr[öo]dinger|wave ?function|bølgefunktion|bell inequal|post-quantum/gi;
  const MEDIUM = /hamiltonian|\bspin|photon|foton|coheren|kohæren|superconduct|superled|tunnel|density functional|\bdft\b|band structure|båndstruktur|electronic structure|elektronstruktur|\batom|laser|cryptograph|kryptogra|semiconductor|halvleder|nanofab|cryogen|optic|optik|plasmon|polariton/gi;
  const decode = arr => { const memo = {}; const h = i => { if (typeof i !== 'number') return i; if (i < 0) return undefined; if (i in memo) return memo[i]; const v = arr[i];
    if (Array.isArray(v)) { const o = []; memo[i] = o; v.forEach(x => o.push(h(x))); return o; }
    if (v && typeof v === 'object') { const o = {}; memo[i] = o; for (const [k, x] of Object.entries(v)) o[k] = h(x); return o; } return v; }; return h(0); };
  const strip = s => (s || '').replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9]+;/g, ' ').replace(/\s+/g, ' ');
  const db = await new Promise((res, rej) => { const r = indexedDB.open('KUCoursesDB'); r.onsuccess = () => res(r.result); r.onerror = rej; });
  const overviews = await new Promise(res => { const q = db.transaction('courses').objectStore('courses').getAll(); q.onsuccess = () => res(q.result); });
  const out = []; let i = 0;
  await Promise.all(Array.from({ length: 8 }, async () => {
    while (i < overviews.length) {
      const id = overviews[i++].id;
      try {
        const j = await fetch(`/course/${id}/__data.json`).then(r => r.json());
        const c = decode(j.nodes[1].data).course;
        const body = strip(c.content) + ' ' + strip(c['learning-outcome']);
        const s = (body.match(STRONG) || []).map(z => z.toLowerCase()), m = (body.match(MEDIUM) || []).map(z => z.toLowerCase());
        out.push({ institution: 'KU', code: id, title: c.title, level: (c.degree || []).map(x => x.type === 'Master' ? 'MSc' : 'BSc').join('/'),
          ects: c.ects, department: (c.department || []).map(x => x.name), language: (c.language || []).map(x => x.name),
          coordinators: c.coordinator || [], kw_strong: s.length, kw_medium: m.length, kw_terms: [...new Set([...s, ...m])],
          objective: strip(c.content).slice(0, 400), url: `https://kucourses.dk/course/${id}`, harvested: new Date().toISOString().slice(0, 10) });
      } catch (e) { /* skip */ }
    }
  }));
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'ku_courses.json' }).click();
  console.log(`Harvested ${out.length} KU courses`);
})();
