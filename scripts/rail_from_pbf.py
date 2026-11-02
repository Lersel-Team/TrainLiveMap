#!/usr/bin/env python3
"""Build data/rail.geojson from a Geofabrik Thailand extract (the data OpenRailwayMap draws).
Usage: rail_from_pbf.py thailand.osm.pbf data/rail.geojson   (needs: pip install osmium)
Keeps railway=rail main lines. Drops yards and sidings (service=*), and metro systems tagged as rail."""
import json, sys, collections
import osmium
SKIP = ('bts', 'bem', 'mrt', 'airport rail link', 'bangkok mass transit')
class H(osmium.SimpleHandler):
    def __init__(self):
        super().__init__(); self.f = []; self.ops = collections.Counter()
    def way(self, w):
        t = w.tags
        if t.get('railway') != 'rail' or 'service' in t: return
        op = (t.get('operator') or '').lower(); self.ops[op] += 1
        if any(x in op for x in SKIP): return
        c = [[round(n.lon, 5), round(n.lat, 5)] for n in w.nodes if n.location.valid()]
        if len(c) > 1: self.f.append({'type': 'Feature', 'properties': {}, 'geometry': {'type': 'LineString', 'coordinates': c}})
h = H(); h.apply_file(sys.argv[1], locations=True)
json.dump({'type': 'FeatureCollection', 'features': h.f}, open(sys.argv[2], 'w'), separators=(',', ':'))
print('ways', len(h.f), 'points', sum(len(x['geometry']['coordinates']) for x in h.f)); print(h.ops.most_common(12))
