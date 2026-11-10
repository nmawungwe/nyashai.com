"""Display-referred colour: push scene-linear values through the scene's view
transform (AgX + look + exposure), exactly as the Cycles stills were.

Blender exposes the view transform only on image save, so values are packed into
a float image, saved with `save_render` (which applies the scene's colour
management) and read back as raw display values.
"""

import math
import os
import tempfile

import bpy
import numpy as np

_TMP = tempfile.mkdtemp(prefix="pavilion_colour_")


def _image_settings(scene, depth="16"):
    s = scene.render.image_settings
    s.file_format = "PNG"
    s.color_mode = "RGBA"
    s.color_depth = depth


def to_display(rgb):
    """(N, 3) scene-linear -> (N, 3) display-referred sRGB-encoded values in 0..1."""
    rgb = np.asarray(rgb, dtype=np.float32).reshape(-1, 3)
    n = len(rgb)
    w = 1024
    h = max(1, math.ceil(n / w))
    buf = np.ones((w * h, 4), dtype=np.float32)
    buf[:n, :3] = rgb
    img = bpy.data.images.new("display_tmp", w, h, float_buffer=True, alpha=True)
    img.pixels.foreach_set(buf.ravel())
    path = os.path.join(_TMP, "display_tmp.png")
    scene = bpy.context.scene
    _image_settings(scene, "16")
    img.save_render(path, scene=scene)
    bpy.data.images.remove(img)
    back = bpy.data.images.load(path)
    back.colorspace_settings.name = "Non-Color"
    out = np.empty(w * h * 4, dtype=np.float32)
    back.pixels.foreach_get(out)
    bpy.data.images.remove(back)
    return out.reshape(-1, 4)[:n, :3]


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def save_display_png(img, path):
    """Save a baked float image through the view transform as an 8-bit sRGB PNG."""
    scene = bpy.context.scene
    _image_settings(scene, "8")
    scene.render.image_settings.color_mode = "RGB"
    img.save_render(path, scene=scene)


def inverse_display(targets_hex, iterations=8):
    """Scene-linear colours that display as `targets_hex` through the view transform.

    Used for painted (emission-only) surfaces such as the backdrop ridges, so the
    art-directed colours survive AgX + look + exposure. Fixed-point iteration on
    each channel's ratio; converges well for the low-saturation backdrop colours.
    """
    t = np.array([[int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)] for h in targets_hex],
                 dtype=np.float32)
    t_lin = srgb_to_linear(t)
    x = t_lin.copy()
    for _ in range(iterations):
        d_lin = srgb_to_linear(to_display(x))
        x = x * np.clip(t_lin / np.maximum(d_lin, 1e-5), 0.5, 2.0)
    err = np.abs(to_display(x) - t).max()
    return x, float(err)
