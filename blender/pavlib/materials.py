"""Built-environment materials (timber, earth wall, paving, fabrics, props).

Everything is noise/wave/voronoi/pointiness/AO driven so it can be baked later.
Most objects keep their origin at the world origin with world-space vertices, so
"Object" texture coordinates are world metres and pattern scales stay consistent.
"""

import bpy

from . import materials_nature
from .config import LAPTOP_SCREEN_IMAGE, PALETTE as P, SLAT_PITCH, TABLET_SCREEN_IMAGE, WALL_H
from .matlib import MATS, bump, cell_random, coords, new, noise, weather
from .util import hex_rgba

__all__ = ["MATS", "build_all"]


def plain(name, color, rough=0.6, metallic=0.0, spec=0.5, wear=0.0, wear_col="#e8dcc6", grain=0.0):
    mat, n, bsdf, _ = new(name)
    col = hex_rgba(color) if isinstance(color, str) else color
    if grain:  # faint mottling so flat colours are not dead flat
        nz = noise(n, coords(n), 60.0, detail=3)
        col = n.mix_rgb(grain, col, nz.outputs["Color"], "OVERLAY")
    if wear:
        col = weather(n, col, wear=wear, wear_col=wear_col)
    if isinstance(col, tuple):
        bsdf.inputs["Base Color"].default_value = col
    else:
        n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular IOR Level"].default_value = spec
    return mat


def mottled(name, dark, light, scale=3.0, rough=0.8, bump_amt=0.15, fine=30.0, contrast=(0.35, 0.65),
            wear=0.0, dust=0.0, bloom=0.0):
    """Two-tone noise material with fine bump; optional edge wear, crevice dust and
    a pale mineral bloom (terracotta, plaster)."""
    mat, n, bsdf, _ = new(name)
    co = coords(n)
    big = noise(n, co, scale, detail=6, rough=0.6)
    fine_n = noise(n, co, fine, detail=3, rough=0.7)
    col = n.mix_rgb(n.map_range(big.outputs["Factor"], *contrast), hex_rgba(dark), hex_rgba(light))
    col = n.mix_rgb(0.12, col, fine_n.outputs["Color"], blend="OVERLAY")
    if bloom:
        b = noise(n, co, scale * 2.5, detail=5)
        col = n.mix_rgb(n.map_range(b.outputs["Factor"], 0.55, 0.7, 0.0, bloom), col, hex_rgba("#e8dcc8"))
    col = weather(n, col, wear=wear, wear_col="#efe2cc", dust=dust, dust_col="#6a5440")
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    if bump_amt:
        bump(n, bsdf, fine_n.outputs["Factor"], strength=bump_amt)
    return mat


def wood(name, dark, light, axis="Z", rough=0.72, grain_scale=60.0, cell=(0.6, 0.6, 0.6), cell_offset=(0, 0, 0),
         weathered=True, grain_range=(0.3, 0.75), knots=False):
    """Weathered hand-cut timber.

    Grain stretched along `axis`, darker ringed end grain, a random tone per piece
    (per slat / per post via `cell`), sun-silvered top faces, pale worn arrises and
    grime in the joints.
    """
    idx = "XYZ".index(axis)
    stretch = [1.0, 1.0, 1.0]
    stretch[idx] = 0.08
    mat, n, bsdf, _ = new(name)
    co = coords(n, scale=tuple(stretch))
    grain = noise(n, co, grain_scale, detail=8, rough=0.65, distortion=0.6)
    blotch = noise(n, coords(n), 2.5, detail=3)
    col = n.mix_rgb(n.map_range(grain.outputs["Factor"], *grain_range), hex_rgba(dark), hex_rgba(light))
    if knots:  # a few dark knots with a halo, and fine pale scratches running with the grain
        kco = coords(n, scale=tuple(0.35 if v == 0.08 else 1.0 for v in stretch))
        kv = n.new("ShaderNodeTexVoronoi")
        kv.inputs["Scale"].default_value = 3.0
        n.link(kco, kv.inputs["Vector"])
        mask = n.map_range(noise(n, kco, 1.3).outputs["Factor"], 0.55, 0.62)
        knot = n.math("MULTIPLY", n.map_range(kv.outputs["Distance"], 0.02, 0.07, 1.0, 0.0), mask)
        halo = n.math("MULTIPLY", n.map_range(kv.outputs["Distance"], 0.07, 0.16, 0.5, 0.0), mask)
        col = n.mix_rgb(halo, col, hex_rgba(dark), "MULTIPLY")
        col = n.mix_rgb(knot, col, hex_rgba("#22150d"))
        sc = list(stretch)
        sc[idx] = 0.02
        scratch = noise(n, coords(n, scale=tuple(v * 1.0 for v in sc)), 260.0, detail=1)
        lines = n.math("MULTIPLY", n.map_range(scratch.outputs["Factor"], 0.68, 0.72),
                       n.map_range(noise(n, coords(n), 4.0).outputs["Factor"], 0.5, 0.6))
        col = n.mix_rgb(n.math("MULTIPLY", lines, 0.35), col, hex_rgba("#c9a27a"))
    col = n.mix_rgb(n.map_range(blotch.outputs["Factor"], 0.4, 0.7, 0.0, 0.35), col, hex_rgba(dark), "MULTIPLY")
    # Per-piece tone: some boards a touch redder, some greyer.
    piece = cell_random(n, cell, cell_offset)
    col = n.mix_rgb(n.map_range(piece, 0.0, 0.5, 0.25, 0.0), col, hex_rgba("#8a5a38"))
    col = n.mix_rgb(n.map_range(piece, 0.5, 1.0, 0.0, 0.3), col, hex_rgba("#6b5a4a"))
    # End grain: faces whose normal runs along the grain get dark growth rings.
    geo = n.new("ShaderNodeNewGeometry")
    sepn = n.new("ShaderNodeSeparateXYZ")
    n.link(geo.outputs["Normal"], sepn.inputs[0])
    along = n.math("ABSOLUTE", sepn.outputs[idx])
    rings = n.new("ShaderNodeTexWave", wave_type="RINGS")
    rings.inputs["Scale"].default_value = 18.0
    rings.inputs["Distortion"].default_value = 4.0
    n.link(coords(n), rings.inputs["Vector"])
    end_col = n.mix_rgb(n.map_range(rings.outputs["Factor"], 0.3, 0.7), hex_rgba("#2a1c12"), hex_rgba("#6e4a30"))
    col = n.mix_rgb(n.map_range(along, 0.8, 0.95), col, end_col)
    if weathered:
        up = n.map_range(sepn.outputs[2], 0.6, 0.95, 0.0, 0.35)
        col = n.mix_rgb(up, col, hex_rgba("#8c8174"))
        col = weather(n, col, wear=0.45, wear_col="#a08468", dust=0.5, dust_col="#2a2018", ao_dist=0.1)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
    bump(n, bsdf, grain.outputs["Factor"], strength=0.3)
    return mat


def rammed_earth():
    mat, n, bsdf, _ = new("rammed_earth")
    co = coords(n)
    warp = noise(n, co, 1.6, detail=3)
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(co, sep.inputs[0])
    # Horizontal strata: z plus gentle noise warp, banded by a wave texture.
    z = n.math("ADD", sep.outputs["Z"], n.math("MULTIPLY", warp.outputs["Factor"], 0.12))
    comb = n.new("ShaderNodeCombineXYZ")
    n.link(sep.outputs["X"], comb.inputs[0])
    n.link(sep.outputs["Y"], comb.inputs[1])
    n.link(z, comb.inputs[2])
    wave = n.new("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z", wave_profile="SIN")
    wave.inputs["Scale"].default_value = 2.1
    wave.inputs["Distortion"].default_value = 1.5
    wave.inputs["Detail"].default_value = 4
    n.link(comb.outputs[0], wave.inputs["Vector"])
    big = noise(n, co, 0.9, detail=4)
    pits = n.new("ShaderNodeTexVoronoi")
    pits.inputs["Scale"].default_value = 26
    n.link(co, pits.inputs["Vector"])
    band = n.ramp(wave.outputs["Factor"], [(0.0, hex_rgba(P["wall_band"])), (0.5, hex_rgba(P["wall"])),
                                           (1.0, hex_rgba(P["wall_light"]))])
    band = n.mix_rgb(0.5, hex_rgba(P["wall"]), band)
    col = n.mix_rgb(n.map_range(big.outputs["Factor"], 0.35, 0.7, 0.0, 0.45), band, hex_rgba(P["wall_light"]))
    pit = n.map_range(pits.outputs["Distance"], 0.0, 0.09, 0.55, 0.0)
    col = n.mix_rgb(pit, col, hex_rgba(P["wall_band"]), "MULTIPLY")
    # Rain streaks running down from the top, and a damp darker band at the foot.
    streak = noise(n, coords(n, scale=(1.0, 1.0, 0.06)), 7.0, detail=5)
    from_top = n.map_range(sep.outputs["Z"], WALL_H, WALL_H - 1.4, 1.0, 0.0)
    drip = n.math("MULTIPLY", from_top, n.map_range(streak.outputs["Factor"], 0.5, 0.7, 0.0, 0.5))
    col = n.mix_rgb(drip, col, hex_rgba("#8a5a3e"))
    damp = n.map_range(sep.outputs["Z"], 0.35, 0.0, 0.0, 0.35)
    col = n.mix_rgb(damp, col, hex_rgba("#7a4e36"))
    col = weather(n, col, wear=0.35, wear_col="#e6bc98", dust=0.35, dust_col="#7a4a32", ao_dist=0.2)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    h = n.math("ADD", n.math("MULTIPLY", wave.outputs["Factor"], 0.6), pit)
    bump(n, bsdf, h, strength=0.35)
    return mat


def paving():
    mat, n, bsdf, _ = new("paving")
    co = coords(n)
    warp = noise(n, co, 3.0, detail=2)
    wv = n.new("ShaderNodeVectorMath", operation="MULTIPLY_ADD")
    n.link(warp.outputs["Color"], wv.inputs[0])
    wv.inputs[1].default_value = (0.12, 0.12, 0.0)
    n.link(co, wv.inputs[2])
    cells = n.new("ShaderNodeTexVoronoi", feature="F1")
    cells.inputs["Scale"].default_value = 2.9
    cells.inputs["Randomness"].default_value = 0.85
    n.link(wv.outputs[0], cells.inputs["Vector"])
    edges = n.new("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    edges.inputs["Scale"].default_value = 2.9
    edges.inputs["Randomness"].default_value = 0.85
    n.link(wv.outputs[0], edges.inputs["Vector"])
    tone = n.new("ShaderNodeSeparateColor")
    n.link(cells.outputs["Color"], tone.inputs[0])
    # Each stone its own colour: honey, pale cream or a rosier slab.
    col = n.ramp(tone.outputs[0], [(0.0, hex_rgba(P["paving_dark"])), (0.45, hex_rgba(P["paving"])),
                                   (0.75, hex_rgba("#e3c9a3")), (1.0, hex_rgba("#c99a7a"))])
    speck = noise(n, co, 45, detail=2)
    col = n.mix_rgb(0.18, col, speck.outputs["Color"], "OVERLAY")
    stain = noise(n, co, 0.9, detail=5)
    col = n.mix_rgb(n.map_range(stain.outputs["Factor"], 0.55, 0.7, 0.0, 0.3), col, hex_rgba("#8a6a4c"))
    # Joints: sandy grout with moss and grime working in.
    grout = n.map_range(edges.outputs["Distance"], 0.012, 0.035)
    moss = n.map_range(noise(n, co, 1.7, detail=3).outputs["Factor"], 0.45, 0.62)
    grout_col = n.mix_rgb(moss, hex_rgba(P["grout"]), hex_rgba("#5f6232"))
    col = n.mix_rgb(grout, grout_col, col)
    col = weather(n, col, dust=0.4, dust_col="#6a5038", ao_dist=0.3)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
    # Stones sit at slightly different heights (per-cell offset) plus surface pitting.
    h = n.math("ADD", grout, n.math("MULTIPLY", speck.outputs["Factor"], 0.15))
    h = n.math("ADD", h, n.math("MULTIPLY", tone.outputs[1], 0.25))
    bump(n, bsdf, h, strength=0.5, distance=0.03)
    return mat


def pattern_fabric(name, a, b, scale=9.0, kind="diamond", rough=0.9):
    """Woven-looking geometric pattern for the throw and patterned cushion."""
    mat, n, bsdf, _ = new(name)
    co = coords(n)
    if kind == "diamond":
        mp = n.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0.0, 0.0, 0.785)
        n.link(co, mp.inputs["Vector"])
        co = mp.outputs[0]
    chk = n.new("ShaderNodeTexChecker")
    chk.inputs["Scale"].default_value = scale
    chk.inputs["Color1"].default_value = hex_rgba(a)
    chk.inputs["Color2"].default_value = hex_rgba(b)
    n.link(co, chk.inputs["Vector"])
    wave = n.new("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z")
    wave.inputs["Scale"].default_value = scale * 0.6
    n.link(co, wave.inputs["Vector"])
    col = n.mix_rgb(n.map_range(wave.outputs["Factor"], 0.85, 0.9), chk.outputs["Color"], hex_rgba(b))
    weave = noise(n, coords(n), 400.0, detail=1)
    col = n.mix_rgb(0.15, col, weave.outputs["Color"], "OVERLAY")
    col = weather(n, col, dust=0.4, dust_col="#4a3f36", ao_dist=0.05)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Sheen Weight"].default_value = 0.5
    bump(n, bsdf, weave.outputs["Factor"], strength=0.15, distance=0.005)
    return mat


def ruled_paper():
    """Notebook pages: paper with faint ruled lines (deliberately no text)."""
    mat, n, bsdf, _ = new("paper_ruled")
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(coords(n), sep.inputs[0])
    rot = n.math("ADD", sep.outputs["Y"], n.math("MULTIPLY", sep.outputs["X"], 0.14))
    lines = n.math("SINE", n.math("MULTIPLY", rot, 6.2832 / 0.0085))
    col = n.mix_rgb(n.map_range(lines, 0.88, 0.97, 0.0, 0.35), hex_rgba(P["paper"]), hex_rgba("#8fa0b5"))
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def sketch_paper():
    """Notebook page with faint pencil sketch strokes (loose curves, no letters)."""
    mat, n, bsdf, _ = new("paper_sketch")
    co = coords(n)
    warp = noise(n, co, 18.0, detail=2)
    wv = n.new("ShaderNodeVectorMath", operation="MULTIPLY_ADD")
    n.link(warp.outputs["Color"], wv.inputs[0])
    wv.inputs[1].default_value = (0.02, 0.02, 0.0)
    n.link(co, wv.inputs[2])
    strokes = n.new("ShaderNodeTexWave", wave_type="RINGS", wave_profile="SIN")
    strokes.inputs["Scale"].default_value = 40.0
    strokes.inputs["Distortion"].default_value = 6.0
    strokes.inputs["Detail"].default_value = 2.0
    n.link(wv.outputs[0], strokes.inputs["Vector"])
    line = n.map_range(strokes.outputs["Factor"], 0.94, 0.99)
    patch = n.map_range(noise(n, co, 9.0).outputs["Factor"], 0.5, 0.58)
    col = n.mix_rgb(n.math("MULTIPLY", n.math("MULTIPLY", line, patch), 0.55), hex_rgba(P["paper"]),
                    hex_rgba("#5d5a57"))
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def screen(name, image_path, strength=2.2):
    mat, n, bsdf, _ = new(name)
    img = bpy.data.images.load(str(image_path), check_existing=True)
    img.pack()  # keep the .blend self-contained
    tex = n.new("ShaderNodeTexImage", image=img, interpolation="Cubic")
    uv = n.new("ShaderNodeTexCoord")
    n.link(uv.outputs["UV"], tex.inputs["Vector"])
    n.link(tex.outputs["Color"], bsdf.inputs["Base Color"])
    n.link(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = 0.15
    return mat


def glow(name, colour, strength):
    """Lantern glass: warm emission (exports as KHR emissive)."""
    mat, n, bsdf, _ = new(name)
    bsdf.inputs["Base Color"].default_value = hex_rgba(colour)
    bsdf.inputs["Emission Color"].default_value = hex_rgba(colour)
    bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def build_all():
    MATS.clear()
    materials_nature.build()
    rammed_earth()
    paving()
    mottled("bench_plaster", P["bench"], P["bench_cap"], scale=4, rough=0.85, bump_amt=0.1, wear=0.4, dust=0.45)
    mottled("terracotta", "#9a5332", P["pot"], scale=5, rough=0.8, bump_amt=0.12, wear=0.3, dust=0.3, bloom=0.4)
    beam_cell = (0.5, 0.5, 0.5)
    wood("timber_post", P["timber"], P["timber_light"], "Z", cell=beam_cell)
    wood("timber_beam_x", P["timber"], P["timber_light"], "X", cell=(50, 0.4, 0.15))
    wood("timber_beam_y", P["timber"], P["timber_light"], "Y", cell=(0.4, 50, 0.15))
    wood("slat", "#5c3620", P["slat"], "Y", grain_scale=40, cell=(SLAT_PITCH, 50, 50),
         cell_offset=((0.4 + SLAT_PITCH / 2) / SLAT_PITCH, 0, 0))  # boundaries fall in the gaps
    wood("table_wood", "#3e2516", "#8a5d3a", "X", rough=0.5, grain_scale=45, grain_range=(0.38, 0.62),
         cell=(50, 0.2, 50), knots=True)
    pattern_fabric("throw", P["fabric"], P["fabric_light"], scale=34, kind="diamond")
    pattern_fabric("cushion_pattern", P["cushion_dark"], P["cushion"], scale=11, kind="diamond")
    mottled("cushion_plain", "#c9b998", P["cushion"], scale=8, rough=0.95, bump_amt=0.08, dust=0.3)
    plain("paper", P["paper"], rough=0.8, grain=0.05)
    ruled_paper()
    sketch_paper()
    plain("notebook_cover", "#7a3b2c", rough=0.6, wear=0.4, wear_col="#c98a6a", grain=0.1)
    plain("ribbon", "#b0402e", rough=0.4)
    plain("ink", P["ink"], rough=0.6)
    plain("aluminium", P["aluminium"], rough=0.3, metallic=0.85, wear=0.3, wear_col="#d8d8dc")
    plain("bezel", P["screen_bezel"], rough=0.25)
    plain("ceramic_white", P["mug_white"], rough=0.2, grain=0.04)
    plain("ceramic_dark", P["mug_dark"], rough=0.3, wear=0.4, wear_col="#8a7a68")
    plain("ceramic_glaze", "#5f7f86", rough=0.18, wear=0.5, wear_col="#d9cdb6", grain=0.06)
    plain("fruit_orange", "#d9761e", rough=0.45, grain=0.12)
    plain("fruit_fig", "#4a2a3a", rough=0.5, grain=0.1)
    plain("lantern_metal", "#2d2a26", rough=0.45, metallic=0.7, wear=0.5, wear_col="#8a6a48")
    glow("lantern_glass", "#ffb45e", 3.0)
    plain("backpack", P["backpack"], rough=0.85, wear=0.3, wear_col="#5d6560", grain=0.15)
    plain("stake", "#3a2c22", rough=0.85, grain=0.2)
    plain("soil", "#6b4a32", rough=1.0)
    for i, c in enumerate(P["books"]):
        plain(f"book_{i}", c, rough=0.7, wear=0.15, grain=0.08)
    screen("screen_laptop", LAPTOP_SCREEN_IMAGE)
    screen("screen_tablet", TABLET_SCREEN_IMAGE)
    return MATS
