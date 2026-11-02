// Loads timetable exports (data/timetable/*.json) into per-train knots used for position estimates.
// Real stops are trusted. Pass times (p:1) are kept only when they fit in order between two stops,
// because the source has some that run backwards.
import fs from 'node:fs';
import path from 'node:path';
const DAY = 86400;
export const normName = s => String(s || '').toLowerCase().replace(/\(.*?\)/g, '').replace(/junction/g, '').replace(/[^a-z0-9]/g, '');
const sec = v => { const m = /^(\d+):(\d\d)/.exec(v || ''); return m ? +m[1] * 3600 + +m[2] * 60 : null; };

export function buildTrain(entries) {
  const bg = entries.find(e => e.bg); if (!bg) return null;
  const t0 = sec(bg.d) ?? sec(bg.a); if (t0 == null) return null;
  const rel = v => (v - t0 + DAY) % DAY;
  const withT = entries.map(e => {
    const stop = e.bg || e.ed || (!e.p && e.a);
    const raw = e.bg ? (sec(e.d) ?? sec(e.a)) : e.ed ? (sec(e.a) ?? sec(e.d)) : (sec(e.d) ?? sec(e.a));
    return raw == null ? null : { ...e, stop: !!stop, r: rel(raw), arr: e.a && !e.bg ? rel(sec(e.a)) : null };
  }).filter(Boolean);
  const anchors = withT.filter(e => e.stop).sort((a, b) => a.r - b.r);
  if (anchors.length < 2) return null;
  const knots = [anchors[0]];
  for (let i = 0; i < anchors.length - 1; i++) {
    const A = anchors[i], B = anchors[i + 1], lo = Math.min(A.km, B.km), hi = Math.max(A.km, B.km), sign = B.km >= A.km ? 1 : -1;
    const passes = withT.filter(e => !e.stop && e.km > lo && e.km < hi && e.r > A.r && e.r < (B.arr ?? B.r)).sort((a, b) => sign * (a.km - b.km));
    let last = A.r;
    for (const p of passes) if (p.r > last) { knots.push(p); last = p.r; }
    knots.push(B);
  }
  // Coordinates: stations we could not geocode are placed by km between known neighbours.
  for (let i = 0; i < knots.length; i++) if (knots[i].lat == null) {
    let a = i - 1, b = i + 1;
    while (a >= 0 && knots[a].lat == null) a--;
    while (b < knots.length && knots[b].lat == null) b++;
    if (a < 0 || b >= knots.length) continue;
    const f = knots[b].km === knots[a].km ? 0 : (knots[i].km - knots[a].km) / (knots[b].km - knots[a].km);
    knots[i] = { ...knots[i], lat: knots[a].lat + (knots[b].lat - knots[a].lat) * f, lon: knots[a].lon + (knots[b].lon - knots[a].lon) * f, guessed: true };
  }
  const usable = knots.filter(k => k.lat != null);
  if (usable.length < 2) return null;
  return { t0, knots: usable.map(k => ({ r: k.r, dep: k.r, arr: k.arr ?? k.r, km: k.km, lat: k.lat, lon: k.lon, name: k.name, key: normName(k.name), stop: k.stop })) };
}

export function loadTimetable(dir, stations) {
  const byName = new Map();
  for (const s of Object.values(stations)) if (s.en) byName.set(normName(s.en), s);
  const trains = {}, unmatched = new Set();
  if (!fs.existsSync(dir)) return { trains, unmatched: [] };
  for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.json'))) {
    const j = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    const st = new Map(j.stations.map(s => [String(s.station_code), s]));
    const per = {};
    for (const [k, v] of Object.entries(j.matrix)) {
      const [no, code] = k.split('_'), s = st.get(code);
      if (!s) continue; // codes such as depots that the export does not list
      const c = byName.get(normName(s.station_name));
      if (!c) unmatched.add(s.station_name);
      (per[no] ||= []).push({ ...v, name: s.station_name, km: s.station_km, lat: c?.lat, lon: c?.lon });
    }
    for (const [no, e] of Object.entries(per)) { const t = buildTrain(e); if (t) trains[no] = t; }
  }
  return { trains, unmatched: [...unmatched] };
}
