"""Natural materials: ground, rock, bark, foliage species, grasses, flowers.

Foliage tint varies per instance (Object Info > Random). That value does not
survive GLB export; stage 2 should bake it into a per-instance colour attribute.
"""

from .config import PALETTE as P, SKY_GLOW_DIR
from .matlib import bump, coords, distance_haze, new, noise, warm_haze, weather
from .util import hex_rgba

LEAF_HAZE = "#a7b3a4"   # what foliage fades towards with distance


def terrain():
    """Patchy hillside ground: dry gold grass, olive green and bare earth patches."""
    mat, n, bsdf, _ = new("terrain")
    co = coords(n)
    warp = noise(n, co, 0.08, detail=2)
    wv = n.new("ShaderNodeVectorMath", operation="MULTIPLY_ADD")
    n.link(warp.outputs["Color"], wv.inputs[0])
    wv.inputs[1].default_value = (6.0, 6.0, 0.0)
    n.link(co, wv.inputs[2])
    big = noise(n, wv.outputs[0], 0.18, detail=5, rough=0.6)
    mid = noise(n, co, 0.9, detail=6, rough=0.6)
    earth = noise(n, wv.outputs[0], 0.45, detail=3)
    streak = noise(n, coords(n, scale=(1, 1, 0.2)), 14.0, detail=4, rough=0.7)
    col = n.ramp(big.outputs["Factor"], [(0.3, hex_rgba(P["terrain_green"])), (0.45, hex_rgba("#8f8a48")),
                                          (0.55, hex_rgba(P["terrain"])), (0.68, hex_rgba(P["terrain_dry"]))])
    col = n.mix_rgb(n.map_range(mid.outputs["Factor"], 0.3, 0.7, 0.0, 0.5), col, hex_rgba("#b89d5c"))
    col = n.mix_rgb(n.map_range(earth.outputs["Factor"], 0.62, 0.72, 0.0, 0.7), col, hex_rgba("#8e6a48"))
    col = n.mix_rgb(0.25, col, streak.outputs["Color"], "OVERLAY")
    col = _slope_detail(n, co, col)
    col = distance_haze(n, col, warm_haze(n, "#ab9d62", "#cbb683", SKY_GLOW_DIR), 15.0, 160.0, 0.5)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    bump(n, bsdf, streak.outputs["Factor"], strength=0.35)
    return mat


def _slope_detail(n, co, col):
    """Beyond the garden (>14 m out): scrub clumps, faint terrace lines and a worn
    path, so the garden runs into a lived-in hillside rather than a blank field."""
    geo = n.new("ShaderNodeNewGeometry")
    dist = n.new("ShaderNodeVectorMath", operation="DISTANCE")
    n.link(geo.outputs["Position"], dist.inputs[0])
    dist.inputs[1].default_value = (2.5, 1.0, 0.0)
    out = n.math("MULTIPLY", n.map_range(dist.outputs["Value"], 12.0, 18.0),
                 n.map_range(dist.outputs["Value"], 34.0, 26.0))   # small clumps only 12-34 m out
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(co, sep.inputs[0])
    # Terrace lines: faint darker contours every ~1.4 m of height.
    terr = n.math("SINE", n.math("MULTIPLY", sep.outputs["Z"], 6.2832 / 1.4))
    col = n.mix_rgb(n.math("MULTIPLY", n.map_range(terr, 0.85, 1.0, 0.0, 0.3), out), col, hex_rgba("#6e6232"))
    # Scrub clumps in stands.
    cells = n.new("ShaderNodeTexVoronoi")
    cells.inputs["Scale"].default_value = 1.0 / 2.2
    n.link(co, cells.inputs["Vector"])
    dots = n.map_range(cells.outputs["Distance"], 0.2, 0.34, 1.0, 0.0)
    stands = n.map_range(noise(n, co, 1.0 / 25.0, detail=3).outputs["Factor"], 0.44, 0.58)
    col = n.mix_rgb(n.math("MULTIPLY", n.math("MULTIPLY", dots, stands), out), col, hex_rgba("#46502a"))
    # Further out the valley floor turns gold like the near ridges; its trees are
    # real geometry (ground_cover.build_scrub), not texture dots.
    far = n.map_range(dist.outputs["Value"], 25.0, 45.0)
    col = n.mix_rgb(n.math("MULTIPLY", far, 0.9), col, hex_rgba("#c9a656"))
    # A worn path winding down towards the valley (north-west).
    warp = noise(n, co, 0.06, detail=2)
    across = n.math("ADD", n.math("SUBTRACT", n.math("MULTIPLY", sep.outputs["X"], 0.5),
                                  n.math("MULTIPLY", sep.outputs["Y"], 0.866)),
                    n.math("MULTIPLY", n.math("SUBTRACT", warp.outputs["Factor"], 0.5), 14.0))
    path = n.map_range(n.math("ABSOLUTE", n.math("ADD", across, 1.5)), 0.55, 0.9, 0.7, 0.0)
    return n.mix_rgb(n.math("MULTIPLY", path, out), col, hex_rgba("#d1b98a"))


def rock():
    """Weathered sandstone: bedding strata, fine pitting, lichen colonies, dark crevices."""
    mat, n, bsdf, _ = new("rock")
    co = coords(n)
    big = noise(n, co, 1.8, detail=6, rough=0.6)
    fine = noise(n, co, 14.0, detail=6, rough=0.75)
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(co, sep.inputs[0])
    strata = n.new("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z", wave_profile="SAW")
    strata.inputs["Scale"].default_value = 3.2
    strata.inputs["Distortion"].default_value = 3.0
    strata.inputs["Detail"].default_value = 6
    n.link(co, strata.inputs["Vector"])
    col = n.ramp(strata.outputs["Factor"], [(0.0, hex_rgba("#8f826c")), (0.35, hex_rgba(P["rock"])),
                                            (0.7, hex_rgba("#c2b499")), (1.0, hex_rgba(P["rock_dark"]))])
    col = n.mix_rgb(n.map_range(big.outputs["Factor"], 0.35, 0.65, 0.0, 0.5), col, hex_rgba(P["rock_dark"]))
    col = n.mix_rgb(0.2, col, fine.outputs["Color"], "OVERLAY")
    # Lichen: grey-green and orange colonies, mostly on upward faces.
    geo = n.new("ShaderNodeNewGeometry")
    upn = n.new("ShaderNodeSeparateXYZ")
    n.link(geo.outputs["Normal"], upn.inputs[0])
    up = n.map_range(upn.outputs["Z"], 0.1, 0.7)
    lich = noise(n, co, 3.5, detail=8, rough=0.75)
    patch = n.math("MULTIPLY", n.map_range(lich.outputs["Factor"], 0.56, 0.62), up)
    lich_col = n.mix_rgb(n.map_range(noise(n, co, 0.8).outputs["Factor"], 0.45, 0.55), hex_rgba("#9a9f78"),
                         hex_rgba("#c98b3a"))
    col = n.mix_rgb(n.math("MULTIPLY", patch, 0.85), col, lich_col)
    col = weather(n, col, dust=0.6, dust_col="#4a3d30", ao_dist=0.25)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    h = n.math("ADD", fine.outputs["Factor"], n.math("MULTIPLY", strata.outputs["Factor"], 0.6))
    h = n.math("ADD", h, n.math("MULTIPLY", patch, 0.3))
    bump(n, bsdf, h, strength=0.7, distance=0.02)
    return mat


def bark():
    """Elongated vertical ridges, low contrast, mossy greening on the lower trunk."""
    mat, n, bsdf, _ = new("bark")
    co = coords(n, scale=(9, 9, 0.7))
    ridges = noise(n, co, 2.2, detail=7, rough=0.6, distortion=0.4)
    tone = noise(n, coords(n), 1.5, detail=3)
    col = n.mix_rgb(n.map_range(ridges.outputs["Factor"], 0.35, 0.68), hex_rgba("#4a3d31"),
                    hex_rgba(P["bark_light"]))
    col = n.mix_rgb(n.map_range(tone.outputs["Factor"], 0.35, 0.7, 0.0, 0.3), col, hex_rgba("#6e6a58"))
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(coords(n), sep.inputs[0])
    moss = n.math("MULTIPLY", n.map_range(sep.outputs["Z"], 1.5, 0.0, 0.0, 0.45),
                  n.map_range(tone.outputs["Factor"], 0.45, 0.6))
    col = n.mix_rgb(moss, col, hex_rgba("#5d6630"))
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.88
    bump(n, bsdf, ridges.outputs["Factor"], strength=0.45, distance=0.03)
    return mat


def foliage(name, dark, mid, light, translucency=0.35, haze=0.45):
    """Leaves: per-instance random tint, translucency for backlit glow, distance haze."""
    mat, n, bsdf, out = new(name)
    info = n.new("ShaderNodeObjectInfo")
    col = n.ramp(info.outputs["Random"], [(0.0, hex_rgba(dark)), (0.55, hex_rgba(mid)), (1.0, hex_rgba(light))])
    col = distance_haze(n, col, LEAF_HAZE, 14.0, 60.0, haze)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Specular IOR Level"].default_value = 0.45
    trans = n.new("ShaderNodeBsdfTranslucent")
    n.link(n.mix_rgb(1.0, col, hex_rgba("#d6c860"), "MULTIPLY"), trans.inputs["Color"])
    mix = n.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = translucency
    n.link(bsdf.outputs[0], mix.inputs[1])
    n.link(trans.outputs[0], mix.inputs[2])
    n.link(mix.outputs[0], out.inputs["Surface"])
    return mat


def canopy_far():
    """Scrub masses: lumpy bump, lighter sunlit tops, per-instance tint, distance haze."""
    mat, n, bsdf, _ = new("canopy_far")
    co = coords(n)
    lumps = noise(n, co, 9.0, detail=4, rough=0.7)
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(geo.outputs["Normal"], sep.inputs[0])
    info = n.new("ShaderNodeObjectInfo")
    top = n.ramp(info.outputs["Random"], [(0.0, hex_rgba("#5d6a2a")), (0.5, hex_rgba("#7d7f36")),
                                          (1.0, hex_rgba("#9a8e48"))])
    col = n.mix_rgb(n.map_range(sep.outputs["Z"], -0.2, 0.9), hex_rgba("#2c3414"), top)
    col = n.mix_rgb(n.map_range(lumps.outputs["Factor"], 0.35, 0.7, 0.0, 0.45), col, hex_rgba("#1f2610"))
    col = distance_haze(n, col, warm_haze(n, "#8c8a58", "#b9a77e", SKY_GLOW_DIR), 20.0, 170.0, 0.6)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    bump(n, bsdf, lumps.outputs["Factor"], strength=0.9, distance=0.1)
    return mat


def grass(name, base, tip_a, tip_b, translucency=0.3, seed_col=None):
    """Per-blade colour (Random Per Island) on top of per-clump tint; optional pale seed heads.

    Seed heads are the faces whose UV.x is 1 (set by the source mesh)."""
    mat, n, bsdf, out = new(name)
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(coords(n), sep.inputs[0])
    info = n.new("ShaderNodeObjectInfo")
    geo = n.new("ShaderNodeNewGeometry")
    blade = n.math("ADD", n.math("MULTIPLY", geo.outputs["Random Per Island"], 0.7),
                   n.math("MULTIPLY", info.outputs["Random"], 0.3))
    tip = n.ramp(blade, [(0.0, hex_rgba(tip_a)), (0.6, hex_rgba(tip_b)), (1.0, hex_rgba("#d8c27e"))])
    col = n.mix_rgb(n.map_range(sep.outputs["Z"], 0.0, 0.45), hex_rgba(base), tip)
    if seed_col:
        uv = n.new("ShaderNodeSeparateXYZ")
        n.link(coords(n, "UV"), uv.inputs[0])
        col = n.mix_rgb(n.map_range(uv.outputs["X"], 0.5, 0.9), col, hex_rgba(seed_col))
    col = distance_haze(n, col, LEAF_HAZE, 14.0, 60.0, 0.4)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    trans = n.new("ShaderNodeBsdfTranslucent")
    n.link(col, trans.inputs["Color"])
    mix = n.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = translucency
    n.link(bsdf.outputs[0], mix.inputs[1])
    n.link(trans.outputs[0], mix.inputs[2])
    n.link(mix.outputs[0], out.inputs["Surface"])
    return mat


def leaf_card(name, dark, mid, light, leaf_len=0.42, leaf_wid=0.17, cells=4.5, translucency=0.45):
    """Alpha-cut leaf-cluster card: many small leaves drawn procedurally in UV space.

    Each voronoi cell holds one rotated, pointed leaf with a midrib; leaf colour
    varies per leaf and per card, and sunlit leaves glow through translucency.
    For export the colour and alpha bake to a texture (glTF alphaMode MASK).
    """
    mat, n, bsdf, out = new(name)
    uv = n.new("ShaderNodeVectorMath", operation="SCALE")
    n.link(coords(n, "UV"), uv.inputs[0])
    uv.inputs["Scale"].default_value = cells
    vor = n.new("ShaderNodeTexVoronoi")
    vor.inputs["Randomness"].default_value = 0.85
    vor.inputs["Scale"].default_value = 1.0
    n.link(uv.outputs[0], vor.inputs["Vector"])
    d = n.new("ShaderNodeVectorMath", operation="SUBTRACT")
    n.link(uv.outputs[0], d.inputs[0])
    n.link(vor.outputs["Position"], d.inputs[1])
    cell_rand = n.new("ShaderNodeSeparateColor")
    n.link(vor.outputs["Color"], cell_rand.inputs[0])
    rot = n.new("ShaderNodeVectorRotate", rotation_type="Z_AXIS")
    n.link(d.outputs[0], rot.inputs["Vector"])
    n.link(n.math("MULTIPLY", cell_rand.outputs[0], 6.2832), rot.inputs["Angle"])
    xy = n.new("ShaderNodeSeparateXYZ")
    n.link(rot.outputs[0], xy.inputs[0])
    # Pointed leaf: width tapers towards both ends.
    u = n.math("DIVIDE", xy.outputs["X"], leaf_len)
    taper = n.math("SUBTRACT", 1.0, n.math("POWER", n.math("ABSOLUTE", u), 1.6))
    half_w = n.math("MULTIPLY", taper, leaf_wid)
    inside = n.math("LESS_THAN", n.math("ABSOLUTE", xy.outputs["Y"]), half_w)
    leaf = n.math("MULTIPLY", inside, n.math("LESS_THAN", n.math("ABSOLUTE", u), 1.0))
    # Keep the card silhouette round, not square.
    centre = n.new("ShaderNodeVectorMath", operation="DISTANCE")
    n.link(coords(n, "UV"), centre.inputs[0])
    centre.inputs[1].default_value = (0.5, 0.5, 0.0)
    leaf = n.math("MULTIPLY", leaf, n.math("LESS_THAN", centre.outputs["Value"], 0.49))
    info = n.new("ShaderNodeObjectInfo")
    tone = n.math("ADD", n.math("MULTIPLY", cell_rand.outputs[1], 0.6), n.math("MULTIPLY", info.outputs["Random"], 0.4))
    col = n.ramp(tone, [(0.0, hex_rgba(dark)), (0.5, hex_rgba(mid)), (1.0, hex_rgba(light))])
    rib = n.map_range(n.math("ABSOLUTE", xy.outputs["Y"]), 0.0, 0.015, 0.35, 0.0)
    col = n.mix_rgb(rib, col, hex_rgba("#e3df8a"))
    col = n.mix_rgb(n.map_range(n.math("ABSOLUTE", u), 0.6, 1.0, 0.0, 0.25), col, hex_rgba(dark))
    col = distance_haze(n, col, LEAF_HAZE, 14.0, 60.0, 0.35)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Specular IOR Level"].default_value = 0.45
    trans = n.new("ShaderNodeBsdfTranslucent")
    n.link(n.mix_rgb(1.0, col, hex_rgba("#e8de70"), "MULTIPLY"), trans.inputs["Color"])
    lit = n.new("ShaderNodeMixShader")
    lit.inputs[0].default_value = translucency
    n.link(bsdf.outputs[0], lit.inputs[1])
    n.link(trans.outputs[0], lit.inputs[2])
    cut = n.new("ShaderNodeMixShader")
    n.link(leaf, cut.inputs[0])
    n.link(n.new("ShaderNodeBsdfTransparent").outputs[0], cut.inputs[1])
    n.link(lit.outputs[0], cut.inputs[2])
    n.link(cut.outputs[0], out.inputs["Surface"])
    return mat


def tinted(name, colours, rough=0.6, translucency=0.0):
    """Small instanced things (petals, fallen leaves): per-instance pick along a ramp."""
    mat, n, bsdf, out = new(name)
    info = n.new("ShaderNodeObjectInfo")
    stops = [(i / max(1, len(colours) - 1), hex_rgba(c)) for i, c in enumerate(colours)]
    col = n.ramp(info.outputs["Random"], stops)
    n.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    if translucency:
        trans = n.new("ShaderNodeBsdfTranslucent")
        n.link(col, trans.inputs["Color"])
        mix = n.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = translucency
        n.link(bsdf.outputs[0], mix.inputs[1])
        n.link(trans.outputs[0], mix.inputs[2])
        n.link(mix.outputs[0], out.inputs["Surface"])
    return mat


def build():
    terrain()
    rock()
    bark()
    canopy_far()
    grass("grass", P["leaf_dark"], P["grass"], P["grass_dry"], seed_col="#e9dcae")
    grass("grass_dry", "#6b6a32", "#c9ad6a", "#e0c98a", translucency=0.35, seed_col="#f1e6c2")
    grass("agave", "#4c6250", "#7d9a86", "#9fb3a0", translucency=0.15)
    # Leaf species: broadleaf, silver olive, bright lime, dark bay, creeper.
    foliage("leaf_tree", P["leaf_dark"], P["leaf"], P["leaf_light"], translucency=0.45)
    foliage("leaf_shrub", "#3f4a1c", "#66702e", "#8e9640", translucency=0.3)
    foliage("leaf_olive", "#55603a", "#7c8656", "#a3a878", translucency=0.25)
    foliage("leaf_lime", "#6f7d22", "#9aa831", "#c4c650", translucency=0.4)
    foliage("leaf_bay", "#24321a", "#3a4c22", "#566a2e", translucency=0.2)
    foliage("leaf_creeper", "#3b5320", "#5e7a2a", "#8c9a3a", translucency=0.35, haze=0.0)
    tinted("leaf_fallen", ["#7a5a2c", "#a87d3a", "#c49a48", "#8a6a3a", "#9b8a42"], rough=0.8)
    tinted("flower_petal", ["#f4efe2", "#fbf6ea", "#efe1c8", "#f1e6f0"], rough=0.5, translucency=0.3)
    tinted("flower_centre", ["#d9a92a", "#e3b93c"], rough=0.6)
    leaf_card("leafcard_tree", "#4f5f1c", "#8a9832", "#d2cf52")
    leaf_card("leafcard_olive", "#4d5a35", "#7f8a58", "#b4b886", leaf_len=0.45, leaf_wid=0.1, cells=5.0,
              translucency=0.3)
