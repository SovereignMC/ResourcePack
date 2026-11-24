#!/usr/bin/env python3
"""Industrial mud pit (structure_industrial_mud_pit): a bolted concrete basin of churned mud with a paddle mixer on a
central shaft, driven by a gearbox + motor on a gantry, four feed hoppers dropping clay and valve outlets.
4-fold symmetric.

    python3 tools/generate/structures/models/industrial_mud_pit.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_mud_pit.bbmodel")


def rot(x, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def build():
    b = Builder("industrial_mud_pit", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- basin: pinwheel walls, mud ----------------------------------------------------------------------
    b.group("basin", parent="frame")
    b.cube("mud", (-14, Y0, -14), (14, 7.2, 14), {"up": "dirt", "*": "dirt"}, "basin", hide={"down"})
    side = b.group("side_n", parent="frame")
    b.cube("wall", (-16, Y0, -16), (14, 9, -14), "concrete", side)
    b.cube("wall_cap", (-16.3, 9, -16.3), (14.3, 9.8, -13.7), "warning_paint_yellow", side)
    b.cube("wall_band", (-16, 5.4, -16.3), (14, 6.6, -14), "hazard_stripe", side)
    for i, x in enumerate((-12, -4, 4, 12)):
        b.cube("wall_bolt%d" % i, (x - 0.6, 7.2, -16.5), (x + 0.6, 8.4, -16), "galvanized", side)
    # outlet: pipe through the wall with a red valve
    b.pipe_run("outlet", [(-8, Y0 + 2.2, -14), (-8, Y0 + 2.2, -17)], 1.2, "copper", "dark_steel", 8, side)
    b.cube("valve", (-9.2, Y0 + 3.6, -16.8), (-6.8, Y0 + 4.3, -16.2), "warning_paint_red", side)
    b.cube("valve_stem", (-8.3, Y0 + 2.2, -16.7), (-7.7, Y0 + 3.6, -16.3), "dark_steel", side)
    # ---- feed hopper over each side ----------------------------------------------------------------------
    hp = b.group("hop_n", parent="frame")
    b.hopper("hop", 0, -9.8, 16, 24, 4.2, 1.5, "galvanized", "warning_paint_yellow", 8, hp)
    b.cylinder("hop_spout", 0, -9.8, 11, 16, 1.2, "dark_steel", 8, hp)
    for i, x in enumerate((-3.8, 3.8)):
        b.cube("hop_leg%d" % i, (x - 0.5, 9.8, -14.8), (x + 0.5, 21, -13.8), "steel_plate", hp, hide={"down"})
    b.cube("hop_arm", (-4.3, 20, -14.8), (4.3, 21.2, -13.6), "dark_steel", hp)
    b.cube("hop_brace", (-0.5, 20, -14.8), (0.5, 21.2, -13), "dark_steel", hp)
    b.cube("hop_load", (-3, 24, -12.8), (3, 24.8, -6.8), "rusted_steel", hp, hide={"down"})
    pour = b.group("pour_n", parent="frame", origin=(0, 11, -9.8))
    b.cube("pour_s", (-0.6, 7.6, -10.4), (0.6, 11, -9.2), "dirt", pour)

    # ---- mixer -------------------------------------------------------------------------------------------
    b.group("mixer", parent="frame", origin=(0, 10, 0))
    m = "mixer"
    b.cylinder("shaft", 0, 0, 5, 28, 1.5, "galvanized", 8, m)
    b.cylinder("shaft_hub", 0, 0, 7.6, 9.6, 2.6, "dark_steel", 8, m)
    b.cylinder("shaft_band", 0, 0, 14, 15, 1.9, "brass", 8, m)
    p0 = b.cube("padd_arm", (1.5, 8, -0.8), (11.6, 9.2, 0.8), "steel_plate", m)
    p1 = b.cube("padd_blade", (9.4, 4.6, -2.6), (10.8, 8, 2.6), "rusted_steel", m)
    p2 = b.cube("padd_tip", (8.6, 8.4, -0.5), (9.0, 11, 0.5), "dark_steel", m)
    p3 = b.cube("padd_haz", (3.6, 9.2, -0.8), (5.4, 9.5, 0.8), "hazard_stripe", m, hide={"down"})
    b.m.radial4([p0, p1, p2, p3], ("_1", "_2", "_3"))

    # ---- gantry + drive ----------------------------------------------------------------------------------
    for i, (x, z) in enumerate(((-14.2, -14.2), (14.2, -14.2), (14.2, 14.2), (-14.2, 14.2))):
        b.cube("gp%d" % i, (x - 0.9, 9.8, z - 0.9), (x + 0.9, 26, z + 0.9), "steel_plate", "frame", hide={"down"})
        b.cube("gp_haz%d" % i, (x - 1.1, 10.4, z - 1.1), (x + 1.1, 12.4, z + 1.1), "hazard_stripe", "frame")
    b.beam("gx", (-15, 27, 0), (15, 27, 0), 2.2, 2.2, "steel_plate", "I", "frame")
    b.beam("gz1", (0, 27, -15), (0, 27, -1.1), 2.2, 2.2, "steel_plate", "I", "frame")
    b.beam("gz2", (0, 27, 1.1), (0, 27, 15), 2.2, 2.2, "steel_plate", "I", "frame")
    edge = b.group("edge_n", parent="frame")
    b.cube("ge", (-15.8, 25.4, -15.8), (14, 26.8, -13.6), "dark_steel", edge)
    b.cube("ge_haz", (-12, 26.8, -15.8), (-6, 27.2, -13.6), "hazard_stripe", edge, hide={"down"})
    b.cube("ge_lamp", (-1, 26.8, -15.2), (1, 27.8, -14.2), "glow_amber", edge, hide={"down"})
    b.cube("gearbox", (-4.4, 28, -4.4), (4.4, 33, 4.4), "dark_steel", "frame")
    b.cube("gearbox_haz", (-4.7, 29.2, -4.7), (4.7, 30.4, 4.7), "hazard_stripe", "frame")
    b.cylinder("motor", 0, 0, 33, 38, 3.2, "steel_plate", 8, "frame")
    b.cylinder("motor_band", 0, 0, 34.4, 35.4, 3.6, "copper", 8, "frame")
    b.cylinder("motor_cap", 0, 0, 38, 38.6, 2.2, "dark_steel", 8, "frame")
    mp = b.group("mpanel_n", parent="frame")
    b.cube("gb_glow", (-1.6, 30.6, -4.9), (1.6, 32.4, -4.4), "glow_amber", mp, hide={"up", "down"})

    # ---- 4-fold ------------------------------------------------------------------------------------------
    for g in (side, hp, pour, edge, mp):
        b.m.radial4([g], ("_e", "_s", "_w"))
    # ---- animation ---------------------------------------------------------------------------------------
    b.spin("mixer", "y", 2.0)
    names = ["", "_e", "_s", "_w"]
    for k, sfx in enumerate(names):
        b.rise("pour_n" + sfx, -3.0, 1.0, phase=0.25 * k, scale_from=1.0, scale_to=0.5)
        x, z = rot(6.2, -6.2, k)
        b.smoke("mb%d" % k, x, 7.2, z, puffs=2, rise=1.6, period=2.0, size=1.6, group="basin", mat="dirt")
        x, z = rot(-6.0, 5.0, k)
        b.smoke("mc%d" % k, x, 7.2, z, puffs=2, rise=1.4, period=4.0, size=1.4, group="basin", mat="dirt")
    b.input_bones(["hop_n", "hop_n_e", "hop_n_s", "hop_n_w"])
    b.output_bones(["side_n", "side_n_e", "side_n_s", "side_n_w"])
    industrial_status_mast(b, 0, 0, 38.6)
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
