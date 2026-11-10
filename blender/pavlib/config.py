"""Named scene parameters. Units: metres, Z up.

Layout (top view): pergola footprint x in [0, PERGOLA_W], y in [0, PERGOLA_D].
Front of the pavilion faces -Y; the hero camera stands in front, right of centre,
looking north-west across the table towards the tree and the valley.
"""

import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = REPO_ROOT / "blender" / "pavilion.blend"
LAPTOP_SCREEN_IMAGE = REPO_ROOT / "src" / "assets" / "projects" / "goveranai.webp"
TABLET_SCREEN_IMAGE = REPO_ROOT / "src" / "assets" / "projects" / "vhenekai.webp"
# Optional serif font for the essay cover; falls back to Blender's built-in font.
ESSAY_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
)

SEED = 1729

# --- Pergola -----------------------------------------------------------------
PERGOLA_W = 5.0
PERGOLA_D = 3.5
PERGOLA_H = 2.6            # top of posts at x = 0
ROOF_PITCH = 0.045         # rise per metre along +X ("rising to the right")
POST_SIZE = 0.16
POSTS = (                  # (x, y) post centres
    (0.10, 0.10),          # front-left corner
    (1.25, 0.10),          # second front post (pair reads as "front-left corner area")
    (0.10, 3.30),          # back-left corner (carries the back beam)
    (2.35, 3.30),          # back post where the rammed-earth wall starts
)
BEAM_W = 0.16
BEAM_H = 0.24
BEAM_OVERHANG = 0.45
SLAT_W = 0.03
SLAT_H = 0.03
SLAT_PITCH = 0.085         # centre-to-centre spacing of roof slats

# --- Rammed earth wall --------------------------------------------------------
WALL_X0 = 2.25
WALL_X1 = 5.65
WALL_Y = PERGOLA_D         # inner face of back wall
WALL_T = 0.45
WALL_H = 2.95
RETURN_WALL_X = 5.20       # inner face of the right-hand return wall
RETURN_WALL_Y0 = -0.05     # near end of return wall (carries the front beam)
NICHE = dict(y=1.2, z=1.05, w=0.6, h=0.62, depth=0.25)
BENCH_H = 0.46
BENCH_D = 0.52

POT_POS = (-0.5, -0.4, 0.0)   # big terracotta pot by the front-left post

# --- Table and props ------------------------------------------------------------
TABLE_CENTER = (2.55, 1.75)
TABLE_SIZE = (1.8, 0.82, 0.76)   # length (x), depth (y), height
TABLE_YAW = math.radians(-4)

# --- Light ---------------------------------------------------------------------
SUN_ELEVATION = math.radians(27)
SUN_AZIMUTH = math.radians(236)     # direction the light comes FROM, 0 = +X, CCW
SUN_STRENGTH = 7.2
SUN_COLOR = (1.0, 0.6, 0.31)
SUN_ANGLE = math.radians(0.8)
SKY_STRENGTH = 0.55          # sky as a light source
# Warm bounce under the roof: a soft upward-facing area light just above the
# paving, standing in for sunlit-floor bounce onto the slats and wall (bakeable).
BOUNCE_POWER = 35.0
BOUNCE_COLOR = (1.0, 0.7, 0.45)
SKY_CAMERA_STRENGTH = 0.8   # sky as seen directly by the camera (stills only)
HAZE_STRENGTH = 1.0          # emissive aerial-perspective colour on far ridges
SKY_GLOW_DIR = (-0.9, 0.42, 0.1)   # low warm glow on the left of the hero view

# --- Palette (sRGB hex sampled from the reference) ------------------------------
PALETTE = dict(
    wall="#c88358", wall_band="#ab6443", wall_light="#dc9f74",
    bench="#d8b693", bench_cap="#e7d3b7",
    timber="#3f2a1c", timber_light="#6a4a33", slat="#8a5534",
    table="#6d4930",
    paving="#dbb98f", paving_dark="#c29a72", grout="#a3815f",
    terrain="#a8904f", terrain_dry="#c9ab68", terrain_green="#867c3e",
    rock="#a99d86", rock_dark="#776b5a",
    bark="#5b4b3d", bark_light="#8a7a68",
    leaf="#8a9435", leaf_light="#c3c04c", leaf_dark="#56611f",
    grass="#8d8a45", grass_dry="#c0aa66",
    pot="#b86a40",
    sky_horizon="#fbefd8", sky_low="#dfeaf0", sky_mid="#a6cdee", sky_zenith="#4a8cd6",
    hill_near="#8f8236", hill_mid="#56632f", hill_far="#4f6a72", hill_farthest="#6a86a6",
    haze="#c9dcec", haze_warm="#f2dcb8",
    fabric="#6b706a", fabric_light="#b9ad97",
    cushion="#d6c8ad", cushion_dark="#2b2a28",
    paper="#efe6d3", ink="#2a2420",
    aluminium="#a3a3a6", screen_bezel="#151515",
    mug_white="#e9e3d8", mug_dark="#3b3631",
    backpack="#2f3330",
    books=("#7d5a44", "#5f6b5c", "#a58a5f", "#6e5662", "#c2b59a", "#4f5f6f", "#9a6a4a"),
)

# --- Cameras: name -> (location, look-at target, focal length mm) ------------------
# Close-ups sit on the hero camera's side of the pavilion so each flight is a
# straight dolly in under the front beam.
CAMERAS = {
    "cam_hero": ((3.7, -6.9, 1.55), (-0.2, 3.0, 2.05), 28.0),
    "cam_projects": ((2.95, 0.35, 1.28), (2.45, 1.82, 0.92), 32.0),
    "cam_writing": ((3.62, 2.42, 1.14), (3.86, 3.2, 0.5), 30.0),
    "cam_reviews": ((4.25, 2.3, 1.02), (4.68, 3.35, 0.68), 32.0),
    # Portrait phone framing (393x852): pavilion and table lower-centre, tree above.
    "cam_hero_portrait": ((2.9, -6.6, 1.45), (1.5, 2.6, 2.6), 26.0),
    "cam_overview": ((14.0, -17.0, 12.5), (0.5, -1.0, 1.5), 30.0),
}
# Cameras whose views decide what scattered geometry is kept (web cameras only).
CULL_CAMERAS = ("cam_hero", "cam_hero_portrait", "cam_projects", "cam_writing", "cam_reviews")
# Aspect ratio per camera (width / height); others use the landscape render size.
CAMERA_ASPECT = {"cam_hero_portrait": 828 / 1792}

# --- Render ----------------------------------------------------------------------
RES_X = 1672
RES_Y = 941
SAMPLES = 160
EXPOSURE = 0.6
LOOK = "AgX - Medium High Contrast"   # Punchy crushed the sky and shadows
