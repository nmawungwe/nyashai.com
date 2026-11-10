"""Terrain plateau, terrace walls, boulders and vineyard stakes (distant hills: matte.py)."""

import math

import bmesh
from mathutils import Vector, noise

from .architecture import paving_inside
from .materials import MATS
from .util import add_box, object_from_bmesh, object_from_data, rng, rock_bmesh
from .views import hero_place, visible

KEEP_RADIUS = 30.0   # terrain this close to the pavilion is always kept

# Plateau ellipse (normalised distance 1 = terrace edge with the retaining wall).
PLATEAU_C = (2.0, -1.0)
PLATEAU_R = (6.0, 9.0)
TERRACE_DROP = 0.7


def plateau_d(x, y):
    dx = (x - PLATEAU_C[0]) / PLATEAU_R[0]
    dy = (y - PLATEAU_C[1]) / PLATEAU_R[1]
    return math.hypot(dx, dy)


def _smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def ground_z(x, y):
    """Height of the ground. Flat plateau, one lower terrace, then the valley."""
    d = plateau_d(x, y)
    n = noise.fractal(Vector((x * 0.05, y * 0.05, 0.3)), 0.6, 2.0, 4)
    z = -TERRACE_DROP * _smooth(0.99, 1.03, d)
    if d > 1.5:
        # Approximate metres beyond the lower terrace; ease down into a shallow valley
        # so the far slopes and ridges stay visible from eye height.
        beyond = (d - 1.5) * 7.0
        # A real valley below the hilltop terrace, as in the artwork: the matte
        # painting's valley then shows above it from the pavilion.
        z -= 45.0 * (1.0 - math.exp(-beyond / 30.0))
    bump = 0.12 * _smooth(1.0, 1.4, d) + 4.0 * _smooth(2.0, 8.0, d)
    return z + n * bump


def build_terrain(coll):
    """Polar grid: dense near the pavilion, coarse towards the valley."""
    segs = 72
    radii = [0.0]
    r, step = 0.0, 0.35
    while r < 320:
        r += step
        radii.append(r)
        step *= 1.09
    cx, cy = 2.5, 1.0
    verts, faces = [], []
    verts.append((cx, cy, ground_z(cx, cy) - 0.02))
    for ri in radii[1:]:
        for s in range(segs):
            a = 2 * math.pi * s / segs
            x, y = cx + ri * math.cos(a), cy + ri * math.sin(a)
            verts.append((x, y, ground_z(x, y) - 0.02))
    # Winding is counter-clockwise seen from above so normals face up (baking
    # uses the true normal; renders hid the earlier downward winding).
    for s in range(segs):
        faces.append((0, 1 + s, 1 + (s + 1) % segs))
    for k in range(len(radii) - 2):
        b0, b1 = 1 + k * segs, 1 + (k + 1) * segs
        ring_r = radii[k + 1]
        for s in range(segs):
            s2 = (s + 1) % segs
            face = (b0 + s, b1 + s, b1 + s2, b0 + s2)
            if ring_r > KEEP_RADIUS:
                # Far terrain only where a web camera can see it.
                c = sum((Vector(verts[i]) for i in face), Vector()) / 4
                size = (Vector(verts[face[0]]) - Vector(verts[face[2]])).length
                if not visible(c, size):
                    continue
            faces.append(face)
    used = sorted({i for f in faces for i in f})
    remap = {old: new for new, old in enumerate(used)}
    verts = [verts[i] for i in used]
    faces = [tuple(remap[i] for i in f) for f in faces]
    return object_from_data("ground_terrain", verts, faces, coll, MATS["terrain"], smooth=True)


def build_retaining_walls(coll):
    """Low dry-stone walls along the terrace edge (west/north-west side)."""
    r = rng(31)
    bm = bmesh.new()
    for t0, t1 in ((math.radians(108), math.radians(150)), (math.radians(160), math.radians(236))):
        steps = int((t1 - t0) * 40)
        for course in range(3):
            for i in range(steps):
                t = t0 + (t1 - t0) * (i + 0.5 * (course % 2)) / steps
                x = PLATEAU_C[0] + PLATEAU_R[0] * 1.0 * math.cos(t)
                y = PLATEAU_C[1] + PLATEAU_R[1] * 1.0 * math.sin(t)
                tang = Vector((-PLATEAU_R[0] * math.sin(t), PLATEAU_R[1] * math.cos(t), 0)).normalized()
                outward = Vector((tang.y, -tang.x, 0))
                base = Vector((x, y, -TERRACE_DROP + 0.05)) + outward * (0.08 * course - 0.05)
                sx = r.uniform(0.18, 0.28)
                c = base + Vector((0, 0, 0.12 + course * 0.22 + r.uniform(-0.02, 0.02)))
                if not visible(c, 0.4):
                    r.random()
                    continue
                verts = rock_bmesh(bm, (0, 0, 0), (sx, 0.17, 0.12), r, subdiv=1, roughness=0.2,
                                   flatten_bottom=False)
                ang = math.atan2(tang.y, tang.x)
                for v in verts:
                    co = v.co
                    v.co = Vector((co.x * math.cos(ang) - co.y * math.sin(ang),
                                   co.x * math.sin(ang) + co.y * math.cos(ang), co.z)) + c
    object_from_bmesh("terrace_walls", bm, coll, MATS["rock"], smooth=True)

    # Low dry-stone garden wall across the hero's mid-left, in front of the vine rows.
    bm = bmesh.new()
    for course in range(2):
        lat = -7.2 + 0.2 * course
        while lat < -2.6:
            x, y, _ = hero_place(7.3 + 0.05 * course + r.uniform(-0.04, 0.04), lat)
            sx = r.uniform(0.17, 0.26)
            rock_bmesh(bm, (x, y, ground_z(x, y) + 0.1 + course * 0.19), (sx, 0.15, 0.11), r, subdiv=1,
                       roughness=0.22, flatten_bottom=False)
            lat += sx * 1.7
    object_from_bmesh("garden_wall", bm, coll, MATS["rock"], smooth=True)

    # Low stone kerb behind the table (north-west edge of the paving, seen behind the backpack).
    bm = bmesh.new()
    for i in range(18):
        t = i / 17
        x = -0.9 + t * 3.0
        y = 4.2 + 0.35 * math.sin(t * 2.2)
        sx = r.uniform(0.2, 0.32)
        rock_bmesh(bm, (x, y, 0.08), (sx, sx * r.uniform(0.6, 0.8), r.uniform(0.09, 0.14)), r, subdiv=2,
                   roughness=0.3)
    object_from_bmesh("garden_kerb", bm, coll, MATS["rock"], smooth=True)


def build_boulders(coll):
    r = rng(41)
    bm = bmesh.new()
    specs = [  # centre, scale (foreground boulders bottom-left of the hero frame)
        (hero_place(5.6, -2.5), (1.3, 0.9, 0.6)),        # big boulder, bottom-left of the hero
        (hero_place(7.2, -3.6), (0.8, 0.65, 0.45)),
        (hero_place(5.8, -0.7, -0.05), (0.8, 0.6, 0.36)),
        ((-0.1, -0.9, -0.05), (0.6, 0.5, 0.36)),
        ((-2.0, -1.3, -0.05), (0.6, 0.5, 0.4)),
        ((-0.4, 4.9, 0.0), (0.5, 0.45, 0.35)),
        ((7.0, 1.0, 0.0), (0.7, 0.55, 0.4)),
    ]
    for k, (c, s) in enumerate(specs):
        # The three hero-foreground boulders get extra subdivision so no facets show.
        rock_bmesh(bm, c, s, r, subdiv=4 if k < 3 else 3, roughness=0.22, strata=0.035)
    return object_from_bmesh("boulders", bm, coll, MATS["rock"], smooth=True)


def build_vineyard(coll):
    """Thin vineyard-style stakes on the lower terrace, mid-left of the hero frame."""
    r = rng(51)
    bm = bmesh.new()
    stakes = []
    # Rows run across the hero view (constant distance), at its mid-left.
    for row, f in enumerate((8.5, 10.5, 12.5)):
        for k in range(10):
            lat = -2.6 - k * 0.85 - row * 0.4
            x, y, _ = hero_place(f + r.uniform(-0.05, 0.05), lat)
            if not paving_inside(x, y) and plateau_d(x, y) < 1.5 and visible((x, y, 0.6), 0.7):
                z = ground_z(x, y)
                h = r.uniform(1.1, 1.45)
                lean = (r.uniform(-0.05, 0.05), r.uniform(-0.05, 0.05), 0)
                add_box(bm, (0.035, 0.035, h), (x, y, z + h / 2 - 0.1), rot=lean)
                stakes.append((x, y, z))
    object_from_bmesh("vineyard_stakes", bm, coll, MATS["stake"])
    return stakes
