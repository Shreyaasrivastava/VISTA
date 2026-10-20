// UI layer. Talks to the backend only through Api (api.js). Attendee and guest screens use Sample (sample.js).
const $ = id => document.getElementById(id);
const T = ['Normal', 'Caution', 'Warning', 'Critical'];
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const pill = t => `<span class="pill t${t}">${T[t]}</span>`;
const neutral = label => `<span class="pill tn">${esc(label)}</span>`;

const NAV = {
  admin: [['overview', 'Overview'], ['zones', 'Live zones'], ['cameras', 'Cameras'], ['thresholds', 'Thresholds'], ['guide', 'Camera setup guide']],
  security: [['alerts', 'Alerts'], ['status', 'Zone status']],
  attendee: [['register', 'Register'], ['ticket', 'My ticket'], ['venues', 'Venue crowding']],
  public: [['venues', 'Venue crowding'], ['location', 'Location alerts']],
};
const EMPTY_TICKET = '<div class="empty">You have not registered yet.<br><button class="btn ghost" type="button" data-go="register" style="margin-top:10px">Go to registration</button></div>';
const DEFAULT_TITLE = document.title;
const FRESH_MS = 30000;          // a reading older than this is "stale"
const POLL_MS = 2000;
const LIVE_PAGES = { admin: ['overview', 'zones'], security: ['status'] };

const S = { user: null, venue: null, cameras: [], latest: [] };
let cur = '', page = '', geo = false, editing = null, pollTimer = null, polling = false;

// ---------- small helpers ----------
const ageMs = r => (r ? Date.now() - Date.parse(r.ts) : Infinity);
function ageText(ms) {
  const s = Math.round(ms / 1000);
  if (s < 5) return 'just now';
  if (s < 60) return `${s} s ago`;
  const m = Math.round(s / 60);
  return m < 60 ? `${m} min ago` : `${Math.round(m / 60)} h ago`;
}
const showErr = msg => { const b = $('apierr'); b.textContent = msg || ''; b.hidden = !msg; };
const maskUrl = u => u.replace(/\/\/([^/@\s:]+):[^@\s]*@/, '//$1:***@');   // hide camera passwords on screen
const note = (el, cls, text) => { el.innerHTML = `<div class="msg ${cls}" style="margin:0 0 12px">${esc(text)}</div>`; };

// ---------- zone cards from API data ----------
function zoneCardApi(item) {
  const cam = S.cameras.find(c => c.id === item.camera_id);
  const r = item.reading;
  const label = `<div><b>${esc(item.zone_name)}</b><span class="v">${esc(item.code)}</span></div>`;
  if (!r) {
    const why = cam && !cam.calibrated ? 'Not calibrated yet. Add the calibration first.' : 'Waiting for the first reading from the vision service.';
    return `<div class="card zone"><div class="top">${label}${neutral('No data')}</div><p style="margin:10px 0 0;color:var(--mut)">${why}</p></div>`;
  }
  const stale = ageMs(r) > FRESH_MS;
  const o = r.occupancy_pct;
  const area = cam && cam.area_sqm ? ` &middot; ${cam.area_sqm} m&sup2;` : '';
  return `<div class="card zone ${stale ? 'tn' : 't' + r.tier}" style="background:var(--surf)">
   <div class="top">${label}${stale ? neutral('Stale') : pill(r.tier)}</div>
   <div class="big" style="color:var(--ink)">${Math.round(o)}%</div>
   <div class="bar" style="color:inherit" aria-hidden="true"><i style="width:${Math.min(o, 100)}%"></i></div>
   <p style="margin:8px 0 0;color:var(--mut);font-size:14px">${r.people_count} people &middot; ${r.density.toFixed(2)} per m&sup2;${area}</p>
   <p style="margin:4px 0 0;color:var(--mut);font-size:14px">Updated ${ageText(ageMs(r))}${r.degraded ? '. Low confidence reading.' : ''}${stale ? ' Check the camera feed.' : ''}</p></div>`;
}
const zoneCards = () => (S.latest.length ? S.latest.map(zoneCardApi).join('') : '<div class="empty">No cameras at this venue yet. Add one on the Cameras page.</div>');

function renderOverview() {
  const cams = S.cameras;
  const fresh = S.latest.filter(x => x.reading && ageMs(x.reading) <= FRESH_MS);
  const need = fresh.filter(x => x.reading.tier >= 2);
  const uncal = cams.filter(c => !c.calibrated).length;
  const card = (l, v, t) => `<div class="card"><div style="color:var(--mut)">${l}</div><div class="big">${v}</div><p style="margin:4px 0 0;color:var(--mut);font-size:14px">${t}</p></div>`;
  $('ov-cards').innerHTML =
    card('Zones monitored', cams.length, need.length ? `${need.length} at Warning or Critical` : 'None at Warning or Critical') +
    card('Cameras calibrated', `${cams.length - uncal} of ${cams.length}`, uncal ? `${uncal} not calibrated yet` : 'All calibrated') +
    card('Reporting now', `${fresh.length} of ${cams.length}`, 'Readings in the last 30 seconds');
  $('ov-attn').innerHTML = need.length ? need.map(zoneCardApi).join('') : '<div class="empty">No zone is at Warning or Critical right now.</div>';
}
function renderThresholds() {
  $('th-body').innerHTML = S.cameras.length
    ? S.cameras.map(c => `<tr><td>${esc(c.zone_name)}</td><td>${esc(c.code)}</td><td>${c.thresholds.caution} / ${c.thresholds.warning} / ${c.thresholds.critical}</td></tr>`).join('')
    : '<tr><td colspan="3">No cameras yet.</td></tr>';
}
function renderCams() {
  $('cams').innerHTML = S.cameras.length
    ? S.cameras.map(c => `<tr><td>${esc(c.code)}</td><td>${esc(c.zone_name)}</td><td>${esc(maskUrl(c.stream_url))}</td><td>${esc(c.ip_address)}</td><td>${c.range_m} m</td><td>${c.thresholds.caution} / ${c.thresholds.warning} / ${c.thresholds.critical}</td><td><span class="pill ${c.calibrated ? 't0' : 't1'}">${c.calibrated ? 'Calibrated' : 'Not calibrated'}</span></td><td><button class="btn ghost" type="button" data-edit="${c.id}">Edit</button></td></tr>`).join('')
    : '<tr><td colspan="8">No cameras yet for this venue. Use Add camera.</td></tr>';
}

// ---------- sample-data screens (attendee and guest) ----------
function venueList(target, qid) {
  const q = $(qid).value.toLowerCase();
  const m = Sample.V.filter(v => (v.name + v.city).toLowerCase().includes(q));
  $(target).innerHTML = m.length ? m.map(v => { const w = Sample.worst(v); return `<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;align-items:start"><div><b>${esc(v.name)}</b><div style="color:var(--mut);font-size:14px">${esc(v.city)}</div></div>${pill(w.t)}</div>
   <p style="margin:8px 0 0;font-size:14px;color:var(--mut)">Busiest area: ${esc(w.n)} at ${Math.round(Sample.occ(w))}%</p></div>`; }).join('') : '<div class="empty">No venue matches that search. Try a shorter name.</div>';
}

// ---------- render ----------
function render() {
  if (cur === 'admin') { renderOverview(); $('zones').innerHTML = zoneCards(); renderThresholds(); }
  else if (cur === 'security') { $('zones-sec').innerHTML = zoneCards(); }
  else if (cur === 'attendee') venueList('vlist-a', 'qa');
  else if (cur === 'public') {
    venueList('vlist', 'q');
    const p = Sample.V[0].zones[0];
    $('geo').innerHTML = geo ? (p.t >= 2 ? `<div class="msg t${p.t}"><b>${T[p.t]} alert near you.</b> Platform 1 is crowded. Move toward the main concourse and follow staff instructions.</div>` : '<div class="msg t0">You are in Platform 1. No alerts right now.</div>') : '<div class="empty">Location is off. Turn it on to get alerts for the zone you are standing in.</div>';
    $('loc').textContent = geo ? 'Turn location off' : 'Turn location on (demo: Platform 1)';
  }
}

// ---------- loading from the API ----------
async function refresh(which) {
  if (!S.venue) return;
  try {
    if (which === 'both') {
      const [cams, latest] = await Promise.all([Api.cameras(S.venue.id), Api.latest(S.venue.id)]);
      S.cameras = cams; S.latest = latest;
    } else {
      S.latest = await Api.latest(S.venue.id);
    }
    showErr('');
  } catch (err) {
    if (err.status !== 401) showErr(err.message);
  }
  if (!S.user) return;                      // logged out while the request was running
  render();
  if (which === 'both' && cur === 'admin') renderCams();
}
function pollLoop() {
  clearTimeout(pollTimer);
  if (!S.user || !S.venue) return;
  const live = (LIVE_PAGES[cur] || []).includes(page);
  if (live && !document.hidden && !polling) {
    polling = true;
    refresh('latest').finally(() => { polling = false; pollTimer = setTimeout(pollLoop, POLL_MS); });
  } else {
    pollTimer = setTimeout(pollLoop, POLL_MS);
  }
}

// ---------- navigation ----------
function buildNav() {
  $('navlist').innerHTML = NAV[cur].map(x => `<li><a href="#/${x[0]}" data-nav="${x[0]}">${x[1]}</a></li>`).join('');
}
function navigate(p, push) {
  if (!cur || !NAV[cur].some(x => x[0] === p)) return;
  page = p;
  document.querySelectorAll('main > .page').forEach(x => { x.hidden = x.id !== 'p-' + cur + '-' + p; });
  document.querySelectorAll('#navlist a').forEach(a => { if (a.dataset.nav === p) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  document.title = NAV[cur].find(x => x[0] === p)[1] + ' | VISTA Crowd Safety';
  if (push !== false) { try { history.pushState(null, '', '#/' + p); } catch (x) { /* ignore */ } }
  $('sidenav').classList.remove('open'); $('menubtn').setAttribute('aria-expanded', 'false');
  $('keybox').innerHTML = ''; $('cammsg').innerHTML = '';
  render();
  if (cur === 'admin' || cur === 'security') refresh('both');
  const hd = document.querySelector('#p-' + cur + '-' + p + ' .title'); if (hd) hd.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
function go(role, who) {
  cur = role; page = '';
  $('login').hidden = !!role;
  document.querySelectorAll('main > .page').forEach(x => { x.hidden = true; });
  $('who').hidden = !role;
  $('whotxt').textContent = role ? who.header : '';
  $('shell').classList.toggle('has-side', !!role); $('side').hidden = !role;
  $('camform').hidden = true;
  if (role) {
    $('sidewho').textContent = who.name; $('sidesub').textContent = who.sub;
    buildNav();
    navigate(NAV[role][0][0], false);
    try { history.replaceState(null, '', '#/' + NAV[role][0][0]); } catch (x) { /* ignore */ }
    pollLoop();
  } else {
    clearTimeout(pollTimer);
    document.title = DEFAULT_TITLE;
    try { history.replaceState(null, '', location.pathname + location.search); } catch (x) { /* ignore */ }
    window.scrollTo(0, 0); render();
  }
}

// ---------- session ----------
const TOKEN_KEY = 'vista-token';
function saveToken(t) { try { if (t) sessionStorage.setItem(TOKEN_KEY, t); else sessionStorage.removeItem(TOKEN_KEY); } catch (x) { /* ignore */ } }
function loadToken() { try { return sessionStorage.getItem(TOKEN_KEY); } catch (x) { return null; } }

function endSession() {
  Api.setToken(null); saveToken(null);
  S.user = null; S.venue = null; S.cameras = []; S.latest = []; editing = null; geo = false;
  $('reg').reset(); $('regmsg').innerHTML = ''; $('ticket').innerHTML = EMPTY_TICKET;
  $('keybox').innerHTML = ''; $('cammsg').innerHTML = ''; showErr('');
  go('');
}
async function startSession(token) {
  Api.setToken(token);
  const user = await Api.me();
  if (!['admin', 'security', 'attendee'].includes(user.role)) {
    Api.setToken(null);
    throw new Api.ApiError(403, 'This account type has no dashboard yet.');
  }
  let venue = null;
  if (user.role === 'admin' || user.role === 'security') {
    const venues = await Api.venues();
    venue = venues[0] || null;
    if (!venue) { Api.setToken(null); throw new Api.ApiError(403, 'This account is not linked to a venue. Ask the platform admin.'); }
  }
  saveToken(token);
  S.user = user; S.venue = venue;
  const who = user.role === 'attendee'
    ? { header: user.username, name: user.username, sub: 'Registration and tickets' }
    : { header: `${user.username}, ${venue.name}`, name: venue.name, sub: `${user.role === 'admin' ? 'Admin' : 'Security'}: ${user.username}` };
  go(user.role, who);
}
Api.onUnauthorized(() => { endSession(); $('lgmsg').innerHTML = '<div class="msg t1">Your session ended. Log in again.</div>'; });

$('lg').onsubmit = async ev => {
  ev.preventDefault();
  const u = $('un').value.trim(), p = $('pw').value, out = $('lgmsg'), btn = $('lgbtn');
  if (!u || !p) { out.innerHTML = '<div class="msg t3">Enter your username and password.</div>'; return; }
  btn.disabled = true; out.innerHTML = '';
  try {
    const t = await Api.login(u, p);
    await startSession(t.access_token);
    $('lg').reset();
  } catch (err) {
    out.innerHTML = `<div class="msg t3">${esc(err.status === 401 ? 'Username or password is wrong. Check both and try again.' : err.message)}</div>`;
  } finally { btn.disabled = false; }
};
$('guest').onclick = () => go('public', { header: 'Guest', name: 'Guest', sub: 'Read-only' });
$('out').onclick = endSession;

// ---------- cameras (admin) ----------
function showKey(code, key) {
  $('keybox').innerHTML = `<div class="keybox"><b>Ingest key for ${esc(code)}. It is shown only once.</b>
   <p style="margin:6px 0">Copy it now and give it to the vision service as VISTA_CAMERA_KEY. If you lose it, generate a new one.</p>
   <code id="keyval">${esc(key)}</code>
   <div class="row" style="margin:10px 0 0"><button class="btn" type="button" id="keycopy">Copy key</button><span id="keycopied" role="status"></span></div></div>`;
  $('keycopy').onclick = async () => {
    try { await navigator.clipboard.writeText(key); $('keycopied').textContent = 'Copied.'; }
    catch (x) { $('keycopied').textContent = 'Could not copy automatically. Select the key and copy it.'; }
  };
}
function openCam(c) {
  editing = c || null;
  $('cftitle').textContent = c ? `Edit ${c.code}` : 'Add camera';
  $('cfz').value = c ? c.zone_name : '';
  $('cfu').value = c ? c.stream_url : ''; $('cfi').value = c ? c.ip_address : ''; $('cfr').value = c ? c.range_m : 30;
  $('cfc').value = c ? c.thresholds.caution : 50; $('cfw').value = c ? c.thresholds.warning : 75; $('cfk').value = c ? c.thresholds.critical : 90;
  $('cfmsg').innerHTML = ''; $('cammsg').innerHTML = ''; $('keybox').innerHTML = '';
  $('cfextra').hidden = !c;
  $('camform').hidden = false;
  $('camform').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); $('cfz').focus();
}
$('camadd').onclick = () => openCam(null);
$('cfcancel').onclick = () => { $('camform').hidden = true; };
$('cams').onclick = ev => {
  const id = ev.target.dataset && ev.target.dataset.edit; if (!id) return;
  const c = S.cameras.find(x => String(x.id) === id); if (c) openCam(c);
};
$('camform').onsubmit = async ev => {
  ev.preventDefault();
  const f = id => $(id).value.trim(), msg = $('cfmsg'), btn = $('cfsave');
  const bad = t => { msg.innerHTML = `<div class="msg t3">${esc(t)}</div>`; };
  const body = {
    zone_name: f('cfz'), stream_url: f('cfu'), ip_address: f('cfi'), range_m: Number(f('cfr')),
    thresholds: { caution: Number(f('cfc')), warning: Number(f('cfw')), critical: Number(f('cfk')) },
  };
  if (!body.zone_name) return bad('Enter a zone name.');
  if (!/^(rtsp|rtmp|https?):\/\/\S+$/i.test(body.stream_url)) return bad('Stream URL must start with rtsp://, rtmp://, http:// or https://.');
  if (!/^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/.test(body.ip_address)) return bad('Enter a valid IPv4 address, like 10.0.4.21.');
  if (!(body.range_m > 0 && body.range_m <= 200)) return bad('Detection range must be between 1 and 200 metres.');
  const th = body.thresholds;
  if (!(th.caution > 0 && th.caution < th.warning && th.warning < th.critical && th.critical <= 100)) return bad('Thresholds must increase: Caution, then Warning, then Critical, all within 100%.');
  btn.disabled = true; msg.innerHTML = '';
  try {
    if (editing) { await Api.patchCamera(editing.id, body); note($('cammsg'), 't0', 'Camera saved.'); }
    else {
      const c = await Api.createCamera(S.venue.id, body);
      showKey(c.code, c.ingest_key);
      note($('cammsg'), 't1', `${c.code} added. It cannot send readings until it is calibrated (see the Camera setup guide).`);
    }
    $('camform').hidden = true;
    await refresh('both');
  } catch (err) { if (err.status !== 401) bad(err.message); }
  finally { btn.disabled = false; }
};
$('cfkey').onclick = async () => {
  if (!editing || !confirm('Generate a new ingest key? The old key stops working at once.')) return;
  try { const r = await Api.rotateKey(editing.id); showKey(editing.code, r.ingest_key); $('camform').hidden = true; }
  catch (err) { if (err.status !== 401) $('cfmsg').innerHTML = `<div class="msg t3">${esc(err.message)}</div>`; }
};
$('cfdel').onclick = async () => {
  if (!editing || !confirm(`Delete ${editing.code} and all its readings? This cannot be undone.`)) return;
  try { await Api.deleteCamera(editing.id); $('camform').hidden = true; note($('cammsg'), 't0', `${editing.code} deleted.`); editing = null; await refresh('both'); }
  catch (err) { if (err.status !== 401) $('cfmsg').innerHTML = `<div class="msg t3">${esc(err.message)}</div>`; }
};
$('cffile').onchange = async ev => {
  const file = ev.target.files[0]; ev.target.value = '';
  const msg = $('cfmsg'), bad = t => { msg.innerHTML = `<div class="msg t3">${esc(t)}</div>`; };
  if (!file || !editing) return;
  if (file.size > 100000) return bad('That file is too large for a calibration file.');
  let data;
  try { data = JSON.parse(await file.text()); } catch (x) { return bad('That file is not valid JSON.'); }
  const need = ['homography', 'zone_polygon', 'camera_xy'];
  if (need.some(k => !(k in data))) return bad('Use camera_patch.json from calibrate.py. It must contain homography, zone_polygon and camera_xy.');
  const body = { homography: data.homography, zone_polygon: data.zone_polygon, camera_xy: data.camera_xy };
  if (data.range_m !== undefined) body.range_m = data.range_m;
  try { await Api.patchCamera(editing.id, body); $('camform').hidden = true; note($('cammsg'), 't0', `Calibration applied to ${editing.code}.`); await refresh('both'); }
  catch (err) { if (err.status !== 401) bad(err.message); }
};

// ---------- attendee and guest screens (sample data) ----------
$('vn').innerHTML = Sample.V.map(v => `<option value="${v.id}">${esc(v.name)}</option>`).join('');
$('q').oninput = render; $('qa').oninput = render;
$('loc').onclick = () => { geo = !geo; render(); };
$('reg').onsubmit = ev => {
  ev.preventDefault();
  const nm = $('nm').value.trim(), ph = $('ph').value.replace(/\s/g, ''), v = Sample.V.find(x => x.id === $('vn').value);
  const mode = document.querySelector('input[name=mode]:checked').value, msg = $('regmsg');
  const bad = t => { msg.innerHTML = `<div class="msg t3">${esc(t)}</div>`; };
  if (!nm) return bad('Enter your full name.');
  if (!/^\d{10}$/.test(ph)) return bad('Enter a 10-digit phone number.');
  const crit = v.zones.find(z => z.t === 3);
  if (crit) return bad(`Registration for ${v.name} is paused because ${crit.n} is at Critical. Try again in a few minutes.`);
  const id = 'VST-' + Math.random().toString(36).slice(2, 8).toUpperCase();
  msg.innerHTML = ''; $('reg').reset();
  $('ticket').innerHTML = '<div class="msg t0" style="margin:0 0 12px">You are registered (sample ticket).</div>' + Sample.qr(id + nm) +
    `<dl><dt>Name</dt><dd>${esc(nm)}</dd><dt>Venue</dt><dd>${esc(v.name)}</dd><dt>Type</dt><dd>${esc(mode)}</dd><dt>Code</dt><dd>${id}</dd></dl>`;
  navigate('ticket');
};

// ---------- wiring ----------
$('ticket').innerHTML = EMPTY_TICKET;
$('navlist').onclick = ev => { const a = ev.target.closest('a[data-nav]'); if (!a) return; ev.preventDefault(); navigate(a.dataset.nav); };
$('menubtn').onclick = () => { const o = $('sidenav').classList.toggle('open'); $('menubtn').setAttribute('aria-expanded', String(o)); };
document.addEventListener('click', ev => { const g = ev.target.closest && ev.target.closest('[data-go]'); if (g) navigate(g.dataset.go); });
window.addEventListener('popstate', () => { const m = location.hash.match(/^#\/(\w+)$/); if (cur && m) navigate(m[1], false); });
setInterval(() => { if (cur === 'attendee' || cur === 'public') { Sample.tick(); render(); } }, 1500);

(async () => {
  const t = loadToken();
  if (!t) return;
  try { await startSession(t); } catch (err) { endSession(); }
})();
if (new URLSearchParams(location.search).get("guest") === "1") {
  const g = document.getElementById("guest");
  if (g) g.click();
}
