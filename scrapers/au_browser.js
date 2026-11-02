// AU kursushøster – køres i browserkonsollen på https://kursuskatalog.au.dk/
// Kataloget har et JSON-API (/api/courses/) som returnerer kurser inkl. beskrivelser,
// så der skal ikke åbnes enkeltsider. Ph.d.-kurser findes ikke i dette katalog.
(async () => {
  const YEAR = '2026^2027';
  const FACULTIES = ['Natural Sciences', 'Technical Sciences'];
  const STRONG = /quantum|qubit|kvante|entangl|sammenfiltr|superposition|schr[öo]dinger|wave ?function|bølgefunktion|bell inequal|post-quantum/gi;
  const MEDIUM = /hamiltonian|\bspin|photon|foton|coheren|kohæren|superconduct|superled|tunnel|density functional|\bdft\b|band structure|båndstruktur|electronic structure|elektronstruktur|\batom|laser|cryptograph|kryptogra|semiconductor|halvleder|nanofab|cryogen|optic|optik/gi;
  const LEVEL = { Bachelor: 'BSc', Kandidat: 'MSc', Master: 'Master', Professionsbachelorer: 'Diplom' };
  const strip = h => (typeof h === 'string' ? h : JSON.stringify(h || '')).replace(/<[^>]+>/g, ' ').replace(/&nbsp;|\\n/g, ' ').replace(/\s+/g, ' ');
  const byCode = {};
  for (const fac of FACULTIES) {
    const url = `/api/courses/?presentationLanguage=da&limit=5000&year=${YEAR}&faculty=${encodeURIComponent(fac)}&sortBy=name&sortOrder=ascending`;
    const { courses } = await fetch(url).then(r => r.json());
    for (const c of courses) {
      const text = strip((c.courseDescriptionOfQualifications || []).map(x => x.description).join(' ')) + ' ' + strip(c.courseObjective) + ' ' + strip(c.syllabus);
      const s = (text.match(STRONG) || []).map(x => x.toLowerCase());
      const m = (text.match(MEDIUM) || []).map(x => x.toLowerCase());
      const r = byCode[c.courseCode] ||= {
        institution: 'AU', level: LEVEL[c.courseLevel] || c.courseLevel, code: c.courseCode, ref: c.courseId,
        title: c.name, ects: c.ects, department: (c.department || {}).name || '', faculty: c.faculty,
        periods: [], programmes: [], kw_strong: 0, kw_medium: 0, kw_terms: [], objective: '',
        url: `https://kursuskatalog.au.dk/da/course/${c.courseId}`,
      };
      r.periods.push(c.period); r.programmes.push(c.programme);
      if (s.length > r.kw_strong) { r.kw_strong = s.length; r.objective = text.slice(0, 400).trim(); }
      r.kw_medium = Math.max(r.kw_medium, m.length);
      r.kw_terms = [...new Set([...r.kw_terms, ...s, ...m])];
    }
  }
  const out = Object.values(byCode).map(r => ({ ...r, periods: [...new Set(r.periods)], programmes: [...new Set(r.programmes)], harvested: new Date().toISOString().slice(0, 10) }));
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'au_courses.json' }).click();
  console.log(`Høstet ${out.length} unikke AU-kurser`);
})();
