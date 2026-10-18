// All calls to the VISTA API live here. app.js never calls fetch directly.
const Api = (() => {
  let token = null;
  let onUnauthorized = () => {};

  class ApiError extends Error {
    constructor(status, message) { super(message); this.status = status; }
  }

  const base = () => ((window.VISTA_CONFIG && window.VISTA_CONFIG.apiBase) || '').replace(/\/$/, '');

  function detailText(d) {
    if (!d) return 'The request failed.';
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) {
      return d.map(x => {
        const where = (x.loc || []).filter(p => p !== 'body').join('.');
        const msg = String(x.msg || '').replace(/^Value error, /, '');
        return where ? `${where}: ${msg}` : msg;
      }).join('. ');
    }
    return 'The request failed.';
  }

  async function req(method, path, body) {
    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = 'Bearer ' + token;
    let res;
    try {
      res = await fetch(base() + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch (err) {
      throw new ApiError(0, `Cannot reach the API at ${base()}. Check that the backend is running.`);
    }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (err) { /* no JSON body */ }
    if (!res.ok) {
      if (res.status === 401 && token) onUnauthorized();
      throw new ApiError(res.status, detailText(data && data.detail));
    }
    return data;
  }

  return {
    ApiError,
    setToken(t) { token = t; },
    onUnauthorized(fn) { onUnauthorized = fn; },
    login: (username, password) => req('POST', '/auth/login', { username, password }),
    me: () => req('GET', '/me'),
    venues: () => req('GET', '/venues'),
    cameras: venueId => req('GET', `/venues/${venueId}/cameras`),
    latest: venueId => req('GET', `/venues/${venueId}/density/latest`),
    createCamera: (venueId, body) => req('POST', `/venues/${venueId}/cameras`, body),
    patchCamera: (id, body) => req('PATCH', `/cameras/${id}`, body),
    deleteCamera: id => req('DELETE', `/cameras/${id}`),
    rotateKey: id => req('POST', `/cameras/${id}/rotate-key`),
  };
})();
