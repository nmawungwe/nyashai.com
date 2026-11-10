"""Matte painting for the distant hills, made from the owner's homepage artwork.

The clean hills in the left of garden-desktop-personal.webp are resampled into
angular space (u = azimuth, v = elevation as seen from the hero camera), so the
painting sits on a curved card exactly where the hills are in the artwork's hero
framing. Outside the clean window the strip is mirror-extended in azimuth (the
mirrored parts fall behind the pavilion, tree and wall). The sky above the far
ridge is keyed out and feathered so the baked sky shows through; the valley at
the bottom fades into the near-terrain colour.

Outputs: a display-referred RGBA PNG for the web (blender/.build/matte.png) and a
scene-linear copy for Cycles so the stills show the same colours through AgX.
"""

import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

from . import config as C
from .util import object_from_data

ART = C.REPO_ROOT / "src" / "assets" / "pavilion" / "garden-desktop-personal.webp"
ART_SIZE = (1672, 941)
# Clean window in the artwork (pixels, top-down): hills, valley and haze only.
CLEAN = dict(x0=0, x1=530, y0=360, y1=590)
ART_MOBILE = C.REPO_ROOT / "src" / "assets" / "pavilion" / "garden-mobile-personal.webp"
# Clean tree-covered valley slopes on the left of the mobile artwork (left of the posts).
VALLEY = dict(x0=0, x1=150, y0=775, y1=875)
EL_BOTTOM = -25.0               # card runs well below the terrace edge so no bottom edge shows
AZ_RANGE = (25.0, 225.0)        # degrees, card coverage around the hero eye
PX_PER_DEG = 20.5
RADIUS = 80.0                   # card radius around the hero eye (m)
SKY_HORIZON = np.array([0.83, 0.81, 0.78], dtype=np.float32)   # baked sky at the horizon (display)
VALLEY_CONTRAST = 0.6
VALLEY_TINT = np.array([1.03, 0.99, 0.86], dtype=np.float32)
OUT_PNG = C.REPO_ROOT / "blender" / ".build" / "matte.png"


def _hero_basis():
    loc, target, lens = C.CAMERAS["cam_hero"]
    loc, target = Vector(loc), Vector(target)
    fwd = (target - loc).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd)
    tan_h = 18.0 / lens
    return loc, fwd, right, up, tan_h, tan_h * ART_SIZE[1] / ART_SIZE[0]


def _dir_of_pixel(px, py):
    loc, fwd, right, up, th, tv = _hero_basis()
    d = fwd + right * ((2 * px / ART_SIZE[0] - 1) * th) + up * ((1 - 2 * py / ART_SIZE[1]) * tv)
    d.normalize()
    return math.degrees(math.atan2(d.y, d.x)), math.degrees(math.asin(d.z))


def _load_art(path=ART):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "Non-Color"    # raw display values
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)[::-1, :, :3]          # top-down rows


def _sample(art, px, py):
    h, w, _ = art.shape
    px = np.clip(px, 0, w - 1.001)
    py = np.clip(py, 0, h - 1.001)
    x0, y0 = np.floor(px).astype(int), np.floor(py).astype(int)
    fx, fy = (px - x0)[..., None], (py - y0)[..., None]
    a = art[y0, x0] * (1 - fx) + art[y0, x0 + 1] * fx
    b = art[y0 + 1, x0] * (1 - fx) + art[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def build_strip():
    """Returns (rgba display array top-down, (el_bottom, el_top) degrees)."""
    art = _load_art()
    az_l, _ = _dir_of_pixel(CLEAN["x0"], (CLEAN["y0"] + CLEAN["y1"]) / 2)
    az_r, _ = _dir_of_pixel(CLEAN["x1"], (CLEAN["y0"] + CLEAN["y1"]) / 2)
    _, el_top = _dir_of_pixel(CLEAN["x1"], CLEAN["y0"])
    _, el_bot = _dir_of_pixel(CLEAN["x0"], CLEAN["y1"])
    el0, el1 = EL_BOTTOM, el_top + 0.5
    w = 4096
    h = int(math.ceil((el1 - el0) * w / (AZ_RANGE[1] - AZ_RANGE[0])))
    az = np.linspace(AZ_RANGE[1], AZ_RANGE[0], w)            # image left = larger azimuth
    el = np.linspace(el1, el0, h)                             # image top = up
    AZ, EL = np.meshgrid(az, el)
    _, el_valley = _dir_of_pixel((CLEAN["x0"] + CLEAN["x1"]) / 2, CLEAN["y1"] - 15)
    # The valley starts along a gently wandering line rather than a ruled one.
    el_line = el_valley + 0.35 * np.sin(np.radians(AZ * 9.0)) + 0.2 * np.sin(np.radians(AZ * 23.0 + 50.0))
    # Outside the clean window the mirrored copies are stretched sideways and
    # lowered by amounts that change with azimuth, so no two repeats of the main
    # peak share a silhouette. Inside the window (the hero's hills) nothing moves.
    lo, hi = min(az_l, az_r), max(az_l, az_r)
    outside = np.maximum(np.maximum(lo - AZ, AZ - hi), 0.0)
    far = _smooth(0.0, 12.0, outside)
    az_w = AZ + 5.0 * np.sin(np.radians(outside * 7.3)) * far
    squash = 1.0 - 0.45 * far * (0.5 + 0.5 * np.sin(np.radians(outside * 4.1 + 40.0)))
    el_s = np.where(EL > el_valley, el_valley + (EL - el_valley) / squash, EL)
    # Mirror-fold azimuth into the clean window (triangle wave: no seams).
    t = (az_w - az_r) / (az_l - az_r)
    t = np.abs(((t + 1) % 2) - 1)
    az_f = np.radians(az_r + t * (az_l - az_r))
    elr = np.radians(el_s)
    d = np.stack([np.cos(elr) * np.cos(az_f), np.cos(elr) * np.sin(az_f), np.sin(elr)], axis=-1)
    loc, fwd, right, up, th, tv = _hero_basis()
    zc = d @ np.array(fwd)
    px = ((d @ np.array(right)) / zc / th + 1) / 2 * ART_SIZE[0]
    py = (1 - (d @ np.array(up)) / zc / tv) / 2 * ART_SIZE[1]
    rgb = _sample(art, px, py)
    # Sky key: bright, low-contrast pixels above the far ridge become transparent,
    # with a soft feather so the baked sky shows through without a hard line.
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    sky = _smooth(0.74, 0.86, lum)
    alpha = 1.0 - sky * (1.0 - _smooth(CLEAN["y0"] + 150, CLEAN["y0"] + 190, py))
    alpha *= _smooth(CLEAN["y0"], CLEAN["y0"] + 40, py)
    # The artwork's sky is near-white, the baked sky is not: wherever a keyed sky
    # pixel keeps some opacity (feathers, mip bleed) it would show as a white
    # stripe on the horizon, so sky pixels take the baked sky's horizon colour.
    rgb = rgb * (1 - sky[..., None]) + SKY_HORIZON * sky[..., None]
    # Below the hills: a mirror-tiled patch of clean valley slopes from the mobile
    # artwork, at the strip's angular resolution, colour-matched to the desktop
    # valley band just under the hills, and blended in under them.
    mobile = _load_art(ART_MOBILE)
    vw, vh = VALLEY["x1"] - VALLEY["x0"], VALLEY["y1"] - VALLEY["y0"]
    tx = (AZ_RANGE[1] - AZ) * PX_PER_DEG / vw
    ty = np.maximum(el_line - EL, 0.0) * PX_PER_DEG / vh
    tx, ty = np.abs(((tx + 1) % 2) - 1), np.abs(((ty + 1) % 2) - 1)
    valley = _sample(mobile, VALLEY["x0"] + tx * (vw - 1), VALLEY["y0"] + ty * (vh - 1))
    patch = mobile[VALLEY["y0"]:VALLEY["y1"], VALLEY["x0"]:VALLEY["x1"]].reshape(-1, 3).mean(axis=0)
    target = art[CLEAN["y1"] - 30:CLEAN["y1"], CLEAN["x0"]:CLEAN["x1"]].reshape(-1, 3).mean(axis=0)
    valley = valley * (target / np.maximum(patch, 1e-3))
    # Sit the valley with the baked garden: calmer contrast, warmer, less blue.
    valley = np.clip((target + (valley - target) * VALLEY_CONTRAST) * VALLEY_TINT, 0.0, 1.0)
    blend = _smooth(el_line + 0.6, el_line - 0.6, EL)[..., None]
    rgb = rgb * (1 - blend) + valley * blend
    alpha = np.maximum(alpha, blend[..., 0])
    # Gentle grade: a touch of haze so the painting sits behind the baked garden.
    haze = np.array([0.86, 0.87, 0.88], dtype=np.float32)
    rgb = rgb * 0.9 + haze * 0.1
    return np.concatenate([rgb, alpha[..., None]], axis=-1).astype(np.float32), (el0, el1)


def _save_png(rgba, path):
    h, w, _ = rgba.shape
    img = bpy.data.images.new("matte_display", w, h, alpha=True)
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(rgba[::-1].ravel())          # Blender rows run bottom-up
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    return img


def build(coll):
    """Create the matte card (run after the view transform is configured)."""
    from bakelib.colour import inverse_display
    rgba, (el0, el1) = build_strip()
    OUT_PNG.parent.mkdir(exist_ok=True)
    _save_png(rgba, OUT_PNG)
    h, w, _ = rgba.shape
    # Scene-linear copy for Cycles: display values pushed back through the inverse
    # view transform, so the stills match what the web draws.
    lin, err = inverse_display_rgb(rgba[..., :3].reshape(-1, 3), inverse_display)
    lin_img = bpy.data.images.new("matte_linear", w, h, alpha=True, float_buffer=True)
    buf = np.concatenate([lin.reshape(h, w, 3), rgba[..., 3:]], axis=-1)
    lin_img.pixels.foreach_set(buf[::-1].ravel())
    lin_img.pack()
    print(f"matte strip {w}x{h}, elevation {el0:.1f}..{el1:.1f} deg, inverse display error {err:.3f}")
    return _card(coll, lin_img, el0, el1)


def inverse_display_rgb(rgb, inverse_display):
    """Invert the view transform for every pixel: quantise to 7 bits per channel
    and invert only the unique colours (the hazy strip has few of them)."""
    q = np.round(np.clip(rgb, 0, 1) * 127).astype(np.int64)
    keys = q[:, 0] * 16384 + q[:, 1] * 128 + q[:, 2]
    uniq, inv = np.unique(keys, return_inverse=True)
    cols = np.stack([uniq // 16384, (uniq // 128) % 128, uniq % 128], axis=1) / 127.0
    hexes = ["#%02x%02x%02x" % tuple(int(round(c * 255)) for c in col) for col in cols]
    lin, err = inverse_display(hexes)
    return lin[inv], err


def _card(coll, image, el0, el1):
    ex, ey, ez = C.CAMERAS["cam_hero"][0]
    az0, az1 = AZ_RANGE
    cols, rows = 200, 10
    verts, faces, uvs = [], [], []
    for i in range(cols + 1):
        a = math.radians(az0 + (az1 - az0) * i / cols)
        for j in range(rows + 1):
            e = el0 + (el1 - el0) * j / rows
            verts.append((ex + RADIUS * math.cos(a), ey + RADIUS * math.sin(a), ez + RADIUS * math.tan(math.radians(e))))
            uvs.append((1.0 - i / cols, j / rows))      # image left = larger azimuth
    for i in range(cols):
        for j in range(rows):
            a, b = i * (rows + 1) + j, (i + 1) * (rows + 1) + j
            faces.append((a, b, b + 1, a + 1))
    obj = object_from_data("matte_card", verts, faces, coll, _material(image))
    uv = obj.data.uv_layers.new(name="UVMap")
    loops = np.empty(len(obj.data.loops), dtype=np.int64)
    obj.data.loops.foreach_get("vertex_index", loops)
    uv.data.foreach_set("uv", np.array(uvs, dtype=np.float32)[loops].ravel())
    obj.visible_shadow = False
    return obj


def _material(image):
    """Cycles: emission of the scene-linear painting, alpha-blended over the sky."""
    mat = bpy.data.materials.new("matte_card")
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
    nt.links.new(nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def matte_png():
    return Path(OUT_PNG)
