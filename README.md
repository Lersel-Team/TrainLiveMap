# TrainLiveMap

Live Thai (SRT) train positions on a 3D map: terrain from AWS Terrain Tiles, satellite from Sentinel-2 cloudless (EOX), or OpenStreetMap.

- `src/server.mjs` polls the public TTS master track-map API every 30s and serves `/api/trains`, `/api/chains` and the web app.
- `scripts/geocode-stations.mjs` builds `data/stations.json` (station cell id -> lat/lon) from OpenStreetMap via Overpass. 19 stations are unmatched (`data/stations.missing.txt`).
- `web/index.html` is a MapLibre GL app: 3D terrain, select a train, Follow mode. Positions between stations are estimated by dead reckoning (60 km/h, capped at the next station).

Run: `node src/server.mjs` then open http://localhost:3000

Not included: ttsview train list and consist. That API needs a login token behind a Cloudflare Turnstile bot check.
