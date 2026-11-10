"""World sky, sun, cameras, anchors and render settings."""

import math

import bpy
from mathutils import Vector

from . import config as C
from .util import Nodes, hex_rgba

CAMERAS = C.CAMERAS


def sun_vector():
    el, az = C.SUN_ELEVATION, C.SUN_AZIMUTH
    return Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))


def build_world():
    world = bpy.data.worlds.new("sky")
    bpy.context.scene.world = world
    nt = world.node_tree
    nt.nodes.clear()
    n = Nodes(nt)
    out = n.new("ShaderNodeOutputWorld")
    bg = n.new("ShaderNodeBackground")
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ")
    n.link(tc.outputs["Generated"], sep.inputs[0])
    # Vertical gradient: luminous warm-white haze at the horizon to soft blue overhead.
    up = n.map_range(sep.outputs["Z"], -0.02, 0.8)
    sky = n.ramp(up, [(0.0, hex_rgba(C.PALETTE["sky_horizon"])), (0.07, hex_rgba(C.PALETTE["sky_low"])),
                      (0.22, hex_rgba(C.PALETTE["sky_mid"])), (0.6, hex_rgba(C.PALETTE["sky_zenith"]))])
    # Warm glow around the sun, plus a broad low glow on the left of the hero view
    # (the sun is just off-frame left), so that side of the sky reads sunlit.
    for direction, power, amount, colour in ((sun_vector(), 3.0, 0.6, "#ffe6c0"),
                                             (C.SKY_GLOW_DIR, 5.0, 0.7, "#ffe0b0")):
        dot = n.new("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        n.link(tc.outputs["Generated"], dot.inputs[0])
        dot.inputs[1].default_value = Vector(direction).normalized()
        glow = n.math("POWER", n.math("MAXIMUM", dot.outputs["Value"], 0.0), power)
        sky = n.mix_rgb(n.math("MULTIPLY", glow, amount), sky, hex_rgba(colour))
    # Bright warm haze band where the far ridges meet the sky, strongest sun-side.
    side = n.new("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    n.link(tc.outputs["Generated"], side.inputs[0])
    side.inputs[1].default_value = Vector(C.SKY_GLOW_DIR).normalized()
    sideways = n.math("ADD", 0.35, n.math("MULTIPLY", n.math("MAXIMUM", side.outputs["Value"], 0.0), 0.65))
    low = n.map_range(sep.outputs["Z"], 0.09, 0.0)
    sky = n.mix_rgb(n.math("MULTIPLY", n.math("MULTIPLY", low, sideways), 0.75), sky, hex_rgba("#fff1db"))
    # Soft scattered fair-weather clouds: noise projected onto a plane overhead.
    zoff = n.math("ADD", sep.outputs["Z"], 0.06)
    proj = n.new("ShaderNodeVectorMath", operation="DIVIDE")
    n.link(tc.outputs["Generated"], proj.inputs[0])
    comb = n.new("ShaderNodeCombineXYZ")
    for i in range(3):
        n.link(zoff, comb.inputs[i])
    n.link(comb.outputs[0], proj.inputs[1])
    cloud_tex = n.new("ShaderNodeTexNoise")
    cloud_tex.inputs["Scale"].default_value = 0.55     # larger cloud forms
    cloud_tex.inputs["Detail"].default_value = 5
    cloud_tex.inputs["Roughness"].default_value = 0.62
    cloud_tex.inputs["Distortion"].default_value = 0.3
    n.link(proj.outputs[0], cloud_tex.inputs["Vector"])
    cover = n.map_range(cloud_tex.outputs["Factor"], 0.53, 0.76)   # wide ramp = soft edges
    band = n.math("MULTIPLY", n.map_range(sep.outputs["Z"], 0.03, 0.1), n.map_range(sep.outputs["Z"], 0.85, 0.3))
    cloud_col = n.mix_rgb(n.map_range(cloud_tex.outputs["Factor"], 0.55, 0.75), hex_rgba("#f2ece4"),
                          n.mix_rgb(1.0, hex_rgba("#ffffff"), hex_rgba("#fff8ec"), "MIX"))
    cloud_col = n.mix_rgb(1.0, cloud_col, (1.35, 1.3, 1.25, 1.0), "MULTIPLY")  # clouds brighter than sky
    sky = n.mix_rgb(n.math("MULTIPLY", cover, n.math("MULTIPLY", band, 0.85)), sky, cloud_col)
    # Below the horizon: dim warm ground bounce (mostly hidden by terrain).
    below = n.map_range(sep.outputs["Z"], -0.02, 0.02)
    sky = n.mix_rgb(below, hex_rgba("#8a7456"), sky)
    n.link(sky, bg.inputs["Color"])
    # The sky seen directly by the camera is brighter than the sky used for lighting,
    # keeping the backdrop luminous without washing out the sunlit shading.
    path = n.new("ShaderNodeLightPath")
    n.link(n.map_range(path.outputs["Is Camera Ray"], 0.0, 1.0, C.SKY_STRENGTH, C.SKY_CAMERA_STRENGTH),
           bg.inputs["Strength"])
    n.link(bg.outputs[0], out.inputs["Surface"])
    return world


def build_sun(coll):
    light = bpy.data.lights.new("sun", "SUN")
    light.energy = C.SUN_STRENGTH
    light.color = C.SUN_COLOR
    light.angle = C.SUN_ANGLE
    obj = bpy.data.objects.new("sun", light)
    obj.rotation_euler = (-sun_vector()).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(obj)
    return obj


def build_bounce(coll):
    light = bpy.data.lights.new("bounce_fill", "AREA")
    light.shape = "RECTANGLE"
    light.size, light.size_y = C.PERGOLA_W, C.PERGOLA_D
    light.energy = C.BOUNCE_POWER
    light.color = C.BOUNCE_COLOR
    obj = bpy.data.objects.new("bounce_fill", light)
    obj.location = (C.PERGOLA_W / 2, C.PERGOLA_D / 2, 0.3)
    obj.rotation_euler = (math.pi, 0, 0)   # area lights emit along -Z; flip to face up
    obj.visible_camera = False
    obj.visible_shadow = False
    coll.objects.link(obj)
    return obj


def build_cameras(coll, anchors):
    for name, (loc, target, lens) in CAMERAS.items():
        cam = bpy.data.cameras.new(name)
        cam.lens = lens
        cam.sensor_width = 36.0
        cam.clip_start = 0.05
        cam.clip_end = 5000.0
        obj = bpy.data.objects.new(name, cam)
        obj.location = loc
        direction = Vector(target) - Vector(loc)
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        coll.objects.link(obj)
    for name in ("anchor_projects", "anchor_writing", "anchor_reviews"):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "SPHERE"
        empty.empty_display_size = 0.05
        empty.location = anchors[name]
        coll.objects.link(empty)
    bpy.context.scene.camera = bpy.data.objects["cam_hero"]


def configure_render(samples=C.SAMPLES):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = C.RES_X
    scene.render.resolution_y = C.RES_Y
    scene.render.resolution_percentage = 100
    cy = scene.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.max_bounces = 6
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 2
    cy.transmission_bounces = 4
    cy.transparent_max_bounces = 24  # alpha-cut leaf cards stack up
    cy.sample_clamp_indirect = 6.0
    cy.blur_glossy = 1.0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = C.LOOK
    scene.view_settings.exposure = C.EXPOSURE
    scene.render.image_settings.file_format = "PNG"
    _use_gpu(scene)


def _use_gpu(scene):
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "METAL"
        if any(d.use for d in prefs.devices):
            scene.cycles.device = "GPU"
            return "METAL"
    except Exception as exc:  # pragma: no cover - CPU fallback
        print("GPU setup failed, using CPU:", exc)
    scene.cycles.device = "CPU"
    return "CPU"
