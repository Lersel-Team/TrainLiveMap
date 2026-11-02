// Worker + API + static server. Polls the public TTS master track-map API every 30s.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadTimetable, normName } from './timetable.mjs';
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const BASE = 'https://ttsmaster.railway.co.th/ttsAPI/trackMap';
const PORT = process.env.PORT || 3000, POLL_MS = 30000;
const stations = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/stations.json')));
const timetable = loadTimetable(process.env.TIMETABLE_DIR || path.join(ROOT, 'data/timetable'), stations);
console.log('timetable:', Object.keys(timetable.trains).length, 'trains; stations without coordinates:', timetable.unmatched.length);
const UA = { 'User-Agent': 'TrainLiveMap/0.1 (personal project)' };

// chains[`${line}:${stationGrid}`] = [{row, lat, lon, name}] ; gridToChain maps any grid (incl. track-only grids)
const chains = {}, gridToChain = {}, rowName = {}, srtStations = new Map();
async function loadStructure() {
  for (const line of [1, 2, 3, 4]) {
    const d = await (await fetch(`${BASE}/structure?line=${line}`, { headers: UA })).json();
    const stGrids = [];
    for (const g of d.detail) {
      const pts = g.grid_detail.filter(c => c.is_name_tag && stations[c.id])
        .map(c => ({ row: c.grid_row, lat: stations[c.id].lat, lon: stations[c.id].lon, name: c.th_name }));
      for (const c of g.grid_detail) if (c.is_name_tag) {
        rowName[`${line}:${g.grid_id}:${c.grid_row}`] = normName(c.en_name);
        const k = stations[c.id];
        if (k && !srtStations.has(c.th_name)) srtStations.set(c.th_name, { th: c.th_name, en: c.en_name, lat: k.lat, lon: k.lon, major: c.class === 1 });
      }
      if (pts.length) { chains[`${line}:${g.grid_id}`] = pts; stGrids.push(g.grid_id); }
    }
    for (const g of d.detail) {
      const cand = stGrids.filter(s => s <= g.grid_id && Math.floor(s / 1000) === Math.floor(g.grid_id / 1000));
      if (cand.length) gridToChain[`${line}:${g.grid_id}`] = `${line}:${Math.max(...cand)}`;
    }
  }
  console.log('structure loaded:', Object.keys(chains).length, 'chains');
}

let state = { updated: null, trains: [] };
async function poll() {
  const trains = [];
  for (const line of [1, 2, 3, 4]) {
    try {
      const rows = await (await fetch(`${BASE}/trains?line=${line}`, { headers: UA })).json();
      for (const r of rows) {
        const chain = gridToChain[`${line}:${r.grid_id}`];
        if (!chain) continue;
        trains.push({ id: r.runhash, no: r.train_code, line, chain, row: r.grid_row, dir: r.dir === 2 ? -1 : 1,
          st: rowName[`${chain}:${r.grid_row}`] || null, lateMin: r.cur_late, atStation: !!r.at_station_f, time: r.cur_time, status: r.run_status });
      }
    } catch (e) { console.warn('poll line', line, e.message); }
  }
  state = { updated: new Date().toISOString(), trains };
  console.log(state.updated, trains.length, 'trains');
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json' };
http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname === '/api/trains') { res.setHeader('content-type', 'application/json'); return res.end(JSON.stringify(state)); }
  if (u.pathname === '/api/timetable') { res.setHeader('content-type', 'application/json'); return res.end(JSON.stringify(timetable.trains)); }
  if (u.pathname === '/api/stations') { res.setHeader('content-type', 'application/json'); return res.end(JSON.stringify([...srtStations.values()])); }
  if (u.pathname === '/api/rail') {
    const f = path.join(ROOT, 'data/rail.geojson');
    res.setHeader('content-type', 'application/json');
    if (!fs.existsSync(f)) return res.end('{"type":"FeatureCollection","features":[]}');
    return fs.createReadStream(f).pipe(res);
  }
  if (u.pathname === '/api/chains') { res.setHeader('content-type', 'application/json'); return res.end(JSON.stringify(chains)); }
  const f = path.join(ROOT, 'web', u.pathname === '/' ? 'index.html' : path.normalize(u.pathname).replace(/^(\.\.[/\\])+/, ''));
  if (!f.startsWith(path.join(ROOT, 'web')) || !fs.existsSync(f)) { res.statusCode = 404; return res.end('not found'); }
  res.setHeader('content-type', MIME[path.extname(f)] || 'application/octet-stream'); fs.createReadStream(f).pipe(res);
}).listen(PORT, () => console.log('http://localhost:' + PORT));

await loadStructure();
await poll();
setInterval(poll, POLL_MS);
