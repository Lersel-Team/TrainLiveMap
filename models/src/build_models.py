"""Run inside Blender 4.4: builds the QSY and BTC vehicles, exports web/models/{qsy,btc}.glb.
Forward is +X, rail level is Z=0, origin at the vehicle centre.
Dimensions are estimates from side diagrams and photos, not manufacturer drawings."""
import bpy, math, os
HERE = globals().get('MODEL_SRC') or os.path.dirname(bpy.data.filepath)
OUT = os.path.join(HERE, '..', '..', 'web', 'models')

class M:
    def __init__(s, name, mats): s.name, s.mats, s.v, s.f, s.fm, s.uv, s.sm = name, mats, [], [], [], [], []
    def pt(s, p): s.v.append(tuple(p)); return len(s.v) - 1
    def face(s, pts, mat, uv=None, smooth=False):
        s.f.append([s.pt(p) for p in pts]); s.fm.append(mat); s.uv.append(uv or [(0, 0)] * len(pts)); s.sm.append(smooth)
    def box(s, c, d, mat):
        x, y, z = c; a, b, e = d[0] / 2, d[1] / 2, d[2] / 2
        P = [(x + i * a, y + j * b, z + k * e) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)): s.face([P[i] for i in q], mat)
    def cyl_y(s, c, r, w, mat, n=14):
        x, y, z = c; ring = lambda yy: [(x + r * math.cos(2 * math.pi * i / n), yy, z + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        A, B = ring(y - w / 2), ring(y + w / 2)
        s.face(A, mat); s.face(B[::-1], mat)
        for i in range(n): j = (i + 1) % n; s.face([A[j], A[i], B[i], B[j]], mat, smooth=True)
    def cyl_x(s, c, r, l, mat, n=12):
        x, y, z = c; ring = lambda xx: [(xx, y + r * math.cos(2 * math.pi * i / n), z + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        A, B = ring(x - l / 2), ring(x + l / 2)
        s.face(A[::-1], mat); s.face(B, mat)
        for i in range(n): j = (i + 1) % n; s.face([A[i], A[j], B[j], B[i]], mat, smooth=True)
    def finish(s, coll):
        me = bpy.data.meshes.new(s.name); me.from_pydata(s.v, [], s.f); me.update()
        for m in s.mats: me.materials.append(m)
        uvl = me.uv_layers.new(name='UV').data
        for poly, mi, uv, sm in zip(me.polygons, s.fm, s.uv, s.sm):
            poly.material_index, poly.use_smooth = mi, sm
            for li, u in zip(poly.loop_indices, uv): uvl[li].uv = u
        ob = bpy.data.objects.new(s.name, me); coll.objects.link(ob); return ob

def flat(name, rgb, rough=.8, metal=0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*[c ** 2.2 for c in rgb], 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    return m
def textured(name, path):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree
    b = next(n for n in t.nodes if n.type == 'BSDF_PRINCIPLED'); b.inputs['Roughness'].default_value = .6
    for n in [n for n in t.nodes if n.type == 'TEX_IMAGE']: t.nodes.remove(n)
    i = t.nodes.new('ShaderNodeTexImage'); i.image = bpy.data.images.load(path, check_existing=False); i.image.pack(); t.links.new(i.outputs['Color'], b.inputs['Base Color'])
    return m

def shell(m, L, hw, z0, zE, zTop, roofMat, xEnd, wAt, tex=0, n=20, arc=8):
    """Body: both sides, roof and end faces sharing one outline. xEnd(z) gives the end position at height z, wAt(x) the half width."""
    rows = [z0, (z0 + zE) / 2 + .3, zE]
    arcs = [(math.cos(math.pi * i / arc / 2), zE + (zTop - zE) * math.sin(math.pi * i / arc / 2)) for i in range(arc + 1)]
    st = [-1 + 2 * i / n for i in range(n + 1)]
    pos = lambda t, z: t * xEnd(z)
    def sideUV(x, z, seen):
        u = (L / 2 - x) / L if seen > 0 else (x + L / 2) / L
        b = .75 if seen > 0 else .5
        return (u, b + .25 * (z - z0) / (zE - z0))
    for seen in (1, -1):
        for i in range(n):
            for k in range(len(rows) - 1):
                a, b = st[i], st[i + 1]; z1, z2 = rows[k], rows[k + 1]
                Q = [(a, z1), (b, z1), (b, z2), (a, z2)]
                pts = [(pos(t, z), seen * wAt(pos(t, z), z), z) for t, z in Q]
                if seen < 0: pts = [pts[1], pts[0], pts[3], pts[2]]
                m.face(pts, tex, [sideUV(p[0], p[2], seen) for p in pts])
    for i in range(n):
        a, b = st[i], st[i + 1]
        for k in range(arc * 2):
            def rp(t, j):
                cc, zz = arcs[j] if j <= arc else arcs[2 * arc - j]
                sgn = 1 if j <= arc else -1
                x = pos(t, zz); return (x, -sgn * wAt(x, zE) * cc, zz)
            # j runs from -Y eave over the top to +Y eave
            m.face([rp(a, k), rp(b, k), rp(b, k + 1), rp(a, k + 1)], roofMat, smooth=True)
    # End faces: horizontal bands across the outline, planar UV from the end atlas cell
    H = zTop - z0
    levels = [(wAt(xEnd(z), z), z) for z in rows] + [(wAt(xEnd(zE), zE) * cc, zz) for cc, zz in arcs[1:]]
    def endUV(y, z, sgn): return ((sgn * y / (2 * hw) + .5) * .25, (z - z0) / H * .25)
    for sgn in (1, -1):
        for k in range(len(levels) - 1):
            (w1, z1), (w2, z2) = levels[k], levels[k + 1]
            pts = [(sgn * xEnd(z1), -sgn * w1, z1), (sgn * xEnd(z1), sgn * w1, z1), (sgn * xEnd(z2), sgn * max(w2, .01), z2), (sgn * xEnd(z2), -sgn * max(w2, .01), z2)]
            m.face(pts, tex, [endUV(p[1], p[2], sgn) for p in pts])

def bogie(m, cx, axles, spacing, r, wheel, frame, axle):
    gauge = .5
    for i in range(axles):
        x = cx + (i - (axles - 1) / 2) * spacing
        for sy in (-1, 1): m.cyl_y((x, sy * gauge, r), r, .14, wheel)
        m.box((x, 0, r), (.14, 1.0, .14), axle)
        for sy in (-1, 1): m.box((x, sy * 1.0, r + .05), (.42, .22, .3), axle)  # axle box and spring
    span = spacing * (axles - 1) + 1.0
    for sy in (-1, 1): m.box((cx, sy * .86, r + .3), (span, .14, .34), frame)
    m.box((cx, 0, r + .42), (span * .55, 1.7, .16), frame)

def qsy(coll, tex):
    L, hw, z0, zE, zTop = 21.0, 1.44, 1.14, 3.12, 3.9
    mats = [tex, flat('qsy_roof', (.84, .14, .17)), flat('dark', (.11, .12, .13)), flat('wheel', (.2, .2, .21), .5, .6), flat('red', (.82, .13, .16)), flat('hazard', (.93, .78, .1)), flat('steel', (.55, .56, .58), .5, .4)]
    m = M('QSY', mats)
    def xEnd(z): return L / 2 - (0 if z <= 2.45 else (z - 2.45) * .62)
    def wAt(x, z):
        over = max(0, abs(x) - (L / 2 - 1.1)); return (hw - .05 * max(0, z - z0) / (zE - z0)) - .34 * (over / 1.1) ** 1.6
    shell(m, L, hw, z0, zE, zTop, 1, xEnd, wAt)
    m.box((0, 0, 1.0), (L - .1, 2.82, .28), 2)                       # underframe
    for sx in (-1, 1):
        bogie(m, sx * 6.6, 3, 1.85, .5, 3, 2, 2)
        m.face([(sx * (L / 2 + .25), -1.25, .35), (sx * (L / 2 + .25), 1.25, .35), (sx * (L / 2 - .15), 1.25, 1.0), (sx * (L / 2 - .15), -1.25, 1.0)] if sx > 0 else [(sx * (L / 2 + .25), 1.25, .35), (sx * (L / 2 + .25), -1.25, .35), (sx * (L / 2 - .15), -1.25, 1.0), (sx * (L / 2 - .15), 1.25, 1.0)], 4)  # snowplough
        m.box((sx * (L / 2 - .2), 0, .62), (.3, 1.0, .18), 5)            # yellow panel
        m.box((sx * (L / 2 + .3), 0, .95), (.7, .3, .24), 2)             # coupler
        for sy in (-1, 1): m.box((sx * (L / 2 - 1.0), sy * 1.28, .75), (.55, .18, .75), 6)  # cab steps
    m.box((0, 0, .72), (5.6, 2.2, .86), 2)                           # fuel tank
    for sy in (-1, 1): m.cyl_x((-.2, sy * .55, .42), .24, 3.0, 6)    # air reservoirs
    m.box((-5.3, 0, zTop - .02), (3.4, 1.5, .16), 2)                 # radiator top
    m.box((-1.0, 0, zTop + .02), (2.2, 1.1, .2), 2)                  # exhaust hatch
    for sx in (-1, 1): m.box((sx * (L / 2 - 1.6), 0, zTop + .02), (.8, .8, .16), 6)
    return m.finish(coll)

def btc(coll, tex):
    L, hw, z0, zE, zTop = 20.0, 1.42, 1.0, 3.1, 3.72
    mats = [tex, flat('btc_roof', (.86, .84, .76)), flat('dark', (.11, .12, .13)), flat('wheel', (.2, .2, .21), .5, .6), flat('steel', (.55, .56, .58), .5, .4)]
    m = M('BTC', mats)
    shell(m, L, hw, z0, zE, zTop, 1, lambda z: L / 2, lambda x, z: hw - .03 * max(0, z - z0) / (zE - z0), n=16, arc=6)
    m.box((0, 0, .88), (L - .1, 2.6, .22), 2)
    for sx in (-1, 1):
        bogie(m, sx * 7.0, 2, 2.1, .43, 3, 2, 2)
        m.box((sx * (L / 2 + .25), 0, .85), (.55, .3, .22), 2)
        for sy in (-1, 1):
            m.box((sx * (L / 2 - .55), sy * 1.3, .72), (.75, .14, .22), 4); m.box((sx * (L / 2 - .55), sy * 1.3, .45), (.75, .14, .1), 4)
    for x in (-3.5, -1, 1.5, 3.5): m.box((x, 0, .6), (1.6, 1.7, .4), 2)
    return m.finish(coll)

coll = bpy.data.collections.get('TrainLiveMap') or bpy.data.collections.new('TrainLiveMap')
if coll.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(coll)
for o in list(coll.objects): bpy.data.objects.remove(o)
a = qsy(coll, textured('qsy_body', os.path.join(HERE, 'qsy.png')))
b = btc(coll, textured('btc_body', os.path.join(HERE, 'btc.png')))
b.location.y = 5
bpy.context.view_layer.update()
os.makedirs(OUT, exist_ok=True)
for ob, name in ((a, 'qsy'), (b, 'btc')):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    loc = ob.location.copy(); ob.location = (0, 0, 0); bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', use_selection=True, export_yup=True, export_apply=False, export_animations=False, export_cameras=False, export_lights=False)
    ob.location = loc
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons); print(name, 'tris', tris, 'bytes', os.path.getsize(os.path.join(OUT, name + '.glb')))
bpy.context.view_layer.update()
