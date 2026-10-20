const API = "http://127.0.0.1:8000";   // use the same address as in config.js
const box = document.getElementById("events");
const fmt = d => new Date(d).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function card(ev) {
  const a = document.createElement("article"); a.className = "card";
  const badge = document.createElement("span"); badge.className = "badge " + ev.status;
  badge.textContent = ev.status === "live" ? "Happening now" : "Upcoming";
  const h = document.createElement("h3"); h.textContent = ev.title;
  const where = document.createElement("p"); where.textContent = [ev.venue, ev.city].filter(Boolean).join(", ");
  const when = document.createElement("p"); when.className = "muted"; when.textContent = fmt(ev.starts_at) + " to " + fmt(ev.ends_at);
  const d = document.createElement("p"); d.textContent = ev.description || "";
  a.append(badge, h, where, when, d);
  return a;
}

fetch(API + "/events")
  .then(r => { if (!r.ok) throw new Error(); return r.json(); })
  .then(list => {
    box.textContent = "";
    if (!list.length) { box.textContent = "No events right now."; return; }
    list.forEach(e => box.append(card(e)));
  })
  .catch(() => { box.textContent = "Could not load events. Check that the backend is running."; });