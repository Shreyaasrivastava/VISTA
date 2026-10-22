// Set or change your own recovery question. Needs a logged-in session from the dashboard.
(function () {
  const TOKEN_KEY = 'vista-token';       // the key the dashboard saves your login under
  const base = ((window.VISTA_CONFIG && window.VISTA_CONFIG.apiBase) || '').replace(/\/$/, '');
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const say = (el, cls, text) => { el.innerHTML = text ? `<div class="msg ${cls}" style="margin:12px 0 0">${esc(text)}</div>` : ''; };
  let token = null;
  try { token = sessionStorage.getItem(TOKEN_KEY); } catch (e) { /* ignore */ }

  function detail(d) {
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map(x => String(x.msg || '').replace(/^Value error, /, '')).join('. ');
    return 'Something went wrong. Try again.';
  }
  async function call(method, path, body) {
    let res;
    try {
      res = await fetch(base + path, { method, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }, body: body ? JSON.stringify(body) : undefined });
    } catch (e) { throw Object.assign(new Error(`Cannot reach the API at ${base}. Check that the backend is running.`), { status: 0 }); }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) throw Object.assign(new Error(res.status === 401 ? 'Your login ended. Log in again.' : detail(data && data.detail)), { status: res.status });
    return data;
  }
  function gate(text) {
    $('gate').innerHTML = `${esc(text)} <a href="app.html">Go to log in</a>`; $('gate').hidden = false; $('rf').hidden = true;
  }
  async function showStatus() {
    const r = await call('GET', '/me/recovery');
    $('status').innerHTML = r.has_recovery
      ? `<div class="msg t0" style="margin:0">Your current question: <b>${esc(r.question)}</b>. Saving again replaces it.</div>`
      : '<div class="msg t1" style="margin:0">You have not set a recovery question yet.</div>';
  }

  $('qsel').onchange = () => { $('ownwrap').hidden = $('qsel').value !== '__own__'; if (!$('ownwrap').hidden) $('qown').focus(); };
  $('show').onchange = () => { const t = $('show').checked ? 'text' : 'password'; $('ans').type = t; $('cur').type = t; };
  $('rf').onsubmit = async ev => {
    ev.preventDefault();
    const q = $('qsel').value === '__own__' ? $('qown').value.trim() : $('qsel').value;
    const a = $('ans').value, cur = $('cur').value, m = $('rm');
    if (q.length < 10) return say(m, 't3', 'Write a question of at least 10 characters.');
    if (!a.trim()) return say(m, 't3', 'Type your answer.');
    if (!cur) return say(m, 't3', 'Type your current password.');
    $('rb').disabled = true; say(m, '', '');
    try {
      await call('PUT', '/me/recovery', { current_password: cur, question: q, answer: a });
      $('ans').value = $('cur').value = '';
      say(m, 't0', 'Saved. You can now use Forgot password if you ever need it.');
      await showStatus();
    } catch (err) {
      if (err.status === 401) gate(err.message); else say(m, 't3', err.message);
    } finally { $('rb').disabled = false; }
  };

  (async () => {
    if (!token) return gate('You need to be logged in to set a recovery question.');
    try { await showStatus(); $('rf').hidden = false; }
    catch (err) { if (err.status === 401) gate(err.message); else { $('rf').hidden = false; say($('status'), 't3', err.message); } }
  })();
})();
