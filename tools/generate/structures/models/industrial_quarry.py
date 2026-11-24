#!/usr/bin/env python3
"""Industrial quarry rig (structure_industrial_quarry), 4-fold symmetric.

Square steel tower (swinging turret) on a base block with a glazed cab, four cutter-head arms that each carry a
spinning toothed cutter wheel and a rising conveyor, rock heaps and a diesel stack in the corners.

    python3 tools/generate/structures/models/industrial_quarry.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_quarry.bbmodel")
SUF = ("", "_e", "_s", "_w")
Y0 = 3.4


def build():
    b = Builder("industrial_quarry", run_length=4.0)
    industrial_plinth(b)
    F = "frame"
    b.cube("base", (-8, Y0, -8), (8, 9, 8), {"up": "dark_steel", "*": "steel_plate"}, F)
    b.cube("base_haz", (-8.3, Y0, -8.3), (8.3, Y0 + 1.2, 8.3), "hazard_stripe", F)
    b.cube("base_top", (-8.4, 9, -8.4), (8.4, 10, 8.4), "dark_steel", F)
    b.cylinder("ring", 0, 0, 10, 11, 8.2, "steel_plate", 12, F)
    up = b.group("upper", parent=F, origin=(0, 11, 0))
    b.cube("cab", (-6, 11, -6), (6, 22, 6), "galvanized", up)
    b.cube("cab_band", (-6.3, 11, -6.3), (6.3, 12.4, 6.3), "dark_steel", up)
    b.cube("cab_haz", (-6.3, 20.4, -6.3), (6.3, 22, 6.3), "hazard_stripe", up)
    b.cube("cab_roof", (-6.8, 22, -6.8), (6.8, 23, 6.8), "dark_steel", up)
    b.cube("roof_plate", (-4, 23, -4), (4, 24, 4), "steel_plate", up)
    side = b.group("side", parent=up)
    for sx, n in ((-1, "l"), (1, "r")):
        x = sx * 3.4
        b.cube("win_%s_f" % n, (x - 1.8, 14, -6.5), (x + 1.8, 19.4, -6), "dark_steel", side)
        b.cube("win_%s" % n, (x - 1.3, 14.6, -6.9), (x + 1.3, 18.8, -6.5), "glass", side, hide={"down", "up"})
    # cutter arm: beam, hub, wheel, rising conveyor
    b.cube("arm_beam", (-2.4, 8.4, -11), (2.4, 10.8, -6), "dark_steel", side)
    b.cube("arm_beam_top", (-2.8, 10.8, -11), (2.8, 11.4, -6), "steel_plate", side)
    b.cube("arm_hub", (-1.4, 6.6, -12.4), (1.4, 9.4, -10.6), "dark_steel", side)
    cut = b.gear("cutter", (0, 8, -13.2), 5.0, 2.2, 10, "z", "dark_steel", "galvanized", "brass", side)
    b.strut("belt", (0, 13.6, -13.2), (0, 21, -6.6), 1.8, 3.2, "rubber", side)
    b.strut("belt_rail_l", (-1.9, 13.9, -13.2), (-1.9, 21.3, -6.6), 0.8, 0.8, "warning_paint_yellow", side)
    b.strut("belt_rail_r", (1.9, 13.9, -13.2), (1.9, 21.3, -6.6), 0.8, 0.8, "warning_paint_yellow", side)
    b.cube("belt_leg", (-0.6, 8.4, -13.8), (0.6, 14, -12.6), "dark_steel", side)
    b.cube("belt_head", (-2.2, 20, -7.2), (2.2, 22, -5.8), "steel_plate", side)
    # diesel stack (NW roof corner) and a hazard lamp
    b.cylinder("exh", -4.6, -4.6, 23, 30, 0.9, "dark_steel", 8, side)
    b.cylinder("exh_cap", -4.6, -4.6, 29.2, 30, 1.3, "rusted_steel", 8, side)
    # rock heap (NE corner) with output hint
    heap = b.group("heap", parent=side, origin=(12, Y0, -12))
    b.taper("rock", 12, -12, Y0, 9.4, 4.4, 1.4, "stone", 4, 8, heap)
    for i, (x, z, s) in enumerate(((8.6, -8.4, 1.6), (15, -8.8, 1.3), (9, -15, 1.4))):
        b.cube("chunk%d" % i, (x - s, Y0, z - s), (x + s, Y0 + 2 * s, z + s), "stone", heap, rotation=(0, 30, 0))
    b.cube("heap_haz", (8.2, Y0, -16), (16, Y0 + 0.8, -15.5), "hazard_stripe", heap)
    b.radial4([side], ("_e", "_s", "_w"))
    industrial_status_mast(b, 0, 0, 24.0)
    for k, s in enumerate(SUF):
        axis = "z" if k % 2 == 0 else "x"
        b.spin("cutter" + s, axis, 0.5, 1 if k < 2 else -1)
        x, z = -4.6, -4.6
        for _ in range(k):
            x, z = -z, x
        b.smoke("q%d" % k, x, 30.4, z, puffs=2, rise=8, period=4.0, size=1.8, group="side" + s)
    b.oscillate("upper", "rotation", "y", 5.0, 4.0)
    b.input_bones(["cutter" + s for s in SUF])
    b.output_bones(["heap" + s for s in SUF])
    return b


if __name__ == "__main__":
    build().save(OUT)
