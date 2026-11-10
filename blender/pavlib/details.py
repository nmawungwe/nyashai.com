"""Lived-in details near the web cameras.

Fruit bowl, loose papers and a pen on the table, a lantern hung from the purlin,
creepers on a post and the wall edge, fallen leaves, pebbles and tiny plants in
the paving, agave rosettes and pale flowers in the foreground grass.
"""

import math

import bmesh
from mathutils import Matrix, Vector

from . import config as C
from .architecture import paving_inside, roof_base
from .landscape import ground_z
from .materials import MATS
from .props import _obj, lathe, xf
from .util import add_cylinder, auto_smooth, object_from_bmesh, rng, rock_bmesh, tube
from .vegetation import _garden_spot, grass_source, leaf_source, scatter
from .views import hero_place, visible


def build(furn, veg, src):
    r = rng(101)
    _table_clutter(furn, r)
    _writing_still_life(furn, r)
    _lantern(furn, r)
    _creepers(veg, src, r)
    _paving_life(veg, src, r)
    _flowers_and_rosettes(veg, src, r)


# --- Table ---------------------------------------------------------------------------

def _table_clutter(coll, r):
    tx, ty = C.TABLE_CENTER
    top = C.TABLE_SIZE[2]
    # Glazed bowl with oranges and figs at the left end of the table.
    bx, by = tx - 0.78, ty - 0.12
    _obj("fruit_bowl", coll, MATS["ceramic_glaze"],
         lambda bm: lathe(bm, [(0.0, 0.0), (0.05, 0.0), (0.055, 0.008), (0.1, 0.04), (0.13, 0.075),
                               (0.125, 0.078), (0.095, 0.045), (0.05, 0.016), (0.0, 0.016)], 32),
         xf((bx, by, top)), smooth=True)
    fruit = [((0.0, 0.0), 0.04, "fruit_orange"), ((0.055, 0.03), 0.038, "fruit_orange"),
             ((-0.045, 0.035), 0.037, "fruit_orange"), ((0.02, -0.05), 0.036, "fruit_orange"),
             ((-0.04, -0.03), 0.028, "fruit_fig"), ((0.03, 0.0), 0.03, "fruit_fig")]
    for i, ((dx, dy), rad, mat) in enumerate(fruit):
        z = top + 0.03 + rad + (0.035 if i >= 4 else 0.0)
        bm = bmesh.new()
        rock_bmesh(bm, (bx + dx, by + dy, z), (rad, rad, rad * (0.92 if mat == "fruit_orange" else 1.1)), r,
                   subdiv=3, roughness=0.03, flatten_bottom=False)
        object_from_bmesh(f"fruit_{i}", bm, coll, MATS[mat], smooth=True)
    # Loose papers: one flat, one with a lifted corner; plus a second pen.
    for i, (dx, dy, yaw, lift) in enumerate(((0.38, -0.2, 0.25, 0.0), (0.5, -0.12, -0.15, 0.025))):
        _sheet(f"loose_paper_{i}", coll, xf((tx + dx, ty + dy, top + 0.001 + 0.0015 * i), yaw), lift)
    _obj("table_pen", coll, MATS["ink"],
         lambda bm: add_cylinder(bm, 0.0045, 0.14, (0, 0, 0), rot=(0, math.pi / 2, 0), segments=10),
         xf((tx + 0.42, ty - 0.27, top + 0.006), 0.9), smooth=True)
    # A loose sheet tucked under the notebook on the bench.
    _sheet("bench_paper", coll, xf((C.WALL_X0 + 2.17, C.WALL_Y - 0.33, C.BENCH_H + 0.001), 0.3), 0.0)


def _sheet(name, coll, M, lift):
    w, h, nu, nv = 0.21, 0.297, 6, 8
    bm = bmesh.new()
    grid = [[bm.verts.new(M @ Vector(((i / nu - 0.5) * w, (j / nv - 0.5) * h,
                                      lift * ((i / nu) * (j / nv)) ** 2)))
             for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    obj = object_from_bmesh(name, bm, coll, MATS["paper"], smooth=True)
    obj.modifiers.new("thickness", "SOLIDIFY").thickness = 0.0006


# --- Bench still life around the notebook ------------------------------------------------

def _writing_still_life(coll, r):
    nb = Vector((C.WALL_X0 + 1.85, C.WALL_Y - 0.27, C.BENCH_H))
    # Pressed leaf on the left page.
    leaf = leaf_source("pressed_leaf", coll, MATS["leaf_fallen"], 0.07, 0.04)
    leaf.location = nb + Vector((-0.08, 0.02, 0.0125))
    leaf.rotation_euler = (0.0, 0.0, 0.6)
    leaf.scale = (1.0, 1.0, 0.2)
    # Small glazed cup to the right of the notebook.
    _obj("bench_cup", coll, MATS["ceramic_glaze"],
         lambda bm: lathe(bm, [(0.0, 0.0), (0.028, 0.0), (0.034, 0.008), (0.04, 0.05), (0.036, 0.05),
                               (0.031, 0.01), (0.0, 0.01)], 24),
         xf(nb + Vector((0.27, 0.06, 0.0))), smooth=True)
    _obj("bench_cup_tea", coll, MATS["soil"],
         lambda bm: add_cylinder(bm, 0.035, 0.002, (0, 0, 0.038), segments=20), xf(nb + Vector((0.27, 0.06, 0.0))))
    # Reading glasses, folded, on the seat pad to the left.
    gM = xf(nb + Vector((-0.33, -0.02, 0.062)), 0.4)
    bm = bmesh.new()
    for sx in (-1, 1):
        ring = [Vector((sx * 0.033 + 0.025 * math.cos(t * math.pi / 8), 0.019 * math.sin(t * math.pi / 8), 0.012))
                for t in range(17)]
        tube(bm, [gM @ p for p in ring], [0.0022] * len(ring), sides=5, cap=False)
        arm = [Vector((sx * 0.058, 0.0, 0.012)), Vector((sx * 0.05, 0.03, 0.006)), Vector((-sx * 0.02, 0.04, 0.004))]
        tube(bm, [gM @ p for p in arm], [0.0015] * 3, sides=4)
    tube(bm, [gM @ Vector(p) for p in ((-0.008, 0.012, 0.014), (0.0, 0.016, 0.016), (0.008, 0.012, 0.014))],
         [0.0018] * 3, sides=4)
    object_from_bmesh("reading_glasses", bm, coll, MATS["lantern_metal"], smooth=True)


# --- Lantern ---------------------------------------------------------------------------

def _lantern(coll, r):
    x, y = 1.95, (C.POSTS[0][1] + C.WALL_Y - 0.15) / 2      # under the middle purlin
    hang = roof_base(x) + C.BEAM_H * 0.2
    top = 2.08
    bm = bmesh.new()
    links = int((hang - top) / 0.03)
    tube(bm, [Vector((x, y, hang - i * (hang - top) / links)) for i in range(links + 1)], [0.004] * (links + 1),
         sides=5)
    lathe(bm, [(0.0, top + 0.01), (0.025, top), (0.09, top - 0.05), (0.1, top - 0.06), (0.06, top - 0.06),
               (0.0, top - 0.055)], 20)
    lathe(bm, [(0.0, top - 0.27), (0.085, top - 0.27), (0.09, top - 0.25), (0.06, top - 0.24), (0.0, top - 0.24)], 20)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        p = Vector((x + 0.072 * math.cos(a), y + 0.072 * math.sin(a), 0))
        tube(bm, [p + Vector((0, 0, top - 0.25)), p + Vector((0, 0, top - 0.06))], [0.004, 0.004], sides=5)
    obj = object_from_bmesh("lantern_frame", bm, coll, MATS["lantern_metal"], smooth=True)
    auto_smooth(obj)
    _obj("lantern_glass", coll, MATS["lantern_glass"],
         lambda bm: lathe(bm, [(0.0, -0.09), (0.065, -0.09), (0.07, 0.0), (0.065, 0.09), (0.0, 0.09)], 20),
         xf((x, y, top - 0.155)), smooth=True)


# --- Creepers --------------------------------------------------------------------------

def _creeper_path(r, base, height, radius, turns, along=None):
    pts = []
    n = int(height / 0.06)
    phase = r.uniform(0, 6.28)
    for i in range(n + 1):
        t = i / n
        a = phase + t * turns * 2 * math.pi
        pts.append(Vector((base[0] + radius * math.cos(a), base[1] + radius * math.sin(a), base[2] + t * height)))
    if along is not None:
        start = pts[-1]
        for i in range(1, 12):
            pts.append(start + along * (i * 0.09) + Vector((0, 0, 0.02 * math.sin(i))))
    return pts


def _leaves_along(r, path, centre_fn, density, scale, out):
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        for _ in range(density):
            p = a.lerp(b, r.random())
            outward = p - centre_fn(p)
            outward.z = 0
            outward = outward.normalized() if outward.length > 1e-4 else Vector((1, 0, 0))
            loc = p + outward * r.uniform(0.0, 0.06) + Vector((0, 0, r.uniform(-0.03, 0.03)))
            yaw = math.atan2(outward.y, outward.x) + r.uniform(-1.0, 1.0)
            s = r.uniform(0.7, 1.3) * scale
            out.append((loc, (r.uniform(-0.6, 0.6), r.uniform(-1.2, -0.2), yaw), (s, s, s)))


def _creepers(coll, src, r):
    leaf = leaf_source("src_leaf_creeper", src, MATS["leaf_creeper"], 0.075, 0.06)
    stems = bmesh.new()
    pts = []
    # 1) Up the front-left corner post and a little way along the front beam.
    px, py = C.POSTS[0]
    h = roof_base(px)
    path = _creeper_path(r, (px, py, 0.0), h - 0.05, C.POST_SIZE * 0.62, 2.2, along=Vector((1, 0, 0.045)))
    tube(stems, path, [0.012 - 0.008 * i / len(path) for i in range(len(path))], sides=5)
    _leaves_along(r, path, lambda p: Vector((px, py, p.z)) if p.z < h - 0.1 else Vector((p.x, py + 0.3, p.z)),
                  16, 1.1, pts)
    # 2) Up the left edge of the rammed-earth wall, fanning onto its face.
    wx, wy = C.WALL_X0, C.WALL_Y
    starts = [(Vector((wx + 0.12, wy - 0.03, 0.0)), 2.3), (Vector((wx + 0.2, wy - 0.03, 0.0)), 1.6)]
    while starts:
        start, height = starts.pop()
        stem, heading = [start], r.uniform(-0.3, 0.6)
        while stem[-1].z < height:
            heading = max(-0.9, min(1.2, heading + r.uniform(-0.35, 0.35)))   # meandering climb
            stem.append(stem[-1] + Vector((0.05 * heading, 0.0, 0.06)))
            if len(stem) > 6 and r.random() < 0.06 and len(starts) < 6:      # side shoots
                starts.append((stem[-1].copy(), stem[-1].z + r.uniform(0.3, 0.8)))
        tube(stems, stem, [0.009 - 0.006 * i / len(stem) for i in range(len(stem))], sides=4)
        _leaves_along(r, stem, lambda p: Vector((p.x, wy + 0.3, p.z)), 6, 0.95, pts)
    object_from_bmesh("creeper_stems", stems, coll, MATS["bark"], smooth=True)
    scatter("creeper_leaves", coll, leaf, pts, radius=0.05)


# --- Paving: fallen leaves, pebbles, tiny plants ---------------------------------------------

def _paving_points(r, n, near_edge=0.0):
    x0, x1, y0, y1 = -0.9, C.RETURN_WALL_X, -6.5, C.WALL_Y - 0.05
    out, tries = [], 0
    while len(out) < n and tries < n * 50:
        tries += 1
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        if not paving_inside(x, y):
            continue
        if near_edge and r.random() < near_edge:
            # keep only points close to the paving outline or the pavilion walls/posts
            edge = any(not paving_inside(x + dx, y + dy) for dx, dy in ((0.35, 0), (-0.35, 0), (0, 0.35), (0, -0.35)))
            if not edge and y < C.WALL_Y - 0.6:
                continue
        if C.WALL_X0 < x < C.RETURN_WALL_X and y > C.WALL_Y - C.BENCH_D - 0.02:
            continue  # under the bench
        if not visible((x, y, 0.02), 0.1):
            continue
        out.append((x, y))
    return out


def _paving_life(coll, src, r):
    fallen = leaf_source("src_leaf_fallen", src, MATS["leaf_fallen"], 0.11, 0.06)
    pts = [(Vector((x, y, 0.022)), (r.uniform(-0.25, 0.25), r.uniform(-0.25, 0.25), r.uniform(0, 6.28)),
            (s, s, s)) for (x, y) in _paving_points(r, 380, near_edge=0.5) for s in [r.uniform(0.7, 1.3)]]
    scatter("fallen_leaves", coll, fallen, pts, cull=False)

    bm = bmesh.new()
    rock_bmesh(bm, (0, 0, 0.3), (1.0, 0.8, 0.6), r, subdiv=2, roughness=0.2, flatten_bottom=True)
    pebble = object_from_bmesh("src_pebble", bm, src, MATS["rock"], smooth=True)
    pts = [(Vector((x, y, 0.012)), (0, 0, r.uniform(0, 6.28)), (s, s * r.uniform(0.7, 1.0), s * 0.8))
           for (x, y) in _paving_points(r, 180, near_edge=0.85) for s in [r.uniform(0.015, 0.05)]]
    scatter("pebbles", coll, pebble, pts, cull=False)

    tuft = grass_source("src_paving_tuft", src, MATS["grass"], r, blades=6, height=0.16, width=0.02)
    pts = [(Vector((x, y, 0.012)), (0, 0, r.uniform(0, 6.28)), (s, s, s))
           for (x, y) in _paving_points(r, 45, near_edge=1.0) for s in [r.uniform(0.5, 1.0)]]
    scatter("paving_tufts", coll, tuft, pts, cull=False)


# --- Flowers and rosettes --------------------------------------------------------------------

def _flower_source(src):
    """Small umbel: a stem splitting into rays, each ending in a tiny rounded floret.

    The head is a loose dome, so it reads as a soft pale cluster from any angle
    (no camera-facing billboards). Slots: 0 stem, 1 florets, 2 floret centres.
    """
    r = rng(103)
    bm = bmesh.new()
    h = 0.4
    s0, s1, s2, s3 = (bm.verts.new(v) for v in ((-0.002, 0, 0), (0.002, 0, 0), (0.001, 0, h), (-0.001, 0, h)))
    bm.faces.new((s0, s1, s2, s3)).material_index = 0
    top = Vector((0, 0, h))
    for k in range(9):
        a = k * 2.4 + r.uniform(-0.3, 0.3)          # golden-angle spread
        spread = 0.012 + 0.03 * math.sqrt((k + 1) / 9)
        tip = top + Vector((spread * math.cos(a), spread * math.sin(a), 0.03 - 0.6 * spread ** 1.5 * 10))
        rv = (bm.verts.new(top), bm.verts.new(top + Vector((0.0015, 0, 0))), bm.verts.new(tip))
        bm.faces.new(rv).material_index = 0
        # Floret: a tiny rounded hexagon facing mostly up and outward.
        n = (tip - top + Vector((0, 0, 0.05))).normalized()
        t1 = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized()
        t2 = n.cross(t1)
        rad = r.uniform(0.006, 0.009)
        ring = [bm.verts.new(tip + (t1 * math.cos(j * math.pi / 3) + t2 * math.sin(j * math.pi / 3)) * rad)
                for j in range(6)]
        bm.faces.new(ring).material_index = 1
        dot = [bm.verts.new(tip + n * 0.0015 + (t1 * math.cos(j * math.pi / 2) + t2 * math.sin(j * math.pi / 2))
                            * rad * 0.3) for j in range(4)]
        bm.faces.new(dot).material_index = 2
    return object_from_bmesh("src_flower", bm, src,
                             [MATS["grass"], MATS["flower_petal"], MATS["flower_centre"]], smooth=True)


def _flowers_and_rosettes(coll, src, r):
    flower = _flower_source(src)
    pts = []
    for _ in range(18):  # a few drifts of flowers in the hero foreground and garden
        cf, cl = r.uniform(4.8, 11.0), r.uniform(-6.0, 0.8)
        for _ in range(r.randint(5, 11)):
            x, y, _ = hero_place(cf + r.gauss(0, 0.6), cl + r.gauss(0, 0.6))
            if not _garden_spot(x, y):
                continue
            z = ground_z(x, y)
            s = r.uniform(0.7, 1.3)
            pts.append((Vector((x, y, z)), (r.uniform(-0.2, 0.2), r.uniform(-0.2, 0.2), r.uniform(0, 6.28)),
                        (s, s, s * r.uniform(0.8, 1.2))))
    scatter("flowers", coll, flower, pts, radius=0.4)

    agave = grass_source("src_agave", src, MATS["agave"], r, blades=12, height=0.5, width=0.09)
    pts = []
    for f, lat in ((5.2, -0.4), (6.4, -1.8), (8.0, -3.2), (6.0, 0.6), (9.5, -0.9), (7.2, -5.0), (11.0, -2.4)):
        x, y, _ = hero_place(f, lat)
        if _garden_spot(x, y):
            s = r.uniform(0.8, 1.3)
            pts.append((Vector((x, y, ground_z(x, y))), (0, 0, r.uniform(0, 6.28)), (s, s, s * 0.9)))
    scatter("agave_rosettes", coll, agave, pts, radius=0.5)
