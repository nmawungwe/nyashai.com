"""Frustum tests against the web cameras, used to cull scattered geometry.

Pure math (no bpy cameras needed), so it can run before the cameras exist.
"""

from mathutils import Vector

from . import config as C

ASPECT = C.RES_X / C.RES_Y
SENSOR = 36.0

def _basis(loc, target):
    fwd = (Vector(target) - Vector(loc)).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd)
    return Vector(loc), fwd, right, up

_VIEWS = None

def _views():
    global _VIEWS
    if _VIEWS is None:
        _VIEWS = []
        for name in C.CULL_CAMERAS:
            loc, target, lens = C.CAMERAS[name]
            aspect = C.CAMERA_ASPECT.get(name, ASPECT)
            # Blender's AUTO sensor fit spans the sensor across the larger dimension.
            half_long = SENSOR / 2 / lens
            half_w, half_h = (half_long, half_long / aspect) if aspect >= 1 else (half_long * aspect, half_long)
            _VIEWS.append((*_basis(loc, target), half_w, half_h))
    return _VIEWS

def visible(p, radius=0.0, margin=0.12):
    """True if a sphere at p (radius metres) may appear in any web camera."""
    p = Vector(p)
    for loc, fwd, right, up, tx, ty in _views():
        d = p - loc
        depth = d.dot(fwd)
        if depth < -radius:
            continue
        depth = max(depth, 0.05)
        slack = radius / depth
        if abs(d.dot(right)) / depth <= tx * (1 + margin) + slack and \
                abs(d.dot(up)) / depth <= ty * (1 + margin) + slack:
            return True
    return False

def hero_distance(p):
    return (Vector(p) - Vector(C.CAMERAS["cam_hero"][0])).length

def hero_place(forward, lateral, z=0.0):
    """World XY at `forward` metres ahead and `lateral` metres right of the hero camera."""
    loc, fwd, right, _ = _basis(*C.CAMERAS["cam_hero"][:2])
    f = Vector((fwd.x, fwd.y, 0)).normalized()
    r = Vector((right.x, right.y, 0)).normalized()
    q = loc + f * forward + r * lateral
    return (q.x, q.y, z)
