# TrainLiveMap

Live Thai (SRT) train positions on a 3D map: terrain from AWS Terrain Tiles, satellite from Sentinel-2 cloudless (EOX), or OpenStreetMap.

- `src/server.mjs` polls the public TTS master track-map API every 30s and serves `/api/trains`, `/api/chains` and the web app.
- `scripts/geocode-stations.mjs` builds `data/stations.json` (station cell id -> lat/lon) from OpenStreetMap via Overpass. 19 stations are unmatched (`data/stations.missing.txt`).
- `src/timetable.mjs` loads timetable exports saved as `data/timetable/*.json` (git-ignored). Restart the server after adding one.
- `scripts/rail_from_pbf.py` builds `data/rail.geojson` from OpenStreetMap, the data OpenRailwayMap draws.
- `web/index.html` is a MapLibre GL app: 3D terrain, rail lines, station labels, select a train, Follow mode.

Position estimate: scheduled position at (now - live delay), capped at the next station after the one the live feed reports. Trains with no timetable creep toward their next station at 60 km/h. Trains move in straight lines between stations, not along the track.

Run: `node src/server.mjs` then open http://localhost:3000

Not included: ttsview train list and consist. That API needs a login token behind a Cloudflare Turnstile bot check.

Track data: download `https://download.geofabrik.de/asia/thailand-latest.osm.pbf`, then run `python3 scripts/rail_from_pbf.py thailand.osm.pbf data/rail.geojson`.

Models: `web/models/*.glb` are built by `models/src/make_textures.py` then `models/src/build_models.py` (run inside Blender 4.4, with `MODEL_SRC` set to `models/src`). Dimensions are estimated from photos and diagrams. Consists are approximate, because the live feed has no consist data.
