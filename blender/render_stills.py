"""Render Cycles preview stills from the saved scene.

Usage (from the repo root):
    /Applications/Blender.app/Contents/MacOS/Blender -b blender/pavilion.blend \
        -P blender/render_stills.py -- <output_dir> [camera ...] [--samples N] [--scale PCT] [--webp]

Cameras default to: cam_hero cam_projects cam_writing cam_reviews cam_overview.
Each still is written as <output_dir>/<name>.png where name drops the "cam_" prefix.
"""

import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402

from pavlib import config, rig  # noqa: E402

DEFAULT_CAMS = ["cam_hero", "cam_hero_portrait", "cam_projects", "cam_writing", "cam_reviews", "cam_overview"]
PORTRAIT_RES = (828, 1792)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: ... -- <output_dir> [camera ...] [--samples N] [--scale PCT]")
    out_dir = Path(argv.pop(0))
    samples, scale, fmt = None, 100, "PNG"
    cams = []
    while argv:
        a = argv.pop(0)
        if a == "--samples":
            samples = int(argv.pop(0))
        elif a == "--scale":
            scale = int(argv.pop(0))
        elif a == "--webp":
            fmt = "WEBP"
        else:
            cams.append(a)
    cams = cams or DEFAULT_CAMS
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    rig.configure_render(samples or scene.cycles.samples)
    scene.render.resolution_percentage = scale
    print("device:", scene.cycles.device)
    scene.render.image_settings.file_format = fmt
    if fmt == "WEBP":
        scene.render.image_settings.quality = 86
    ext = "webp" if fmt == "WEBP" else "png"
    for name in cams:
        scene.camera = bpy.data.objects[name]
        portrait = name in config.CAMERA_ASPECT
        scene.render.resolution_x, scene.render.resolution_y = PORTRAIT_RES if portrait else (config.RES_X, config.RES_Y)
        scene.render.filepath = str(out_dir / f"{name.removeprefix('cam_')}.{ext}")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"rendered {name} in {time.time() - t0:.1f}s -> {scene.render.filepath}")


main()
