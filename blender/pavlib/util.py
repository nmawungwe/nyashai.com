"""Generic helpers: scene reset, collections, mesh primitives, node wiring."""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise


# --- Scene / collections ----------------------------------------------------------

def reset_scene():
    """Start from an empty file (no default cube/camera/light)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.node_groups,
                 bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.worlds):
        for block in list(coll):
            coll.remove(block)


_collections = {}


def collection(name, parent=None, hide_render=False):
    if name in _collections and _collections[name].name in bpy.data.collections:
        return _collections[name]
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    coll.hide_render = hide_render
    _collections[name] = coll
    return coll


def link(obj, coll):
    coll.objects.link(obj)
    return obj


# --- Colour ------------------------------------------------------------------------

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h, alpha=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


# --- Mesh objects ------------------------------------------------------------------

def object_from_bmesh(name, bm, coll, material=None, smooth=False):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for p in mesh.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    if material is not None:
        mats = material if isinstance(material, (list, tuple)) else [material]
        for m in mats:
            mesh.materials.append(m)
    return link(obj, coll)


def object_from_data(name, verts, faces, coll, material=None, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    mesh.validate()
    if smooth:
        for p in mesh.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    if material is not None:
        mesh.materials.append(material)
    return link(obj, coll)


def add_box(bm, size, center=(0, 0, 0), rot=(0, 0, 0)):
    """Add an axis-aligned box (then rotated by XYZ euler) into an existing bmesh."""
    sx, sy, sz = size
    m = Matrix.Translation(center) @ _euler_matrix(rot) @ Matrix.Diagonal((sx, sy, sz, 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def add_cylinder(bm, radius, depth, center=(0, 0, 0), rot=(0, 0, 0), segments=12, radius2=None):
    m = Matrix.Translation(center) @ _euler_matrix(rot)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius if radius2 is None else radius2,
                          depth=depth, matrix=m)


def _euler_matrix(rot):
    from mathutils import Euler
    return Euler(rot, "XYZ").to_matrix().to_4x4()


def box_object(name, size, center, coll, material, rot=(0, 0, 0), bevel=0.0):
    bm = bmesh.new()
    add_box(bm, size, center, rot)
    obj = object_from_bmesh(name, bm, coll, material)
    if bevel:
        add_bevel(obj, bevel)
    return obj


def add_bevel(obj, width, segments=2):
    """Small rounded bevel on hard edges so they catch a highlight; normals hardened."""
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.profile = 0.6
    mod.limit_method = "ANGLE"
    mod.harden_normals = True
    auto_smooth(obj)
    return mod


def auto_smooth(obj, angle_deg=35.0):
    """Smooth shading with sharp edges above `angle_deg` (Blender 4.1+ auto-smooth)."""
    mesh = obj.data
    if not getattr(mesh, "polygons", None):
        return
    mesh.shade_smooth()
    mesh.set_sharp_from_angle(angle=math.radians(angle_deg))


def add_timber(bm, length, width, height, matrix, r, wobble=0.006, seg_len=0.35):
    """A hand-cut beam along local +X (centred): slightly wavy, twisted, uneven
    section and checked (split) arrises. Real geometry so it bakes and exports."""
    n = max(2, int(length / seg_len))
    seed = Vector((r.uniform(0, 100), r.uniform(0, 100), r.uniform(0, 100)))
    rings = []
    for i in range(n + 1):
        t = i / n
        x = -length / 2 + t * length
        p = seed + Vector((x * 1.3, 0, 0))
        oy = wobble * noise.noise(p)
        oz = wobble * noise.noise(p + Vector((17, 0, 0)))
        sw = 1.0 + 0.04 * noise.noise(p + Vector((0, 23, 0)))
        sh = 1.0 + 0.04 * noise.noise(p + Vector((0, 0, 31)))
        twist = 0.02 * noise.noise(p * 0.5 + Vector((7, 7, 7)))
        ring = []
        for cy, cz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            y = cy * width / 2 * sw
            z = cz * height / 2 * sh
            y, z = y * math.cos(twist) - z * math.sin(twist), y * math.sin(twist) + z * math.cos(twist)
            ring.append(bm.verts.new(matrix @ Vector((x, y + oy, z + oz))))
        rings.append(ring)
    for i in range(n):
        for k in range(4):
            k2 = (k + 1) % 4
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def tube(bm, points, radii, sides=8, cap=True, twist_noise=0.0, seed=0):
    """Sweep a circle along a polyline using parallel-transport frames."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    tangents = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tangents.append((b - a).normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    normal = tangents[0].cross(ref).normalized()
    rings = []
    for i, (p, t) in enumerate(zip(pts, tangents)):
        if i > 0:
            axis = tangents[i - 1].cross(t)
            if axis.length > 1e-6:
                ang = tangents[i - 1].angle(t)
                normal = (Matrix.Rotation(ang, 3, axis.normalized()) @ normal).normalized()
        binormal = t.cross(normal).normalized()
        ring = []
        for s in range(sides):
            a = 2 * math.pi * s / sides
            r = radii[i]
            if twist_noise:
                r *= 1.0 + twist_noise * noise.noise(Vector((p.x * 2 + s, p.y * 2, p.z * 2 + seed)))
            ring.append(bm.verts.new(p + (normal * math.cos(a) + binormal * math.sin(a)) * r))
        rings.append(ring)
    for i in range(n - 1):
        for s in range(sides):
            s2 = (s + 1) % sides
            bm.faces.new((rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])


def catmull_rom(ctrl, samples_per_seg=4):
    """Smooth a list of control points (tuples) into a denser polyline."""
    pts = [Vector(c) for c in ctrl]
    if len(pts) < 3:
        return pts
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(samples_per_seg):
            t = k / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def rock_bmesh(bm, center, scale, rng, subdiv=3, roughness=0.25, flatten_bottom=True, strata=0.0):
    """Displaced icosphere for boulders and wall stones (real geometry, exportable)."""
    m = Matrix.Translation(center) @ Matrix.Diagonal((*scale, 1))
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4))
    offset = Vector((rng.uniform(0, 100), rng.uniform(0, 100), rng.uniform(0, 100)))
    for v in res["verts"]:
        d = v.co.normalized()
        n1 = noise.fractal(d * 1.3 + offset, 0.5, 2.0, 4)
        n2 = noise.noise(d * 4.0 + offset)
        r = 1.0 + roughness * n1 + roughness * 0.25 * n2
        if strata:  # stepped bedding planes and crisp small-scale breakup
            r += strata * (abs(math.sin(d.z * 9.0 + n1 * 2.0)) - 0.5)
            r += strata * 0.6 * noise.noise(d * 11.0 + offset)
        co = d * r
        if flatten_bottom and co.z < -0.35:
            co.z = -0.35 + (co.z + 0.35) * 0.2
        v.co = m @ co
    return res["verts"]


def rng(salt):
    from .config import SEED
    return random.Random(SEED * 1000 + salt)


# --- Shader node helpers -------------------------------------------------------------

class Nodes:
    """Tiny wrapper for building node trees with less ceremony."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links

    def new(self, kind, **props):
        node = self.nodes.new(kind)
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def link(self, out, inp):
        self.links.new(out, inp)

    def mix_rgb(self, fac, a, b, blend="MIX"):
        node = self.new("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self._set(node.inputs[0], fac)
        self._set(node.inputs[6], a)
        self._set(node.inputs[7], b)
        return node.outputs[2]

    def math(self, op, a, b=None, clamp=False):
        node = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        self._set(node.inputs[0], a)
        if b is not None:
            self._set(node.inputs[1], b)
        return node.outputs[0]

    def map_range(self, value, fmin, fmax, tmin=0.0, tmax=1.0):
        node = self.new("ShaderNodeMapRange", clamp=True)
        self._set(node.inputs[0], value)
        node.inputs[1].default_value = fmin
        node.inputs[2].default_value = fmax
        node.inputs[3].default_value = tmin
        node.inputs[4].default_value = tmax
        return node.outputs[0]

    def ramp(self, fac, stops):
        node = self.new("ShaderNodeValToRGB")
        self._set(node.inputs[0], fac)
        el = node.color_ramp.elements
        while len(el) > len(stops):
            el.remove(el[-1])
        while len(el) < len(stops):
            el.new(0.5)
        for e, (pos, col) in zip(el, stops):
            e.position = pos
            e.color = col
        return node.outputs[0]

    def _set(self, socket, value):
        if hasattr(value, "is_output") or isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, socket)
        else:
            socket.default_value = value
