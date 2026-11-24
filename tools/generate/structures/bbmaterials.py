"""Procedural texture materials for bblib.Builder (deterministic, seeded numpy).

Every generator is `fn(w, h, rng, kind)` -> uint8 RGBA array (h, w, 4) drawn in the face's reading
orientation (u right, v down as seen from outside; for `up` faces north is at the top). `kind` is
'top', 'bottom' or 'side'. Colours come from industrial_palette.json only.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "industrial_palette.json"), encoding="utf-8") as _f:
    PALETTE = {k: np.array(v, float) for k, v in json.load(_f).items() if not k.startswith("_")}


def P(name):
    return PALETTE[name]


def _solid(w, h, col, rng, var=5):
    a = np.empty((h, w, 4))
    a[..., :3] = np.asarray(col, float) + rng.integers(-var, var + 1, (h, w, 1))
    a[..., 3] = 255
    return a


def _bevel(a, hi=14, lo=18):
    h, w = a.shape[:2]
    if w > 2 and h > 2:
        a[0, :, :3] += hi
        a[:, 0, :3] += hi * 0.5
        a[-1, :, :3] -= lo
        a[:, -1, :3] -= lo * 0.7
    return a


def _blobs(w, h, rng, cell=4):
    """Smooth-ish value noise in [0,1]."""
    gw, gh = w // cell + 2, h // cell + 2
    g = rng.random((gh, gw))
    ys = (np.arange(h) / cell)
    xs = (np.arange(w) / cell)
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a = g[y0][:, x0] * (1 - fy) * (1 - fx) + g[y0][:, x0 + 1] * (1 - fy) * fx
    a += g[y0 + 1][:, x0] * fy * (1 - fx) + g[y0 + 1][:, x0 + 1] * fy * fx
    return a


def _fin(a):
    return np.clip(np.rint(a), 0, 255).astype(np.uint8)


def _rivet(a, x, y):
    h, w = a.shape[:2]
    if 0 <= x < w and 0 <= y < h:
        a[y, x, :3] = P("steel_hi") + 24
        if x + 1 < w and y + 1 < h:
            a[y + 1, x + 1, :3] = P("steel_lo") - 14


def steel_plate(w, h, rng, kind):
    a = _bevel(_solid(w, h, P("steel"), rng))
    if w >= 12:
        a[:, w // 2, :3] -= 12  # panel seam
    if h >= 12:
        a[h // 2, :, :3] -= 10
    if w >= 5 and h >= 5:
        for x in range(2, w - 2, 4 if w > 8 else max(1, w - 5)):
            _rivet(a, x, 1)
            _rivet(a, x, h - 3)
        for y in range(2, h - 2, 4 if h > 8 else max(1, h - 5)):
            _rivet(a, 1, y)
            _rivet(a, w - 3, y)
    return _fin(a)


def dark_steel(w, h, rng, kind):
    a = _solid(w, h, P("dark_steel"), rng, 3)
    a[..., :3] += rng.integers(-5, 6, (h, 1, 1))  # brushed streaks
    return _fin(_bevel(a, 10, 14))


def galvanized(w, h, rng, kind):
    a = _solid(w, h, P("galvanized"), rng, 3)
    sp = (_blobs(w, h, rng, 2) - 0.5) * 34
    a[..., :3] += sp[..., None]
    return _fin(_bevel(a, 10, 16))


def rusted_steel(w, h, rng, kind):
    a = _solid(w, h, P("steel_lo"), rng, 5)
    n = _blobs(w, h, rng, 3) + (rng.random((h, w)) - 0.5) * 0.25
    for lo, col in ((0.55, "rust_dark"), (0.62, "rust"), (0.78, "rust_hi")):
        m = n > lo
        a[m, :3] = P(col) + rng.integers(-5, 6, (int(m.sum()), 1))
    if h > 3:  # drips
        for x in rng.integers(0, w, max(1, w // 6)):
            a[min(h - 1, h // 2):, x, :3] = P("rust_dark")
    return _fin(_bevel(a, 8, 14))


def hazard_stripe(w, h, rng, kind):
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    band = ((x + y) // 3) % 2 == 0
    a = _solid(w, h, P("hazard_black"), rng, 3)
    a[band, :3] = P("hazard_yellow") + rng.integers(-6, 7, (int(band.sum()), 1))
    return _fin(a)


def copper(w, h, rng, kind):
    a = _solid(w, h, P("copper"), rng, 4)
    a[..., :3] += ((np.arange(w) % 5 == 0)[None, :, None]) * 14
    pat = rng.random((h, w)) > 0.96
    a[pat, :3] = P("patina")
    return _fin(_bevel(a, 18, 22))


def brass(w, h, rng, kind):
    a = _solid(w, h, P("brass"), rng, 4)
    a[..., :3] += ((np.arange(h) % 4 == 0)[:, None, None]) * 12
    return _fin(_bevel(a, 18, 24))


def rubber(w, h, rng, kind):
    return _fin(_bevel(_solid(w, h, P("rubber"), rng, 3), 10, 6))


def concrete(w, h, rng, kind):
    a = _solid(w, h, P("concrete"), rng, 4)
    a[..., :3] += ((_blobs(w, h, rng, 5) - 0.5) * 22)[..., None]
    pits = rng.random((h, w))
    a[pits > 0.975, :3] = P("concrete_lo")
    a[pits < 0.02, :3] = P("concrete_hi")
    return _fin(a)


def glass(w, h, rng, kind):
    a = _solid(w, h, P("glass"), rng, 3)
    if w > 2 and h > 2:
        a[0, :, :3] = P("glass_lo")
        a[-1, :, :3] = P("glass_lo")
        a[:, 0, :3] = P("glass_lo")
        a[:, -1, :3] = P("glass_lo")
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    m = ((x - y + h // 2) % max(6, w) < 2) & (x > 0) & (y > 0) & (x < w - 1) & (y < h - 1)
    a[m, :3] = P("glass_hi")
    return _fin(a)


def grate(w, h, rng, kind):
    a = _solid(w, h, P("grate_hole"), rng, 2)
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    bars = (x % 3 == 0) | (y % 3 == 0)
    a[bars, :3] = P("grate_bar") + rng.integers(-6, 7, (int(bars.sum()), 1))
    return _fin(a)


def _glow(name):
    def fn(w, h, rng, kind):
        a = _solid(w, h, P(name), rng, 6)
        yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        d = np.sqrt(((xx + .5) / w - .5) ** 2 + ((yy + .5) / h - .5) ** 2)
        t = np.clip(1 - d * 1.6, 0, 1)[..., None]
        a[..., :3] = a[..., :3] * (1 - t * .8) + P(name + "_hi") * t * .8
        edge = (d > 0.55)[..., None]
        a[..., :3] = np.where(edge, 0.65 * a[..., :3] + .35 * P(name + "_lo"), a[..., :3])
        return _fin(a)
    return fn


def _paint(name):
    def fn(w, h, rng, kind):
        a = _solid(w, h, P(name), rng, 3)
        chips = rng.random((h, w)) > 0.97
        a[chips, :3] = P(name + "_lo")
        return _fin(_bevel(a, 10, 16))
    return fn


def wood_plank(w, h, rng, kind):
    a = _solid(w, h, P("wood"), rng, 4)
    ph = 4
    for y in range(0, h, ph):
        a[y, :, :3] = P("wood_lo")
        if y + 1 < h:
            a[y + 1, :, :3] = P("wood_hi")
        off = int(rng.integers(0, max(1, w)))
        a[y:y + ph, off % w, :3] = P("wood_lo")
    grain = rng.random((h, w)) > 0.92
    a[grain, :3] = P("wood_lo") + 8
    return _fin(a)


def brick(w, h, rng, kind):
    a = np.empty((h, w, 4))
    a[..., :3] = P("mortar")
    a[..., 3] = 255
    for row, y in enumerate(range(0, h, 4)):
        off = 4 if row % 2 else 0
        for x in range(-off, w, 8):
            col = P("brick") if rng.random() > 0.3 else P("brick_lo")
            x0, x1 = max(0, x), min(w, x + 7)
            y1 = min(h, y + 3)
            if x1 > x0 and y1 > y:
                a[y:y1, x0:x1, :3] = col + rng.integers(-7, 8, (y1 - y, x1 - x0, 1))
    return _fin(a)


def stone(w, h, rng, kind):
    a = _solid(w, h, P("stone"), rng, 5)
    cell = _blobs(w, h, rng, 3)
    a[..., :3] += ((cell - .5) * 40)[..., None]
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    crack = ((x * 7 + y * 3 + int(rng.integers(0, 9))) % 11 == 0) & (rng.random((h, w)) > 0.5)
    a[crack, :3] = P("stone_lo")
    return _fin(_bevel(a, 8, 10))


def dirt(w, h, rng, kind):
    a = _solid(w, h, P("dirt"), rng, 8)
    f = rng.random((h, w))
    a[f > 0.9, :3] = P("dirt_lo")
    a[f < 0.04, :3] = P("stone")
    return _fin(a)


def water(w, h, rng, kind):
    a = _solid(w, h, P("water"), rng, 4)
    for y in range(1, h, 4):
        o = int(rng.integers(0, 4))
        a[y, o::4, :3] = P("water_hi")
    return _fin(a)


def leaves(w, h, rng, kind):
    a = _solid(w, h, P("leaves"), rng, 4)
    f = _blobs(w, h, rng, 2)
    a[f > 0.66, :3] = P("leaves_hi")
    a[f < 0.3, :3] = P("leaves_lo")
    return _fin(a)


MATERIALS = {
    "steel_plate": steel_plate, "dark_steel": dark_steel, "galvanized": galvanized,
    "rusted_steel": rusted_steel, "hazard_stripe": hazard_stripe, "copper": copper, "brass": brass,
    "rubber": rubber, "concrete": concrete, "glass": glass, "grate": grate,
    "glow_amber": _glow("glow_amber"), "glow_red": _glow("glow_red"), "glow_cyan": _glow("glow_cyan"),
    "warning_paint_yellow": _paint("paint_yellow"), "warning_paint_red": _paint("paint_red"),
    "wood_plank": wood_plank, "brick": brick, "stone": stone, "dirt": dirt, "water": water, "leaves": leaves,
}


def paint(name, w, h, rng, kind):
    if name not in MATERIALS:
        raise KeyError("unknown material %r (have: %s)" % (name, ", ".join(sorted(MATERIALS))))
    return MATERIALS[name](w, h, rng, kind)
