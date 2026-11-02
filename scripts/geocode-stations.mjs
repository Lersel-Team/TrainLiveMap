// Builds data/stations.json: structure cell id -> {th,en,lat,lon} by matching Thai names to OSM stations.
import fs from 'node:fs';
const API = 'https://ttsmaster.railway.co.th/ttsAPI/trackMap/structure?line=';
const norm = s => (s||'').replace(/\(.*?\)/g,'').replace(/^(ชุมทาง|สถานี|ที่หยุดรถ)\s*/,'').replace(/\s+/g,'').toLowerCase();
const q = `[out:json][timeout:120];area["ISO3166-1"="TH"]->.a;(node(area.a)["railway"~"^(station|halt)$"];);out body;`;
const MIRRORS=['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter','https://maps.mail.ru/osm/tools/overpass/api/interpreter'];
let ov;
for (const m of MIRRORS) { try { const r=await fetch(m,{method:'POST',body:'data='+encodeURIComponent(q),headers:{'Content-Type':'application/x-www-form-urlencoded','User-Agent':'TrainLiveMap/0.1'}}); const t=await r.text(); ov=JSON.parse(t); console.log('ok',m); break; } catch(e){ console.log('fail',m,e.message.slice(0,60)); } }
if(!ov) throw new Error('all overpass mirrors failed');
const osm = new Map();
for (const e of ov.elements) for (const k of ['name:th','name']) if (e.tags?.[k]) { const n=norm(e.tags[k]); if(!osm.has(n)) osm.set(n,[]); osm.get(n).push(e); }
console.log('osm nodes', ov.elements.length);
const out = {}; const miss = [];
for (const line of [1,2,3,4]) {
  const d = await (await fetch(API+line)).json();
  for (const g of d.detail) for (const c of g.grid_detail) {
    if (!c.is_name_tag) continue;
    const hit = osm.get(norm(c.th_name));
    if (hit) out[c.id] = { th:c.th_name, en:c.en_name, lat:hit[0].lat, lon:hit[0].lon };
    else miss.push(`${line}:${c.id} ${c.th_name} / ${c.en_name}`);
  }
}
fs.writeFileSync('data/stations.json', JSON.stringify(out,null,1));
fs.writeFileSync('data/stations.missing.txt', miss.join('\n'));
console.log('matched', Object.keys(out).length, 'missing', miss.length);
