#!/usr/bin/env python3
"""Industrial wood cutter (structure_industrial_woodcutter): a log in a debarking gantry, four disc saws.

    python3 tools/generate/structures/models/industrial_woodcutter.py   # writes bbmodels/structure_industrial_woodcutter.bbmodel

A tree trunk turns on the centre line inside a gantry frame (corner posts + ring beams + cross beams + hoist chain).
On every side a carriage with a horizontal disc saw advances into the log; each side also has a stack of cut
logs (output) and a dust cyclone with a smoking stack. 4-fold symmetric: the north side is built once and cloned.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_woodcutter.bbmodel")
SUF = ("_e", "_s", "_w")
# inward motion of the north module after a 90 degree turn: (axis, sign) for N, E, S, W
INWARD = [("z", 1), ("x", -1), ("z", -1), ("x", 1)]
NAMES = ["", "_e", "_s", "_w"]


def build():
    b = Builder("industrial_woodcutter", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- the log: debarked trunk with bands and a grapple crown ------------------------------
    b.group("trunk", parent="frame", origin=(0, 15, 0))
    b.cylinder("log", 0, 0, Y0, 27, 4.2, {"*": "wood_plank", "up": "wood_plank"}, 8, "trunk")
    b.cylinder("log_foot", 0, 0, Y0, Y0 + 1.6, 5.2, "dark_steel", 8, "trunk")
    for i, y in enumerate((9.0, 15.0, 21.0)):
        b.cylinder("log_band%d" % i, 0, 0, y, y + 0.9, 4.8, "rusted_steel", 8, "trunk")
    b.cylinder("crown", 0, 0, 27, 28.4, 5.0, "dark_steel", 8, "trunk")
    b.cylinder("crown_hub", 0, 0, 28.4, 29.4, 1.6, "brass", 8, "trunk")
    b.cylinder("chain", 0, 0, 29.4, 30.2, 0.7, "galvanized", 4, "trunk")
    for i in range(4):  # grapple claws
        a = i * 90
        c = b.cube("claw%d" % i, (4.2, 24.2, -0.7), (5.4, 27.6, 0.7), "steel_plate", "trunk",
                   rotation=(0, a, 0), origin=(0, 26, 0), hide={"down"})

    # ---- frame: four posts, ring beams, cross beams ------------------------------------------
    b.group("gantry", parent="frame")
    g = "gantry"
    P = 11.5
    posts = []
    for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        x, z = sx * P, sz * P
        b.cube("post%d" % i, (x - 1.2, Y0, z - 1.2), (x + 1.2, 30, z + 1.2), "steel_plate", g, hide={"down"})
        b.cube("post_foot%d" % i, (x - 1.8, Y0, z - 1.8), (x + 1.8, Y0 + 1.6, z + 1.8), "dark_steel", g)
        b.cube("post_band%d" % i, (x - 1.5, 21, z - 1.5), (x + 1.5, 22.2, z + 1.5), "hazard_stripe", g)
        b.cube("post_band2_%d" % i, (x - 1.5, 9, z - 1.5), (x + 1.5, 10.2, z + 1.5), "hazard_stripe", g)
        b.cube("post_cap%d" % i, (x - 1.7, 30, z - 1.7), (x + 1.7, 32.4, z + 1.7), "dark_steel", g)
    ring = b.cube("ring_n", (-P + 1.7, 30, -P - 1.2), (P - 1.7, 32, -P + 1.2), "steel_plate", g)
    ring_top = b.cube("ring_n_stripe", (-P + 1.7, 32, -P - 0.8), (P - 1.7, 32.5, -P + 0.8), "warning_paint_yellow", g)
    b.cube("cross_x", (-P + 1.7, 30, -1.2), (P - 1.7, 32, 1.2), "steel_plate", g)
    b.cube("cross_z", (-1.2, 30.3, -P + 1.7), (1.2, 31.7, P - 1.7), "dark_steel", g)
    b.m.radial4([ring, ring_top], SUF)
    # ---- side module (north) ---------------------------------------------------------------
    s = b.group("side_n", parent="frame")
    b.cube("saw_base", (-4.5, Y0, -14.6), (4.5, Y0 + 6, -9.6), "dark_steel", s)
    b.cube("saw_base_top", (-4.9, Y0 + 6, -14.9), (4.9, Y0 + 6.8, -9.3), "steel_plate", s)
    b.panel("saw_panel", (-3, Y0 + 1.2, -14.6), 6, 4, "north", "rusted_steel", "dark_steel", group=s)
    b.rivet_strip("saw_riv", (-3.5, Y0 + 5.4, -14.6), "north", 7, 3.5, 0, "galvanized", s)
    b.cube("saw_rail_l", (-2.4, Y0 + 6.8, -13.5), (-1.4, Y0 + 7.6, -7.4), "galvanized", s)
    b.cube("saw_rail_r", (1.4, Y0 + 6.8, -13.5), (2.4, Y0 + 7.6, -7.4), "galvanized", s)
    carr = b.group("carr_n", parent=s, origin=(0, 10.4, -10))
    b.cube("carr_body", (-3.2, 10.2, -14.0), (3.2, 12.6, -10.0), "rusted_steel", carr)
    b.cube("carr_cheek", (-3.4, 10.0, -14.2), (3.4, 10.6, -9.8), "dark_steel", carr)
    b.cylinder("motor", 0, -12.0, 12.6, 15.2, 1.9, "galvanized", 8, carr)
    b.cylinder("motor_cap", 0, -12.0, 15.2, 16, 1.4, "copper", 8, carr)
    b.cube("arm", (-1.0, 9.8, -10.2), (1.0, 11.2, -8.4), "steel_plate", carr)
    b.cube("hood", (-3.5, 11.4, -11.4), (3.5, 12.2, -8.6), "hazard_stripe", carr)
    b.cube("hood_back", (-3.5, 10.0, -11.6), (3.5, 12.2, -11.0), "dark_steel", carr)
    b.pipe("ram", (0, Y0 + 5.2, -13.2), 5, 0.9, "z", "copper", 8, carr)
    b.gear("saw_n", (0, 10.7, -8.4), 3.0, 0.6, 12, "y", "galvanized", "steel_plate", "brass", carr)
    # cut-log stack (output)
    cr = b.group("crate_n", parent=s, origin=(7.6, 6, -12.6))
    b.cube("cradle_l", (5.2, Y0, -15.2), (5.9, Y0 + 3, -10), "dark_steel", cr, hide={"down"})
    b.cube("cradle_r", (9.4, Y0, -15.2), (10.1, Y0 + 3, -10), "dark_steel", cr, hide={"down"})
    b.cube("cradle_base", (5.2, Y0, -15.2), (10.1, Y0 + 0.8, -10), "steel_plate", cr)
    for i, (z, y) in enumerate(((-14.0, Y0 + 2.2), (-11.4, Y0 + 2.2), (-12.7, Y0 + 4.6))):
        b.pipe("cutlog%d" % i, (7.65, y, z), 4.2, 1.25, "x", {"*": "wood_plank", "up": "wood_plank"}, 8, cr)
    # dust cyclone + smoking stack
    b.chimney("cyc", -8.0, -12.6, Y0, 14.5, 2.2, 1.3, "galvanized", "dark_steel", 8, s)
    b.cylinder("cyc_band", -8.0, -12.6, 8.2, 9.0, 2.6, "hazard_stripe", 8, s)
    b.pipe("cyc_duct", (-6.2, 8.6, -12.6), 3.6, 0.8, "x", "copper", 8, s)
    b.m.radial4([s], SUF)
    # ---- hoist chain, status mast ------------------------------------------------------------
    industrial_status_mast(b, 0, 0, 32.4)
    # ---- animation -------------------------------------------------------------------------
    b.spin("trunk", "y", 4.0)
    for k, nm in enumerate(NAMES):
        ax, sg = INWARD[k]
        b.piston("carr_n" + nm, ax, 1.9 * sg, 2.0, phase=0.25 * k)
        b.spin("saw_n" + nm, "y", 0.5, 1 if k % 2 == 0 else -1)
        b.smoke("cyc%d" % k, *rot_pt(-8.0, 14.9, -12.6, k), puffs=3, rise=8, period=4.0, size=2.2,
                group="side_n" + nm)
    b.input_bones(["trunk"])
    b.output_bones(["crate_n" + n for n in NAMES])
    return b


def rot_pt(x, y, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, y, z


if __name__ == "__main__":
    b = build()
    b.save(OUT)
