"""Shared material plumbing: the MATS registry and small node-building helpers.

Every effect here is a regular Cycles shader input (noise, voronoi, pointiness,
ambient occlusion, world position), so all of it can be baked to textures later.
"""

import bpy

from .util import Nodes, hex_rgba

MATS = {}


def new(name):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    nt.nodes.clear()
    n = Nodes(nt)
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    n.link(bsdf.outputs[0], out.inputs["Surface"])
    MATS[name] = mat
    return mat, n, bsdf, out


def coords(n, kind="Object", scale=(1, 1, 1)):
    tc = n.new("ShaderNodeTexCoord")
    sock = tc.outputs[kind]
    if scale != (1, 1, 1):
        mp = n.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        n.link(sock, mp.inputs["Vector"])
        sock = mp.outputs[0]
    return sock


def noise(n, vec, scale, detail=4.0, rough=0.55, distortion=0.0):
    node = n.new("ShaderNodeTexNoise")
    n.link(vec, node.inputs["Vector"])
    node.inputs["Scale"].default_value = scale
    node.inputs["Detail"].default_value = detail
    node.inputs["Roughness"].default_value = rough
    node.inputs["Distortion"].default_value = distortion
    return node


def bump(n, bsdf, height, strength=0.2, distance=0.02):
    b = n.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    n.link(height, b.inputs["Height"])
    n.link(b.outputs[0], bsdf.inputs["Normal"])


def weather(n, col, wear=0.0, wear_col="#d9c7a8", dust=0.0, dust_col="#5a4a3a", ao_dist=0.12):
    """Edge wear on convex edges (pointiness) and dust/grime in crevices (AO)."""
    geo = n.new("ShaderNodeNewGeometry")
    if wear:
        w = n.map_range(geo.outputs["Pointiness"], 0.52, 0.6, 0.0, wear)
        col = n.mix_rgb(w, col, hex_rgba(wear_col))
    if dust:
        ao = n.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = ao_dist
        d = n.map_range(ao.outputs["AO"], 0.95, 0.35, 0.0, dust)
        col = n.mix_rgb(d, col, hex_rgba(dust_col))
    return col


def cell_random(n, cell, offset=(0, 0, 0)):
    """A random value per block of space (per slat, per post) from snapped coordinates.

    `cell` is the block size in metres; `offset` shifts the grid, in cells."""
    co = coords(n)
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = offset
    mp.inputs["Scale"].default_value = tuple(1.0 / c for c in cell)
    n.link(co, mp.inputs["Vector"])
    snap = n.new("ShaderNodeVectorMath", operation="FLOOR")
    n.link(mp.outputs[0], snap.inputs[0])
    wn = n.new("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    n.link(snap.outputs[0], wn.inputs["Vector"])
    return wn.outputs["Value"]


def distance_haze(n, col, haze_col, start, end, amount, centre=(2.5, 1.0, 0.0)):
    """Aerial perspective baked into albedo: blend towards haze by distance from the pavilion."""
    geo = n.new("ShaderNodeNewGeometry")
    dist = n.new("ShaderNodeVectorMath", operation="DISTANCE")
    n.link(geo.outputs["Position"], dist.inputs[0])
    dist.inputs[1].default_value = centre
    haze = hex_rgba(haze_col) if isinstance(haze_col, str) else haze_col   # hex or a colour socket
    return n.mix_rgb(n.map_range(dist.outputs["Value"], start, end, 0.0, amount), col, haze)


def warm_haze(n, cool_hex, warm_hex, glow_dir, centre=(2.5, 1.0, 0.0)):
    """Haze colour that warms towards the glow (sun-side) azimuth.

    Uses the surface's world position relative to the pavilion, so it bakes into
    static textures; the browser only needs the matching sky dome and fog colour.
    """
    geo = n.new("ShaderNodeNewGeometry")
    rel = n.new("ShaderNodeVectorMath", operation="SUBTRACT")
    n.link(geo.outputs["Position"], rel.inputs[0])
    rel.inputs[1].default_value = centre
    flat = n.new("ShaderNodeVectorMath", operation="MULTIPLY")
    n.link(rel.outputs[0], flat.inputs[0])
    flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    unit = n.new("ShaderNodeVectorMath", operation="NORMALIZE")
    n.link(flat.outputs[0], unit.inputs[0])
    dot = n.new("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    n.link(unit.outputs[0], dot.inputs[0])
    gx, gy = glow_dir[0], glow_dir[1]
    ln = (gx * gx + gy * gy) ** 0.5
    dot.inputs[1].default_value = (gx / ln, gy / ln, 0.0)
    return n.mix_rgb(n.map_range(dot.outputs["Value"], 0.2, 1.0), hex_rgba(cool_hex), hex_rgba(warm_hex))
