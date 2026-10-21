const API = (window.VISTA_CONFIG && window.VISTA_CONFIG.apiBase) || "http://localhost:8000";
const $ = id => document.getElementById(id);
const role = () => document.querySelector("input[name=role]:checked").value;
const show = (text, ok) => {
  $("msg").textContent = "";
  const d = document.createElement("div"); d.className = "msg " + (ok ? "ok" : "err"); d.textContent = text;
  $("msg").append(d);
};
function sync() { $("vbox").hidden = role() === "attendee"; $("cbox").hidden = role() === "attendee"; }
document.querySelectorAll("input[name=role]").forEach(r => r.addEventListener("change", sync));
sync();

fetch(API + "/public/venues").then(r => r.json()).then(list => {
  list.forEach(v => {
    const o = document.createElement("option"); o.value = v.id;
    o.textContent = v.name + (v.city ? ", " + v.city : ""); $("v").append(o);
  });
}).catch(() => {});

$("f").addEventListener("submit", async ev => {
  ev.preventDefault();
  const u = $("u").value.trim(), p = $("p").value;
  if (u.length < 3) return show("Username must have at least 3 characters.");
  if (p.length < 8) return show("Password must have at least 8 characters.");
  if (p !== $("p2").value) return show("The two passwords do not match.");
  const body = { username: u, password: p, role: role() };
  if (role() !== "attendee") body.venue_id = Number($("v").value) || null;
  if (role() !== "attendee") body.access_code = $("c").value.trim();
  try {
    const res = await fetch(API + "/auth/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return show(typeof data.detail === "string" ? data.detail : "Please check the form and try again.");
    show("Account created. Taking you to log in...", true);
    setTimeout(() => { location.href = "app.html"; }, 1500);
  } catch (err) { show("Cannot reach the server. Check that the backend is running."); }
});