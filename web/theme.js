(function () {
  var KEY = 'vista-theme', root = document.documentElement;
  function get() { try { return localStorage.getItem(KEY) || 'system'; } catch (e) { return 'system'; } }
  function apply(m) {
    if (m === 'light' || m === 'dark') root.setAttribute('data-theme', m);
    else root.removeAttribute('data-theme');
  }
  apply(get());
  document.addEventListener('DOMContentLoaded', function () {
    var box = document.getElementById('theme');
    if (!box) return;
    function mark() {
      var m = get();
      box.querySelectorAll('button').forEach(function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute('data-mode') === m));
      });
    }
    box.addEventListener('click', function (ev) {
      var m = ev.target.getAttribute && ev.target.getAttribute('data-mode');
      if (!m) return;
      try { localStorage.setItem(KEY, m); } catch (e) {}
      apply(m); mark();
    });
    mark();
  });
})();
