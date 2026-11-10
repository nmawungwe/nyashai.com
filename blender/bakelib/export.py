"""Sky equirect, unlit export materials, camera metadata and the GLB itself."""

import json
import math

import bpy
import numpy as np
from mathutils import Matrix

from .colour import to_display

# Blender Z-up -> glTF/three Y-up: (x, y, z) -> (x, z, -y).
TO_Y_UP = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
WEB_CAMERAS = ("cam_hero", "cam_hero_portrait", "cam_projects", "cam_writing", "cam_reviews")
ANCHORS = ("anchor_projects", "anchor_writing", "anchor_reviews")


# --- Sky -------------------------------------------------------------------------------

def render_sky(path, width=2048):
    """Equirectangular render of the world only (same view transform as the stills).

    The image is oriented for three.js EquirectangularReflectionMapping: u = 0.5
    looks along +X (three), u = 0.75 along +Z (three) = Blender -Y.
    """
    scene = bpy.context.scene
    hidden = [o for o in scene.objects if not o.hide_render]
    for o in hidden:
        o.hide_render = True
    cam_data = bpy.data.cameras.new("sky_cam")
    cam_data.type = "PANO"
    cam_data.panorama_type = "EQUIRECTANGULAR"
    cam = bpy.data.objects.new("sky_cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (2.5, 1.0, 1.5)
    # Looking along Blender +X with Z up puts +X at the image centre.
    cam.rotation_euler = (math.pi / 2, 0.0, -math.pi / 2)
    prev = (scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.cycles.samples)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = width, width // 2
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 256
    s = scene.render.image_settings
    s.file_format, s.color_mode, s.quality = "WEBP", "RGB", 94
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.cycles.samples = prev
    for o in hidden:
        o.hide_render = False
    bpy.data.objects.remove(cam)


# --- Unlit materials ---------------------------------------------------------------------

def _unlit(name, colour_socket_fn, alpha_fn=None):
    """Material shaped the way the glTF exporter recognises as KHR_materials_unlit:
    Output <- [Mix(alpha, Transparent, ...)] <- Mix(Is Camera Ray, _, Emission(colour))."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(colour_socket_fn(nt), emit.inputs["Color"])
    path = nt.nodes.new("ShaderNodeLightPath")
    trick = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(path.outputs["Is Camera Ray"], trick.inputs[0])
    nt.links.new(emit.outputs[0], trick.inputs[2])
    final = trick
    if alpha_fn:
        cut = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(alpha_fn(nt), cut.inputs[0])
        nt.links.new(nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0], cut.inputs[1])
        nt.links.new(trick.outputs[0], cut.inputs[2])
        final = cut
    nt.links.new(final.outputs[0], out.inputs["Surface"])
    return mat


def _image_node(nt, image, uv_name):
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_name
    nt.links.new(uv.outputs[0], tex.inputs[0])
    return tex


def atlas_material(name, png_path):
    img = bpy.data.images.load(png_path, check_existing=True)
    img.colorspace_settings.name = "sRGB"
    return _unlit(name, lambda nt: _image_node(nt, img, "bake").outputs["Color"])


def vertex_material(name, leaf_tex=None):
    def colour(nt):
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "bake_col"
        if leaf_tex is None:
            return vc.outputs["Color"]
        tex = _image_node(nt, leaf_tex, "UVMap")
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(vc.outputs["Color"], mul.inputs[6])
        nt.links.new(tex.outputs["Color"], mul.inputs[7])
        return mul.outputs[2]

    def alpha(nt):
        # Round(alpha) is the pattern the exporter writes as alphaMode MASK (cutoff 0.5).
        tex = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeTexImage")
        rnd = nt.nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        nt.links.new(tex.outputs["Alpha"], rnd.inputs[0])
        return rnd.outputs[0]
    return _unlit(name, colour, alpha if leaf_tex is not None else None)


def matte_material(name, png_path):
    """Matte painting: unlit texture with a soft (blended) alpha edge into the sky."""
    img = bpy.data.images.load(png_path, check_existing=True)
    img.colorspace_settings.name = "sRGB"
    img.alpha_mode = "STRAIGHT"

    def colour(nt):
        tex = _image_node(nt, img, "UVMap")
        tex.extension = "EXTEND"
        return tex.outputs["Color"]

    def alpha(nt):
        return next(n for n in nt.nodes if n.bl_idname == "ShaderNodeTexImage").outputs["Alpha"]
    return _unlit(name, colour, alpha)


def flat_material(name, linear_rgb):
    disp = to_display([linear_rgb])[0]

    def colour(nt):
        rgb = nt.nodes.new("ShaderNodeRGB")
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in disp]
        rgb.outputs[0].default_value = (*lin, 1.0)
        return rgb.outputs[0]
    return _unlit(name, colour)


def screen_material(name, source):
    img = next(n.image for n in source.node_tree.nodes if n.bl_idname == "ShaderNodeTexImage")
    return _unlit(name, lambda nt: _image_node(nt, img, "UVMap").outputs["Color"])


def strip_uvs(obj, keep):
    for uv in list(obj.data.uv_layers):
        if uv.name != keep:
            obj.data.uv_layers.remove(uv)


# --- Cameras and anchors -----------------------------------------------------------------

def camera_metadata(aspects):
    """Positions/orientations in three.js (Y-up) space, vertical FOV and design aspect."""
    data = {"cameras": {}, "anchors": {}}
    for name in WEB_CAMERAS:
        cam = bpy.data.objects[name]
        loc = TO_Y_UP @ cam.matrix_world.translation
        rot = (TO_Y_UP @ cam.matrix_world.to_3x3()).to_quaternion()
        aspect = aspects.get(name, 1672 / 941)
        half = 18.0 / cam.data.lens          # 36 mm sensor across the longer side (AUTO fit)
        yfov = 2 * math.atan(half / aspect) if aspect >= 1 else 2 * math.atan(half)
        data["cameras"][name] = {"position": list(loc), "quaternion": [rot.x, rot.y, rot.z, rot.w],
                                 "yfov": math.degrees(yfov), "aspect": aspect}
    for name in ANCHORS:
        data["anchors"][name] = list(TO_Y_UP @ bpy.data.objects[name].matrix_world.translation)
    return data


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def export_glb(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True,
        export_cameras=True, export_lights=False, export_yup=True,
        export_normals=False, export_tangents=False, export_texcoords=True,
        export_vertex_color="MATERIAL", export_attributes=True, export_materials="EXPORT",
        export_image_format="AUTO", export_extras=False)


def mean_display(obj):
    """Mean display colour of a vertex-coloured object (for logging only)."""
    ca = obj.data.color_attributes.get("bake_col")
    if ca is None:
        return None
    a = np.empty(len(ca.data) * 4, dtype=np.float32)
    ca.data.foreach_get("color", a)
    return a.reshape(-1, 4)[:, :3].mean(axis=0)

