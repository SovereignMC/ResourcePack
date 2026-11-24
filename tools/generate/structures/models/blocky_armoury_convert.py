#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_armoury.bbmodel to a 4-way symmetric layout.
Reads the git HEAD version unless --src is given.

Layout: the armour stand turns on a pedestal in the centre; per side (built on the south, cloned with radial4 as a
pinwheel so the racks never overlap) a weapon rack with 3 rifles, 2 swords and a shield, plus a small anvil with
its hammer and an ammo crate in front of it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _blocky_set_a import els, box, run  # noqa: E402


def convert(m):
    # --- rack: pinwheel half (x -15.5 .. 10.8) ------------------------------------------------
    p_left, p_right = els(m, "rack_post")
    box(p_right, (8.2, 2, 10.8), (10.6, 32, 13.2))
    (top,) = els(m, "rack_top"); box(top, (-15.5, 31, 10.5), (10.8, 33.5, 13.5))
    for e in els(m, "rack_bar"):
        e["to"][0] = 8.2
    (bb,) = els(m, "rack_backboard"); box(bb, (-13, 2, 10.2), (10.2, 9.5, 11))  # low kick board only
    swords = els(m, "sword_")
    third = [e for e in swords if e["from"][0] >= 7.9]
    m.delete(third)
    rack = [p_left, p_right, top, bb] + els(m, "rack_bar") + els(m, "rifle_") + els(m, "sword_") + els(m, "shield_")
    # --- anvil assembly: shrink, mirror (post on the right of the anvil) and move to the south strip --------
    asm = els(m, "anvil_") + els(m, "hot_blade") + els(m, "hammer_post") + [m.group("hammer")]
    m.scale(asm, 0.55, about=(-7, 2, -6))
    old = list(asm)
    asm = m.clone(old, mirror="x", suffix="")
    m.delete(old)
    m.translate(asm, dx=-13.2, dz=14.85)
    crate = els(m, "ammo_crate")
    m.scale(crate, 0.7, about=(12, 2, -12))
    m.translate(crate, dx=4.1 - 12, dz=8.2 + 12)
    # --- centre: the armour stand on its pedestal ---------------------------------------------
    stand = m.group("armour_stand")
    m.translate(stand, dx=-8, dz=2)
    module = rack + asm + crate
    m.radial4(module, ("_e", "_s", "_w"))
    return m


if __name__ == "__main__":
    run("armoury", convert)
