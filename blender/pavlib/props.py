"""Furniture and props: worktable, chair + throw, devices, mugs, bench items, pot, backpack.

Each prop is modelled in a local frame, then transformed into world space so the
object origin stays at the world origin (consistent procedural texture scale).
Positions that later stages need (anchors, cameras) are returned in `ANCHORS`.
"""

import math
import os

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

from . import config as C
from .materials import MATS
from .util import add_bevel, add_box, add_cylinder, auto_smooth, catmull_rom, object_from_bmesh, rng, tube

ANCHORS = {}


def xf(loc, yaw=0.0, pitch=0.0, roll=0.0):
    return Matrix.Translation(loc) @ Euler((pitch, roll, yaw), "XZY").to_matrix().to_4x4()


def _obj(name, coll, mat, build, matrix=None, bevel=0.0, subsurf=0, smooth=False):
    bm = bmesh.new()
    build(bm)
    if matrix is not None:
        bm.transform(matrix)
    obj = object_from_bmesh(name, bm, coll, mat, smooth=smooth)
    if smooth:
        auto_smooth(obj, 50.0)
    if bevel:
        add_bevel(obj, bevel)
    if subsurf:
        mod = obj.modifiers.new("subsurf", "SUBSURF")
        mod.levels = mod.render_levels = subsurf
    return obj


def lathe(bm, profile, segments=24, matrix=Matrix.Identity(4)):
    """Revolve a (radius, z) profile around Z."""
    rings = []
    for r, z in profile:
        ring = []
        for s in range(segments):
            a = 2 * math.pi * s / segments
            ring.append(bm.verts.new(matrix @ Vector((r * math.cos(a), r * math.sin(a), z))))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for s in range(segments):
            s2 = (s + 1) % segments
            bm.faces.new((rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]))
    if profile[0][0] > 0:
        bm.faces.new(list(reversed(rings[0])))


def quad_uv(name, coll, mat, corners):
    """A single textured quad (corners in world space, CCW from bottom-left)."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(c) for c in corners], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop.uv = co
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# --- Table group -------------------------------------------------------------------

def build_table(coll):
    tx, ty = C.TABLE_CENTER
    L, D, H = C.TABLE_SIZE
    M = xf((tx, ty, 0), C.TABLE_YAW)

    def table(bm):
        add_box(bm, (L, D, 0.055), (0, 0, H - 0.0275))
        for sx in (-1, 1):
            for sy in (-1, 1):
                add_box(bm, (0.075, 0.075, H - 0.055), (sx * (L / 2 - 0.12), sy * (D / 2 - 0.08), (H - 0.055) / 2))
            add_box(bm, (0.05, D - 0.16, 0.06), (sx * (L / 2 - 0.12), 0, 0.18))
        add_box(bm, (L - 0.24, 0.05, 0.06), (0, 0, 0.18))
        add_box(bm, (L - 0.3, 0.035, 0.08), (0, -(D / 2 - 0.08), H - 0.095))
    _obj("table", coll, MATS["table_wood"], table, M, bevel=0.009)

    # Chair at the front-right end of the table, facing the table, throw over its back.
    cM = xf((tx + 0.72, ty - D / 2 - 0.3, 0), C.TABLE_YAW + math.radians(-14))

    def chair(bm):
        seat = 0.46
        add_box(bm, (0.46, 0.44, 0.04), (0, 0, seat))
        for sx in (-1, 1):
            add_box(bm, (0.045, 0.045, seat), (sx * 0.2, 0.19, seat / 2))
            add_box(bm, (0.05, 0.05, 0.92), (sx * 0.2, -0.19, 0.46))
            add_box(bm, (0.03, 0.36, 0.035), (sx * 0.2, 0, 0.2))
        for z in (0.7, 0.86):
            add_box(bm, (0.42, 0.03, 0.06), (0, -0.19, z))
    _obj("chair", coll, MATS["table_wood"], chair, cM, bevel=0.008)
    _throw(coll, cM)

    top = H
    # Laptop, facing the hero camera.
    lap_pos = Vector((tx + 0.05, ty + 0.05, top))
    lap_yaw = C.TABLE_YAW + math.radians(10)
    _laptop(coll, xf(lap_pos, lap_yaw))
    # Tablet on a stand to its left.
    _tablet(coll, xf((tx - 0.55, ty + 0.12, top), lap_yaw - math.radians(12)))
    # Mugs.
    _mug(coll, "mug_white", MATS["ceramic_white"], (tx - 0.25, ty - 0.05, top), 0.3)
    _mug(coll, "mug_dark", MATS["ceramic_dark"], (tx + 0.55, ty - 0.1, top), 2.2)
    # A closed notebook / sketchbook near the dark mug for clutter.
    _obj("table_book", coll, MATS["book_3"],
         lambda bm: add_box(bm, (0.22, 0.16, 0.025), (0, 0, 0.0125)),
         xf((tx + 0.72, ty + 0.18, top), 0.3), bevel=0.005)


def _laptop(coll, M):
    w, d = 0.33, 0.23
    lid_tilt = math.radians(108)

    def base(bm):
        add_box(bm, (w, d, 0.016), (0, 0, 0.008))
    _obj("laptop_base", coll, MATS["aluminium"], base, M, bevel=0.005)
    hinge = Matrix.Translation((0, d / 2 - 0.005, 0.016)) @ Matrix.Rotation(-(lid_tilt - math.pi / 2), 4, "X")

    def lid(bm):
        add_box(bm, (w, 0.008, 0.215), (0, 0.004, 0.1075))
    _obj("laptop_lid", coll, MATS["aluminium"], lid, M @ hinge, bevel=0.003)
    sw, sh = w - 0.022, (w - 0.022) * 720 / 1265
    corners = [M @ hinge @ Vector(c) for c in ((-sw / 2, -0.0015, 0.012), (sw / 2, -0.0015, 0.012),
                                                (sw / 2, -0.0015, 0.012 + sh), (-sw / 2, -0.0015, 0.012 + sh))]
    quad_uv("laptop_screen", coll, MATS["screen_laptop"], corners)
    ANCHORS["anchor_projects"] = (M @ hinge @ Vector((0, 0, 0.012 + sh / 2))).to_tuple()


def _tablet(coll, M):
    tilt = math.radians(68)
    w, h = 0.25, 0.25 * 720 / 1265 + 0.02
    R = Matrix.Translation((0, 0.03, 0.012)) @ Matrix.Rotation(-(math.pi / 2 - tilt), 4, "X")

    def stand(bm):
        add_box(bm, (0.12, 0.09, 0.012), (0, 0.02, 0.006))
        add_box(bm, (0.08, 0.01, 0.12), (0, 0.075, 0.055), rot=(math.radians(-25), 0, 0))
    _obj("tablet_stand", coll, MATS["aluminium"], stand, M, bevel=0.002)

    def body(bm):
        add_box(bm, (w, 0.008, h), (0, 0.004, h / 2))
    _obj("tablet_body", coll, MATS["bezel"], body, M @ R, bevel=0.0035)
    sw, sh = w - 0.02, (w - 0.02) * 720 / 1265
    z0 = (h - sh) / 2
    corners = [M @ R @ Vector(c) for c in ((-sw / 2, -0.001, z0), (sw / 2, -0.001, z0),
                                            (sw / 2, -0.001, z0 + sh), (-sw / 2, -0.001, z0 + sh))]
    quad_uv("tablet_screen", coll, MATS["screen_tablet"], corners)


def _mug(coll, name, mat, pos, yaw):
    M = xf(pos, yaw)

    def mug(bm):
        lathe(bm, [(0.0, 0.0), (0.042, 0.0), (0.045, 0.01), (0.045, 0.095), (0.039, 0.095), (0.039, 0.012),
                   (0.0, 0.012)], 20)
        pts = [Vector((0.044 + 0.028 * math.sin(t), 0, 0.05 + 0.03 * math.cos(t)))
               for t in [i * math.pi / 8 for i in range(9)]]
        tube(bm, pts, [0.006] * len(pts), sides=6)
    _obj(name, coll, mat, mug, M, smooth=True)

    def coffee(bm):
        add_cylinder(bm, 0.039, 0.002, (0, 0, 0.075), segments=20)
    _obj(name + "_coffee", coll, MATS["soil"], coffee, M)


def _throw(coll, chair_M):
    """Patterned throw folded over the chair back, hanging in soft vertical folds.

    The cross-section follows a path over the backrest; fold depth grows as the
    cloth falls away from the rail, folds wander slowly, and the hem is uneven.
    """
    r = rng(23)
    w, n_u = 0.38, 26
    path = [(-0.19 + 0.02, 0.34), (-0.19 + 0.025, 0.62), (-0.19 + 0.015, 0.9), (-0.19, 0.95), (-0.19 - 0.03, 0.955),
            (-0.19 - 0.06, 0.91), (-0.19 - 0.08, 0.7), (-0.19 - 0.085, 0.42), (-0.19 - 0.08, 0.12)]
    curve = catmull_rom([(0, y, z) for y, z in path], 6)
    phases = [r.uniform(0, 6.28) for _ in range(3)]
    hem = [r.uniform(-0.03, 0.03) for _ in range(n_u + 1)]
    bm = bmesh.new()
    grid = []
    nv = len(curve)
    for j, p in enumerate(curve):
        hang = min(1.0, max(0.0, (0.93 - p.z) * 2.2))
        side = 1.0 if p.y > -0.19 else -1.0          # which side of the rail (front/back)
        row = []
        for i in range(n_u + 1):
            u = i / n_u
            x = (u - 0.5) * w * (1.0 + 0.1 * hang)
            fold = (0.03 * math.sin(u * 13.0 + phases[0] + j * 0.04) +
                    0.015 * math.sin(u * 27.0 + phases[1]) +
                    0.008 * math.sin(u * 47.0 + phases[2] - j * 0.07)) * hang
            # Folds bunch the cloth so its edges pull in slightly towards the middle.
            x -= 0.03 * hang * math.sin((u - 0.5) * math.pi)
            z = p.z + (hem[i] * hang if j == nv - 1 or j == 0 else 0.0)
            row.append(bm.verts.new(chair_M @ Vector((x, p.y + side * fold, z))))
        grid.append(row)
    for j in range(nv - 1):
        for i in range(n_u):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    obj = object_from_bmesh("throw", bm, coll, MATS["throw"], smooth=True)
    sol = obj.modifiers.new("thickness", "SOLIDIFY")
    sol.thickness = 0.008


# --- Bench group ---------------------------------------------------------------------

def build_bench_items(coll):
    seat = C.BENCH_H
    wy = C.WALL_Y
    r = rng(21)

    def cushion(bm):
        add_box(bm, (0.44, 0.14, 0.4), (0, 0, 0.2))
    lean = math.radians(-14)
    _soft("cushion_plain", coll, MATS["cushion_plain"], (0.44, 0.15, 0.4),
          xf((C.WALL_X0 + 0.55, wy - 0.17, seat), math.radians(4), lean), seed=1)
    _soft("cushion_pattern", coll, MATS["cushion_pattern"], (0.42, 0.15, 0.4),
          xf((C.WALL_X0 + 1.05, wy - 0.16, seat), math.radians(-6), lean, math.radians(5)), seed=2)
    # Seat pad along the bench.
    _soft("bench_pad", coll, MATS["cushion_plain"], (1.3, 0.42, 0.06), xf((C.WALL_X0 + 0.95, wy - 0.27, seat), 0),
          round_=0.025, squash=0.3, seed=3)

    # Open notebook lying flat.
    nb = Vector((C.WALL_X0 + 1.85, wy - 0.27, seat))
    nyaw = math.radians(-8)
    M = xf(nb, nyaw)

    def cover(bm):  # slightly proud of the pages so its coloured edge shows all round
        add_box(bm, (0.336, 0.234, 0.006), (0, 0, 0.003))
    _obj("notebook_cover", coll, MATS["notebook_cover"], cover, M, bevel=0.002)
    bm = bmesh.new()
    for side in (-1, 1):
        # Each page block curls gently up towards the spine.
        cols = []
        for i in range(9):
            t = i / 8
            x = side * (0.004 + t * 0.148)
            z = 0.004 + 0.012 * (1 - t) ** 2 + 0.006
            cols.append((bm.verts.new(M @ Vector((x, -0.102, z))), bm.verts.new(M @ Vector((x, 0.102, z)))))
        for i in range(8):
            a, b = cols[i], cols[i + 1]
            f = (a[0], b[0], b[1], a[1]) if side > 0 else (a[1], b[1], b[0], a[0])
            bm.faces.new(f).material_index = 1 if side > 0 else 0   # right page: pencil sketch
    object_from_bmesh("notebook_pages", bm, coll, [MATS["paper_ruled"], MATS["paper_sketch"]], smooth=True)
    # Ribbon marker from the spine, over the right page and off the bottom edge.
    rib = [M @ Vector(p) for p in ((0.012, 0.1, 0.012), (0.03, 0.0, 0.0115), (0.045, -0.1, 0.011),
                                   (0.05, -0.125, 0.004), (0.052, -0.15, 0.0005))]
    bm = bmesh.new()
    side = (M.to_3x3() @ Vector((0.004, 0, 0)))
    verts = [(bm.verts.new(p - side), bm.verts.new(p + side)) for p in rib]
    for a, b in zip(verts, verts[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    object_from_bmesh("notebook_ribbon", bm, coll, MATS["ribbon"], smooth=True)
    _obj("notebook_pen", coll, MATS["ink"],
         lambda bm: add_cylinder(bm, 0.005, 0.14, (0, 0, 0), rot=(0, math.pi / 2, 0), segments=8),
         xf(nb + Vector((0.05, -0.02, 0.022)), nyaw + 0.5))
    ANCHORS["anchor_writing"] = (M @ Vector((0, 0, 0.02))).to_tuple()

    # Standing essay copy leaning against the wall, plus a stack of books.
    ex = C.RETURN_WALL_X - 0.62
    eM = xf((ex, wy - 0.12, seat), math.radians(-10), math.radians(-9))
    ew, eh = 0.235, 0.32

    def essay(bm):
        add_box(bm, (ew, 0.006, eh), (0, 0, eh / 2))
    _obj("essay_copy", coll, MATS["paper"], essay, eM, bevel=0.0018)
    _essay_text(coll, eM, ew, eh)
    ANCHORS["anchor_reviews"] = (eM @ Vector((0.12, 0, eh * 0.55))).to_tuple()

    z = seat
    bx = C.RETURN_WALL_X - 0.24
    for i in range(7):
        bw = r.uniform(0.22, 0.28)   # along the spine
        bd = r.uniform(0.15, 0.2)
        bh = r.uniform(0.025, 0.05)
        yaw = math.radians(r.uniform(-7, 7))  # spines face the room
        _book(coll, f"book_stack_{i}", xf((bx + r.uniform(-0.01, 0.01), wy - 0.2, z), yaw), bw, bd, bh,
              MATS[f"book_{i % len(C.PALETTE['books'])}"])
        z += bh
    # Tiny succulent in front of the books (reference detail).
    _obj("succulent_pot", coll, MATS["terracotta"],
         lambda bm: lathe(bm, [(0.0, 0), (0.035, 0), (0.045, 0.06), (0.04, 0.06), (0.0, 0.05)], 14),
         xf((ex + 0.24, wy - 0.38, seat), 0), smooth=True)
    ANCHORS["succulent"] = (ex + 0.24, wy - 0.38, seat + 0.06)


def _soft(name, coll, mat, size, M, round_=0.05, squash=1.0, seed=0):
    """Cushion: subdivided rounded box, bulged faces, a sagging top and soft wrinkles."""
    sx, sy, sz = size
    bm = bmesh.new()
    add_box(bm, size, (0, 0, sz / 2))
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.calc_face_angle(0.0) > 1.0], offset=round_, segments=3,
                    profile=0.6, affect="EDGES")
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    for v in bm.verts:
        fx = max(0.0, 1 - (2 * v.co.x / sx) ** 2)
        fz = max(0.0, 1 - (2 * (v.co.z - sz / 2) / sz) ** 2)
        v.co.y *= 1 + 0.4 * fx * fz                      # plump middle
        top = max(0.0, (v.co.z - sz * 0.6) / (sz * 0.4))
        v.co.z -= squash * 0.025 * top * fx              # slumped, squashed top
        v.co.x *= 1 + squash * 0.05 * top                # top spreads as it slumps
        w = noise.noise(v.co * 18 + off)
        v.co += v.normal * squash * 0.004 * w            # soft wrinkles
    bm.transform(M)
    return object_from_bmesh(name, bm, coll, mat, smooth=True)


def _book(coll, name, M, w, d, h, mat):
    """Book lying flat, spine along local -Y. Boards + spine in colour, page block in paper."""
    def boards(bm):
        add_box(bm, (w, d, 0.004), (0, 0, 0.002))
        add_box(bm, (w, d, 0.004), (0, 0, h - 0.002))
        add_box(bm, (w, 0.005, h), (0, -d / 2 + 0.0025, h / 2))
    _obj(name, coll, mat, boards, M, bevel=0.0018)

    def pages(bm):
        add_box(bm, (w - 0.008, d - 0.01, h - 0.008), (0, 0.0, h / 2))
    _obj(name + "_pages", coll, MATS["paper"], pages, M, bevel=0.001)


def _font():
    for path in C.ESSAY_FONT_CANDIDATES:
        if os.path.exists(path):
            return bpy.data.fonts.load(path, check_existing=True)
    return None


def _essay_text(coll, M, ew, eh):
    """Cover title as real geometry (converted from text curves; no font needed at runtime)."""
    font = _font()
    lines = [("ESSAY", 0.012, eh - 0.035), ("The Adolescence", 0.026, eh - 0.105),
             ("of Technology", 0.026, eh - 0.138), ("Dario Amodei", 0.017, 0.05)]
    bm = bmesh.new()
    for text, size, z in lines:
        cu = bpy.data.curves.new("essay_text_tmp", "FONT")
        cu.body = text
        cu.size = size
        cu.align_x = "LEFT"
        cu.resolution_u = 2
        if font:
            cu.font = font
        tmp = bpy.data.objects.new("essay_text_tmp", cu)
        bpy.context.scene.collection.objects.link(tmp)
        bpy.context.view_layer.update()
        mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        # Text lies in local XY; stand it up on the cover's front face (-Y).
        T = M @ Matrix.Translation((-ew / 2 + 0.02, -0.0035, z)) @ Matrix.Rotation(math.pi / 2, 4, "X")
        mesh.transform(T)
        bm.from_mesh(mesh)
        bpy.data.meshes.remove(mesh)
        bpy.data.objects.remove(tmp)
        bpy.data.curves.remove(cu)
    object_from_bmesh("essay_title", bm, coll, MATS["ink"])


# --- Floor props ------------------------------------------------------------------------

def build_floor_props(coll):
    # Large terracotta pot between the front posts (shrub is added by vegetation).
    pot_pos = C.POT_POS
    _obj("pot_large", coll, MATS["terracotta"],
         lambda bm: lathe(bm, [(p.x, p.y) for p in catmull_rom(
             [(0.0, 0.0), (0.2, 0.0), (0.3, 0.18), (0.34, 0.4), (0.3, 0.64), (0.25, 0.72), (0.27, 0.75),
              (0.24, 0.765), (0.22, 0.7), (0.0, 0.68)], 3)], 48),
         xf(pot_pos), smooth=True)
    ANCHORS["pot_large_top"] = (pot_pos[0], pot_pos[1], 0.72)

    # Backpack leaning on the second front post.
    px, py = C.POSTS[1]
    bM = xf((px + 0.2, py - 0.22, 0.0), math.radians(-15), math.radians(-8))

    _soft("backpack", coll, MATS["backpack"], (0.3, 0.16, 0.44), bM, round_=0.06)
    _soft("backpack_pocket", coll, MATS["backpack"], (0.22, 0.06, 0.17), bM @ Matrix.Translation((0, -0.095, 0.05)),
          round_=0.025, squash=0.3, seed=3)
    _soft("backpack_flap", coll, MATS["backpack"], (0.27, 0.12, 0.05), bM @ Matrix.Translation((0, -0.025, 0.41)),
          round_=0.02)

    def straps(bm):
        for sx in (-0.09, 0.09):
            pts = [Vector((sx, 0.1, 0.42)), Vector((sx * 1.1, 0.14, 0.3)), Vector((sx * 1.2, 0.13, 0.12)),
                   Vector((sx, 0.09, 0.05))]
            tube(bm, pts, [0.012] * 4, sides=5)
        tube(bm, [Vector((-0.04, 0.0, 0.46)), Vector((0, 0.0, 0.5)), Vector((0.04, 0.0, 0.46))], [0.008] * 3, 5)
    _obj("backpack_straps", coll, MATS["backpack"], straps, bM, smooth=True)

    # Small pot in the wall niche.
    nk = C.NICHE
    npos = (C.RETURN_WALL_X + nk["depth"] * 0.5, nk["y"], nk["z"] + 0.035)
    _obj("pot_niche", coll, MATS["terracotta"],
         lambda bm: lathe(bm, [(0.0, 0), (0.07, 0), (0.1, 0.12), (0.11, 0.17), (0.095, 0.18), (0.0, 0.16)], 18),
         xf(npos), smooth=True)
    ANCHORS["pot_niche_top"] = (npos[0], npos[1], npos[2] + 0.17)
