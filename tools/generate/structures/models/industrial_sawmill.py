#!/usr/bin/env python3
"""Industrial sawmill (structure_industrial_sawmill), 4-fold symmetric.

Central steel saw housing with a big circular saw blade (hooded) on every side, a log carriage shuttling on rails
into each blade, a lumber stack and a sawdust cyclone per corner pair, extraction fan on the roof.

    python3 tools/generate/structures/models/industrial_sawmill.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_sawmill.bbmodel")
SUF = ("", "_e", "_s", "_w")
Y0 = 3.4


def build():
    b = Builder("industrial_sawmill", run_length=4.0)
    industrial_plinth(b)
    F = "frame"
    # ---- central housing ---------------------------------------------------------------------
    b.cube("h_foot", (-7.6, Y0, -7.6), (7.6, Y0 + 1.6, 7.6), "dark_steel", F)
    b.cube("h_body", (-7, Y0 + 1.6, -7), (7, 18, 7), {"up": "steel_plate", "*": "steel_plate"}, F)
    b.cube("h_band", (-7.3, 17, -7.3), (7.3, 18.6, 7.3), "hazard_stripe", F)
    b.cube("h_roof", (-6, 18.6, -6), (6, 19.6, 6), "dark_steel", F)
    b.cylinder("fan_ring", 0, 0, 19.6, 21.4, 3.8, "galvanized", 12, F)
    b.fan("exfan", (0, 21.6, 0), 3.0, 4, "y", "galvanized", "dark_steel", F)
    # ---- side module (north) -------------------------------------------------------------------
    side = b.group("side", parent=F)
    b.cube("spindle", (-2.2, 10, -9.0), (2.2, 14, -7), "dark_steel", side)
    b.rivet_strip("h_riv", (-5.4, 6.4, -7.0), "north", 10.8, 2.7, 0, "galvanized", side)
    b.panel("h_panel_l", (-6.6, 8, -7), 2.4, 4.0, "north", "glow_amber", "dark_steel", 0.5, 0.6, side)
    b.panel("h_panel_r", (4.2, 8, -7), 2.4, 4.0, "north", "glow_cyan", "dark_steel", 0.5, 0.6, side)
    blade = b.gear("saw", (0, 12, -9.6), 5.4, 0.8, 16, "z", "galvanized", "steel_plate", "brass", side)
    b.cube("hood_top", (-5, 18, -11.2), (5, 19, -8.2), "warning_paint_yellow", side)
    b.cube("hood_l", (-5.9, 12.5, -11.2), (-5.2, 19, -8.2), "dark_steel", side)
    b.cube("hood_r", (5.2, 12.5, -11.2), (5.9, 19, -8.2), "dark_steel", side)
    for sx, n in ((-1, "l"), (1, "r")):
        b.cube("rail_" + n, (sx * 3.2 - 0.6, Y0, -16), (sx * 3.2 + 0.6, 5, -8), "dark_steel", side)
        b.cube("rail_top_" + n, (sx * 3.2 - 0.9, 5, -16), (sx * 3.2 + 0.9, 5.6, -8), "steel_plate", side)
    for i, z in enumerate((-15.2, -12, -9)):
        b.cube("tie%d" % i, (-4.4, Y0, z - 0.5), (4.4, 4.4, z + 0.5), "steel_plate", side)
    car = b.group("carriage", parent=side, origin=(0, 6, -13))
    b.cube("car_deck", (-4.2, 5.6, -15.4), (4.2, 6.6, -10.4), "steel_plate", car)
    b.cube("car_haz", (-4.2, 6.6, -15.5), (4.2, 7.2, -15.2), "hazard_stripe", car)
    b.cube("car_cradle_l", (-3.8, 6.6, -14.6), (-2.8, 8.2, -11), "dark_steel", car)
    b.cube("car_cradle_r", (2.8, 6.6, -14.6), (3.8, 8.2, -11), "dark_steel", car)
    b.pipe("log", (0, 8.4, -12.8), 6.4, 2.3, "z", "wood_plank", 8, car, cap_mat="wood_plank")
    # lumber stack (NE corner) and sawdust cyclone (NW)
    pl = b.group("planks", parent=side, origin=(12, Y0, -13))
    for i in range(3):
        o = 0.4 * (i % 2)
        b.cube("plank%d" % i, (8.6 + o, Y0 + i * 1.5, -15.4), (15.4 + o, Y0 + 1.5 * (i + 1), -12.6), {"up": "wood_plank", "*": "wood_plank"}, pl)
    b.cube("plank_strap", (11.0, Y0, -15.6), (11.8, Y0 + 4.5, -12.4), "warning_paint_yellow", pl, hide={"down"})
    b.cube("plank_pallet", (8.2, Y0, -15.6), (15.8, Y0 + 0.5, -12.4), "dark_steel", pl)
    cy = b.group("cyclone", parent=side)
    b.cylinder("cy_foot", -10, -11, Y0, Y0 + 1, 3.0, "dark_steel", 8, cy)
    b.cylinder("cy_drum", -10, -11, 11, 17, 2.8, "galvanized", 8, cy)
    b.taper("cy_cone", -10, -11, Y0 + 1, 11, 0.9, 2.7, "steel_plate", 4, 8, cy)
    b.cylinder("cy_band", -10, -11, 13.5, 14.5, 3.1, "warning_paint_yellow", 8, cy)
    b.cylinder("cy_top", -10, -11, 17, 18, 2.0, "dark_steel", 8, cy)
    b.pipe_run("cy_duct", [(-10, 17.8, -11), (-10, 19.6, -11), (-10, 19.6, -6.5), (-7.0, 19.6, -6.5)], 0.9, "copper", "dark_steel", 8, cy)
    b.radial4([side], ("_e", "_s", "_w"))
    industrial_status_mast(b, 0, 0, 22.0)
    for k, s in enumerate(SUF):
        axis = "z" if k % 2 == 0 else "x"
        b.spin("saw" + s, axis, 0.5, 1)
        pax, sg = ((("z", 1)), ("x", -1), ("z", -1), ("x", 1))[k] if False else (("z", 1), ("x", -1), ("z", -1), ("x", 1))[k]
        b.piston("carriage" + s, pax, 3.0 * sg, 2.0)
        x, z = -10, -11
        for _ in range(k):
            x, z = -z, x
        b.smoke("d%d" % k, x, 18.5, z, puffs=2, rise=7, period=4.0, size=2.0, group="cyclone" + s, mat="wood_plank")
    b.spin("exfan", "y", 0.25)
    b.input_bones(["carriage" + s for s in SUF])
    b.output_bones(["planks" + s for s in SUF])
    return b


if __name__ == "__main__":
    build().save(OUT)
