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
    def cyl_z(s, c, r, h, mat, n=10):
        x, y, z = c; ring = lambda zz: [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n), zz) for i in range(n)]
        A, B = ring(z - h / 2), ring(z + h / 2)
        s.face(A[::-1], mat); s.face(B, mat)
        for i in range(n): j = (i + 1) % n; s.face([A[i], A[j], B[j], B[i]], mat, smooth=True)
    def rod(s, p, q, r, mat):
        px, py, pz = p; qx, qy, qz = q; dx, dy, dz = qx - px, qy - py, qz - pz; l = math.sqrt(dx * dx + dy * dy + dz * dz) or 1
        ax = (dy, -dx, 0) if abs(dz) < l * .9 else (1, 0, 0); al = math.sqrt(sum(v * v for v in ax)) or 1; ax = [v / al * r for v in ax]
        ay = (dy * ax[2] - dz * ax[1], dz * ax[0] - dx * ax[2], dx * ax[1] - dy * ax[0]); ay = [v / l for v in ay]
        C = lambda o, i, j: (o[0] + i * ax[0] + j * ay[0], o[1] + i * ax[1] + j * ay[1], o[2] + i * ax[2] + j * ay[2])
        Q = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        for k in range(4):
            a, b = Q[k], Q[(k + 1) % 4]; s.face([C(p, *a), C(p, *b), C(q, *b), C(q, *a)], mat)
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


def roof_and_ends(m, L, hw, z0, zE, zTop, roofMat, xEnd, wAt, tex=0, n=20, arc=8, rows=None, ends=True):
    rows = rows or [z0, (z0 + zE) / 2, zE]
    arcs = [(math.cos(math.pi * i / arc / 2), zE + (zTop - zE) * math.sin(math.pi * i / arc / 2)) for i in range(arc + 1)]
    st = [-1 + 2 * i / n for i in range(n + 1)]
    pos = lambda t, z: t * xEnd(z)
    for i in range(n):
        a, b = st[i], st[i + 1]
        for k in range(arc * 2):
            def rp(t, j):
                cc, zz = arcs[j] if j <= arc else arcs[2 * arc - j]
                sgn = 1 if j <= arc else -1
                x = pos(t, zz); return (x, -sgn * wAt(x, zE) * cc, zz)
            m.face([rp(a, k), rp(b, k), rp(b, k + 1), rp(a, k + 1)], roofMat, smooth=True)
    if not ends: return
    H = zTop - z0
    levels = [(wAt(xEnd(z), z), z) for z in rows] + [(wAt(xEnd(zE), zE) * cc, zz) for cc, zz in arcs[1:]]
    wEnd = levels[0][0]
    uv = lambda y, z, sgn: ((sgn * y / (2 * wEnd) + .5) * .25, (z - z0) / H * .25)
    for sgn in (1, -1):
        for k in range(len(levels) - 1):
            (w1, z1), (w2, z2) = levels[k], levels[k + 1]; w2 = max(w2, .01)
            pts = [(sgn * xEnd(z1), -sgn * w1, z1), (sgn * xEnd(z1), sgn * w1, z1), (sgn * xEnd(z2), sgn * w2, z2), (sgn * xEnd(z2), -sgn * w2, z2)]
            m.face(pts, tex, [uv(p[1], p[2], sgn) for p in pts])

def side_uv(L, z0, zE, x, z, seen):
    u = (L / 2 - x) / L if seen > 0 else (x + L / 2) / L
    return (u, (.75 if seen > 0 else .5) + .25 * (z - z0) / (zE - z0))

def bogie(m, cx, axles, spacing, r, wheel, frame, axle, steel, motors=False):
    """Wheelsets, side frames with pedestals, coil springs, brake shoes, centre bolster."""
    g = .5; span = spacing * (axles - 1) + 1.1
    for i in range(axles):
        x = cx + (i - (axles - 1) / 2) * spacing
        m.box((x, 0, r), (.16, 1.25, .16), axle)
        if motors: m.cyl_y((x + .55, 0, r + .02), .3, .78, frame, n=10)
        for sy in (-1, 1):
            m.cyl_y((x, sy * g, r), r, .13, wheel, n=20)                # tread
            m.cyl_y((x, sy * (g + .07), r), r * .78, .03, steel, n=16)  # web
            m.cyl_y((x, sy * (g + .09), r), r * .28, .05, frame, n=10)  # hub
            m.cyl_y((x, sy * .96, r), .13, .22, steel, n=10)            # axle box
            m.box((x, sy * .96, r + .13), (.42, .26, .1), frame)
            for dx in (-.14, .14): m.cyl_z((x + dx, sy * .96, r + .32), .075, .34, steel, n=8)  # coil springs
            m.box((x + (r + .05) * (1 if i % 2 else -1), sy * g, r), (.08, .14, .34), frame)   # brake shoe
    for sy in (-1, 1):
        m.box((cx, sy * .96, r + .55), (span, .16, .18), frame)
        m.box((cx, sy * .96, r - .05), (span * .55, .1, .1), frame)
        for dx in (-span / 2 + .1, span / 2 - .1): m.box((cx + dx, sy * .96, r + .32), (.12, .14, .42), frame)
        m.cyl_z((cx, sy * .75, r + .62), .13, .3, steel, n=10)         # secondary spring
    m.box((cx, 0, r + .68), (.5, 1.9, .2), frame)
    for sx in (-1, 1): m.box((cx + sx * span / 2, 0, r + .55), (.12, 2.0, .16), frame)

def coupler(m, x, sgn, z, dark, steel):
    m.box((x, 0, z), (.5, .22, .2), dark)
    m.box((x + sgn * .3, 0, z), (.2, .32, .26), dark)
    for sy in (-.25, .25):
        m.rod((x, sy, z - .08), (x + sgn * .25, sy * 1.3, z - .36), .02, steel)

# =============================================================== QSY
def qsy(coll, tex):
    L, hw, z0, zE, zTop = 21.0, 1.44, 1.14, 3.12, 3.9
    TEX, ROOF, DARK, WHEEL, RED, YEL, STEEL, GLASS, BLACK, CHROME, RAIL = range(11)
    mats = [tex, flat('qsy_roof', (.72, .13, .15), .5), flat('dark', (.16, .16, .17), .75), flat('wheel', (.26, .25, .24), .5, .5), flat('red', (.72, .12, .14), .5),
            flat('hazard', (.86, .70, .08), .6), flat('steel', (.46, .47, .48), .6, .3), flat('glass', (.05, .08, .11), .12, .7), flat('black', (.05, .05, .06), .8), flat('chrome', (.72, .73, .75), .25, .9), flat('rail_y', (.86, .72, .1), .5)]
    m = M('QSY', mats)
    def xEnd(z): return L / 2 - (0 if z <= 2.42 else (z - 2.42) * .66)
    def wAt(x, z):
        over = max(0, abs(x) - (L / 2 - 1.15)); return (hw - .06 * max(0, z - z0) / (zE - z0)) - .36 * (over / 1.15) ** 1.7
    rows = [z0, 1.8, 2.42, zE]; n = 24; st = [-1 + 2 * i / n for i in range(n + 1)]
    # Extra stations near the ends so the chamfered cab corners read as curves
    st = sorted(set(st + [s * (1 - f) for s in (-1, 1) for f in (.02, .05, .08)]))
    for seen in (1, -1):
        for i in range(len(st) - 1):
            for k in range(len(rows) - 1):
                a, b = st[i], st[i + 1]; z1, z2 = rows[k], rows[k + 1]
                pts = [(t * xEnd(z), seen * wAt(t * xEnd(z), z), z) for t, z in ((a, z1), (b, z1), (b, z2), (a, z2))]
                if seen < 0: pts = [pts[1], pts[0], pts[3], pts[2]]
                m.face(pts, TEX, [side_uv(L, z0, zE, p[0], p[2], seen) for p in pts], smooth=True)
    roof_and_ends(m, L, hw, z0, zE, zTop, ROOF, xEnd, wAt, rows=rows, n=24)
    # Underframe, sole bar and walkway edge
    m.box((0, 0, 1.05), (L - .15, 2.86, .2), BLACK)
    m.box((0, 0, 1.14), (L - .05, 2.92, .05), DARK)
    for sx in (-1, 1):
        cx = sx * 6.7
        bogie(m, cx, 3, 1.9, .5, WHEEL, BLACK, DARK, STEEL, motors=True)
        ex = sx * (L / 2)
        # Cab front: windscreens (two panes), wipers, visor, lights, number box
        for sy in (-1, 1):
            zA, zB = 2.46, 3.14; y1, y2 = sy * .04, sy * 1.02
            xa, xb = sx * (xEnd(zA) + .02), sx * (xEnd(zB) + .02)
            pts = [(xa, y1, zA), (xa, y2, zA), (xb, y2 * .93, zB), (xb, y1, zB)]
            if sx * sy < 0: pts = pts[::-1]
            m.face(pts, GLASS)
            m.rod((xa + sx * .01, sy * .5, zA + .02), (xb + sx * .02, sy * .3, zB - .15), .012, BLACK)
            m.cyl_x((ex + sx * .02, sy * 1.0, 2.0), .1, .06, CHROME, n=12)         # headlight
            m.cyl_x((ex + sx * .02, sy * 1.0, 1.72), .06, .05, RED, n=10)          # marker
            m.rod((ex + sx * .05, sy * 1.28, 1.2), (ex + sx * .05, sy * 1.2, 2.2), .018, RAIL)   # front grab rail
            # Side door, steps, grab rails, rear-view mirror
            dx = sx * (L / 2 - 1.55)
            dy = sy * (wAt(dx, 1.9) + .012)
            for off in (-.44, .44): m.box((dx + off, dy, 1.9), (.03, .02, 1.5), DARK)
            m.box((dx, dy, 2.64), (.91, .02, .03), DARK)
            m.box((dx + .3 * sx, dy, 1.78), (.14, .03, .05), STEEL)   # door handle
            for zz, dd in ((.5, .38), (.78, .34), (1.03, .3)):
                m.box((dx, sy * 1.28, zz), (.72, dd, .05), YEL)
            for off in (-.5, .5):
                m.rod((dx + off, sy * 1.5, 1.05), (dx + off, sy * 1.5, 2.65), .017, RAIL)
                m.rod((dx + off, sy * 1.5, 1.05), (dx + off, sy * 1.46, .62), .017, RAIL)
            # Cab side window
            wx = sx * (L / 2 - 1.55)
            m.box((wx, sy * (hw - .02), 2.62), (.82, .05, .66), BLACK)
            m.box((wx, sy * (hw + .005), 2.62), (.72, .03, .56), GLASS)
            m.box((sx * (L / 2 - .92), sy * (hw - .14), 2.72), (.06, .24, .34), CHROME)
        # Visor over the windscreen and horns on the roof
        m.box((sx * (xEnd(3.2) + .08), 0, 3.2), (.22, 2.2, .05), BLACK)
        for sy in (-.28, .28): m.cyl_x((sx * (xEnd(3.8) - .4), sy, 3.92), .055, .38, CHROME, n=8)
        # Snowplough: faceted V in red with a hazard panel
        for sy in (-1, 1):
            pts = [(ex + sx * .36, 0, .22), (ex - sx * .02, sy * 1.28, .22), (ex - sx * .02, sy * 1.28, 1.02), (ex + sx * .22, 0, 1.02)]
            if sx * sy > 0: pts = pts[::-1]
            m.face(pts, RED)
            for i in range(4):
                t0, t1 = i / 4, (i + .5) / 4
                A = lambda t, z: (ex + sx * (.36 - .38 * t) + sx * .012, sy * 1.28 * t, z)
                q = [A(t0, .26), A(t1, .26), A(t1, .5), A(t0, .5)]
                if sx * sy > 0: q = q[::-1]
                m.face(q, YEL)
        m.box((ex + sx * .08, 0, 1.08), (.3, 2.6, .14), BLACK)
        coupler(m, ex + sx * .3, sx, .92, BLACK, STEEL)
        # Roof grab and cab roof hatch
        m.box((sx * (L / 2 - 2.5), 0, zTop + .02), (.9, .9, .12), STEEL)
    # Fuel tank with baffles, air reservoirs, battery boxes
    m.box((0, 0, .72), (5.8, 2.3, .62), BLACK)
    for x in (-2.8, -1.4, 0, 1.4, 2.8): m.box((x, 0, .72), (.06, 2.34, .66), DARK)
    for sy in (-1, 1):
        m.cyl_x((.0, sy * .72, .28), .19, 3.2, STEEL, n=12)
        m.box((-3.5, sy * 1.25, .85), (1.1, .25, .5), DARK); m.box((3.5, sy * 1.25, .85), (1.1, .25, .5), DARK)
        # Radiator louvres at the No.2 end: dark recess with individual slats
        wy = sy * (hw - .05 * .85)
        m.box((-7.55, wy, 2.45), (2.1, .04, 1.05), BLACK)
        for i in range(22):
            z = 1.95 + i * .048; m.box((-7.55, sy * (hw - .02 - .05 * (z - z0) / (zE - z0)), z), (2.04, .05, .02), STEEL)
        for x in (-8.6, -6.5): m.box((x, wy, 2.45), (.05, .07, 1.09), STEEL)
        m.box((-7.55, wy, 3.0), (2.15, .07, .05), STEEL); m.box((-7.55, wy, 1.92), (2.15, .07, .05), STEEL)
        # Small engine-room window, intake grille high on the body
        m.box((-5.7, sy * (hw - .04), 2.68), (.42, .03, .5), GLASS)
        m.box((3.2, sy * (hw - .05), 2.92), (1.6, .03, .22), BLACK)
    # Roof: radiator fan housing with fans, dynamic brake grid, exhaust stack, antennas
    m.box((-7.5, 0, zTop - .12), (3.6, 1.7, .22), DARK)
    for x in (-8.5, -6.5):
        m.cyl_z((x, 0, zTop + .02), .62, .08, BLACK, n=20)
        for a in range(6): m.rod((x, 0, zTop + .07), (x + .6 * math.cos(a * 1.047), .6 * math.sin(a * 1.047), zTop + .07), .025, STEEL)
    m.box((-2.0, 0, zTop - .02), (3.0, 1.3, .2), DARK)
    for i in range(16): m.box((-3.4 + i * .19, 0, zTop + .09), (.05, 1.24, .04), BLACK)
    m.cyl_z((1.1, .22, zTop + .05), .16, .24, BLACK, n=10); m.cyl_z((1.1, -.22, zTop + .05), .16, .24, BLACK, n=10)
    m.box((3.5, 0, zTop - .02), (2.6, 1.1, .16), STEEL)
    m.rod((5.8, .4, zTop), (5.8, .4, zTop + .42), .012, BLACK)
    # Long hand rails along the body
    return m.finish(coll)

# =============================================================== BTC, after B.T.C. 294
WINDOWS = (-7.35, -5.25, -3.15, -1.05, 1.05, 3.15, 5.25, 7.35)
WIN_W, WZ1, WZ2 = 1.25, 1.72, 2.52
def btc(coll, tex):
    L, hw, z0, zE, zTop = 20.0, 1.42, 1.0, 3.1, 3.72
    TEX, ROOF, DARK, WHEEL, STEEL, FRAME, INT, BLACK, GUTTER = range(9)
    mats = [tex, flat('btc_roof', (.74, .72, .64), .85), flat('dark', (.16, .16, .17), .75), flat('wheel', (.26, .25, .24), .5, .5), flat('steel', (.46, .47, .48), .6, .3),
            flat('win_frame', (.36, .38, .40), .4, .5), flat('interior', (.09, .09, .10), .9), flat('black', (.05, .05, .06), .8), flat('gutter', (.58, .57, .52), .7)]
    m = M('BTC', mats)
    def wall_y(z): return hw - (.13 * ((1.35 - z) / .35) ** 2 if z < 1.35 else 0)  # sill turns under
    uv = lambda x, z, seen: side_uv(L, z0, zE, x, z, seen)
    DOOR = 8.65; DW = .48; DZ2 = 2.78
    ops = [(c - WIN_W / 2, c + WIN_W / 2, WZ1, WZ2, 'w') for c in WINDOWS] + [(s * DOOR - DW, s * DOOR + DW, z0, DZ2, 'd') for s in (-1, 1)]
    xs = sorted({-L / 2, L / 2} | {o[0] for o in ops} | {o[1] for o in ops})
    zs = [z0, 1.12, 1.24, 1.35, WZ1, WZ2, DZ2, zE]
    def inside(xa, xb, za, zb):
        for o in ops:
            if xa >= o[0] - 1e-6 and xb <= o[1] + 1e-6 and za >= o[2] - 1e-6 and zb <= o[3] + 1e-6: return o
    for seen in (1, -1):
        def quad(pts, mat, uvs=None, smooth=False):
            if seen < 0: pts = [pts[1], pts[0], pts[3], pts[2]]; uvs = uvs and [uvs[1], uvs[0], uvs[3], uvs[2]]
            m.face(pts, mat, uvs, smooth)
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            for k in range(len(zs) - 1):
                za, zb = zs[k], zs[k + 1]
                if inside(xa, xb, za, zb): continue
                P = [(xa, seen * wall_y(za), za), (xb, seen * wall_y(za), za), (xb, seen * wall_y(zb), zb), (xa, seen * wall_y(zb), zb)]
                quad(P, TEX, [uv(p[0], p[2], seen) for p in P], smooth=za < 1.35)
        for o in ops:
            a, b, c, d, kind = o; depth = .07 if kind == 'w' else .62
            yo, yi = seen * hw, seen * (hw - depth)
            # Reveal: sill, head and jambs
            for Q in ([(a, yi, c), (b, yi, c), (b, yo, c), (a, yo, c)], [(a, yo, d), (b, yo, d), (b, yi, d), (a, yi, d)], [(a, yi, c), (a, yo, c), (a, yo, d), (a, yi, d)], [(b, yo, c), (b, yi, c), (b, yi, d), (b, yo, d)]):
                quad(Q, FRAME if kind == 'w' else INT)
            if kind == 'w':
                pane = [(a, yi, c), (b, yi, c), (b, yi, d), (a, yi, d)]
                quad(pane, TEX, [uv(p[0], p[2], seen) for p in pane])
                m.box(((a + b) / 2, seen * (hw + .012), c - .02), (b - a + .1, .05, .04), FRAME)       # drip sill
                m.box(((a + b) / 2, seen * (hw + .012), d + .03), (b - a + .1, .05, .03), FRAME)       # head
                for x in (a - .03, b + .03): m.box((x, seen * (hw + .008), (c + d) / 2), (.03, .04, d - c + .05), FRAME)
            else:
                back = [(a, yi, c), (b, yi, c), (b, yi, d), (a, yi, d)]
                quad(back, INT)
                m.box(((a + b) / 2, seen * (hw - .32), z0 + .02), (b - a, .6, .04), DARK)              # vestibule floor
                ins = 1 if a > 0 else -1
                m.box(((a + b) / 2, seen * (hw - .62), 1.9), (.62, .02, 1.7), STEEL)                   # inner door
                m.box(((a + b) / 2, seen * (hw - .64), 2.25), (.4, .02, .55), INT)
                for x in (a - .05, b + .05):                                                           # grab rails, as photographed
                    m.rod((x, seen * (hw + .06), 1.25), (x, seen * (hw + .06), 2.6), .017, STEEL)
                    m.rod((x, seen * (hw + .06), 2.6), (x, seen * (hw - .02), 2.65), .017, STEEL)
                    m.rod((x, seen * (hw + .06), 1.25), (x, seen * (hw - .02), 1.18), .017, STEEL)
                cx = (a + b) / 2
                for zz, dd, oy in ((.42, .28, .0), (.72, .26, -.02)):                                  # step treads
                    m.box((cx, seen * (hw - .02 + oy), zz), (b - a, dd, .04), STEEL)
                for x in (a + .02, b - .02): m.box((x, seen * (hw - .02), .68), (.04, .24, .72), DARK)  # step hangers
        # Gutter along the eave
        m.box((0, seen * (hw + .012), zE + .015), (L, .05, .05), GUTTER)
    # Roof with low ventilators and rain strip
    roof_and_ends(m, L, hw, z0, zE, zTop, ROOF, lambda z: L / 2, lambda x, z: hw, rows=[z0, zE], n=20, arc=8, ends=True)
    for x in (-7.5, -5, -2.5, 0, 2.5, 5, 7.5):
        m.cyl_z((x, 0, zTop + .03), .13, .08, GUTTER, n=10); m.cyl_z((x, 0, zTop + .08), .17, .03, GUTTER, n=10)
    m.box((0, 0, 1.0), (L - .1, 2.62, .08), BLACK)
    m.box((0, 0, .92), (L - .4, 2.2, .1), DARK)
    for sx in (-1, 1):
        bogie(m, sx * 7.0, 2, 2.1, .43, WHEEL, BLACK, DARK, STEEL)
        ex = sx * L / 2
        coupler(m, ex + sx * .22, sx, .85, BLACK, STEEL)
        # End: gangway door, bellows frame, tail lamp brackets, ladder rungs
        m.box((ex + sx * .01, 0, 2.05), (.04, .98, 1.95), DARK)
        m.box((ex + sx * .03, 0, 2.55), (.03, .46, .62), INT)
        m.box((ex + sx * .1, 0, 3.05), (.2, 1.1, .08), BLACK)
        for sy in (-1, 1):
            m.box((ex + sx * .1, sy * .55, 2.05), (.2, .08, 2.0), BLACK)
            m.rod((ex + sx * .05, sy * .9, 1.15), (ex + sx * .05, sy * .9, 2.9), .016, STEEL)
            m.cyl_x((ex + sx * .03, sy * 1.1, 1.3), .07, .05, DARK, n=8)
        m.box((ex + sx * .12, 0, 1.0), (.25, 1.3, .1), STEEL)                                          # gangway plate
    # Under-floor gear: truss rods, battery box, water tank, generator, brake cylinder
    for sy in (-1, 1):
        m.rod((-4.5, sy * 1.0, .9), (-2.2, sy * 1.0, .5), .025, STEEL); m.rod((-2.2, sy * 1.0, .5), (2.2, sy * 1.0, .5), .025, STEEL); m.rod((2.2, sy * 1.0, .5), (4.5, sy * 1.0, .9), .025, STEEL)
    for x, w, h in ((-3.3, 1.5, .34), (-1.1, 1.3, .4), (1.2, 1.8, .36), (3.5, 1.2, .3)):
        m.box((x, 0, .9 - h / 2 - .05), (w, 1.5, h), BLACK)
        for i in range(int(w / .3)): m.box((x - w / 2 + .15 + i * .3, .76, .9 - h / 2 - .05), (.05, .02, h - .05), DARK)
    m.cyl_x((.0, .55, .42), .15, 1.6, STEEL, n=10)
    return m.finish(coll)

# =============================================================== CNR stainless set
def cnr(coll, name, tex, c):
    L, hw, z0, zE, zTop = 23.0, 1.46, 1.0, 3.2, 3.78
    TEX, ROOF, DARK, WHEEL, STEEL, FRAME, GLASS, BLACK, YEL, TAIL = range(10)
    mats = [tex, flat('cnr_roof', (.60, .61, .62), .55, .4), flat('dark', (.16, .16, .17), .75), flat('wheel', (.26, .25, .24), .5, .5), flat('steel', (.46, .47, .48), .6, .3),
            flat('cnr_frame', (.14, .15, .16), .5), flat('glass', (.05, .08, .11), .12, .7), flat('black', (.05, .05, .06), .8), flat('cnr_yel', (.86, .62, .08), .55), flat('tail', (.85, .08, .08), .4)]
    m = M(name.upper(), mats)
    def wall_y(z): return hw - (.08 * ((1.25 - z) / .25) ** 2 if z < 1.25 else 0)
    uv = lambda x, z, seen: side_uv(L, z0, zE, x, z, seen)
    ww, z1, z2 = c['ww'], c['z1'], c['z2']
    ops = [(x - ww / 2, x + ww / 2, z1, z2) for x in c['windows']]
    xs = sorted({-L / 2, L / 2} | {o[0] for o in ops} | {o[1] for o in ops})
    zs = [z0, 1.12, 1.25, z1, z2, zE]
    def hole(xa, xb, za, zb):
        return any(xa >= o[0] - 1e-6 and xb <= o[1] + 1e-6 and za >= o[2] - 1e-6 and zb <= o[3] + 1e-6 for o in ops)
    for seen in (1, -1):
        def quad(P, mat, uvs=None):
            if seen < 0: P = [P[1], P[0], P[3], P[2]]; uvs = uvs and [uvs[1], uvs[0], uvs[3], uvs[2]]
            m.face(P, mat, uvs)
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            for k in range(len(zs) - 1):
                za, zb = zs[k], zs[k + 1]
                if hole(xa, xb, za, zb): continue
                P = [(xa, seen * wall_y(za), za), (xb, seen * wall_y(za), za), (xb, seen * wall_y(zb), zb), (xa, seen * wall_y(zb), zb)]
                quad(P, TEX, [uv(p[0], p[2], seen) for p in P])
        for a, b, cc, d in ops:
            yo, yi = seen * hw, seen * (hw - .05)
            for Q in ([(a, yi, cc), (b, yi, cc), (b, yo, cc), (a, yo, cc)], [(a, yo, d), (b, yo, d), (b, yi, d), (a, yi, d)], [(a, yi, cc), (a, yo, cc), (a, yo, d), (a, yi, d)], [(b, yo, cc), (b, yi, cc), (b, yi, d), (b, yo, d)]):
                quad(Q, FRAME)
            quad([(a, yi, cc), (b, yi, cc), (b, yi, d), (a, yi, d)], GLASS)
        for sx in (-1, 1):
            dx = sx * 10.75                                   # plug door: outline, window, handle, step
            dy = seen * (hw + .006)
            m.box((dx, dy, 1.95), (.9, .012, 1.7), BLACK); m.box((dx, seen * (hw + .012), 1.95), (.84, .012, 1.64), STEEL)
            m.box((dx, seen * (hw + .018), 2.42), (.46, .012, .62), GLASS)
            m.box((dx, seen * (hw - .02), .78), (.8, .24, .05), STEEL); m.box((dx, seen * (hw - .02), .52), (.8, .24, .05), STEEL)
            for off in (-.5, .5): m.rod((dx + off, seen * (hw + .05), 1.2), (dx + off, seen * (hw + .05), 2.55), .015, STEEL)
    roof_and_ends(m, L, hw, z0, zE, zTop, ROOF, lambda z: L / 2, lambda x, z: hw, rows=[z0, zE], n=22, arc=8)
    for sy in (-1, 1): m.box((0, sy * (hw + .01), zE + .02), (L, .04, .04), STEEL)   # gutter
    # Roof A/C package at each end with its louvres; end walls, gangway, tail lamps, ladder rungs
    for sx in (-1, 1):
        ex = sx * L / 2
        m.box((sx * (L / 2 - 1.5), 0, zTop + .12), (2.6, 2.0, .36), DARK)
        for i in range(10): m.box((sx * (L / 2 - 2.65 + i * .25), 0, zTop + .31), (.1, 1.9, .04), BLACK)
        for sy in (-1, 1):
            for i in range(8): m.box((sx * (L / 2 - 2.5 + i * .25), sy * 1.01, zTop + .12), (.1, .02, .26), STEEL)
            m.cyl_x((ex + sx * .03, sy * .95, 2.95), .07, .04, TAIL, n=10)
            for z in (1.5, 1.85, 2.2, 2.55): m.box((ex + sx * .04, sy * .62, z), (.05, .28, .03), BLACK)
        # Gangway door with its window, and the bellows frame around it
        m.box((ex + sx * .01, 0, 1.98), (.03, .92, 2.0), FRAME)
        m.box((ex + sx * .025, 0, 1.98), (.02, .84, 1.92), YEL)
        m.box((ex + sx * .04, 0, 2.5), (.02, .36, .66), GLASS)
        m.box((ex + sx * .06, 0, 1.0), (.2, 1.3, .08), STEEL)
        bogie(m, sx * 8.1, 2, 2.4, .43, WHEEL, BLACK, DARK, STEEL)
        coupler(m, ex + sx * .22, sx, .86, BLACK, STEEL)
        for sy in (-.4, .4): m.box((ex + sx * .1, sy, .95), (.15, .1, .14), STEEL)   # hose brackets, as in the photo
    # Equipment skirt and under-floor boxes
    m.box((0, 0, .96), (L - .1, 2.72, .08), BLACK)
    for x, w, h in ((-4.2, 2.2, .46), (-1.3, 1.9, .5), (1.4, 2.2, .46), (4.3, 2.0, .42)):
        m.box((x, 0, .92 - h / 2), (w, 2.4, h), DARK)
        for i in range(int(w / .4)):
            for sy in (-1, 1): m.box((x - w / 2 + .2 + i * .4, sy * 1.21, .92 - h / 2), (.04, .02, h - .06), BLACK)
    return m.finish(coll)

coll = bpy.data.collections.get('TrainLiveMap') or bpy.data.collections.new('TrainLiveMap')
if coll.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(coll)
for o in list(coll.objects):
    me = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
import json
layouts = json.load(open(os.path.join(HERE, 'cnr_layouts.json')))
vehicles = [(qsy(coll, textured('qsy_body', os.path.join(HERE, 'qsy.jpg'))), 'qsy'), (btc(coll, textured('btc_body', os.path.join(HERE, 'btc.jpg'))), 'btc')]
for name, c in layouts.items():
    vehicles.append((cnr(coll, name, textured(name + '_body', os.path.join(HERE, name + '.jpg')), c), name))
for i, (ob, name) in enumerate(vehicles): ob.location.y = 5 * i
bpy.context.view_layer.update()
os.makedirs(OUT, exist_ok=True)
for ob, name in vehicles:
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    loc = ob.location.copy(); ob.location = (0, 0, 0); bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', use_selection=True, export_yup=True, export_apply=False, export_animations=False, export_cameras=False, export_lights=False, export_image_format='AUTO')
    ob.location = loc
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons); print(name, 'tris', tris, 'bytes', os.path.getsize(os.path.join(OUT, name + '.glb')))
bpy.context.view_layer.update()
