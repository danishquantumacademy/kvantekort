// SDU kursushøster – køres i browserkonsollen på https://odin.sdu.dk/
// ODIN har ingen samlet liste. Derfor:
//  1) Naturvidenskab: gennemløb interne koder PRÆFIKS001–999 og behold dem, der findes.
//  2) TEK: kurser uden intern kode hentes via fagbeskrivelses-id fra studieordningerne.
// Kun kursusbeskrivelser med status "Approved - active" beholdes.
(async () => {
  const PREFIXES = ['FY', 'FT', 'KE', 'MM', 'DM', 'AI', 'NAT', 'QC'];
  const TEK_STOS = [79152, 79155, 78711, 78712, 79171, 79172, 79291]; // Fysik og Teknologi, Engineering Physics, Elektronik
  const BASE = '/sitecore/index.php?lang=en&';
  const STRONG = /quantum|qubit|kvante|entangl|sammenfiltr|superposition|schr[öo]dinger|wave ?function|bølgefunktion|bell inequal|post-quantum/gi;
  const MEDIUM = /hamiltonian|\bspin|photon|foton|coheren|kohæren|superconduct|superled|tunnel|density functional|\bdft\b|band structure|båndstruktur|electronic structure|elektronstruktur|\batom|laser|cryptograph|kryptogra|semiconductor|halvleder|nanofab|cryogen|optic|optik|plasmon|polariton/gi;
  const lvl = l => /^Bachelor of Engineering/.test(l) ? 'Diplom' : /^Bachelor/.test(l) ? 'BSc' : /^Professional Master/.test(l) ? 'Master' : /^PhD/.test(l) ? 'PhD' : /^Master/.test(l) ? 'MSc' : l;
  const pool = async (items, fn, n = 12) => { let i = 0; await Promise.all(Array.from({ length: n }, async () => { while (i < items.length) await fn(items[i++]); })); };

  const jobs = [];
  for (const p of PREFIXES) for (let i = 1; i < 1000; i++) { const c = p + String(i).padStart(3, '0'); jobs.push({ url: BASE + 'a=searchfagbesk&internkode=' + c }); }
  for (const id of TEK_STOS) {
    const d = new DOMParser().parseFromString(await fetch(BASE + 'a=sto&id=' + id).then(r => r.text()), 'text/html');
    for (const e of d.querySelectorAll('[data-fagbesk-id]')) if (!/^[A-Z]{1,6}\d{3,}\w*:/.test(e.textContent.trim()))
      jobs.push({ url: BASE + 'a=fagbesk&id=' + e.getAttribute('data-fagbesk-id'), fid: e.getAttribute('data-fagbesk-id') });
  }
  const out = {};
  await pool(jobs, async j => {
    const t = await fetch(j.url).then(r => r.text()).catch(() => '');
    if (t.length < 200) return;
    const d = new DOMParser().parseFromString(t, 'text/html');
    d.querySelectorAll('style,script').forEach(e => e.remove());
    const x = d.body.textContent.replace(/\s+/g, ' ');
    if (!/Approved - active/.test(x.slice(0, 160))) return;
    const g = re => (x.match(re) || [])[1] || '';
    const a = x.search(/Course introduction|Learning outcome|Content|Purpose/);
    const body = x.slice(a > 0 ? a : 300);
    const s = (body.match(STRONG) || []).map(z => z.toLowerCase()), m = (body.match(MEDIUM) || []).map(z => z.toLowerCase());
    const level = g(/Level: (.*?) (?:STADS|ECTS)/);
    const code = g(/^\s*([A-Z]{1,6}\d{3,}\w*):/) || (level.match(/Course ID: (\w+)/) || [])[1] || g(/STADS ID \(UVA\): (\S+)/);
    out[code] ||= {
      institution: 'SDU', code, level: lvl(level), phd_approved: /approved as PhD/.test(level),
      title: g(/^\s*(?:[A-Z]{1,6}\d{3,}\w*: )?(.*?) \|/).trim(), ects: parseFloat(g(/ECTS value: ([\d.,]+)/).replace(',', '.')) || null,
      language: g(/Teaching language: (.*?)(?: EKA| Assessment)/), board: g(/(Study Board[^:]*?|Academic Study Board[^:]*?) (?:Teaching language|Programme)/),
      kw_strong: s.length, kw_medium: m.length, kw_terms: [...new Set([...s, ...m])], objective: body.slice(0, 400),
      url: j.fid ? `https://odin.sdu.dk/sitecore/index.php?a=fagbesk&id=${j.fid}&lang=en` : `https://odinlister.sdu.dk/fagbesk/internkode/${code}/en`,
      harvested: new Date().toISOString().slice(0, 10),
    };
  });
  const list = Object.values(out);
  const blob = new Blob([JSON.stringify(list, null, 1)], { type: 'application/json' });
  Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'sdu_courses.json' }).click();
  console.log(`Høstet ${list.length} aktive SDU-kurser`);
})();
