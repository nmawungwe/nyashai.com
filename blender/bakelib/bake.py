"""Cycles bakes: atlas textures, vegetation vertex colours and leaf-card textures."""

import bpy
import numpy as np

from .colour import save_display_png, srgb_to_linear, to_display

PASSES = {"DIRECT", "INDIRECT", "DIFFUSE", "TRANSMISSION", "EMIT"}   # no glossy: the web view is unlit


def configure(samples):
    scene = bpy.context.scene
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.bake.margin = 16
    scene.render.bake.margin_type = "EXTEND"


def _select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def use_tint_attribute():
    """Replace Object Info > Random with the realised per-instance `tint` attribute."""
    for mat in bpy.data.materials:
        nt = mat.node_tree
        if nt is None:
            continue
        for info in [n for n in nt.nodes if n.bl_idname == "ShaderNodeObjectInfo"]:
            attr = nt.nodes.new("ShaderNodeAttribute")
            attr.attribute_name = "tint"
            for link in list(info.outputs["Random"].links):
                nt.links.new(attr.outputs["Fac"], link.to_socket)


def bake_atlas(obj, size, path):
    """COMBINED bake of one joined group into a float image, saved display-referred.
    `size` is an int (square) or a (width, height) tuple."""
    w, h = size if isinstance(size, tuple) else (size, size)
    img = bpy.data.images.new(f"atlas_{obj.name}", w, h, float_buffer=True, alpha=False)
    for slot in obj.material_slots:
        nt = slot.material.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.name = node.label = "BAKE_TARGET"
        node.image = img
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "bake"
        nt.links.new(uv.outputs[0], node.inputs[0])
        nt.nodes.active = node
    obj.data.uv_layers["bake"].active = True
    obj.data.uv_layers["bake"].active_render = True
    _select_only([obj])
    bpy.ops.object.bake(type="COMBINED", pass_filter=PASSES, target="IMAGE_TEXTURES", use_clear=True)
    save_display_png(img, path)
    for slot in obj.material_slots:  # leave the shared materials clean for the next group
        nt = slot.material.node_tree
        for n in [n for n in nt.nodes if n.name.startswith("BAKE_TARGET") or
                  (n.bl_idname == "ShaderNodeUVMap" and n.uv_map == "bake")]:
            nt.nodes.remove(n)
    return img


def vertex_bake_material(mat):
    """Copy of a foliage material for vertex baking.

    Camera/bake rays see an opaque leaf (so the sample at a card corner is lit
    leaf, not empty card), while shadow rays still see the alpha-cut leaves, so
    dappling inside the canopy matches the stills.
    """
    copy = mat.copy()
    copy.name = f"{mat.name}__bake"
    nt = copy.node_tree
    for mix in [n for n in nt.nodes if n.bl_idname == "ShaderNodeMixShader"]:
        src = mix.inputs[1].links[0].from_node if mix.inputs[1].links else None
        if src is None or src.bl_idname != "ShaderNodeBsdfTransparent" or not mix.inputs[0].links:
            continue
        mask = mix.inputs[0].links[0].from_socket
        path = nt.nodes.new("ShaderNodeLightPath")
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(path.outputs["Is Shadow Ray"], inv.inputs[1])
        mx = nt.nodes.new("ShaderNodeMath")
        mx.operation = "MAXIMUM"
        nt.links.new(mask, mx.inputs[0])
        nt.links.new(inv.outputs[0], mx.inputs[1])
        nt.links.new(mx.outputs[0], mix.inputs[0])
    return copy


def bake_vertex_colours(objs):
    """COMBINED bake into a `bake_col` colour attribute on each object (scene-linear)."""
    originals = {}
    for o in objs:
        mesh = o.data
        ca = mesh.color_attributes.new("bake_col", "FLOAT_COLOR", "POINT")
        mesh.color_attributes.active_color = ca
        mesh.color_attributes.render_color_index = mesh.color_attributes.find("bake_col")
        originals[o.name] = [s.material for s in o.material_slots]
        for slot in o.material_slots:
            if slot.material and not slot.material.name.endswith("__bake"):
                slot.material = bpy.data.materials.get(f"{slot.material.name}__bake") or \
                    vertex_bake_material(slot.material)
    _select_only(objs)
    bpy.ops.object.bake(type="COMBINED", pass_filter=PASSES, target="VERTEX_COLORS")
    for o in objs:
        for slot, mat in zip(o.material_slots, originals[o.name]):
            slot.material = mat


LEAF_OBJECTS = ("tree_canopy", "pot_shrub_cards", "shrub_leaves", "olive_leaves", "lime_leaves", "bay_leaves",
                "creeper_leaves", "fallen_leaves")


def share_per_leaf(objs, block_sizes):
    """Give every vertex of one leaf / leaf card the same baked colour (their mean).

    Realised instances keep their source's vertex order, so instance k owns
    vertices [k * n, (k + 1) * n). Per-corner values made cards read as speckle."""
    for o in objs:
        n = block_sizes.get(o.name)
        if not n or o.name not in LEAF_OBJECTS:
            continue
        ca = o.data.color_attributes["bake_col"]
        count = len(ca.data)
        if count % n:
            print(f"share_per_leaf: {o.name} has {count} verts, not a multiple of {n}; skipped")
            continue
        a = np.empty(count * 4, dtype=np.float32)
        ca.data.foreach_get("color", a)
        a = a.reshape(-1, n, 4)
        a[:] = a.mean(axis=1, keepdims=True)
        ca.data.foreach_set("color", a.ravel())


def vertex_colours_to_display(objs):
    """Convert every `bake_col` to display-referred values (stored linearised for glTF)."""
    arrays, counts = [], []
    for o in objs:
        ca = o.data.color_attributes["bake_col"]
        a = np.empty(len(ca.data) * 4, dtype=np.float32)
        ca.data.foreach_get("color", a)
        arrays.append(a.reshape(-1, 4)[:, :3])
        counts.append(len(ca.data))
    disp = to_display(np.concatenate(arrays))
    lin = srgb_to_linear(disp)
    start = 0
    for o, n in zip(objs, counts):
        out = np.ones((n, 4), dtype=np.float32)
        out[:, :3] = lin[start:start + n]
        o.data.color_attributes["bake_col"].data.foreach_set("color", out.ravel())
        start += n


def bake_card_texture(card_mat, path, size=512, mean_target=0.8):
    """Leaf-card texture: RGB = per-leaf colour modulation around `mean_target`
    (the lit colour comes from vertex colours), A = leaf mask (glTF MASK)."""
    mesh = bpy.data.meshes.new("card_plane")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop.uv = co
    tint = mesh.attributes.new("tint", "FLOAT", "POINT")
    tint.data.foreach_set("value", [0.5] * 4)
    plane = bpy.data.objects.new("card_plane", mesh)
    bpy.context.scene.collection.objects.link(plane)
    mat = card_mat.copy()
    mesh.materials.append(mat)
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial")
    bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    cut = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeMixShader" and n.inputs[1].links and
               n.inputs[1].links[0].from_node.bl_idname == "ShaderNodeBsdfTransparent")
    colour_src = bsdf.inputs["Base Color"].links[0].from_socket
    mask_src = cut.inputs[0].links[0].from_socket
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    results = {}
    for key, src in (("colour", colour_src), ("mask", mask_src)):
        nt.links.new(src, emit.inputs["Color"])
        img = bpy.data.images.new(f"card_{key}", size, size, float_buffer=True, alpha=False)
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.nodes.active = node
        _select_only([plane])
        bpy.ops.object.bake(type="EMIT", target="IMAGE_TEXTURES", use_clear=True)
        a = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        results[key] = a.reshape(-1, 4)
    mask = (results["mask"][:, 0] > 0.5).astype(np.float32)
    col = to_display(results["colour"][:, :3])
    # Brightness-only modulation (per-leaf light/dark, midrib); hue comes from the
    # vertex colours, so per-channel ratios would only add false tints.
    lum = col @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mean = lum[mask > 0].mean() if mask.any() else 1.0
    mod = np.repeat(np.clip(lum / max(mean, 1e-4) * mean_target, 0.0, 1.0)[:, None], 3, axis=1)
    # Transparent texels take the mean tone so mipmaps don't darken leaf edges.
    mod[mask == 0] = mean_target
    rgba = np.concatenate([mod, mask[:, None]], axis=1)
    tex = bpy.data.images.new(f"leaftex_{card_mat.name}", size, size, alpha=True)
    tex.colorspace_settings.name = "sRGB"
    tex.pixels.foreach_set(rgba.ravel())   # byte image: values stored as-is (display-referred)
    tex.filepath_raw = path
    tex.file_format = "PNG"
    tex.save()
    bpy.data.objects.remove(plane)
    return tex


def sway_weights(objs, ground_z):
    """Per-vertex sway (0 at roots/attachment, 1 at tips) in a `_sway` attribute."""
    for o in objs:
        mesh = o.data
        n = len(mesh.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        name = o.name
        if name in ("tree_canopy",):
            r = np.hypot(co[:, 0] - 0.55, co[:, 1] - 5.35)       # distance from the trunk axis
            w = np.clip(0.25 + r / 6.0 + (co[:, 2] - 4.0) / 12.0, 0.0, 1.0)
        elif name.startswith(("fallen_leaves", "pebbles", "essay_title")):
            w = np.zeros(n)
        elif name.startswith("creeper"):
            w = np.full(n, 0.25)
        else:
            # Height above the ground; shrubs bend over more height than grass.
            h = co[:, 2] - np.array([ground_z(x, y) for x, y in co[:, :2]])
            scale = 1.6 if "leaves" in name or "cards" in name else 0.6
            w = np.clip(h / scale, 0.0, 1.0)
        attr = mesh.attributes.new("_sway", "FLOAT", "POINT")
        attr.data.foreach_set("value", w.astype(np.float32))

