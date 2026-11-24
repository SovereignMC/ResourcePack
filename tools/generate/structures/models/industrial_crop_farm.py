#!/usr/bin/env python3
"""Industrial crop farm (structure_industrial_crop_farm), 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_crop_farm.py

A truss irrigation tower with a water tank, a turning sprinkler arm and four wind rotors in the middle, ringed by four
steel hydroponic trays (pinwheel) with swaying wheat and a grow-light gantry each.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_crop_farm.bbmodel")
Y0 = 3.4


def build():
    b = Builder("industrial_crop_farm", run_length=4.0)
    industrial_plinth(b)
    fr = "frame"
    # ---- central tower -------------------------------------------------------------------------
    b.group("tower", parent=fr)
    b.cube("tw_foot", (-4.6, Y0, -4.6), (4.6, 5.4, 4.6), {"up": "dark_steel", "*": "steel_plate"}, "tower")
    b.cube("tw_foot_band", (-4.8, 4.0, -4.8), (4.8, 4.8, 4.8), "hazard_stripe", "tower", hide={"up", "down"})
    b.truss("tw", -3.2, -3.2, 3.2, 3.2, 5.4, 27.0, "steel_plate", 1.2, True, "tower", "dark_steel")
    b.cube("tw_deck", (-4.4, 27.0, -4.4), (4.4, 28.0, 4.4), "grate", "tower")
    b.cylinder("tw_tank", 0, 0, 28.0, 34.0, 4.0, "galvanized", 12, "tower")
    b.cylinder("tw_tank_band", 0, 0, 30.0, 31.2, 4.5, "hazard_stripe", 12, "tower")
    b.cylinder("tw_tank_band2", 0, 0, 33.0, 34.0, 4.4, "copper", 12, "tower")
    b.cylinder("tw_tank_top", 0, 0, 34.0, 34.8, 3.0, "dark_steel", 12, "tower", cap_mat="water")
    b.cube("tw_gauge", (-0.8, 29.0, -4.6), (0.8, 33.0, -4.2), "glow_cyan", "tower", hide={"down", "up"})
    # sprinkler arm (spins) just under the deck
    sp = b.group("sprinkler", parent=fr, origin=(0, 14.0, 0))
    b.cube("sp_hub", (-1.6, 13.0, -1.6), (1.6, 15.0, 1.6), "brass", sp)
    b.cube("sp_arm_x", (-8.4, 13.6, -0.5), (8.4, 14.4, 0.5), "copper", sp)
    b.cube("sp_arm_z", (-0.5, 13.6, -8.4), (0.5, 14.4, 8.4), "copper", sp)
    for i, (x, z) in enumerate(((8.4, 0), (-8.4, 0), (0, 8.4), (0, -8.4))):
        b.cube("sp_nozzle%d" % i, (x - 0.7, 12.4, z - 0.7), (x + 0.7, 13.6, z + 0.7), "dark_steel", sp)
        b.cube("sp_drop%d" % i, (x - 0.4, 11.4, z - 0.4), (x + 0.4, 12.4, z + 0.4), "water", sp, hide={"up"})
    # ---- north module -----------------------------------------------------------------------------
    side = b.group("side_n", parent=fr)
    # wind rotor on the tower (fan on a stub axle)
    b.cube("rot_axle", (-0.5, 20.5, -6.2), (0.5, 21.5, -3.2), "dark_steel", side)
    fan = b.fan("rot_n", (0, 21.0, -6.6), 4.6, 4, "z", "warning_paint_yellow", "dark_steel", side, 20)
    # tray
    b.cube("tr_frame", (-14.0, Y0, -14.2), (7.0, 6.4, -7.6), "steel_plate", side)
    b.cube("tr_band", (-14.2, 4.0, -14.4), (7.2, 4.9, -7.4), "hazard_stripe", side, hide={"up", "down"})
    b.cube("tr_rim", (-14.0, 6.4, -14.2), (7.0, 7.0, -7.6), "dark_steel", side, hide={"down"})
    b.cube("tr_soil", (-13.3, 6.4, -13.5), (6.3, 7.1, -8.3), {"up": "dirt", "*": "dirt"}, side, hide={"down"})
    b.cube("tr_water_pipe", (-12.0, 4.8, -7.2), (-10.8, 5.8, -3.8), "copper", side)
    # gantry with grow light
    for nm, x in (("l", -13.6), ("r", 6.2)):
        b.cube("gan_post_" + nm, (x, 7.0, -14.0), (x + 0.8, 20.0, -13.2), "steel_plate", side)
        b.cube("gan_post2_" + nm, (x, 7.0, -8.6), (x + 0.8, 20.0, -7.8), "steel_plate", side)
    b.cube("gan_bar", (-13.8, 19.4, -14.0), (7.0, 20.8, -7.8), {"north": "hazard_stripe", "*": "dark_steel"}, side)
    b.cube("gan_light", (-12.6, 18.8, -13.2), (5.8, 19.4, -8.6), "glow_amber", side, hide={"up"})
    # wheat (swaying): 2 rows x 8
    crop = b.group("crop_n", parent=side, origin=(-3.5, 7.1, -10.9))
    k = 0
    for r, z in enumerate((-12.4, -9.4)):
        for i in range(8):
            x = -12.4 + i * 2.4
            b.cube("wh%d_stalk" % k, (x - 0.4, 7.1, z - 0.4), (x + 0.4, 12.0, z + 0.4), "leaves", crop, hide={"down"})
            b.cube("wh%d_ear" % k, (x - 0.6, 12.0, z - 0.6), (x + 0.6, 14.4, z + 0.6), "brass", crop, hide={"down"})
            k += 1
    # ---- 4-fold --------------------------------------------------------------------------------
    b.m.radial4([side], ("_e", "_s", "_w"))
    b.cube("cap_x", (-3.0, 34.8, -0.7), (3.0, 35.6, 0.7), "dark_steel", fr)
    industrial_status_mast(b, 0, 0, 35.6)
    # ---- animation ------------------------------------------------------------------------------
    b.spin("sprinkler", "y", 4.0)
    for n, ax, d in (("rot_n", "z", 1), ("rot_n_e", "x", 1), ("rot_n_s", "z", -1), ("rot_n_w", "x", -1)):
        b.spin(n, ax, 2.0, d)
    for n, ph in (("crop_n", 0.0), ("crop_n_e", 0.25), ("crop_n_s", 0.5), ("crop_n_w", 0.75)):
        b.oscillate(n, "rotation", "z" if n in ("crop_n", "crop_n_s") else "x", 3.0, 2.0, ph)
    b.input_bones(["sprinkler"])
    b.output_bones(["crop_n", "crop_n_e", "crop_n_s", "crop_n_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
