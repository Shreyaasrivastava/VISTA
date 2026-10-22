// Forgot password page. Talks to the VISTA API directly (no login needed).
(function () {
  const base = ((window.VISTA_CONFIG && window.VISTA_CONFIG.apiBase) || '').replace(/\/$/, '');
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const say = (el, cls, text) => { el.innerHTML = text ? `<div class="msg ${cls}" style="margin:12px 0 0">${esc(text)}</div>` : ''; };
  const bytes = s => new TextEncoder().encode(s).length;
  let username = '';

  function detail(d) {
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map(x => String(x.msg || '').replace(/^Value error, /, '')).join('. ');
    return 'Something went wrong. Try again.';
  }
  async function post(path, body) {
    let res;
    try {
      res = await fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    } catch (e) {
      throw new Error(`Cannot reach the API at ${base}. Check that the backend is running.`);
    }
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) throw new Error(detail(data && data.detail));
    return data;
  }

  $('f1').onsubmit = async ev => {
    ev.preventDefault();
    const u = $('user').value.trim();
    if (!u) return say($('m1'), 't3', 'Enter your username.');
    $('b1').disabled = true; say($('m1'), '', '');
    try {
      const r = await post('/auth/recovery/question', { username: u });
      username = u;
      $('question').textContent = r.question;
      $('f1').hidden = true; $('f2').hidden = false; $('answer').focus();
    } catch (err) { say($('m1'), 't3', err.message); }
    finally { $('b1').disabled = false; }
  };

  $('f2').onsubmit = async ev => {
    ev.preventDefault();
    const answer = $('answer').value, np = $('np').value, np2 = $('np2').value, m = $('m2');
    if (!answer.trim()) return say(m, 't3', 'Type your answer.');
    if (np.length < 10) return say(m, 't3', 'Use a new password of at least 10 characters.');
    if (bytes(np) > 72) return say(m, 't3', 'Use a new password of at most 72 bytes.');
    if (np !== np2) return say(m, 't3', 'The two new passwords do not match.');
    $('b2').disabled = true; say(m, '', '');
    try {
      await post('/auth/recovery/reset', { username, answer, new_password: np });
      $('f2').hidden = true; $('done').hidden = false;
      $('answer').value = $('np').value = $('np2').value = '';
    } catch (err) { say(m, 't3', err.message); }
    finally { $('b2').disabled = false; }
  };

  $('again').onclick = () => {
    $('f2').hidden = true; $('f1').hidden = false;
    $('answer').value = $('np').value = $('np2').value = ''; say($('m2'), '', ''); $('user').focus();
  };
  $('show').onchange = () => { const t = $('show').checked ? 'text' : 'password'; $('answer').type = t; $('np').type = t; $('np2').type = t; };
})();
