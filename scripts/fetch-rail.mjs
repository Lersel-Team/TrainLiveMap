// Builds data/rail.geojson: mainline railway geometry from OpenStreetMap (same source OpenRailwayMap draws).
// Fetched in regional boxes because a whole-country query times out on public Overpass servers.
// Boxes are rectangles, so short stretches of track just over the border are included.
import fs from 'node:fs';
const BOXES = [[5.5,99,8,102.2],[8,98,11,100.5],[11,98.5,13.3,101],[13.3,99,14.6,102.8],[14.6,99,16.5,105.7],[16.5,99,20.5,105]];
const MIRRORS = ['https://overpass.private.coffee/api/interpreter', 'https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'];
const ways = new Map();
for (const b of BOXES) {
  const q = `[out:json][timeout:80];way(${b.join(',')})["railway"="rail"][!"service"];out geom;`;
  let done = false;
  for (const m of [...MIRRORS, ...MIRRORS]) {
    if (done) break;
    try {
      const r = await fetch(m, { method: 'POST', body: 'data=' + encodeURIComponent(q), headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'TrainLiveMap/0.1' }, signal: AbortSignal.timeout(90000) });
      const j = JSON.parse(await r.text());
      for (const w of j.elements) ways.set(w.id, w);
      console.log('box', b.join(','), j.elements.length, 'ways', new URL(m).host); done = true;
    } catch (e) { console.log('fail', new URL(m).host, e.message.slice(0, 60)); await new Promise(r => setTimeout(r, 5000)); }
  }
  if (!done) throw new Error('box failed: ' + b);
}
const round = x => Math.round(x * 1e5) / 1e5;
const features = [...ways.values()].filter(w => w.geometry?.length > 1).map(w => ({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: w.geometry.map(p => [round(p.lon), round(p.lat)]) } }));
fs.writeFileSync('data/rail.geojson', JSON.stringify({ type: 'FeatureCollection', features }));
console.log('ways', features.length, 'bytes', fs.statSync('data/rail.geojson').size);
