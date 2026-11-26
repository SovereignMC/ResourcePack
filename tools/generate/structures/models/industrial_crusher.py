#!/usr/bin/env python3
"""Industrial gyratory crusher station (structure_industrial_crusher), 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_crusher.py

A concrete foundation carries a bolted, flanged cylindrical crusher body topped by a wide conical feed hopper full
of ore. A cross-shaped spider beam holds the mainshaft cap (the mast sits on it). Four discharge chutes feed four
short belt conveyors that spill crushed ore into piles; a motor with a belt guard sits in each corner.
Running: mainshaft/mantle and conveyor rollers spin, the ore in the hopper bobs.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_crusher.bbmodel")
Y0 = 3.4
SUF = ("", "_e", "_s", "_w")


def build():
    b = Builder("industrial_crusher", run_length=4.0)
    industrial_plinth(b)
    fr = "frame"
    # ---- foundation + body -------------------------------------------------------------------------
    b.group("body", parent=fr)
    g = "body"
    b.cube("found", (-7.8, Y0, -7.8), (7.8, 6.0, 7.8), {"up": "concrete", "*": "concrete"}, g)
    b.cube("found_cap", (-8.2, 5.4, -8.2), (8.2, 6.0, 8.2), "dark_steel", g)
    b.cylinder("shell", 0, 0, 6.0, 16.0, 6.8, "steel_plate", 8, g)
    for i, y in enumerate((6.0, 10.5, 15.0)):
        b.cylinder("flange%d" % i, 0, 0, y, y + 1.2, 7.4, "dark_steel", 8, g)
    for i, y in enumerate((6.0, 15.0)):
        for k in range(8):
            a = math.radians(k * 45 + 22.5)
            x, z = 7.2 * math.cos(a), 7.2 * math.sin(a)
            b.cube("bolt%d_%d" % (i, k), (x - 0.5, y + 1.2, z - 0.5), (x + 0.5, y + 1.8, z + 0.5), "galvanized", g, hide={"down"})
    b.cylinder("haz", 0, 0, 12.4, 13.2, 7.0, "hazard_stripe", 8, g)
    b.taper("upper", 0, 0, 16.2, 20.0, 6.8, 8.0, "steel_plate", 3, 8, g)
    b.hopper("hopper", 0, 0, 20.0, 29.0, 10.0, 8.0, "galvanized", "dark_steel", 12, g)
    b.cylinder("hop_band", 0, 0, 23.0, 24.0, 9.3, "warning_paint_yellow", 8, g)
    # spider cross-beam on the hopper rim + mainshaft cap
    b.cube("spider_x", (-10.8, 29.0, -1.1), (10.8, 30.6, 1.1), {"up": "hazard_stripe", "*": "dark_steel"}, g)
    b.cube("spider_z", (-1.1, 29.0, -10.8), (1.1, 30.6, 10.8), {"up": "hazard_stripe", "*": "dark_steel"}, g, hide={"down"})
    b.cylinder("cap_base", 0, 0, 30.6, 32.0, 3.6, "dark_steel", 12, g)
    shaft = b.group("shaft", parent=g, origin=(0, 30.6, 0))
    b.cylinder("cap", 0, 0, 32.0, 34.0, 2.8, "steel_plate", 12, shaft)
    b.cylinder("cap_ring", 0, 0, 33.0, 33.6, 3.2, "brass", 12, shaft)
    b.cube("cap_stripe_x", (-2.8, 34.0, -0.6), (2.8, 34.5, 0.6), "hazard_stripe", shaft, hide={"down"})
    b.cube("cap_stripe_z", (-0.6, 34.0, -2.8), (0.6, 34.5, 2.8), "hazard_stripe", shaft, hide={"down", "up"})
    # mantle head poking out of the hopper between spider arms
    b.taper("mantle", 0, 0, 29.0, 32.0, 4.2, 2.8, "rusted_steel", 3, 12, shaft)
    # ---- ore in the hopper (NE quadrant, cloned 4x, bobs) -------------------------------------------------
    ore = b.group("ore", parent=fr, origin=(0, 29, 0))
    for i, (x, z, s, r) in enumerate(((5.2, 4.4, 2.6, 20), (7.6, 6.4, 2.2, 50), (4.2, 7.6, 2.0, 75),
                                       (7.8, 3.0, 1.7, 10), (5.6, 5.8, 1.6, 35), (9.0, 5.4, 1.5, 60), (5.8, 9.0, 1.5, 15))):
        y = 29.0 if i != 4 else 30.8
        b.cube("ore%d" % i, (x - s / 2, y, z - s / 2), (x + s / 2, y + s * 0.8, z + s / 2),
               "stone" if i % 2 == 0 else "rusted_steel", ore, rotation=(0, r, 0), hide={"down"})
    # ---- side module (north): discharge chute, conveyor, crushed-ore pile ------------------------------
    side = b.group("side_n", parent=fr)
    b.cube("chute_box", (-3.0, 8.6, -9.0), (3.0, 12.6, -6.4), "dark_steel", side)
    b.cube("chute_band", (-3.3, 10.4, -9.3), (3.3, 11.2, -6.4), "hazard_stripe", side)
    b.cube("chute_lip", (-2.4, 8.4, -10.2), (2.4, 9.4, -9.0), "steel_plate", side)
    b.conveyor("cv", 0, -7.6, 0, -13.0, 7.8, 5.0, "rubber", "steel_plate", side)
    pile = b.group("pile", parent=side, origin=(0, Y0, -14.0))
    b.taper("pile_t", 0, -14.0, Y0, 7.0, 2.9, 0.8, "stone", 4, 8, pile)
    for i, (x, z, s) in enumerate(((-3.0, -13.0, 1.0), (3.0, -12.8, 1.0), (-2.2, -15.2, 0.9), (2.4, -15.0, 1.0))):
        b.cube("pchunk%d" % i, (x - s, Y0, z - s), (x + s, Y0 + 1.6 * s, z + s), "stone", pile, rotation=(0, 20 + 25 * i, 0))
    # ---- corner module (NW): motor + belt guard --------------------------------------------------------
    cm = b.group("corner_nw", parent=fr)
    b.cube("m_base", (-14.0, Y0, -14.0), (-9.4, Y0 + 0.8, -9.4), "dark_steel", cm)
    b.cube("m_body", (-13.6, Y0 + 0.8, -13.6), (-9.4, 10.0, -9.4), "galvanized", cm)
    for i, y in enumerate((5.8, 8.2)):
        b.cube("m_fin%d" % i, (-14.0, y, -14.0), (-9.0, y + 0.7, -9.0), "dark_steel", cm)
    b.cube("m_lid", (-13.8, 10.0, -13.8), (-9.2, 10.8, -9.2), "warning_paint_yellow", cm)
    b.cube("m_box", (-12.6, 10.8, -12.6), (-10.4, 12.0, -10.4), "steel_plate", cm, hide={"down"})
    b.cube("guard", (-3.4, 8.2, -1.4), (3.4, 11.6, 1.4), "warning_paint_yellow", cm, rotation=(0, 45, 0), origin=(-7.4, 9.9, -7.4))
    # ---- 4-fold -----------------------------------------------------------------------------------------
    b.radial4(["ore"], ("_e", "_s", "_w"))
    b.radial4([side], ("_e", "_s", "_w"))
    b.radial4([cm], ("_1", "_2", "_3"))
    industrial_status_mast(b, 0, 0, 34.5)
    # ---- animation --------------------------------------------------------------------------------------
    b.spin("shaft", "y", 2.0)
    for k, s in enumerate(SUF):
        b.bob("ore" + s, 0.5, 2.0, phase=0.25 * k)
        for r in (0, 1):
            b.spin("cv_roller%d_t%s" % (r, s), "y", 0.5)
    b.input_bones(["ore" + s for s in SUF])
    b.output_bones(["pile" + s for s in SUF])
    return b


if __name__ == "__main__":
    build().save(OUT)
