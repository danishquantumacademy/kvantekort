// Turns the front-page design (design/Main.dc.html, design/Portal.dc.html, made on the Claude design canvas)
// into plain HTML templates for the site: site/home_template.html and site/portal_template.html.
// The design files hold markup with {{ holes }}, <sc-for>/<sc-if> and a small Component class; this script runs the
// class in a browser, fills the markup for each state the page needs, and adds a few lines of plain JavaScript for the
// interactive parts (explanation depth, count-up numbers, role tabs). Numbers are left as %%TOKENS%% that
// scripts/build_site.py fills from the data.
// Run locally after changing the design:  node scripts/render_design.js   (needs Playwright with Chromium)
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');

function parts(file) {
  const s = fs.readFileSync(path.join(ROOT, 'design', file), 'utf8');
  const helmet = s.match(/<helmet>([\s\S]*?)<\/helmet>/)[1];
  const body = s.match(/<x-dc>([\s\S]*?)<\/x-dc>/)[1].replace(/<helmet>[\s\S]*?<\/helmet>/, '');
  const script = s.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)[1];
  const title = s.match(/<title>([\s\S]*?)<\/title>/)[1];
  return { helmet, body, script, title };
}

function must(s, a, b) {
  if (!s.includes(a)) throw new Error('design changed, text not found: ' + a.slice(0, 80));
  return s.split(a).join(b);
}

// runs in the browser: fills the markup with the values from renderVals() for the given state
function renderInPage({ markup, script, state }) {
  class DCLogic { constructor(props) { this.props = props || {}; this.state = {}; } setState(s) { Object.assign(this.state, s); } }
  const Component = new Function('DCLogic', script + '\nreturn Component;')(DCLogic);
  const c = new Component({});
  Object.assign(c.state, state);
  const vals = c.renderVals();
  const get = (scope, p) => p.trim().split('.').reduce((o, k) => (o == null ? undefined : o[k]), scope);
  const HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;
  const fill = (str, scope) => str.replace(HOLE, (_, p) => { const v = get(scope, p); return v == null ? '' : String(v); });
  function walk(node, scope) {
    for (const ch of [...node.childNodes]) {
      if (ch.nodeType === 3) { if (HOLE.test(ch.data)) { HOLE.lastIndex = 0; ch.data = fill(ch.data, scope); } HOLE.lastIndex = 0; continue; }
      if (ch.nodeType !== 1) continue;
      const tag = ch.tagName.toLowerCase();
      if (tag === 'sc-for') {
        const list = get(scope, ch.getAttribute('list').replace(/[{}]/g, '')) || [];
        const as = ch.getAttribute('as');
        list.forEach((item) => {
          const frag = document.createDocumentFragment();
          [...ch.childNodes].forEach((n) => frag.appendChild(n.cloneNode(true)));
          const box = document.createElement('div'); box.appendChild(frag);
          walk(box, { ...scope, [as]: item });
          [...box.childNodes].forEach((n) => ch.parentNode.insertBefore(n, ch));
        });
        ch.remove();
        continue;
      }
      if (tag === 'sc-if') {
        const v = get(scope, ch.getAttribute('value').replace(/[{}]/g, ''));
        if (v) { walk(ch, scope); [...ch.childNodes].forEach((n) => ch.parentNode.insertBefore(n, ch)); }
        ch.remove();
        continue;
      }
      for (const a of [...ch.attributes]) {
        if (a.name.startsWith('hint-')) { ch.removeAttribute(a.name); continue; }
        if (!a.value.includes('{{')) continue;
        const m = a.value.match(/^\{\{\s*([^}]+?)\s*\}\}$/);
        if (m && typeof get(scope, m[1]) === 'function') { ch.removeAttribute(a.name); ch.setAttribute('data-on', m[1]); continue; }
        ch.setAttribute(a.name, fill(a.value, scope));
      }
      walk(ch, scope);
    }
  }
  const t = document.createElement('template');
  t.innerHTML = markup;
  const box = document.createElement('div');
  box.appendChild(t.content.cloneNode(true));
  walk(box, vals);
  return box.innerHTML;
}

const BASE_CSS = `
html{scroll-behavior:smooth}
[hidden]{display:none!important}
a:focus-visible,button:focus-visible{outline:2px solid #7b9bff;outline-offset:3px}
@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto}}
@media (max-width:700px){
  h1{font-size:36px!important}
  h2{font-size:28px!important}
  section>div,main{padding-left:16px!important;padding-right:16px!important}
  section>div{padding-top:56px!important;padding-bottom:56px!important}
  header>div{padding-left:16px!important;padding-right:16px!important}
  header a>span+span{display:none}
  #top div[style*="height: 1200px"]{opacity:.3}
}`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const render = (markup, script, state) => page.evaluate(renderInPage, { markup, script, state });

  // ---------- public front page ----------
  const M = parts('Main.dc.html');
  let mBody = M.body;
  for (const [hole, tok] of [['n.courses', 'COURSES'], ['n.groups', 'GROUPS'], ['n.positions', 'POSITIONS'], ['n.orgs', 'ORGS']])
    mBody = must(mBody, `>{{ ${hole} }}<`, `><span data-count>%%${tok}%%</span><`);
  mBody = must(mBody, 'research groups, 662 members', 'research groups, %%MEMBERS%% members');
  let simple = await render(mBody, M.script, { deep: false, k: 1 });
  const deep = await render(mBody, M.script, { deep: true, k: 1 });
  // the two depths differ only in the card texts: keep one set of cards and swap the texts in the browser
  const texts = await page.evaluate(({ a, b }) => {
    const pick = (h) => { const d = document.createElement('div'); d.innerHTML = h;
      return [...d.querySelectorAll('#learn article')].map((ar) => [...ar.querySelectorAll(':scope > span, :scope > h3, :scope > p')].map((e) => e.textContent)); };
    return { simple: pick(a), deep: pick(b) };
  }, { a: simple, b: deep });
  let home = simple;
  home = must(home, 'href="Portal.dc.html"', 'href="portal.html"');
  home = must(home, '<a href="#about">About the data</a>', '<a href="about.html">About the data</a>');
  home = must(home, '<a href="#about">Contact</a>', '<a href="https://danishquantumacademy.dk">Danish Quantum Academy</a>');
  home = must(home, '<a href="#about">Request access from Danish Quantum Academy</a>', '<a href="https://danishquantumacademy.dk">Request access from Danish Quantum Academy</a>');
  const homeJs = `<script>
(function(){
  // old links to the proficiency triangle (index.html?inst=…&levels=…) open the triangle page
  if (location.search && !/staticrypt/.test(location.search)) { location.replace('proficiency.html' + location.search + location.hash); return; }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  // explanation depth
  var bs = document.querySelector('[data-on="setSimple"]'), bd = document.querySelector('[data-on="setDeep"]');
  var on = bs.getAttribute('style'), off = bd.getAttribute('style');
  var T = ${JSON.stringify(texts)};
  var cards = [].slice.call(document.querySelectorAll('#learn article'));
  function depth(d){ cards.forEach(function(ar, i){ [].slice.call(ar.querySelectorAll(':scope > span, :scope > h3, :scope > p')).forEach(function(e, j){ e.textContent = T[d ? 'deep' : 'simple'][i][j]; }); });
    bs.setAttribute('style', d ? off : on); bd.setAttribute('style', d ? on : off);
    bs.setAttribute('aria-pressed', String(!d)); bd.setAttribute('aria-pressed', String(d)); }
  bs.addEventListener('click', function(){ depth(false); }); bd.addEventListener('click', function(){ depth(true); }); depth(false);
  // numbers count up when the section comes into view
  var nums = [].slice.call(document.querySelectorAll('[data-count]'));
  if (reduce || !('IntersectionObserver' in window)) return;
  nums.forEach(function(el){ el.dataset.n = el.textContent; el.textContent = '0'; });
  var io = new IntersectionObserver(function(es){ es.forEach(function(e){ if (!e.isIntersecting) return; io.disconnect();
    var t0 = performance.now();
    (function step(t){ var k = Math.min(1, (t - t0) / 1600), q = 1 - Math.pow(1 - k, 3);
      nums.forEach(function(el){ el.textContent = String(Math.round(+el.dataset.n * q)); });
      if (k < 1) requestAnimationFrame(step); })(t0); }); }, { threshold: .3 });
  io.observe(nums[0].closest('section'));
})();
</script>`;

  // ---------- logged-in page (role tabs) ----------
  const P = parts('Portal.dc.html');
  let pScript = P.script;
  pScript = must(pScript, "'288 quantum courses", "'%%COURSES%% quantum courses");
  pScript = must(pScript, "'509 positions", "'%%POSITIONS%% positions");
  pScript = must(pScript, "'23 groups and 662 members", "'%%GROUPS%% groups and %%MEMBERS%% members");
  pScript = must(pScript, "'87 organisations, 73 of them", "'%%ORGS%% organisations, %%ORGS_TRI%% of them");
  const roles = ['student', 'researcher', 'industry'];
  const pv = [];
  for (const r of roles) pv.push(await render(P.body, pScript, { role: r }));
  let portal = await page.evaluate(({ pv, roles }) => {
    const box = document.createElement('div'); box.innerHTML = pv[0];
    const main0 = box.querySelector('main');
    roles.forEach((r, i) => {
      const B = document.createElement('div'); B.innerHTML = pv[i];
      const m = B.querySelector('main'); m.setAttribute('data-role', r); if (i) m.hidden = true;
      m.querySelectorAll('[data-on="r.pick"]').forEach((b, j) => { b.removeAttribute('data-on'); b.setAttribute('data-pick', roles[j]); b.setAttribute('aria-pressed', String(j === i)); });
      main0.parentNode.insertBefore(m, main0);
    });
    main0.remove();
    return box.innerHTML;
  }, { pv, roles });
  const LINK = { 'Courses and triangles': 'proficiency.html', 'Study planner': 'planner.html', 'PhD and postdoc projects': 'proficiency.html?levels=PHDP,PDP',
    'Research groups': 'groups.html', 'Educators': 'people.html', 'Companies and organisations': 'industry.html', 'Job-ad demand': 'industry.html', 'Events': 'events.html' };
  portal = portal.replace(/<a href="#open"([^>]*)>(\s*<span[^>]*>)([^<]+)</g, (m, a, s, title) => {
    if (!LINK[title]) throw new Error('no link for tile ' + title);
    return `<a href="${LINK[title]}"${a}>${s}${title}<`;
  });
  portal = must(portal, '<a href="#open"', '<a href="proficiency.html"');
  portal = must(portal, '<a href="Main.dc.html" style="display: flex', '<a href="index.html" style="display: flex');
  portal = must(portal, '<a href="Main.dc.html" style="color: #141a2b; text-decoration: none">Public front page</a>', '<a href="index.html" style="color: #141a2b; text-decoration: none">Front page</a>');
  portal = must(portal, '<a href="Main.dc.html" style="display: inline-flex', '<a href="portal.html?staticrypt_logout" style="display: inline-flex');
  if (/Main\.dc\.html|Portal\.dc\.html|#open"/.test(portal + home)) throw new Error('design link left over');
  const portalJs = `<script>
(function(){
  var mains = [].slice.call(document.querySelectorAll('main[data-role]'));
  function show(r, focus){ mains.forEach(function(m){ m.hidden = m.getAttribute('data-role') !== r; });
    try { localStorage.setItem('dqa-role', r); } catch (e) {}
    if (focus) { var b = document.querySelector('main[data-role="' + r + '"] [data-pick="' + r + '"]'); if (b) b.focus(); } }
  document.addEventListener('click', function(e){ var b = e.target.closest('[data-pick]'); if (b) show(b.getAttribute('data-pick'), true); });
  var r = null; try { r = localStorage.getItem('dqa-role'); } catch (e) {}
  if (r && document.querySelector('main[data-role="' + r + '"]')) show(r, false);
})();
</script>`;

  const doc = (title, helmet, body, js) => `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${title}</title>
${helmet.trim().replace('</style>', BASE_CSS + '\n</style>')}
</head>
<body>
<!-- made from design/${title.includes('logged') ? 'Portal' : 'Main'}.dc.html by scripts/render_design.js; edit the design, not this file -->
${body.trim()}
${js}
</body>
</html>
`;
  fs.writeFileSync(path.join(ROOT, 'site/home_template.html'), doc('Quantum Denmark – Danish Quantum Academy', M.helmet, home, homeJs));
  fs.writeFileSync(path.join(ROOT, 'site/portal_template.html'), doc('Quantum Denmark – logged in', P.helmet, portal, portalJs));
  await browser.close();
  console.log('wrote site/home_template.html and site/portal_template.html');
})().catch((e) => { console.error(e); process.exit(1); });
