"""Tree, shrubs and grasses.

Leaves and grass clumps are *instances* (Geometry Nodes "Instance on Points")
of tiny source meshes, driven by point clouds generated here with fixed seeds.
Point attributes `rot` (euler) and `scl` (vector) control each instance.
"""

import math

import bmesh
import bpy
from mathutils import Vector

from . import config as C
from .architecture import paving_inside
from .landscape import ground_z, plateau_d
from .materials import MATS
from .util import catmull_rom, object_from_bmesh, rng, rock_bmesh, tube
from .views import hero_distance, hero_place, visible

_GN = None

TREE_BASE = Vector((1.15, 5.7, 0.0))


# --- Instancing plumbing --------------------------------------------------------------

def _scatter_group():
    global _GN
    if _GN is not None and _GN.name in bpy.data.node_groups:
        return _GN
    ng = bpy.data.node_groups.new("scatter_instances", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Instance", in_out="INPUT", socket_type="NodeSocketObject")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nd, ln = ng.nodes, ng.links
    gi, go = nd.new("NodeGroupInput"), nd.new("NodeGroupOutput")
    info = nd.new("GeometryNodeObjectInfo")
    info.transform_space = "ORIGINAL"
    iop = nd.new("GeometryNodeInstanceOnPoints")
    rot = nd.new("GeometryNodeInputNamedAttribute")
    rot.data_type = "FLOAT_VECTOR"
    rot.inputs["Name"].default_value = "rot"
    e2r = nd.new("FunctionNodeEulerToRotation")
    scl = nd.new("GeometryNodeInputNamedAttribute")
    scl.data_type = "FLOAT_VECTOR"
    scl.inputs["Name"].default_value = "scl"
    ln.new(gi.outputs[0], iop.inputs["Points"])
    ln.new(gi.outputs[1], info.inputs["Object"])
    ln.new(info.outputs["Geometry"], iop.inputs["Instance"])
    ln.new(rot.outputs["Attribute"], e2r.inputs[0])
    ln.new(e2r.outputs[0], iop.inputs["Rotation"])
    ln.new(scl.outputs["Attribute"], iop.inputs["Scale"])
    ln.new(iop.outputs[0], go.inputs[0])
    _GN = ng
    return ng


def scatter(name, coll, source, points, radius=0.3, cull=True):
    """points: list of (location, euler, scale-vector).

    With `cull`, instances that no web camera can see (frustum test, `radius`
    metres times the instance scale) are dropped to save triangles.
    """
    if cull:
        points = [p for p in points if visible(p[0], radius * max(p[2]))]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p[0]) for p in points], [], [])
    rot = mesh.attributes.new("rot", "FLOAT_VECTOR", "POINT")
    scl = mesh.attributes.new("scl", "FLOAT_VECTOR", "POINT")
    rot.data.foreach_set("vector", [c for p in points for c in p[1]])
    scl.data.foreach_set("vector", [c for p in points for c in p[2]])
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    ng = _scatter_group()
    mod = obj.modifiers.new("scatter", "NODES")
    mod.node_group = ng
    ident = ng.interface.items_tree["Instance"].identifier
    if hasattr(mod, "properties"):  # Blender 5.x modifier input API
        getattr(mod.properties.inputs, ident).value = source
    else:  # Blender 4.x ID-property API
        mod[ident] = source
    return obj


def leaf_source(name, coll, mat, length, width):
    """Pointed leaf with a slight centre fold, petiole at the origin, pointing +X."""
    L, W = length, width
    bm = bmesh.new()
    pts = [(0, 0, 0), (0.3 * L, 0.5 * W, 0.03 * L), (0.7 * L, 0.38 * W, 0.02 * L), (L, 0, -0.05 * L),
           (0.7 * L, -0.38 * W, 0.02 * L), (0.3 * L, -0.5 * W, 0.03 * L)]
    v = [bm.verts.new(p) for p in pts]
    for f in ((0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)):  # 4 triangles per leaf
        bm.faces.new([v[i] for i in f])
    return object_from_bmesh(name, bm, coll, mat, smooth=True)


def grass_source(name, coll, mat, r, blades=7, height=0.55, width=0.03, seeds=0):
    """A clump of thin blades, each with its own height, lean and curve.

    Blades are separate mesh islands, so the material can colour each one
    (Random Per Island). `seeds` blades end in a small pale seed head whose UVs
    are (1, 0) so the material can pick them out; everything else is UV (0, 0).
    """
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    def face(verts, is_seed=False):
        f = bm.faces.new(verts)
        for loop in f.loops:
            loop[uv_layer].uv = (1.0 if is_seed else 0.0, 0.0)
        return f

    for b in range(blades):
        a = 2 * math.pi * b / blades + r.uniform(-0.4, 0.4)
        lean = r.uniform(0.05, 0.7)
        h = height * r.uniform(0.45, 1.15)
        w = width * r.uniform(0.6, 1.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0)) * w * 0.5
        root = d * r.uniform(0.0, 0.04)
        pts = [root + d * (lean * h * t ** 1.8) + Vector((0, 0, h * t * (1 - 0.15 * lean * t))) for t in (0, 0.5, 1.0)]
        v0 = (bm.verts.new(pts[0] - side), bm.verts.new(pts[0] + side))
        v1 = (bm.verts.new(pts[1] - side * 0.6), bm.verts.new(pts[1] + side * 0.6))
        tip = bm.verts.new(pts[2])
        face((v0[0], v0[1], v1[1], v1[0]))
        face((v1[0], v1[1], tip))
        if b < seeds:  # slender seed head continuing from the tip
            up = (pts[2] - pts[1]).normalized()
            s0 = bm.verts.new(pts[2] - side * 1.4 + up * 0.02)
            s1 = bm.verts.new(pts[2] + side * 1.4 + up * 0.02)
            s2 = bm.verts.new(pts[2] + up * 0.09)
            face((tip, s1, s2), True)
            face((tip, s2, s0), True)
    return object_from_bmesh(name, bm, coll, mat, smooth=True)


def card_source(name, coll, mat, size):
    """Leaf-cluster card: a gently cupped 3x3 grid with 0..1 UVs (8 triangles)."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    grid = [[bm.verts.new(((i / 2 - 0.5) * size, (j / 2 - 0.5) * size,
                           -0.12 * size * ((i / 2 - 0.5) ** 2 + (j / 2 - 0.5) ** 2) * 4)) for i in range(3)]
            for j in range(3)]
    for j in range(2):
        for i in range(2):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (di, dj) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                loop[uv_layer].uv = ((i + di) / 2, (j + dj) / 2)
    return object_from_bmesh(name, bm, coll, mat, smooth=True)


def _card_points(r, clusters, scale_range, out):
    """Cards on cluster shells, facing outward-and-up with a random spin."""
    from mathutils import Quaternion
    for center, radii, count in clusters:
        for _ in range(count):
            loc, local = _shell_point(r, center, radii)
            outward = local.normalized() if local.length > 1e-4 else Vector((0, 0, 1))
            jitter = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * 0.5
            normal = (outward * 0.8 + Vector((0, 0, 0.6)) + jitter).normalized()
            q = normal.to_track_quat("Z", "Y") @ Quaternion((0, 0, 1), r.uniform(0, 6.283))
            s = r.uniform(*scale_range)
            out.append((loc, tuple(q.to_euler("XYZ")), (s, s, s)))


def _twigs(bm, r, clusters, per=5):
    """Thin twigs radiating inside each clump so cards read as attached foliage."""
    for center, radii, _ in clusters:
        c = Vector(center)
        for _ in range(per):
            d = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-0.3, 0.8))).normalized()
            end = c + Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])) * 0.8
            mid = (c + end) / 2 + Vector((0, 0, 0.05))
            tube(bm, [c, mid, end], [0.018, 0.011, 0.005], sides=3, cap=False)


def _shell_point(r, center, radii, shell=0.55):
    """Random point inside an ellipsoid, biased towards its surface."""
    while True:
        p = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1)))
        if p.length <= 1.0 and p.length >= shell * r.random():
            break
    return Vector((center[0] + p.x * radii[0], center[1] + p.y * radii[1], center[2] + p.z * radii[2])), p


def _leaf_points(r, clusters, scale_range, out):
    for center, radii, count in clusters:
        for _ in range(count):
            loc, local = _shell_point(r, center, radii)
            outward = local.normalized() if local.length > 1e-4 else Vector((0, 0, 1))
            yaw = math.atan2(outward.y, outward.x) + r.uniform(-1.2, 1.2)
            pitch = r.uniform(-0.9, 0.5) - 0.3 * outward.z
            roll = r.uniform(-1.0, 1.0)
            s = r.uniform(*scale_range)
            out.append((loc, (roll, pitch, yaw), (s, s, s)))


# --- Tree -------------------------------------------------------------------------------

def _branch_specs():
    b = TREE_BASE
    trunk = [b + Vector(o) for o in ((0, 0, -0.3), (0.15, 0.0, 0.9), (-0.1, -0.15, 1.9), (-0.45, -0.3, 2.8),
                                     (-0.6, -0.35, 3.4))]
    fork = trunk[-1]
    main = [  # control points relative to the fork, base radius, tip radius
        ([(0, 0, 0), (-1.2, -0.3, 1.2), (-2.6, -0.6, 2.3), (-4.0, -1.0, 2.8)], 0.24, 0.05),   # up-left
        ([(0, 0, 0), (1.0, -0.7, 0.9), (2.3, -1.8, 1.7), (3.5, -2.9, 2.1)], 0.23, 0.05),     # over the roof
        ([(0, 0, 0), (0.2, 0.8, 1.3), (0.0, 2.0, 2.5), (-0.5, 3.0, 3.1)], 0.2, 0.045),       # back
        ([(0, 0, 0), (-0.3, 0.2, 1.6), (-0.6, 0.3, 3.1), (-0.9, 0.0, 4.2)], 0.2, 0.04),      # up
        ([(0, 0, 0), (-0.9, -0.9, 0.5), (-1.9, -2.1, 1.0), (-2.7, -3.2, 1.3)], 0.18, 0.04),  # front-left, low
    ]
    return trunk, fork, main


def build_tree(coll, src_coll):
    r = rng(61)
    trunk, fork, main = _branch_specs()
    bm = bmesh.new()
    pts = catmull_rom(trunk, 5)
    radii = [0.36 - 0.12 * (i / (len(pts) - 1)) + (0.14 if i == 0 else 0.0) for i in range(len(pts))]
    tube(bm, pts, radii, sides=20, twist_noise=0.12, seed=1)
    tips = []
    for ctrl, r0, r1 in main:
        pts = catmull_rom([fork + Vector(c) for c in ctrl], 5)
        rad = [r0 + (r1 - r0) * (i / (len(pts) - 1)) for i in range(len(pts))]
        tube(bm, pts, rad, sides=12, twist_noise=0.08, seed=len(tips))
        # Secondary branches off the main branch.
        for k in range(3):
            i0 = int(len(pts) * r.uniform(0.35, 0.85))
            start = pts[i0]
            d = (pts[-1] - pts[0]).normalized()
            off = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.2, 1.0))).normalized()
            end = start + (d * 0.6 + off).normalized() * r.uniform(1.0, 1.8)
            mid = (start + end) / 2 + Vector((0, 0, 0.2))
            sp = catmull_rom([start, mid, end], 3)
            tube(bm, sp, [rad[i0] * 0.55 * (1 - 0.7 * t / (len(sp) - 1)) for t in range(len(sp))], sides=8)
            tips.append(end)
        tips.append(pts[-1])
    object_from_bmesh("tree_wood", bm, coll, MATS["bark"], smooth=True)

    # Canopy: clusters around branch tips plus a few fill clusters, so the
    # crown is broken up (sky shows through) rather than one blob.
    clusters = []
    for t in tips:
        rad = (r.uniform(1.2, 1.7), r.uniform(1.2, 1.6), r.uniform(0.7, 1.0))
        clusters.append(((t.x, t.y, t.z + 0.1), rad, int(62 * rad[0] * rad[1])))
    for _ in range(8):
        a, b = r.sample(tips, 2)
        m = (a + b) / 2 + Vector((0, 0, r.uniform(0.2, 0.6)))
        rad = (r.uniform(0.9, 1.3), r.uniform(0.9, 1.3), r.uniform(0.5, 0.8))
        clusters.append(((m.x, m.y, m.z), rad, int(58 * rad[0] * rad[1])))
    twigs = bmesh.new()
    _twigs(twigs, r, clusters)
    object_from_bmesh("tree_twigs", twigs, coll, MATS["bark"], smooth=True)
    leaf = card_source("src_leafcard_tree", src_coll, MATS["leafcard_tree"], 0.44)
    points = []
    _card_points(r, clusters, (0.8, 1.2), points)
    canopy = scatter("tree_canopy", coll, leaf, points)
    return len(canopy.data.vertices) + _shade_tree(coll, leaf, r) + _dapple_tree(coll, leaf, r)


DAPPLE_TREE_BASE = Vector((-3.6, -8.2, 0.0))


def _dapple_tree(coll, leaf, r):
    """Off-camera tree whose sparse crown sits between the sun and the roof.

    Sun rays reaching the slat-striped part of the wall pass through the roof
    around (2.5, 1.2) and, further back towards the sun, through this crown at
    about (-1.3, -4.3, 6.3), so leaf dapples break up the slat stripes. No web
    camera sees it; like the shade tree it is a bake-only shadow caster.
    """
    b = DAPPLE_TREE_BASE
    b = Vector((b.x, b.y, ground_z(b.x, b.y)))
    bm = bmesh.new()
    trunk = catmull_rom([b + Vector(o) for o in ((0, 0, -0.3), (0.3, 0.4, 1.8), (0.9, 1.4, 3.6), (1.6, 2.6, 5.0))], 4)
    tube(bm, trunk, [0.22 - 0.12 * i / (len(trunk) - 1) for i in range(len(trunk))], sides=10, twist_noise=0.1)
    top = trunk[-1]
    centres = [Vector(c) for c in ((-2.2, -4.9, 6.0), (-0.9, -3.8, 6.6), (-1.5, -3.4, 5.8), (-0.2, -4.7, 6.3),
                                   (-1.2, -5.2, 6.8))]
    for c in centres:
        pts = catmull_rom([top, (top + c) / 2 + Vector((0, 0, 0.3)), c], 3)
        tube(bm, pts, [0.1 - 0.07 * i / (len(pts) - 1) for i in range(len(pts))], sides=6)
    object_from_bmesh("dapple_tree_wood", bm, coll, MATS["bark"], smooth=True)
    clusters = [(c.to_tuple(), (1.1, 1.1, 0.6), 24) for c in centres]
    points = []
    _card_points(r, clusters, (0.9, 1.3), points)
    scatter("dapple_tree_canopy", coll, leaf, points, cull=False)
    return len(points)


SHADE_TREE_BASE = Vector((-4.6, -13.0, 0.0))


def _shade_tree(coll, leaf, r):
    """Second, off-frame tree south-west of the terrace.

    No web camera sees it; it exists only to sit between the low sun and the
    paving so its sparse crown throws dappled shadows across the foreground.
    For export it is a bake-only shadow caster (exclude it from the GLB).
    """
    b = SHADE_TREE_BASE
    b = Vector((b.x, b.y, ground_z(b.x, b.y)))
    bm = bmesh.new()
    trunk = catmull_rom([b + Vector(o) for o in ((0, 0, -0.3), (0.2, 0.1, 1.5), (0.5, 0.4, 3.0), (0.8, 0.8, 4.2))], 4)
    tube(bm, trunk, [0.26 - 0.12 * i / (len(trunk) - 1) for i in range(len(trunk))], sides=10, twist_noise=0.1)
    top = trunk[-1]
    tips = []
    for d in ((2.5, 3.5, 1.8), (1.0, 1.0, 2.6), (3.6, 1.2, 1.4), (0.2, 3.0, 1.6)):
        end = top + Vector(d)
        pts = catmull_rom([top, (top + end) / 2 + Vector((0, 0, 0.4)), end], 4)
        tube(bm, pts, [0.13 - 0.09 * i / (len(pts) - 1) for i in range(len(pts))], sides=6)
        tips.append(end)
    object_from_bmesh("shade_tree_wood", bm, coll, MATS["bark"], smooth=True)
    clusters = [((t.x, t.y, t.z), (1.5, 1.5, 0.8), 45) for t in tips]
    clusters.append((((tips[0] + tips[2]) / 2 + Vector((0, 0, 0.3))).to_tuple(), (1.4, 1.4, 0.7), 35))
    points = []
    _card_points(r, clusters, (0.9, 1.3), points)
    scatter("shade_tree_canopy", coll, leaf, points, cull=False)
    return len(points)


# --- Shrubs and grasses ---------------------------------------------------------------------

def _shrub_clusters(r, base, height, spread, n_clusters, density, low=False):
    """Leaf clusters stacked up a stem; `low` makes a ground-hugging mound (no bare stem)."""
    z0, dz, rz = (0.15, 0.45, 0.45) if low else (0.35, 0.6, 0.3)
    clusters = []
    for i in range(n_clusters):
        t = (i + 0.5) / n_clusters
        c = (base[0] + r.uniform(-spread, spread) * 0.6, base[1] + r.uniform(-spread, spread) * 0.6,
             base[2] + height * (z0 + dz * t))
        rad = (spread * r.uniform(0.5, 0.8), spread * r.uniform(0.5, 0.8), height * rz)
        clusters.append((c, rad, int(density * rad[0] * rad[1] * 4)))
    return clusters


def _garden_spot(x, y):
    """Free ground for planting: not paved, not inside the pavilion or wall."""
    if paving_inside(x, y):
        return False
    if -0.3 < x < 5.8 and -0.2 < y < 4.1:   # pavilion footprint incl. walls
        return False
    if math.hypot(x - C.POT_POS[0], y - C.POT_POS[1]) < 1.3:   # keep the big pot readable
        return False
    return True


def build_shrubs(coll, src_coll, anchors, stakes):
    r = rng(71)
    # Species: broadleaf, silver olive, bright lime (small round leaves), dark glossy bay.
    sources = {
        "shrub": leaf_source("src_leaf_shrub", src_coll, MATS["leaf_shrub"], 0.12, 0.055),
        "olive": leaf_source("src_leaf_olive", src_coll, MATS["leaf_olive"], 0.11, 0.035),
        "lime": leaf_source("src_leaf_lime", src_coll, MATS["leaf_lime"], 0.075, 0.065),
        "bay": leaf_source("src_leaf_bay", src_coll, MATS["leaf_bay"], 0.14, 0.05),
    }
    pts = {k: [] for k in sources}
    stems = bmesh.new()

    def shrub(base, height, spread, kind="shrub", n_clusters=4, density=900, leaf_scale=1.0, low=False):
        clusters = _shrub_clusters(r, base, height, spread, n_clusters, density * 0.5, low)
        _leaf_points(r, clusters, (0.7 * leaf_scale, 1.2 * leaf_scale), pts[kind])
        if low:
            return
        k = min(1.0, height / 0.8)  # thinner stems on small plants
        for c, _, _ in clusters[:3]:
            tube(stems, [Vector(base), (Vector(base) + Vector(c)) / 2 + Vector((0, 0, 0.1 * k)), Vector(c)],
                 [0.025 * k, 0.017 * k, 0.008 * k], sides=5)

    # Tall shrub in the big pot by the front-left posts: small olive leaves on cards.
    pot_clusters = _shrub_clusters(r, anchors["pot_large_top"], 1.45, 0.6, 7, 70)
    pot_cards = []
    _card_points(r, pot_clusters, (0.8, 1.15), pot_cards)
    base = Vector(anchors["pot_large_top"])
    for c, _, _ in pot_clusters:
        tube(stems, [base, (base + Vector(c)) / 2 + Vector((0, 0, 0.1)), Vector(c)], [0.025, 0.017, 0.008], sides=5)
    _twigs(stems, r, pot_clusters, per=3)
    scatter("pot_shrub_cards", coll, card_source("src_leafcard_olive", src_coll, MATS["leafcard_olive"], 0.3),
            pot_cards, radius=0.2)
    # Potted plant in the wall niche and the succulent.
    shrub(anchors["pot_niche_top"], 0.45, 0.17, "olive", n_clusters=3, density=2600, leaf_scale=0.6)
    shrub(anchors["succulent"], 0.08, 0.05, "shrub", n_clusters=1, density=9000, leaf_scale=0.3)
    # Garden planting: only where the hero camera looks (3-16 m out), mixing
    # medium shrubs with low leafy mounds so the mid-ground reads as lush.
    placed = 0
    while placed < 40:
        f, lat = r.uniform(5.5, 17.0), r.uniform(-9.0, 2.0)
        x, y, _ = hero_place(f, lat)
        if not _garden_spot(x, y) or plateau_d(x, y) > 1.9:
            continue
        z = ground_z(x, y)
        if not visible((x, y, z + 0.5), 0.8):
            continue
        roll = r.random()
        if roll < 0.4:   # medium shrubs of mixed species and heights
            kind = r.choice(["shrub", "olive", "bay", "lime"])
            shrub((x, y, z), r.uniform(0.6, 1.6), r.uniform(0.4, 0.75), kind, n_clusters=3, density=330,
                  leaf_scale=1.25 if kind != "lime" else 1.0)
        elif roll < 0.75:  # low bright mounds
            shrub((x, y, z), r.uniform(0.25, 0.5), r.uniform(0.3, 0.5), r.choice(["lime", "shrub"]), n_clusters=2,
                  density=360, leaf_scale=1.0, low=True)
        else:  # small silver cushions
            shrub((x, y, z), r.uniform(0.2, 0.35), r.uniform(0.25, 0.4), "olive", n_clusters=2, density=420,
                  leaf_scale=0.9, low=True)
        placed += 1
    # Further out: fewer, larger leaves; still leaf cards, not blobs.
    placed = 0
    while placed < 38:
        # 15-50 m out, denser near the garden and thinning towards the matte painting.
        x, y, _ = hero_place(15.0 + 35.0 * r.random() ** 1.8, r.uniform(-18.0, 2.0))
        if not _garden_spot(x, y):
            continue
        z = ground_z(x, y)
        if not visible((x, y, z + 0.8), 1.2):
            continue
        shrub((x, y, z), r.uniform(0.7, 1.4), r.uniform(0.9, 1.4), r.choice(["shrub", "olive", "bay"]),
              n_clusters=3, density=45, leaf_scale=2.2, low=True)
        placed += 1
    # Vines at the stakes on the lower terrace.
    for (x, y, z) in stakes:
        shrub((x + 0.1, y, z), r.uniform(0.7, 1.1), 0.4, "shrub", n_clusters=2, density=450, leaf_scale=1.15)
    object_from_bmesh("shrub_stems", stems, coll, MATS["bark"], smooth=True)
    return sum(len(scatter(f"{k}_leaves", coll, sources[k], pts[k], radius=0.1).data.vertices) for k in sources)
