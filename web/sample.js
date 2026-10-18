// SAMPLE DATA ONLY. Used by the attendee and guest screens until their API endpoints exist
// (registration in Phase 4, public venue status later). Admin and security screens never use this.
const Sample = (() => {
  const tz = o => (o < 50 ? 0 : o < 75 ? 1 : o < 90 ? 2 : 3);
  const V = [
    { id: 'rly', name: 'Jaipur Junction Railway Station', city: 'Jaipur', zones: [{ n: 'Platform 1', a: 140, s: .42 }, { n: 'Foot overbridge', a: 60, s: .3 }, { n: 'Main concourse', a: 300, s: .55 }] },
    { id: 'tmp', name: 'Govind Dev Ji Temple', city: 'Jaipur', zones: [{ n: 'Entry courtyard', a: 220, s: .6 }, { n: 'Inner hall', a: 90, s: .7 }] },
    { id: 'std', name: 'SMS Stadium, Gate 3', city: 'Jaipur', zones: [{ n: 'Gate 3 approach', a: 180, s: .2 }] },
  ];
  const Z = [];
  const occ = z => z.cnt / (z.a * 1.08) * 100;
  V.forEach(v => v.zones.forEach(z => { z.v = v; z.cnt = Math.round(z.a * 1.08 * z.s); z.t = tz(occ(z)); Z.push(z); }));
  const worst = v => v.zones.reduce((m, z) => (z.t > m.t ? z : m), v.zones[0]);
  function tick() {
    Z.forEach(z => {
      z.cnt = Math.max(0, Math.min(Math.round(z.a * 1.5), z.cnt + Math.round(Math.random() * 6 - 3)));
      z.t = tz(occ(z));
    });
  }
  function qr(seed) {
    let h = 0; for (const c of seed) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    const r = () => (h ^= h << 13, h ^= h >>> 17, h ^= h << 5, (h >>> 0) / 4294967296);
    const N = 25; let d = '';
    const fin = (x, y) => { d += `<rect x="${x}" y="${y}" width="7" height="7"/><rect x="${x + 1}" y="${y + 1}" width="5" height="5" fill="#fff"/><rect x="${x + 2}" y="${y + 2}" width="3" height="3"/>`; };
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      if ((x < 8 && y < 8) || (x > N - 9 && y < 8) || (x < 8 && y > N - 9)) continue;
      if (r() > .5) d += `<rect x="${x}" y="${y}" width="1" height="1"/>`;
    }
    fin(0, 0); fin(N - 7, 0); fin(0, N - 7);
    return `<svg viewBox="-1 -1 ${N + 2} ${N + 2}" role="img" aria-label="Demo QR code" fill="#000">${d}</svg>`;
  }
  return { V, Z, occ, worst, tick, qr };
})();
