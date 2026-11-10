"""Stage 2: bake lighting from blender/pavilion.blend and export the web scene.

Usage (from the repo root; normally via blender/export.sh):
    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P blender/bake_export.py -- [--samples N] [--quick]

Writes to blender/.build/: pavilion.raw.glb, sky.webp, cameras.json and the
intermediate atlas / leaf textures. Nothing is written back to pavilion.blend.
`--quick` bakes at quarter resolution with few samples for pipeline checks.
"""

import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402

from bakelib import bake, export, prepare  # noqa: E402
from pavlib import config, landscape, rig  # noqa: E402

OUT = HERE / ".build"


def log(msg, t0=[time.time()]):  # noqa: B006 - simple elapsed-time logger
    print(f"[bake {time.time() - t0[0]:7.1f}s] {msg}", flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    quick = "--quick" in argv
    samples = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else (16 if quick else 160)
    OUT.mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(config.BLEND_PATH))
    rig.configure_render(samples)
    log(f"opened scene, samples={samples}, device={bpy.context.scene.cycles.device}")

    block_sizes = prepare.instance_block_sizes()
    prepare.store_instance_tint()
    prepare.realise_all()
    bake.use_tint_attribute()
    prepare.split_terrain()
    atlases = {}
    for name, members in prepare.group_members().items():
        if members:
            atlases[name] = prepare.join_and_unwrap(name, members)
            log(f"joined + unwrapped {name}: {len(atlases[name].data.polygons)} faces")

    bake.configure(samples)
    for name, obj in atlases.items():
        size = prepare.ATLAS_GROUPS[name]
        size = tuple(v // (4 if quick else 1) for v in size) if isinstance(size, tuple) else size // (4 if quick else 1)
        bake.bake_atlas(obj, size, str(OUT / f"{name}.png"))
        log(f"baked atlas {name} at {size}px")

    veg = prepare.vertex_bake_objects()
    bake.bake_vertex_colours(veg)
    bake.share_per_leaf(veg, block_sizes)
    bake.vertex_colours_to_display(veg)
    bake.sway_weights(veg, landscape.ground_z)
    log(f"baked vertex colours on {len(veg)} objects")

    leaf_tex = {}
    for mat_name in ("leafcard_tree", "leafcard_olive"):
        leaf_tex[mat_name] = bake.bake_card_texture(bpy.data.materials[mat_name], str(OUT / f"{mat_name}.png"))
    export.render_sky(str(OUT / "sky.webp"), 1024 if quick else 4096)
    log("leaf textures + sky done")

    # Swap every exported surface to an unlit material.
    for name, obj in atlases.items():
        obj.data.materials.clear()
        obj.data.materials.append(export.atlas_material(f"atlas_{name}", str(OUT / f"{name}.png")))
        obj.data.polygons.foreach_set("material_index", [0] * len(obj.data.polygons))
        export.strip_uvs(obj, "bake")
    unlit_cache = {}
    for obj in veg:
        is_card = any(s.material and s.material.name.startswith("leafcard") for s in obj.material_slots)
        for slot in obj.material_slots:
            src = slot.material.name
            if src not in unlit_cache:
                unlit_cache[src] = export.vertex_material(f"{src}_unlit", leaf_tex.get(src))
            slot.material = unlit_cache[src]
        export.strip_uvs(obj, "UVMap" if is_card else "")
    screens = [bpy.data.objects[n] for n in prepare.OWN_TEXTURE]
    for obj in screens:
        obj.material_slots[0].material = export.screen_material(f"{obj.name}_unlit", obj.material_slots[0].material)
    matte = bpy.data.objects["matte_card"]
    matte.material_slots[0].material = export.matte_material("matte_hills", str(OUT / "matte.png"))
    export.strip_uvs(matte, "UVMap")
    glass = bpy.data.objects["lantern_glass"]
    glass.material_slots[0].material = export.flat_material("lantern_glow", (1.0, 0.45, 0.12))

    cams = [bpy.data.objects[n] for n in export.WEB_CAMERAS]
    anchors = [bpy.data.objects[n] for n in export.ANCHORS]
    meta = export.camera_metadata(config.CAMERA_ASPECT)
    meta["fog"] = config.PALETTE["haze"]
    export.write_json(str(OUT / "cameras.json"), meta)
    objects = list(atlases.values()) + veg + screens + [glass, matte] + cams + anchors
    export.export_glb(str(OUT / "pavilion.raw.glb"), objects)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects if o.type == "MESH")
    log(f"exported {len(objects)} objects, {tris} triangles")


main()
