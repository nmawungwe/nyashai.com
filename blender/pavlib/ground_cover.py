"""Ground cover: grass clumps in the garden and foreground.

Split out of vegetation.py; uses the same instancing helpers.
"""

import math

from mathutils import Vector

from .landscape import ground_z, plateau_d
from .materials import MATS
from .util import rng
from .vegetation import _garden_spot, grass_source, scatter
from .views import hero_place, visible


def grass_points(r, n, sampler):
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 20:
        tries += 1
        x, y = sampler()
        if not _garden_spot(x, y) or plateau_d(x, y) > 1.8:
            continue
        z = ground_z(x, y)
        if not visible((x, y, z), 0.4):
            continue
        s = r.uniform(0.7, 1.4)
        pts.append((Vector((x, y, z)), (0, 0, r.uniform(0, 6.28)), (s, s, s * r.uniform(0.8, 1.3))))
    return pts


def build_grass(coll, src_coll):
    r = rng(81)
    clump = grass_source("src_grass_clump", src_coll, MATS["grass"], r, blades=12, height=0.55, width=0.013, seeds=2)
    wide = grass_source("src_grass_wide", src_coll, MATS["grass"], r, blades=10, height=0.38, width=0.022)

    def garden():
        x, y, _ = hero_place(r.uniform(5.0, 17.0), r.uniform(-9.0, 3.0))
        return x, y

    def foreground():  # bottom of the hero frame (ground is visible from ~5 m), round the boulders
        x, y, _ = hero_place(r.uniform(4.6, 8.0), r.uniform(-4.5, 0.5))
        return x, y

    tall = grass_source("src_grass_tall", src_coll, MATS["grass_dry"], r, blades=10, height=0.9, width=0.01,
                        seeds=5)
    pts = grass_points(r, 400, garden) + grass_points(r, 220, foreground)
    # Three grass types: green clumps, broad-bladed clumps and tall dry seed grass.
    groups = {"grass_clumps": (clump, []), "grass_wide": (wide, []), "grass_tall": (tall, [])}
    for i, p in enumerate(pts):
        key = ("grass_clumps", "grass_clumps", "grass_clumps", "grass_clumps", "grass_wide", "grass_wide",
               "grass_tall", "grass_tall", "grass_tall", "grass_clumps")[i % 10]
        groups[key][1].append(p)
    for name, (src, items) in groups.items():
        scatter(name, coll, src, items, radius=0.4, cull=False)
    return len(pts)
