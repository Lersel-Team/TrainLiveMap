// Builds data/stations.json: structure cell id -> {th,en,lat,lon} by matching Thai names to OSM stations.
import fs from 'node:fs';
const API = 'https://ttsmaster.railway.co.th/ttsAPI/trackMap/structure?line=';
const norm = s => (s||'').replace(/\(.*?\)/g,'').replace(/^(ชุมทาง|สถานี|ที่หยุดรถ)\s*/,'').replace(/\s+/g,'').toLowerCase();
const q = `[out:json][timeout:120];area["ISO3166-1"="TH"]->.a;(node(area.a)["railway"~"^(station|halt)$"];);out body;`;
const MIRRORS=['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter','https://maps.mail.ru/osm/tools/overpass/api/interpreter'];
let ov;
for (const m of MIRRORS) { try { const r=await fetch(m,{method:'POST',body:'data='+encodeURIComponent(q),headers:{'Content-Type':'application/x-www-form-urlencoded','User-Agent':'TrainLiveMap/0.1'},signal:AbortSignal.timeout(90000)}); const t=await r.text(); ov=JSON.parse(t); console.log('ok',m); break; } catch(e){ console.log('fail',m,e.message.slice(0,60)); } }
if(!ov) throw new Error('all overpass mirrors failed');
const osm = new Map();
for (const e of ov.elements) for (const k of ['name:th','name']) if (e.tags?.[k]) { const n=norm(e.tags[k]); if(!osm.has(n)) osm.set(n,[]); osm.get(n).push(e); }
console.log('osm nodes', ov.elements.length);
const out = {}; const miss = []; const cand = [];
for (const line of [1,2,3,4]) {
  const d = await (await fetch(API+line,{signal:AbortSignal.timeout(30000)})).json();
  for (const g of d.detail) for (const c of g.grid_detail) {
    if (!c.is_name_tag) continue;
    const hit = osm.get(norm(c.th_name));
    if (hit) cand.push({ c, hit, grid: g.grid_id, line });
    else miss.push(`${line}:${c.id} ${c.th_name} / ${c.en_name}`);
  }
}
// Same-named stations exist in OSM: use unambiguous stations in the grid as the reference point.
const major = new Set();
const med = a => [...a].sort((x, y) => x - y)[a.length >> 1];
for (const x of cand) {
  const sure = cand.filter(y => y.line === x.line && y.grid === x.grid && new Set(y.hit.map(h => h.id)).size === 1);
  let best = x.hit[0];
  if (x.hit.length > 1 && sure.length) {
    const la = med(sure.map(y => y.hit[0].lat)), lo = med(sure.map(y => y.hit[0].lon));
    best = x.hit.reduce((b, h) => ((h.lat-la)**2 + (h.lon-lo)**2 < (b.lat-la)**2 + (b.lon-lo)**2 ? h : b));
  }
  out[x.c.id] = { th: x.c.th_name, en: x.c.en_name, lat: best.lat, lon: best.lon };
  if (x.c.class === 1) major.add(best.id);
}
fs.writeFileSync('data/stations.json', JSON.stringify(out,null,1));
// Every OSM station and halt in Thailand, for the map's label layer.
const all = ov.elements.filter(e => e.tags?.['name:th'] || e.tags?.name).map(e => ({ th: e.tags['name:th'] || e.tags.name, en: e.tags['name:en'] || '', lat: e.lat, lon: e.lon, major: major.has(e.id) }));
fs.writeFileSync('data/osm-stations.json', JSON.stringify(all));
console.log('label stations', all.length, 'major', major.size);
fs.writeFileSync('data/stations.missing.txt', miss.join('\n'));
console.log('matched', Object.keys(out).length, 'missing', miss.length);
