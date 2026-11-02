// Worker + API + static server. Polls the public TTS master track-map API every 30s.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const BASE = 'https://ttsmaster.railway.co.th/ttsAPI/trackMap';
const PORT = process.env.PORT || 3000, POLL_MS = 30000;
const stations = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/stations.json')));
const UA = { 'User-Agent': 'TrainLiveMap/0.1 (personal project)' };

// chains[`${line}:${stationGrid}`] = [{row, lat, lon, name}] ; gridToChain maps any grid (incl. track-only grids)
const chains = {}, gridToChain = {};
async function loadStructure() {
  for (const line of [1, 2, 3, 4]) {
    const d = await (await fetch(`${BASE}/structure?line=${line}`, { headers: UA })).json();
    const stGrids = [];
    for (const g of d.detail) {
      const pts = g.grid_detail.filter(c => c.is_name_tag && stations[c.id])
        .map(c => ({ row: c.grid_row, lat: stations[c.id].lat, lon: stations[c.id].lon, name: c.th_name }));
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
          lateMin: r.cur_late, atStation: !!r.at_station_f, time: r.cur_time, status: r.run_status });
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
  if (u.pathname === '/api/chains') { res.setHeader('content-type', 'application/json'); return res.end(JSON.stringify(chains)); }
  const f = path.join(ROOT, 'web', u.pathname === '/' ? 'index.html' : path.normalize(u.pathname).replace(/^(\.\.[/\\])+/, ''));
  if (!f.startsWith(path.join(ROOT, 'web')) || !fs.existsSync(f)) { res.statusCode = 404; return res.end('not found'); }
  res.setHeader('content-type', MIME[path.extname(f)] || 'application/octet-stream'); fs.createReadStream(f).pipe(res);
}).listen(PORT, () => console.log('http://localhost:' + PORT));

await loadStructure();
await poll();
setInterval(poll, POLL_MS);
