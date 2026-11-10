"""Turn the procedural scene into bakeable meshes.

- Scattered instances are realised; each instance's random tint is stored as a
  `tint` attribute first, so it survives realisation.
- Modifiers (bevel, solidify, subdivision) are applied.
- The terrain is split into a near part (shares the detailed ground atlas) and a
  far part (low-resolution atlas).
- Atlas groups are joined into one mesh each and given a fresh `bake` UV map.
"""

import math

import bmesh
import bpy

# name: (texture size, object names or collection prefix rules)
ATLAS_GROUPS = {
    "architecture": 2048,
    "masonry": 2048,
    "furniture": 2048,
    "essay": 1024,
    "wood": 2048,
    "paving": 2048,
    "terrain_near": 2048,
    "terrain_far": 1024,
}
# Objects that keep their own crisp, unlit textures (never resampled into an atlas).
OWN_TEXTURE = {"laptop_screen", "tablet_screen"}
EMISSIVE_FLAT = {"lantern_glass"}
SHADOW_ONLY_PREFIXES = ("shade_tree_", "dapple_tree_")
WOOD = {"tree_wood", "tree_twigs", "shrub_stems", "creeper_stems"}
# Walls and bench fill the frame in the close-up views, so they get their own
# atlas instead of sharing texels with every pergola slat.
MASONRY = {"wall_rammed_earth", "bench_masonry"}
PAVING = {"ground_paving", "boulders", "terrace_walls", "garden_wall", "garden_kerb", "vineyard_stakes"}
NEAR_RADIUS = 32.0   # terrain within this distance of the pavilion gets the finer terrain atlas


def _select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def store_instance_tint():
    """Write a per-instance random value to a `tint` attribute before realisation."""
    ng = bpy.data.node_groups.get("scatter_instances")
    if ng is None:
        return
    nodes, links = ng.nodes, ng.links
    iop = next(n for n in nodes if n.bl_idname == "GeometryNodeInstanceOnPoints")
    out = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")
    rnd = nodes.new("FunctionNodeRandomValue")
    rnd.data_type = "FLOAT"
    store = nodes.new("GeometryNodeStoreNamedAttribute")
    store.data_type = "FLOAT"
    store.domain = "INSTANCE"
    store.inputs["Name"].default_value = "tint"
    links.new(iop.outputs[0], store.inputs["Geometry"])
    links.new(rnd.outputs["Value"], store.inputs["Value"])
    realize = nodes.new("GeometryNodeRealizeInstances")
    links.new(store.outputs[0], realize.inputs[0])
    links.new(realize.outputs[0], out.inputs[0])


def instance_block_sizes():
    """Vertices per instance for every scatter object (read before realisation),
    so baked colours can later be shared by all vertices of one leaf / card."""
    sizes = {}
    for o in bpy.context.scene.objects:
        for mod in o.modifiers:
            if mod.type == "NODES" and mod.node_group and mod.node_group.name == "scatter_instances":
                ident = mod.node_group.interface.items_tree["Instance"].identifier
                src = getattr(mod.properties.inputs, ident).value
                if src is not None:
                    sizes[o.name] = len(src.data.vertices)
    return sizes


def realise_all():
    """Apply every modifier (and so realise every scatter) on all mesh objects."""
    meshes = [o for o in bpy.context.scene.objects if o.type in {"MESH", "CURVE", "FONT"}
              and o.users_collection and o.users_collection[0].name != "instance_sources"]
    _select_only(meshes)
    bpy.ops.object.convert(target="MESH")


def split_terrain():
    terrain = bpy.data.objects["ground_terrain"]
    bm = bmesh.new()
    bm.from_mesh(terrain.data)
    far_faces = [f for f in bm.faces if math.hypot(f.calc_center_median().x - 2.5,
                                                   f.calc_center_median().y - 1.0) > NEAR_RADIUS]
    far = bm.copy()
    keep = {f.index for f in far_faces}
    bmesh.ops.delete(far, geom=[f for f in far.faces if f.index not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=far_faces, context="FACES")
    near_mesh, far_mesh = bpy.data.meshes.new("terrain_near"), bpy.data.meshes.new("terrain_far")
    bm.to_mesh(near_mesh)
    far.to_mesh(far_mesh)
    bm.free()
    far.free()
    for mesh in (near_mesh, far_mesh):
        mesh.materials.append(terrain.data.materials[0])
        obj = bpy.data.objects.new(mesh.name, mesh)
        terrain.users_collection[0].objects.link(obj)
    bpy.data.objects.remove(terrain)


def group_members():
    """Object names for each atlas group (after realisation)."""
    objs = bpy.context.scene.objects
    coll = lambda o: o.users_collection[0].name if o.users_collection else ""  # noqa: E731
    groups = {name: [] for name in ATLAS_GROUPS}
    for o in objs:
        if o.type != "MESH" or o.name in OWN_TEXTURE or o.name in EMISSIVE_FLAT:
            continue
        c = coll(o)
        if o.name in WOOD:
            groups["wood"].append(o)
        elif o.name in PAVING:
            groups["paving"].append(o)
        elif o.name in ("terrain_near", "terrain_far"):
            groups[o.name].append(o)
        elif o.name == "essay_copy":
            groups["essay"].append(o)
        elif o.name in MASONRY:
            groups["masonry"].append(o)
        elif c == "architecture":
            groups["architecture"].append(o)
        elif c == "furniture" and o.name != "essay_title":
            groups["furniture"].append(o)
        elif o.name == "matte_card":
            continue   # keeps its own texture (exported by bake_export)
    return groups


def join_and_unwrap(name, members):
    _select_only(members)
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = f"bake_{name}"
    mesh = obj.data
    for uv in list(mesh.uv_layers):
        mesh.uv_layers.remove(uv)
    mesh.uv_layers.new(name="bake")
    _select_only([obj])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def vertex_bake_objects():
    """Everything drawn with baked vertex colours: realised vegetation plus the essay title."""
    out = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or not o.users_collection:
            continue
        c = o.users_collection[0].name
        if o.name.startswith(SHADOW_ONLY_PREFIXES + ("bake_",)) or o.name in WOOD:
            continue
        if c == "vegetation" or o.name == "essay_title":
            out.append(o)
    return out
