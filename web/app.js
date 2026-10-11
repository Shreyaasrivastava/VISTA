const T=['Normal','Caution','Warning','Critical'];
const tz=(z,o)=>{const t=z.th;return o<t[0]?0:o<t[1]?1:o<t[2]?2:3};
const V=[
 {id:'rly',name:'Jaipur Junction Railway Station',city:'Jaipur',zones:[{n:'Platform 1',a:140,s:.42},{n:'Foot overbridge',a:60,s:.3},{n:'Main concourse',a:300,s:.55}]},
 {id:'tmp',name:'Govind Dev Ji Temple',city:'Jaipur',zones:[{n:'Entry courtyard',a:220,s:.6},{n:'Inner hall',a:90,s:.7}]},
 {id:'std',name:'SMS Stadium, Gate 3',city:'Jaipur',zones:[{n:'Gate 3 approach',a:180,s:.2}]}
];
const CAMS=[
 {id:'CAM-01',v:'rly',z:'Platform 1',url:'rtsp://10.0.4.21/s1',ip:'10.0.4.21',r:35,th:[50,75,90],cal:'Calibrated'},
 {id:'CAM-02',v:'rly',z:'Foot overbridge',url:'rtsp://10.0.4.22/s1',ip:'10.0.4.22',r:20,th:[50,75,90],cal:'Calibrated'},
 {id:'CAM-05',v:'rly',z:'Main concourse',url:'rtsp://10.0.4.23/s1',ip:'10.0.4.23',r:45,th:[50,75,90],cal:'Calibrated'},
 {id:'CAM-03',v:'tmp',z:'Entry courtyard',url:'rtsp://10.0.7.10/s1',ip:'10.0.7.10',r:40,th:[50,70,85],cal:'Calibrated'},
 {id:'CAM-06',v:'tmp',z:'Inner hall',url:'rtsp://10.0.7.11/s1',ip:'10.0.7.11',r:25,th:[50,70,85],cal:'Calibrated'},
 {id:'CAM-04',v:'std',z:'Gate 3 approach',url:'rtsp://10.0.9.31/s1',ip:'10.0.9.31',r:30,th:[50,75,90],cal:'Needs recalibration'}
];
const Z=[];
V.forEach(v=>v.zones.forEach(z=>{z.v=v;z.cnt=Math.round(z.a*1.08*z.s);z.th=[50,75,90];z.hold=0;z.surge=false;Z.push(z)}));
CAMS.forEach(c=>{const z=Z.find(x=>x.v.id===c.v&&x.n===c.z);if(z)z.th=c.th});
Z.forEach(z=>z.t=tz(z,occ(z)));
function occ(z){return z.cnt/(z.a*1.08)*100}
function worst(v){return v.zones.reduce((m,z)=>z.t>m.t?z:m,v.zones[0])}
const A=[];let geo=false,n=0,cur='',me=null,editing=null;
const mine=()=>me?Z.filter(z=>z.v.id===me.venue):[];
const vname=id=>V.find(v=>v.id===id).name;
const e=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pill=t=>`<span class="pill t${t}">${T[t]}</span>`;
const hm=d=>d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});

function raise(z){
  let a=A.find(x=>x.z===z&&x.st==='Open');
  if(a){a.t=z.t;return}
  A.unshift({id:++n,z:z,t:z.t,at:new Date(),st:'Open'});
}
function tick(){
  Z.forEach(z=>{
    z.cnt+=z.surge?Math.round(z.a*.075):Math.round(Math.random()*6-3);
    z.cnt=Math.max(0,Math.min(Math.round(z.a*1.5),z.cnt));
    const raw=tz(z,occ(z));
    if(raw!==z.t){if(++z.hold>=3){z.t=raw;z.hold=0;if(raw>=2)raise(z)}}else z.hold=0;
  });
  const now=Date.now();
  A.forEach(a=>{if(a.st==='Open'&&a.t===3&&now-a.at>30000)a.st='Escalated'});
  render();
}
const $=id=>document.getElementById(id);
const NAV={
 admin:[['overview','Overview'],['zones','Live zones'],['cameras','Cameras'],['thresholds','Thresholds'],['guide','Camera setup guide']],
 security:[['alerts','Alerts'],['status','Zone status']],
 attendee:[['register','Register'],['ticket','My ticket'],['venues','Venue crowding']],
 public:[['venues','Venue crowding'],['location','Location alerts']]
};
const SUB={security:'All venues',attendee:'Registration and tickets',public:'Read-only'};
const EMPTY_TICKET='<div class="empty">You have not registered yet.<br><button class="btn ghost" type="button" data-go="register" style="margin-top:10px">Go to registration</button></div>';
const DEFAULT_TITLE=document.title;
let page='';
function zoneCard(z){const o=occ(z);return `<div class="card zone t${z.t}" style="background:var(--surf)">
   <div class="top"><div><b>${e(z.n)}</b><span class="v">${e(z.v.name)}</span></div>${pill(z.t)}</div>
   <div class="big" style="color:var(--ink)">${Math.round(o)}%</div>
   <div class="bar" style="color:inherit" aria-hidden="true"><i style="width:${Math.min(o,100)}%"></i></div>
   <p style="margin:8px 0 0;color:var(--mut);font-size:14px">${z.cnt} people &middot; ${(z.cnt/z.a).toFixed(2)} per m&sup2; &middot; ${z.a} m&sup2;</p></div>`}
function venueList(target,qid){
  const q=$(qid).value.toLowerCase();
  const m=V.filter(v=>(v.name+v.city).toLowerCase().includes(q));
  $(target).innerHTML=m.length?m.map(v=>{const w=worst(v);return `<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;align-items:start"><div><b>${e(v.name)}</b><div style="color:var(--mut);font-size:14px">${e(v.city)}</div></div>${pill(w.t)}</div>
   <p style="margin:8px 0 0;font-size:14px;color:var(--mut)">Busiest area: ${e(w.n)} at ${Math.round(occ(w))}%</p></div>`}).join(''):'<div class="empty">No venue matches that search. Try a shorter name.</div>';
}
function renderOverview(zs){
  const cs=CAMS.filter(c=>c.v===me.venue),need=zs.filter(z=>z.t>=2),recal=cs.filter(c=>c.cal!=='Calibrated').length;
  const open=A.filter(a=>a.z.v.id===me.venue&&a.st==='Open').length;
  const card=(l,v,t)=>`<div class="card"><div style="color:var(--mut)">${l}</div><div class="big">${v}</div><p style="margin:4px 0 0;color:var(--mut);font-size:14px">${t}</p></div>`;
  $('ov-cards').innerHTML=card('Zones monitored',zs.length,need.length?need.length+' at Warning or Critical':'None at Warning or Critical')+card('Cameras',cs.length,recal?recal+' not calibrated':'All calibrated')+card('Open alerts',open,open?'Waiting for acknowledgement':'Nothing waiting');
  $('ov-attn').innerHTML=need.length?need.map(zoneCard).join(''):'<div class="empty">No zone is at Warning or Critical right now.</div>';
}
function renderThresholds(zs){
  $('th-body').innerHTML=zs.map(z=>{const cs=CAMS.filter(c=>c.v===me.venue&&c.z===z.n).map(c=>c.id).join(', ')||'None yet';return `<tr><td>${e(z.n)}</td><td>${e(cs)}</td><td>${z.th.join(' / ')}</td></tr>`}).join('');
}
function render(){
  if(cur==='admin'){const zs=mine();$('zones').innerHTML=zs.map(zoneCard).join('');renderOverview(zs);renderThresholds(zs)}
  else if(cur==='security'){
    $('feed').innerHTML=A.length?A.map(a=>`<div class="card alert t${a.t}" style="background:var(--surf);margin-bottom:10px">
   <div class="top" style="display:flex;justify-content:space-between;gap:8px">${pill(a.t)}<span style="color:var(--mut);font-size:14px">${hm(a.at)}</span></div>
   <p><b>${e(a.z.n)}</b>, ${e(a.z.v.name)}</p>
   <p style="color:var(--mut)!important;font-size:14px">${a.st==='Open'&&a.t===3?'Escalates to the control room if nobody acknowledges within 30 seconds.':'Status: '+a.st}</p>
   ${a.st==='Open'?`<button class="btn" data-ack="${a.id}" style="margin-top:6px">Acknowledge</button>`:`<span class="pill t${a.st==='Escalated'?3:0}" style="margin-top:6px;display:inline-block">${a.st}</span>`}
  </div>`).join(''):'<div class="empty">No alerts. Warning and Critical alerts show up here.</div>';
    $('zones-sec').innerHTML=Z.map(zoneCard).join('');
  }
  else if(cur==='attendee')venueList('vlist-a','qa');
  else if(cur==='public'){
    venueList('vlist','q');
    const p=V[0].zones[0];
    $('geo').innerHTML=geo?(p.t>=2?`<div class="msg t${p.t}"><b>${T[p.t]} alert near you.</b> Platform 1 is crowded. Move toward the main concourse and follow staff instructions.</div>`:`<div class="msg t0">You are in Platform 1. No alerts right now.</div>`):'<div class="empty">Location is off. Turn it on to get alerts for the zone you are standing in.</div>';
    $('loc').textContent=geo?'Turn location off':'Turn location on (demo: Platform 1)';
  }
}
function navigate(p,push){
  if(!cur||!NAV[cur].some(x=>x[0]===p))return;
  page=p;
  document.querySelectorAll('main > .legal').forEach(x=>x.hidden=true);
  document.querySelectorAll('main > .page').forEach(x=>x.hidden=x.id!=='p-'+cur+'-'+p);
  document.querySelectorAll('#navlist a').forEach(a=>{if(a.dataset.nav===p)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
  document.title=NAV[cur].find(x=>x[0]===p)[1]+' | VISTA Crowd Safety';
  if(push!==false){try{history.pushState(null,'','#/'+p)}catch(x){}}
  $('sidenav').classList.remove('open');$('menubtn').setAttribute('aria-expanded','false');
  render();
  const hd=document.querySelector('#p-'+cur+'-'+p+' .title');if(hd)hd.focus({preventScroll:true});
  window.scrollTo(0,0);
}
function qr(seed){
  let h=0;for(const c of seed)h=(h*31+c.charCodeAt(0))>>>0;
  const r=()=>(h^=h<<13,h^=h>>>17,h^=h<<5,(h>>>0)/4294967296);
  const N=25;let d='';
  const fin=(x,y)=>{d+=`<rect x="${x}" y="${y}" width="7" height="7"/><rect x="${x+1}" y="${y+1}" width="5" height="5" fill="#fff"/><rect x="${x+2}" y="${y+2}" width="3" height="3"/>`};
  for(let y=0;y<N;y++)for(let x=0;x<N;x++){
    if((x<8&&y<8)||(x>N-9&&y<8)||(x<8&&y>N-9))continue;
    if(r()>.5)d+=`<rect x="${x}" y="${y}" width="1" height="1"/>`}
  fin(0,0);fin(N-7,0);fin(0,N-7);
  return `<svg viewBox="-1 -1 ${N+2} ${N+2}" role="img" aria-label="Demo QR code" fill="#000">${d}</svg>`;
}
document.getElementById('vn').innerHTML=V.map(v=>`<option value="${v.id}">${e(v.name)}</option>`).join('');
document.getElementById('surge').onclick=()=>{const z=mine()[0];if(z)z.surge=true};
document.getElementById('reset').onclick=()=>{mine().forEach(z=>{z.surge=false;z.cnt=Math.round(z.a*1.08*z.s);z.t=tz(z,occ(z));z.hold=0});for(let i=A.length-1;i>=0;i--)if(A[i].z.v.id===me.venue)A.splice(i,1);render()};
$('q').oninput=render;$('qa').oninput=render;
document.getElementById('loc').onclick=()=>{geo=!geo;render()};
document.getElementById('feed').onclick=ev=>{const id=ev.target.dataset.ack;if(!id)return;const a=A.find(x=>x.id==id);if(a)a.st='Acknowledged';render()};
document.getElementById('reg').onsubmit=ev=>{
  ev.preventDefault();
  const nm=document.getElementById('nm').value.trim(),ph=document.getElementById('ph').value.replace(/\s/g,''),v=V.find(x=>x.id===document.getElementById('vn').value);
  const mode=document.querySelector('input[name=mode]:checked').value,msg=document.getElementById('regmsg');
  const bad=t=>{msg.innerHTML=`<div class="msg t3">${t}</div>`};
  if(!nm)return bad('Enter your full name.');
  if(!/^\d{10}$/.test(ph))return bad('Enter a 10-digit phone number.');
  const crit=v.zones.find(z=>z.t===3);
  if(crit)return bad(`Registration for ${e(v.name)} is paused because ${e(crit.n)} is at Critical. Try again in a few minutes.`);
  const id='VST-'+Math.random().toString(36).slice(2,8).toUpperCase();
  msg.innerHTML='';document.getElementById('reg').reset();
  document.getElementById('ticket').innerHTML='<div class="msg t0" style="margin:0 0 12px">You are registered.</div>'+qr(id+nm)+`<dl><dt>Name</dt><dd>${e(nm)}</dd><dt>Venue</dt><dd>${e(v.name)}</dd><dt>Type</dt><dd>${e(mode)}</dd><dt>Code</dt><dd>${id}</dd></dl>`;
  navigate('ticket');
};
const USERS={
 'jaipur.admin':{pw:'jj@123',role:'admin',label:'Admin ADM-101',venue:'rly'},
 'govind.admin':{pw:'gd@123',role:'admin',label:'Admin ADM-102',venue:'tmp'},
 'stadium.admin':{pw:'sms@123',role:'admin',label:'Admin ADM-103',venue:'std'},
 security:{pw:'guard123',role:'security',label:'Security staff'},
 attendee:{pw:'attendee123',role:'attendee',label:'Attendee'}
};
function buildNav(){
  $('navlist').innerHTML=NAV[cur].map(x=>`<li><a href="#/${x[0]}" data-nav="${x[0]}">${x[1]}</a></li>`).join('');
}
function go(role,label,user){
  cur=role;me=role==='admin'?user:null;page='';
  $('login').hidden=!!role;
  document.querySelectorAll('main > .page').forEach(x=>x.hidden=true);
  $('who').hidden=!role;
  $('whotxt').textContent=role==='admin'?label+', '+vname(me.venue):(role?label:'');
  $('shell').classList.toggle('has-side',!!role);$('side').hidden=!role;
  $('camform').hidden=true;$('cammsg').innerHTML='';
  if(role){
    $('sidewho').textContent=role==='admin'?vname(me.venue):label;
    $('sidesub').textContent=role==='admin'?label:SUB[role];
    buildNav();renderCams();
    navigate(NAV[role][0][0],false);
    try{history.replaceState(null,'','#/'+NAV[role][0][0])}catch(x){}
  }else{
    document.title=DEFAULT_TITLE;
    try{history.replaceState(null,'',location.pathname+location.search)}catch(x){}
    window.scrollTo(0,0);render();
  }
}
function renderCams(){
  const rows=CAMS.filter(c=>me&&c.v===me.venue);
  document.getElementById('cams').innerHTML=rows.length?rows.map(c=>`<tr><td>${e(c.id)}</td><td>${e(c.z)}</td><td>${e(c.url)}</td><td>${e(c.ip)}</td><td>${c.r} m</td><td>${c.th.join(' / ')}</td><td><span class="pill ${c.cal==='Calibrated'?'t0':'t1'}">${e(c.cal)}</span></td><td><button class="btn ghost" type="button" data-edit="${e(c.id)}">Edit</button></td></tr>`).join(''):'<tr><td colspan="8">No cameras yet for this venue. Use Add camera.</td></tr>';
}
function openCam(c){
  editing=c||null;
  const f=id=>document.getElementById(id);
  f('cfz').innerHTML=V.find(v=>v.id===me.venue).zones.map(z=>`<option>${e(z.n)}</option>`).join('');
  f('cftitle').textContent=c?'Edit '+c.id:'Add camera';
  f('cfz').value=c?c.z:f('cfz').options[0].value;
  f('cfu').value=c?c.url:'';f('cfi').value=c?c.ip:'';f('cfr').value=c?c.r:30;
  f('cfc').value=c?c.th[0]:50;f('cfw').value=c?c.th[1]:75;f('cfk').value=c?c.th[2]:90;
  f('cfmsg').innerHTML='';f('cammsg').innerHTML='';f('camform').hidden=false;
  f('camform').scrollIntoView({behavior:'smooth',block:'nearest'});f('cfu').focus();
}
document.getElementById('lg').onsubmit=ev=>{
  ev.preventDefault();
  const u=USERS[document.getElementById('un').value.trim().toLowerCase()],pw=document.getElementById('pw').value;
  if(!u||u.pw!==pw){document.getElementById('lgmsg').innerHTML='<div class="msg t3">Username or password is wrong. Check both and try again.</div>';return}
  document.getElementById('lg').reset();document.getElementById('lgmsg').innerHTML='';
  go(u.role,u.label,u);
};
document.getElementById('guest').onclick=()=>go('public','Guest');
document.getElementById('out').onclick=()=>{
  document.getElementById('reg').reset();document.getElementById('regmsg').innerHTML='';
  document.getElementById('ticket').innerHTML=EMPTY_TICKET;
  geo=false;go('');
};
document.getElementById('camadd').onclick=()=>openCam(null);
document.getElementById('cfcancel').onclick=()=>{document.getElementById('camform').hidden=true};
document.getElementById('cams').onclick=ev=>{const id=ev.target.dataset.edit;if(!id)return;const c=CAMS.find(x=>x.id===id&&me&&x.v===me.venue);if(c)openCam(c)};
document.getElementById('camform').onsubmit=ev=>{
  ev.preventDefault();
  const f=id=>document.getElementById(id).value.trim(),bad=t=>{document.getElementById('cfmsg').innerHTML=`<div class="msg t3">${t}</div>`};
  const url=f('cfu'),ip=f('cfi'),r=+f('cfr'),th=[+f('cfc'),+f('cfw'),+f('cfk')];
  if(!/^(rtsp|rtmp|https?):\/\/\S+$/i.test(url))return bad('Stream URL must start with rtsp://, rtmp://, http:// or https://.');
  if(!/^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/.test(ip))return bad('Enter a valid IPv4 address, like 10.0.4.21.');
  if(!(r>0&&r<=200))return bad('Detection range must be between 1 and 200 metres.');
  if(!(th[0]>0&&th[0]<th[1]&&th[1]<th[2]&&th[2]<=100))return bad('Thresholds must increase: Caution, then Warning, then Critical, all within 100%.');
  const zn=f('cfz');
  if(editing){Object.assign(editing,{z:zn,url,ip,r,th})}
  else{const k=Math.max(0,...CAMS.map(c=>+c.id.slice(4)))+1;CAMS.push({id:'CAM-'+String(k).padStart(2,'0'),v:me.venue,z:zn,url,ip,r,th,cal:'Not calibrated'})}
  const z=Z.find(x=>x.v.id===me.venue&&x.n===zn);
  if(z){z.th=th;z.t=tz(z,occ(z));z.hold=0}
  document.getElementById('camform').hidden=true;
  document.getElementById('cammsg').innerHTML='<div class="msg t0" style="margin:0 0 12px">Camera saved.</div>';
  renderCams();render();
};
$('ticket').innerHTML=EMPTY_TICKET;
$('navlist').onclick=ev=>{const a=ev.target.closest('a[data-nav]');if(!a)return;ev.preventDefault();navigate(a.dataset.nav)};
$('menubtn').onclick=()=>{const o=$('sidenav').classList.toggle('open');$('menubtn').setAttribute('aria-expanded',String(o))};
document.addEventListener('click',ev=>{const g=ev.target.closest&&ev.target.closest('[data-go]');if(g)navigate(g.dataset.go)});
window.addEventListener('popstate',()=>{const m=location.hash.match(/^#\/(\w+)$/);if(cur&&m)navigate(m[1],false)});
render();setInterval(tick,1500);
