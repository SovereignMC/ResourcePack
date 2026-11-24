#!/usr/bin/env python3
"""Industrial electrolysis plant (structure_industrial_electrolysis): four open glowing cells with electrode banks and
bubbling gas under frame hoods, copper bus bars to a central rectifier with cooling fins and a fan, and a gas
collector sphere on legs with a vent stack. 4-fold symmetric (pinwheel pipework).

    python3 tools/generate/structures/models/industrial_electrolysis.py   # writes bbmodels/structure_industrial_electrolysis.bbmodel
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_electrolysis.bbmodel")


def rot(x, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def build():
    b = Builder("industrial_electrolysis", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- central rectifier ------------------------------------------------------------------------------
    b.group("rectifier", parent="frame")
    r = "rectifier"
    b.cube("rc_body", (-4.4, Y0, -4.4), (4.4, 12.4, 4.4), "dark_steel", r)
    b.cube("rc_foot", (-5, Y0, -5), (5, Y0 + 1.4, 5), "steel_plate", r)
    b.cube("rc_cap", (-4.9, 12.4, -4.9), (4.9, 13.4, 4.9), "steel_plate", r)
    b.cube("rc_haz", (-4.7, 8.6, -4.7), (4.7, 9.6, 4.7), "hazard_stripe", r)
    # side module of the rectifier: cooling fins, a gauge and rivets
    rs = b.group("rc_side", parent="frame")
    for i, x in enumerate((-3.2, -1.6, 0.0, 1.6, 3.2)):
        b.cube("fin%d" % i, (x - 0.4, Y0 + 2, -6.2), (x + 0.4, 8.2, -4.4), "copper", rs)
    b.cube("fin_top", (-3.8, 8.0, -6.4), (3.8, 8.6, -4.4), "dark_steel", rs)
    b.cube("fin_bot", (-3.8, Y0 + 1.6, -6.4), (3.8, Y0 + 2.2, -4.4), "dark_steel", rs)
    b.cube("gauge_f", (-2.0, 10.2, -4.9), (2.0, 12.0, -4.4), "dark_steel", rs)
    b.cube("gauge", (-1.5, 10.6, -5.0), (1.5, 11.6, -4.9), "glow_amber", rs, hide={"up", "down"})
    # coil crown with insulators
    b.cylinder("coil", 0, 0, 13.4, 16, 3.4, "copper", 8, r)
    b.cylinder("coil_band", 0, 0, 14.2, 14.8, 3.8, "dark_steel", 8, r)
    # cooling fan on the roof, between the collector legs
    rf = b.fan("rfan", (0, 17.2, 0), 2.6, 4, "y", "galvanized", "dark_steel", r)
    b.ring("rfan_guard", 0, 0, 16.2, 17.2, 3.0, 2.5, "warning_paint_yellow", 8, r)

    # ---- gas collector on four legs ---------------------------------------------------------------------
    b.group("coll", parent="frame", origin=(0, 27, 0))
    b.tank("sphere", 0, 0, 22, 31, 4.6, "galvanized", "dark_steel", 12, 2, "coll")
    b.cylinder("sphere_belt", 0, 0, 25.6, 26.6, 5.2, "warning_paint_yellow", 12, "coll")
    b.chimney("vent", 0, 0, 33, 44, 1.4, 1.0, "steel_plate", "dark_steel", 8, "coll")
    for i, (x, z) in enumerate(((-3.1, -3.1), (3.1, -3.1), (3.1, 3.1), (-3.1, 3.1))):
        b.cube("leg%d" % i, (x - 0.7, 13.4, z - 0.7), (x + 0.7, 22.4, z + 0.7), "steel_plate", "frame", hide={"down"})
        b.cube("leg_foot%d" % i, (x - 1.0, 13.4, z - 1.0), (x + 1.0, 14.0, z + 1.0), "dark_steel", "frame")
        b.cube("leg_head%d" % i, (x - 1.0, 21.8, z - 1.0), (x + 1.0, 22.6, z + 1.0), "dark_steel", "frame")

    # ---- cell module (NE quadrant) ----------------------------------------------------------------------
    cx, cz = 9.6, -9.6
    cell = b.group("cell_n", parent="frame")
    b.cube("c_floor", (cx - 5, Y0, cz - 5), (cx + 5, Y0 + 1, cz + 5), "dark_steel", cell)
    for nm, (a, c) in {"n": ((cx - 5, cz - 5), (cx + 5, cz - 4.1)), "s": ((cx - 5, cz + 4.1), (cx + 5, cz + 5)),
                       "w": ((cx - 5, cz - 4.1), (cx - 4.1, cz + 4.1)), "e": ((cx + 4.1, cz - 4.1), (cx + 5, cz + 4.1))}.items():
        b.cube("c_wall_" + nm, (a[0], Y0 + 1, a[1]), (c[0], 10.6, c[1]), "steel_plate", cell)
    b.cube("c_liquid", (cx - 4.1, Y0 + 1, cz - 4.1), (cx + 4.1, 10.4, cz + 4.1), {"up": "glow_cyan", "*": "glow_cyan"}, cell,
           hide={"north", "south", "east", "west", "down"})
    b.ring("c_rim", cx, cz, 10.6, 11.3, 7.07, 5.8, "dark_steel", 4, cell)
    b.cube("c_band", (cx - 5.2, 5.4, cz - 5.2), (cx + 5.2, 6.6, cz + 5.2), "hazard_stripe", cell)
    # level window with glow and rivets on the north face
    b.cube("c_win_f", (cx - 2.2, 6.8, cz - 5.5), (cx + 2.2, 9.8, cz - 5.0), "dark_steel", cell, hide={"up", "down"})
    b.cube("c_win", (cx - 1.6, 7.2, cz - 5.6), (cx + 1.6, 9.4, cz - 5.4), "glow_cyan", cell, hide={"up", "down"})
    # frame hood
    for i, (x, z) in enumerate(((cx - 4.6, cz - 4.6), (cx + 4.6, cz - 4.6), (cx + 4.6, cz + 4.6), (cx - 4.6, cz + 4.6))):
        b.cube("h_post%d" % i, (x - 0.5, 11.3, z - 0.5), (x + 0.5, 19, z + 0.5), "warning_paint_yellow", cell, hide={"down"})
    b.ring("h_rail", cx, cz, 18.2, 19, 7.07, 5.9, "warning_paint_yellow", 4, cell)
    b.taper("h_cone", cx, cz, 19, 22, 2.8, 1.4, "steel_plate", 3, 8, cell)
    b.cube("h_stay_x", (cx - 5.5, 18.3, cz - 0.4), (cx + 5.5, 18.9, cz + 0.4), "dark_steel", cell)
    b.cube("h_stay_z", (cx - 0.4, 18.3, cz - 5.5), (cx + 0.4, 18.9, cz + 5.5), "dark_steel", cell)
    # electrode bank: alternating copper / graphite plates with glowing terminal caps, bus bars on top
    el = b.group("elec_n", parent=cell, origin=(cx, 11, cz))
    for i, x in enumerate((cx - 2.4, cx, cx + 2.4)):
        m = "copper" if i % 2 == 0 else "dark_steel"
        b.cube("plate%d" % i, (x - 0.4, Y0 + 2, cz - 2.0), (x + 0.4, 15.6, cz + 2.0), m, el)
        b.cube("term%d" % i, (x - 0.6, 15.6, cz - 0.6), (x + 0.6, 16.4, cz + 0.6), "glow_amber" if i % 2 == 0 else "glow_red", el, hide={"down"})
    b.cube("bus_a", (cx - 3.0, 16.4, cz - 0.4), (cx + 3.0, 16.9, cz + 0.4), "copper", el, hide={"down"})
    # bus bar and gas line, pinwheel
    b.pipe_run("bus", [(cx, 20.8, cz - 0.0), (cx, 24.2, cz)], 0.9, "copper", "dark_steel", 8, cell, flange=True)
    b.pipe_run("gas", [(cx, 22, cz), (cx, 26, cz), (cx, 26, 0), (4.4, 26, 0)], 1.0, "galvanized", "dark_steel", 8, cell)
    b.cube("gas_valve", (cx - 1.5, 26 - 1.5, -2.2 + 0.0), (cx + 1.5, 26 + 1.5, -0.8), "warning_paint_red", cell)

    # ---- 4-fold -----------------------------------------------------------------------------------------
    b.m.radial4([cell], ("_e", "_s", "_w"))
    b.m.radial4([rs], ("_e", "_s", "_w"))

    # ---- animation --------------------------------------------------------------------------------------
    b.spin(rf, "y", 0.5)
    b.pulse_scale("coll", 1.0, 1.05, 2.0)
    names = ["cell_n", "cell_n_e", "cell_n_s", "cell_n_w"]
    for k, cn in enumerate(names):
        x, z = rot(cx, cz, k)
        for j, (dx, dz) in enumerate(((-2.2, -2.2), (2.0, 0.4), (-0.4, 2.4))):
            px, pz = rot(cx + dx, cz + dz, k)
            b.smoke("bub%d_%d" % (k, j), px, 10.3, pz, puffs=2, rise=6.0, period=2.0 if j != 1 else 4.0, size=1.3,
                    group=cn, mat="glow_cyan")
    b.input_bones(["elec_n", "elec_n_e", "elec_n_s", "elec_n_w"])
    b.output_bones(["coll"])
    industrial_status_mast(b, 0, 0, 44.0)
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
