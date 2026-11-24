#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_crusher.bbmodel (stamp mill) to a 4-way symmetric layout.
Reads the git HEAD version unless --src is given.

Layout: square mortar in the centre with one stamp in the middle; per side (built on the north and cloned with
radial4) one stamp pair is replaced by a stamp + its own camshaft with a flywheel, a ground feed bin with chute and
a dust pile. Frame posts move to the corners and the frame top becomes a square ring.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _blocky_set_a import els, box, run  # noqa: E402


def convert(m):
    # --- square body --------------------------------------------------------------------------
    (slab,) = els(m, "base_slab"); box(slab, (-15, 0, -15), (15, 3, 15))
    (mb,) = els(m, "mortar_box"); box(mb, (-9, 3, -9), (9, 8, 9))
    (ml,) = els(m, "mortar_lip"); box(ml, (-9.5, 8, -9.5), (9.5, 9, 9.5))
    (mo,) = els(m, "mortar_ore"); box(mo, (-8.2, 8, -8.2), (8.2, 8.6, 8.2))
    # corner posts
    for e, (sx, sz) in zip(els(m, "frame_post"), ((-1, -1), (-1, 1), (1, -1), (1, 1))):
        box(e, (sx * 13.4 - 1.2, 3, sz * 13.4 - 1.2), (sx * 13.4 + 1.2, 35, sz * 13.4 + 1.2))
    # top: square ring from the old top bar (north side) + clones of it; a ring of 4 bars
    (top,) = els(m, "frame_top"); box(top, (-14.5, 34, -14.6), (14.5, 36.5, -12.2))
    # guides (north bars become the ring beams between the posts)
    low = els(m, "frame_guide_low"); high = els(m, "frame_guide_high")
    box(low[0], (-12, 20, -14.5), (12, 22, -12.3)); box(high[0], (-12, 30, -14.5), (12, 31.5, -12.3))
    m.delete([low[1], high[1]])
    # diagonal braces: remove (the ring beams replace them)
    m.delete(els(m, "frame_diag"))
    # --- per-side module ------------------------------------------------------------------------
    # stamp 0 moves to the north side, tappet pointing north (-z) at the camshaft
    s0 = m.group("stamp_0")
    m.translate(s0, dx=7, dz=-5)
    # stamp 1 stays in the centre, without tappet
    s1 = m.group("stamp_1")
    m.delete([e for e in m.elements_in(s1) if "tappet" in e["name"]])
    m.delete(m.group("stamp_2"))
    for e in m.elements_in(s1):
        if e["name"] == "stamp_1_rod":
            e["to"][1] = 29
    # camshaft: shorter axle with the flywheel at its end, moved to the north side
    cam = m.group("camshaft")
    for e in m.elements_in(cam, recursive=False):
        if e["name"] in ("cam_axle", "cam_axle_b"):
            e["from"][0] = -9 if e["name"] == "cam_axle" else -8.99
            e["to"][0] = 6 if e["name"] == "cam_axle" else 5.99
    m.delete(m.find("cam_lobe_2"))
    fly = m.group("flywheel")
    m.scale(fly, 0.72, about=(16.5, 26, -6))
    m.translate(cam, dz=-5.0)
    m.translate(fly, dx=-8.6)
    # feed bin: scaled-down hopper on the ground with its chute leaning on the mortar
    hop = els(m, "hopper_body") + els(m, "hopper_chute") + els(m, "hopper_ore") + els(m, "ore_chunk")
    m.scale(hop, 0.5, about=(0, 14, 6))
    m.translate(hop, dx=7.5, dy=-11.0, dz=-18.6)
    dust = els(m, "dust_pile")
    m.translate(dust, dx=-4, dz=-4.5)
    module = [s0, cam, top, low[0], high[0]] + hop + dust
    m.radial4(module, ("_e", "_s", "_w"))
    # cross bracing on top carries the status mast in the centre
    (cx,) = m.clone([top], offset=(0, 0, 14.6), suffix="_cx")
    m.clone([cx], rot=90, suffix="_cz")
    return m


if __name__ == "__main__":
    run("crusher", convert)
