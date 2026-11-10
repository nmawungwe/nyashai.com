"""Build the garden pavilion scene from scratch and save blender/pavilion.blend.

Usage (from the repo root):
    /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_scene.py

Re-running rebuilds the same scene (fixed seeds). Collections map to the planned
bake/export groups: architecture, furniture, ground, vegetation, backdrop.
"""

import importlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bpy  # noqa: E402

import pavlib  # noqa: E402
from pavlib import (architecture, config, details, ground_cover, landscape, materials,  # noqa: E402
                    materials_nature, matlib, matte, props, rig, util, vegetation, views)

for mod in (config, util, views, matlib, materials_nature, materials, architecture, props, landscape, vegetation,
            ground_cover, details, rig, matte):
    importlib.reload(mod)


def build():
    util.reset_scene()
    util._collections.clear()
    materials.build_all()

    arch = util.collection("architecture")
    furn = util.collection("furniture")
    ground = util.collection("ground")
    veg = util.collection("vegetation")
    backdrop = util.collection("backdrop")
    rigc = util.collection("rig")
    sources = util.collection("instance_sources", hide_render=True)
    sources.hide_viewport = False

    architecture.build(arch)
    architecture.paving(ground)
    landscape.build_terrain(ground)
    landscape.build_retaining_walls(ground)
    landscape.build_boulders(ground)
    stakes = landscape.build_vineyard(ground)

    props.ANCHORS.clear()
    props.build_table(furn)
    props.build_bench_items(furn)
    props.build_floor_props(furn)

    n_leaves = vegetation.build_tree(veg, sources)
    n_shrub = vegetation.build_shrubs(veg, sources, props.ANCHORS, stakes)
    n_grass = ground_cover.build_grass(veg, sources)
    details.build(furn, veg, sources)

    rig.build_world()
    rig.build_sun(rigc)
    rig.build_bounce(rigc)
    rig.build_cameras(rigc, props.ANCHORS)
    rig.configure_render()
    matte.build(backdrop)   # distant hills: matte painting from the homepage artwork

    for obj in sources.objects:
        obj.location = (0, 0, -50)  # keep sources out of sight in viewport too
    print(f"instances: tree leaves {n_leaves}, shrub leaves {n_shrub}, grass clumps {n_grass}")
    report()

    config.BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(config.BLEND_PATH), compress=True)
    print("saved", config.BLEND_PATH)


def report():
    """Print evaluated triangle counts per collection (instances realised)."""
    dg = bpy.context.evaluated_depsgraph_get()
    per_coll = {}
    total = 0
    for inst in dg.object_instances:
        obj = inst.object
        if obj.type != "MESH":
            continue
        owner = (inst.parent if inst.is_instance else obj).original
        coll_name = owner.users_collection[0].name if owner.users_collection else "?"
        if coll_name == "instance_sources":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        tris = len(mesh.loop_triangles)
        per_coll[coll_name] = per_coll.get(coll_name, 0) + tris
        total += tris
    objs = [o for o in bpy.data.objects if o.users_collection and o.users_collection[0].name != "instance_sources"]
    print("objects (excluding instance sources):", len(objs))
    for k, v in sorted(per_coll.items()):
        print(f"  tris {k:14s} {v:8d}")
    print(f"  tris {'TOTAL':14s} {total:8d}")


if __name__ == "__main__":
    build()
