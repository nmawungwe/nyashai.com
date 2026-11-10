"""Pergola, rammed-earth walls, masonry bench and stone paving."""

import math

import bmesh
from mathutils import Matrix, Vector, noise

from . import config as C
from .materials import MATS
from .util import add_bevel, add_box, add_timber, box_object, object_from_bmesh, object_from_data, rng


def roof_base(x):
    """Z of the underside of the main beams at position x (roof pitches up to +X)."""
    return C.PERGOLA_H + C.ROOF_PITCH * x


def build(coll):
    _posts(coll)
    _beams_and_slats(coll)
    _walls(coll)
    _bench(coll)


def _timber_matrix(center, axis, pitch=0.0):
    """Matrix taking add_timber's local +X onto world `axis` ("X", "Y" or "Z")."""
    rot = {"X": Matrix.Rotation(-pitch, 4, "Y"),
           "Y": Matrix.Rotation(math.pi / 2, 4, "Z"),
           "Z": Matrix.Rotation(-math.pi / 2, 4, "Y")}[axis]
    return Matrix.Translation(center) @ rot


def _posts(coll):
    r = rng(12)
    bm = bmesh.new()
    for x, y in C.POSTS:
        h = roof_base(x)
        add_timber(bm, h, C.POST_SIZE, C.POST_SIZE, _timber_matrix((x, y, h / 2), "Z"), r)
    obj = object_from_bmesh("pergola_posts", bm, coll, MATS["timber_post"])
    add_bevel(obj, 0.014)
    bm = bmesh.new()
    for x, y in C.POSTS:
        add_box(bm, (0.26, 0.26, 0.06), (x, y, 0.03))
    obj = object_from_bmesh("pergola_footings", bm, coll, MATS["bench_plaster"])
    add_bevel(obj, 0.01)


def _pitched_timber_x(bm, r, x0, x1, y, width, height, z_offset=0.0):
    """Beam along X following the roof pitch; its underside sits on roof_base(x)."""
    length = x1 - x0
    xc = (x0 + x1) / 2
    ang = math.atan(C.ROOF_PITCH)
    zc = roof_base(xc) + height / 2 + z_offset
    add_timber(bm, length / math.cos(ang), width, height, _timber_matrix((xc, y, zc), "X", ang), r)


def _beams_and_slats(coll):
    r = rng(13)
    ov = C.BEAM_OVERHANG
    x0, x1 = -ov, C.PERGOLA_W + ov
    front_y, back_y = C.POSTS[0][1], C.WALL_Y - 0.15
    bm = bmesh.new()
    _pitched_timber_x(bm, r, x0, x1, front_y, C.BEAM_W, C.BEAM_H)
    _pitched_timber_x(bm, r, x0 + 0.3, x1, back_y, C.BEAM_W, C.BEAM_H)
    _pitched_timber_x(bm, r, x0 + 0.15, x1, (front_y + back_y) / 2, C.BEAM_W * 0.8, C.BEAM_H * 0.8,
                      z_offset=C.BEAM_H * 0.2)
    obj = object_from_bmesh("pergola_beams_x", bm, coll, MATS["timber_beam_x"])
    add_bevel(obj, 0.012)

    # Side beams (along Y) tie the posts together under the X beams.
    bm = bmesh.new()
    for x in sorted({p[0] for p in C.POSTS} | {C.RETURN_WALL_X - 0.1}):
        z = roof_base(x) - C.BEAM_H * 0.4
        add_timber(bm, back_y - front_y + 0.5, C.BEAM_W * 0.85, C.BEAM_H * 0.8,
                   _timber_matrix((x, (front_y + back_y) / 2, z), "Y"), r)
    obj = object_from_bmesh("pergola_beams_y", bm, coll, MATS["timber_beam_y"])
    add_bevel(obj, 0.012)

    # Roof slats run front-to-back, sitting on the X beams. Each slat is level;
    # the pitch comes from slat height increasing with x.
    bm = bmesh.new()
    n = int((x1 - x0 - 0.1) / C.SLAT_PITCH)
    y0, y1 = front_y - 0.05, C.WALL_Y + 0.05
    for i in range(n):
        x = x0 + 0.05 + i * C.SLAT_PITCH
        z = roof_base(x) + C.BEAM_H + C.SLAT_H / 2 + 0.002
        jitter = r.uniform(-0.01, 0.01)
        add_box(bm, (C.SLAT_W, y1 - y0 + jitter, C.SLAT_H), (x + jitter * 0.3, (y0 + y1) / 2, z),
                rot=(r.uniform(-0.01, 0.01), 0, r.uniform(-0.004, 0.004)))
    obj = object_from_bmesh("pergola_slats", bm, coll, MATS["slat"])
    add_bevel(obj, 0.004, segments=1)

    # Fascia board along the front edge hides the slat ends (as in the reference).
    bm = bmesh.new()
    _pitched_timber_x(bm, r, x0, x1, front_y - 0.1, 0.04, 0.13, z_offset=C.BEAM_H - 0.04)
    obj = object_from_bmesh("pergola_fascia", bm, coll, MATS["timber_beam_x"])
    add_bevel(obj, 0.008)


def _walls(coll):
    t, H = C.WALL_T, C.WALL_H
    bm = bmesh.new()
    # Back wall.
    add_box(bm, (C.WALL_X1 - C.WALL_X0, t, H), ((C.WALL_X0 + C.WALL_X1) / 2, C.WALL_Y + t / 2, H / 2))
    # Right-hand return wall with a niche cut out of its inner face.
    rx0, rx1 = C.RETURN_WALL_X, C.RETURN_WALL_X + t
    ry0, ry1 = C.RETURN_WALL_Y0, C.WALL_Y
    nk = C.NICHE
    ny0, ny1 = nk["y"] - nk["w"] / 2, nk["y"] + nk["w"] / 2
    nz0, nz1 = nk["z"], nk["z"] + nk["h"]
    xc, xw = (rx0 + rx1) / 2, t
    add_box(bm, (xw, ry1 - ry0, nz0), (xc, (ry0 + ry1) / 2, nz0 / 2))                       # below
    add_box(bm, (xw, ry1 - ry0, H - nz1), (xc, (ry0 + ry1) / 2, (nz1 + H) / 2))            # above
    add_box(bm, (xw, ny0 - ry0, nz1 - nz0), (xc, (ry0 + ny0) / 2, (nz0 + nz1) / 2))        # near side
    add_box(bm, (xw, ry1 - ny1, nz1 - nz0), (xc, (ny1 + ry1) / 2, (nz0 + nz1) / 2))        # far side
    back_x0 = rx0 + nk["depth"]
    add_box(bm, (rx1 - back_x0, ny1 - ny0, nz1 - nz0), ((back_x0 + rx1) / 2, nk["y"], (nz0 + nz1) / 2))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    _subdivide_for_bake(bm, 0.5)
    _subdivide_for_bake(bm, 0.3)
    # Rammed earth is hand-tamped: let faces and edges wander by a centimetre or so.
    for v in bm.verts:
        v.co += Vector((noise.noise(v.co * 1.7), noise.noise(v.co * 1.7 + Vector((9, 0, 0))),
                        noise.noise(v.co * 1.7 + Vector((0, 9, 0))) * 0.5)) * 0.012
    obj = object_from_bmesh("wall_rammed_earth", bm, coll, MATS["rammed_earth"])
    add_bevel(obj, 0.03, segments=3)
    # Niche shelf (thin timber board).
    box_object("wall_niche_shelf", (nk["depth"] + 0.04, nk["w"], 0.035),
               (rx0 + nk["depth"] / 2 - 0.02, nk["y"], nz0 + 0.0175), coll, MATS["table_wood"], bevel=0.005)


def _subdivide_for_bake(bm, edge_len):
    """Split long edges so large faces still have vertices for later vertex-colour AO."""
    long_edges = [e for e in bm.edges if e.calc_length() > edge_len]
    if long_edges:
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)


def _bench(coll):
    x0, x1 = C.WALL_X0 + 0.1, C.RETURN_WALL_X
    y1 = C.WALL_Y
    y0 = y1 - C.BENCH_D
    bm = bmesh.new()
    add_box(bm, (x1 - x0, C.BENCH_D - 0.04, C.BENCH_H - 0.06), ((x0 + x1) / 2, (y0 + y1) / 2 + 0.02,
                                                                 (C.BENCH_H - 0.06) / 2))
    add_box(bm, (x1 - x0 + 0.04, C.BENCH_D + 0.03, 0.06), ((x0 + x1) / 2 - 0.02, (y0 + y1) / 2 - 0.015,
                                                           C.BENCH_H - 0.03))
    obj = object_from_bmesh("bench_masonry", bm, coll, MATS["bench_plaster"])
    add_bevel(obj, 0.02, segments=3)


PAVING_BOUNDS = (-1.0, C.RETURN_WALL_X + 0.1, -7.5, C.WALL_Y + 0.02)


def paving_inside(x, y):
    """Left edge runs diagonally away from the hero camera so the foreground
    bottom-left is garden (boulders, grasses) and bottom-right is paving."""
    x0, x1, y0, y1 = PAVING_BOUNDS
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    wobble = 0.45 * noise.noise(Vector((x * 0.6, y * 0.6, 3.1)))
    left_edge = -0.6 + max(0.0, -y) * 0.7
    return x > left_edge + wobble


def paving(coll):
    """Irregular paved terrace under and in front of the pergola.

    A grid clipped by a noisy outline (keeps vertices for vertex AO and a clean
    planar UV later). Stone joints come from the voronoi `paving` material.
    """
    step = 0.25
    x0, x1, y0, y1 = PAVING_BOUNDS
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    verts, faces, index = [], [], {}
    inside = paving_inside

    for j in range(ny + 1):
        for i in range(nx + 1):
            index[(i, j)] = len(verts)
            x, y = x0 + i * step, y0 + j * step
            verts.append((x, y, 0.012 + 0.006 * noise.noise(Vector((x * 2, y * 2, 0.0)))))
    for j in range(ny):
        for i in range(nx):
            cx, cy = x0 + (i + 0.5) * step, y0 + (j + 0.5) * step
            if inside(cx, cy):
                faces.append((index[(i, j)], index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]))
    obj = object_from_data("ground_paving", verts, faces, coll, MATS["paving"])
    # Drop unused vertices left by the clipping.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return obj
