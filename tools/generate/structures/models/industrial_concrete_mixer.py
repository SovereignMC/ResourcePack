#!/usr/bin/env python3
"""Industrial concrete mixer (structure_industrial_concrete_mixer), 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_concrete_mixer.py

An upright ribbed mixing drum with a ring gear in the middle, driven by four motor + pinion sets (one per side),
fed by four cement silos in the corners through pinwheel pipes, with stacks of cement bags between the motors and
silos.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_concrete_mixer.bbmodel")
Y0 = 3.4


def build():
    b = Builder("industrial_concrete_mixer", run_length=4.0)
    industrial_plinth(b)
    fr = "frame"
    # ---- static base under the drum: output pad, ring beam, legs ---------------------------------
    b.group("base", parent=fr)
    b.cylinder("pad_c", 0, 0, Y0, 5.0, 6.2, "concrete", 8, "base", cap_mat="concrete")
    b.cylinder("pad_ring", 0, 0, 4.4, 5.2, 6.8, "hazard_stripe", 8, "base")
    b.cube("slump", (-2.4, 5.2, -2.4), (2.4, 6.4, 2.4), "concrete", "base", rotation=(0, 22.5, 0))
    # ring beam as a square of four pinwheel bars (x -9..9)
    rb = b.group("ringbeam_n", parent=fr)
    b.cube("rb_bar", (-9.6, 9.0, -9.6), (7.6, 10.8, -7.8), {"north": "hazard_stripe", "*": "dark_steel"}, rb)
    b.cube("rb_leg", (-7.4, Y0, -7.4), (-5.8, 9.0, -5.8), "steel_plate", rb)
    b.cube("rb_leg_foot", (-8.0, Y0, -8.0), (-5.2, 4.6, -5.2), "dark_steel", rb)
    b.cube("rb_leg_band", (-7.6, 6.0, -7.6), (-5.6, 7.2, -5.6), "hazard_stripe", rb)
    # ---- drum (spins) ---------------------------------------------------------------------------
    dr = b.group("drum", parent=fr, origin=(0, 20, 0))
    b.cylinder("dr_body", 0, 0, 13.2, 26.0, 7.0, "steel_plate", 12, dr)
    b.cylinder("dr_skirt", 0, 0, 10.8, 13.2, 6.4, "dark_steel", 12, dr)
    b.cylinder("dr_band_lo", 0, 0, 14.0, 15.0, 7.5, "copper", 12, dr)
    b.cylinder("dr_band_haz", 0, 0, 19.4, 21.4, 7.4, "hazard_stripe", 12, dr)
    b.cylinder("dr_band_hi", 0, 0, 24.6, 25.6, 7.5, "copper", 12, dr)
    b.taper("dr_shoulder", 0, 0, 26.0, 29.4, 7.0, 4.8, "rusted_steel", 3, 12, dr)
    b.cylinder("dr_mouth", 0, 0, 29.4, 31.0, 5.0, "dark_steel", 12, dr, cap_mat="concrete")
    b.cylinder("dr_mouth_rim", 0, 0, 30.8, 31.6, 5.5, "galvanized", 12, dr)
    b.cube("dr_paddle_x", (-4.6, 30.0, -0.5), (4.6, 30.8, 0.5), "steel_plate", dr)
    b.cube("dr_paddle_z", (-0.5, 29.8, -4.6), (0.5, 30.6, 4.6), "steel_plate", dr)
    import math
    for i in range(8):
        a = math.radians(i * 45 + 22.5)
        x, z = 7.2 * math.cos(a), 7.2 * math.sin(a)
        b.cube("dr_rib%d" % i, (x - 0.5, 15.0, z - 0.5), (x + 0.5, 24.6, z + 0.5), "galvanized", dr,
               rotation=(0, -math.degrees(a), 0), origin=(x, 20, z), hide={"down"})
    b.gear("dr_ring", (0, 12.2, 0), 7.6, 2.0, 16, "y", "dark_steel", "steel_plate", "brass", dr)
    # ---- north module --------------------------------------------------------------------------
    side = b.group("side_n", parent=fr)
    # motor + pinion
    b.cube("mt_ped", (-3.4, Y0, -15.2), (3.4, 8.4, -11.4), "dark_steel", side)
    b.cube("mt_ped_band", (-3.6, 4.6, -15.4), (3.6, 5.6, -11.2), "hazard_stripe", side, hide={"up", "down"})
    b.pipe("mt_body", (0, 11.6, -13.2), 5.0, 2.6, "z", "galvanized", 8, side, cap_mat="copper")
    b.cube("mt_fins", (-3.0, 14.1, -15.6), (3.0, 14.8, -10.8), "steel_plate", side, hide={"down"})
    b.cube("mt_box", (-1.4, 14.8, -14.2), (1.4, 16.4, -12.2), "dark_steel", side)
    b.cube("mt_led", (-0.6, 15.2, -14.5), (0.6, 16.0, -14.2), "glow_red", side, hide={"down", "up"})
    b.cube("mt_shaft", (-0.5, 11.4, -10.9), (0.5, 12.8, -8.6), "steel_plate", side)
    b.gear("pin_n", (0, 12.2, -9.2), 1.9, 2.0, 8, "y", "dark_steel", "steel_plate", "brass", side)
    # cement bags + pallet
    bags = b.group("bags_n", parent=side, origin=(6.2, Y0, -13.2))
    b.cube("bag_pallet", (3.8, Y0, -15.6), (8.6, 4.6, -10.4), "wood_plank", bags)
    for k, (x, z, y, rr) in enumerate(((4.0, -14.8, 4.6, 6), (4.0, -12.2, 4.6, -5), (6.4, -13.4, 4.6, 8), (5.0, -13.5, 7.0, -4))):
        b.cube("bag_%d" % k, (x, y, z - 1.2), (x + 2.2, y + 2.4, z + 1.2), {"up": "concrete", "*": "galvanized"}, bags,
               rotation=(0, rr, 0))
    b.cube("bag_strap", (3.8, 6.0, -15.4), (8.4, 6.4, -10.6), "warning_paint_yellow", bags, hide={"up", "down"})
    # silo at the north-east corner
    sx, sz = 12.0, -12.0
    b.cylinder("silo_foot", sx, sz, Y0, Y0 + 2.2, 4.0, "dark_steel", 12, side)
    b.tank("silo", sx, sz, Y0 + 2.2, 29.0, 3.3, "galvanized", "dark_steel", 12, 3, side)
    b.cylinder("silo_haz", sx, sz, 13.0, 14.6, 3.6, "hazard_stripe", 12, side)
    b.cylinder("silo_haz2", sx, sz, 22.0, 23.6, 3.6, "hazard_stripe", 12, side)
    b.cylinder("silo_vent", sx, sz, 31.0, 33.0, 1.0, "dark_steel", 8, side)
    b.cylinder("silo_valve", sx, sz, 8.0, 10.0, 1.4, "copper", 8, side)
    b.ladder("silo_lad", (sx - 3.2, Y0 + 2.2, sz), 24, "west", 2.6, "steel_plate", side)
    b.cube("silo_glow", (sx - 3.5, 17.0, sz - 0.7), (sx - 3.2, 19.0, sz + 0.7), "glow_cyan", side, hide={"down", "up"})
    # pinwheel feed pipe from the silo top to the drum mouth
    b.pipe_run("feed", [(sx, 31.0, sz), (sx, 34.0, sz), (3.4, 34.0, sz), (3.4, 34.0, -3.4), (3.4, 31.6, -3.4)],
               0.9, "copper", "dark_steel", 8, side)
    # ---- 4-fold -----------------------------------------------------------------------------------
    b.m.radial4([side, rb], ("_e", "_s", "_w"))
    b.cube("spider_x", (-4.8, 34.4, -0.7), (4.8, 36.0, 0.7), "dark_steel", fr)
    b.cube("spider_z", (-0.7, 34.0, -4.8), (0.7, 35.6, 4.8), "dark_steel", fr)
    industrial_status_mast(b, 0, 0, 36.0)
    # ---- animation --------------------------------------------------------------------------------
    b.spin("drum", "y", 4.0)
    for n in ("pin_n", "pin_n_e", "pin_n_s", "pin_n_w"):
        b.spin(n, "y", 1.0, -1)
    b.input_bones(["bags_n", "bags_n_e", "bags_n_s", "bags_n_w"])
    b.output_bones(["drum"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
