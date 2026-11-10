# /// script
# requires-python = ">=3.10"
# dependencies = ["onnxruntime", "numpy", "pillow", "scipy", "huggingface_hub"]
# ///
"""Bake the depth atlas that the pavilion WebGL scene reads.

Usage (from the repo root; re-run whenever the artwork changes):

    uv run scripts/bake-depth.py

For every source image it writes `<name>-depth.webp`, a greyscale atlas:

    top half     depth, white = near (Depth Anything V2 Small, Apache-2.0)
    bottom half  foliage mask, white = leaves that may sway in the breeze
"""
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from PIL import Image
from scipy import ndimage

ASSETS = Path(__file__).resolve().parent.parent / "src/assets/pavilion"
# (source image, atlas width in px, long side given to the depth model)
SOURCES = [
    ("garden-desktop-personal.webp", 1024, 1036),
    ("garden-mobile-personal.webp", 640, 1036),
]
PATCH = 14  # ViT patch size: model input sides must be multiples of it
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def estimate_depth(session: ort.InferenceSession, image: Image.Image, long_side: int) -> np.ndarray:
    """Relative inverse depth in 0..1 (1 = nearest) at the image's own size."""
    scale = long_side / max(image.size)
    width, height = (max(PATCH, round(side * scale / PATCH) * PATCH) for side in image.size)
    pixels = np.asarray(image.resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32) / 255
    tensor = ((pixels - MEAN) / STD).transpose(2, 0, 1)[None]
    depth = session.run(None, {session.get_inputs()[0].name: tensor})[0].squeeze()
    low, high = np.percentile(depth, [0.5, 99.5])
    depth = np.clip((depth - low) / (high - low), 0, 1)
    return np.asarray(
        Image.fromarray(depth).resize(image.size, Image.Resampling.BICUBIC), dtype=np.float32
    ).clip(0, 1)


def soften_depth(depth: np.ndarray) -> np.ndarray:
    """Grow near surfaces a little so their edges hide the stretched background."""
    grown = ndimage.grey_dilation(depth, size=(7, 7))
    return ndimage.gaussian_filter(grown, sigma=1.6)


def foliage_mask(image: Image.Image, depth: np.ndarray) -> np.ndarray:
    """Interior of green/olive regions, excluding the distant hills."""
    hue, saturation, value = (
        np.asarray(channel, dtype=np.float32) / 255 for channel in image.convert("HSV").split()
    )
    degrees = hue * 360
    leafy = (degrees > 30) & (degrees < 130) & (saturation > 0.2) & (value > 0.12)
    leafy = ndimage.binary_opening(leafy, iterations=2)
    interior = ndimage.binary_erosion(leafy, iterations=1)
    mask = ndimage.gaussian_filter(interior.astype(np.float32), sigma=4)
    not_distant = np.clip((depth - 0.12) / 0.12, 0, 1)
    return np.clip(mask * 1.4, 0, 1) * not_distant


def main() -> None:
    model = hf_hub_download("onnx-community/depth-anything-v2-small", "onnx/model.onnx")
    session = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    for name, atlas_width, long_side in SOURCES:
        image = Image.open(ASSETS / name).convert("RGB")
        depth = soften_depth(estimate_depth(session, image, long_side))
        mask = foliage_mask(image, depth)
        size = (atlas_width, round(atlas_width * image.height / image.width))
        halves = [
            Image.fromarray((layer * 255).astype(np.uint8)).resize(size, Image.Resampling.LANCZOS)
            for layer in (depth, mask)
        ]
        atlas = Image.new("L", (size[0], size[1] * 2))
        atlas.paste(halves[0], (0, 0))
        atlas.paste(halves[1], (0, size[1]))
        target = ASSETS / name.replace("-personal.webp", "-depth.webp")
        atlas.save(target, "WEBP", quality=90, method=6)
        print(f"{target.name}: {atlas.size[0]}x{atlas.size[1]}, {target.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
