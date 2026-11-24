#!/usr/bin/env python3
"""Industrial steam power plant (structure_industrial_power_plant), 4-fold symmetric.

Central vertical boiler drum with a pressure gauge on every side; a turbine-generator set with a spinning flywheel,
steam line and insulator pylons with a sparking wire on each side; brick furnace + coal hopper + tall smoke stack in
every corner.

    python3 tools/generate/structures/models/industrial_power_plant.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_power_plant.bbmodel")
SUF = ("", "_e", "_s", "_w")
Y0 = 3.4


def build():
    b = Builder("industrial_power_plant", run_length=4.0)
    industrial_plinth(b)
    F = "frame"
    # ---- boiler -------------------------------------------------------------------------------
    b.group("boiler", parent=F)
    B = "boiler"
    b.cylinder("b_foot", 0, 0, Y0, Y0 + 1.6, 7.6, "dark_steel", 12, B)
    b.tank("b_drum", 0, 0, Y0 + 1.6, 22, 6.6, "steel_plate", "copper", 12, 3, B)
    b.cylinder("b_haz", 0, 0, Y0 + 1.6, Y0 + 3.4, 6.9, "hazard_stripe", 12, B)
    b.cylinder("b_dome_cap", 0, 0, 24, 25.2, 2.6, "dark_steel", 8, B)
    b.cylinder("b_collar", 0, 0, 24.8, 26, 3.4, "copper", 8, B)
    # ---- side module (north): turbine set, steam line, pylons, gauge -------------------------------
    side = b.group("side", parent=F)
    b.cube("t_base", (-5.6, Y0, -15.4), (5.6, Y0 + 2.4, -7.6), "dark_steel", side)
    b.cube("t_base_haz", (-5.8, Y0, -15.6), (5.8, Y0 + 0.9, -15.3), "hazard_stripe", side)
    b.pipe("t_drum", (0, 9.4, -11.2), 7.4, 4.0, "z", "galvanized", 12, side)
    for i, z in enumerate((-14.0, -8.4)):
        b.pipe("t_ring%d" % i, (0, 9.4, z), 1.0, 4.5, "z", "copper", 12, side)
    b.cube("t_saddle_a", (-3, Y0+ 2.4, -13.2), (3, 5.6, -12.2), "steel_plate", side)
    b.cube("t_saddle_b", (-3, Y0 + 2.4, -10.2), (3, 5.6, -9.2), "steel_plate", side)
    b.cube("t_cover", (-1.4, 13.2, -12.6), (1.4, 14.4, -9.8), "dark_steel", side)
    fw = b.gear("flywheel", (0, 9.4, -15.9), 4.6, 1.6, 12, "z", "dark_steel", "steel_plate", "brass", side)
    b.cube("fw_guard_t", (-5.2, 14.4, -16.9), (5.2, 15.2, -14.8), "warning_paint_yellow", side)
    b.cube("fw_guard_l", (-5.2, 5.8, -16.9), (-4.4, 14.4, -14.8), "warning_paint_yellow", side)
    b.cube("fw_guard_r", (4.4, 5.8, -16.9), (5.2, 14.4, -14.8), "warning_paint_yellow", side)
    b.pipe_run("steam", [(0, 15.6, -6.4), (0, 15.6, -11.2), (0, 14.4, -11.2)], 0.9, "copper", "dark_steel", 8, side)
    b.cube("gauge_box", (-1.8, 17, -7.6), (1.8, 20.6, -6.6), "dark_steel", side)
    b.cube("gauge_glow", (-1.2, 17.8, -8.0), (1.2, 19.8, -7.6), "glow_amber", side, hide={"down", "up"})
    b.cube("gauge_hood", (-2, 20.4, -8.4), (2, 21, -6.4), "warning_paint_yellow", side)
    # insulator pylons + wire + spark
    for sx, nm in ((-1, "l"), (1, "r")):
        x = 7.3 * sx
        b.cube("ins_%s_base" % nm, (x - 1.2, Y0, -12.8), (x + 1.2, Y0 + 1.2, -11.2), "dark_steel", side)
        b.cube("ins_%s_post" % nm, (x - 0.5, Y0 + 1.2, -12.3), (x + 0.5, 18.4, -11.7), "galvanized", side)
        for i, y in enumerate((8, 10.6, 13.2, 15.8)):
            b.cube("ins_%s_d%d" % (nm, i), (x - 1.3, y, -13), (x + 1.3, y + 0.6, -11), "brass", side)
        b.cube("ins_%s_cap" % nm, (x - 0.9, 18.4, -12.6), (x + 0.9, 19.2, -11.4), "dark_steel", side)
    b.cube("wire", (-7.4, 18.5, -12.2), (7.4, 18.9, -11.8), "copper", side)
    sp = b.group("spark", parent=side, origin=(0, 19.7, -12))
    b.cube("spark_core", (-0.9, 18.9, -12.9), (0.9, 20.7, -11.1), "glow_cyan", sp)
    b.cube("spark_arc_l", (-3.6, 19.0, -12.3), (-0.9, 19.6, -11.7), "glow_cyan", sp)
    b.cube("spark_arc_r", (0.9, 19.0, -12.3), (3.6, 19.6, -11.7), "glow_cyan", sp)
    # ---- corner module (NE): furnace, hopper, stack ------------------------------------------
    cor = b.group("corner", parent=F)
    b.cube("f_block", (9.6, Y0, -15.6), (15.8, 10.6, -9.6), {"up": "dark_steel", "*": "brick"}, cor)
    b.cube("f_cornice", (9.3, 10.6, -15.9), (16.1, 11.4, -9.3), "dark_steel", cor)
    b.cube("f_base", (9.3, Y0, -15.9), (16.1, Y0 + 1.0, -9.3), "dark_steel", cor)
    b.cube("f_door", (11.6, 5.0, -15.9), (14.4, 8.4, -15.6), "dark_steel", cor, hide={"down"})
    b.cube("f_glow", (12.0, 5.5, -16.2), (14.0, 7.5, -15.9), "glow_amber", cor, hide={"down"})
    b.cube("f_door2", (9.3, 5.0, -14.4), (9.6, 8.4, -11.6), "dark_steel", cor, hide={"down"})
    b.chimney("stack", 13.6, -13.6, 11.4, 37, 2.6, 1.9, "steel_plate", "dark_steel", 8, cor)
    b.cylinder("stack_haz", 13.6, -13.6, 20, 21.4, 2.5, "hazard_stripe", 8, cor)
    b.cylinder("stack_band", 13.6, -13.6, 29, 30, 2.3, "copper", 8, cor)
    b.hopper("hopper", 10.9, -10.9, 11.4, 15.4, 1.9, 0.8, "galvanized", "dark_steel", 8, cor)
    b.cube("hopper_chute", (10.4, 10.8, -11.4), (11.4, 11.6, -10.4), "dark_steel", cor)
    b.radial4([side], ("_e", "_s", "_w"))
    b.radial4([cor], ("_e", "_s", "_w"))
    industrial_status_mast(b, 0, 0, 26)
    # ---- animation ---------------------------------------------------------------------------
    for k, s in enumerate(SUF):
        sg = side + s
        b.spin("flywheel" + s, "z" if k % 2 == 0 else "x", 1.0, 1 if k < 2 else -1)
        b.pulse_scale("spark" + s, 0.5, 1.4, 0.5, phase=0.15 * k)
        x, z = (13.6, -13.6)
        for _ in range(k):
            x, z = -z, x
        b.smoke("c%d" % k, x, 37.5, z, puffs=3, rise=10, period=4.0, size=2.8, group="corner" + s)
    b.input_bones(["hopper" + s for s in SUF[:1]] and ["corner" + s for s in SUF])
    b.output_bones(["spark" + s for s in SUF])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
