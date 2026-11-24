#!/usr/bin/env python3
"""Industrial munitions factory (structure_industrial_munitions_factory), 4-fold symmetric.

Four-column hydraulic press with a reciprocating ram in the centre; four conveyor arms feed shells to crates at the
ends; a red accumulator tank with a hydraulic line in every corner; beacons on the crown.

    python3 tools/generate/structures/models/industrial_munitions_factory.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_munitions_factory.bbmodel")
SUF = ("", "_e", "_s", "_w")
Y0 = 3.4


def shell(b, name, x, z, y0, grp, h=5.0):
    """Upright artillery shell: brass casing, yellow band, tapered red warhead."""
    b.cylinder(name + "_case", x, z, y0, y0 + h, 1.15, "brass", 8, grp, cap_mat="dark_steel")
    b.cylinder(name + "_band", x, z, y0 + h - 1.4, y0 + h - 0.8, 1.3, "warning_paint_yellow", 8, grp)
    b.taper(name + "_nose", x, z, y0 + h, y0 + h + 2.6, 1.15, 0.45, "warning_paint_red", 3, 8, grp)


def build():
    b = Builder("industrial_munitions_factory", run_length=4.0)
    industrial_plinth(b)
    F = "frame"

    # ---- press: bed, columns, crown, master cylinder --------------------------------------------
    b.cube("bed", (-7, Y0, -7), (7, 7, 7), {"up": "steel_plate", "*": "dark_steel"}, F)
    b.cube("bed_plate", (-5.2, 7, -5.2), (5.2, 7.5, 5.2), {"up": "galvanized", "*": "steel_plate"}, F)
    b.cube("bed_foot", (-7.6, Y0, -7.6), (7.6, Y0 + 1.2, 7.6), "steel_plate", F)
    col = b.group("col", parent=F)
    cx = cz = -5.8
    b.cube("col_post", (cx - 1.4, 7, cz - 1.4), (cx + 1.4, 29, cz + 1.4), "steel_plate", col)
    for i, y in enumerate((11, 17, 23)):
        b.cube("col_rib%d" % i, (cx - 1.8, y, cz - 1.8), (cx + 1.8, y + 1, cz + 1.8), "dark_steel", col)
    b.cube("col_shoe", (cx - 2, 7, cz - 2), (cx + 2, 8.2, cz + 2), "dark_steel", col)
    b.cube("col_cap", (cx - 1.9, 29, cz - 1.9), (cx + 1.9, 30.4, cz + 1.9), "warning_paint_yellow", col)
    for i, (dx, dz) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        b.cube("col_bolt%d" % i, (cx + dx * 1.4 - 0.4 + (0.4 if dx > 0 else 0), 7.8, cz + dz * 1.4 - 0.4 + (0.4 if dz > 0 else 0)),
               (cx + dx * 1.4 + 0.4 + (0.4 if dx > 0 else 0), 8.4, cz + dz * 1.4 + 0.4 + (0.4 if dz > 0 else 0)), "galvanized", col)
    b.cube("crown", (-9, 30.4, -9), (9, 34, 9), {"up": "steel_plate", "*": "dark_steel"}, F)
    b.cube("crown_top", (-7, 34, -7), (7, 35, 7), "steel_plate", F)
    band = b.cube("crown_band", (-8.6, 31.0, -9.5), (8.6, 33.4, -9), "hazard_stripe", F)
    b.cylinder("master", 0, 0, 35, 40, 3.4, "galvanized", 12, F, cap_mat="dark_steel")
    b.cylinder("master_collar", 0, 0, 35, 36.2, 4.2, "dark_steel", 12, F)
    b.cylinder("master_ring", 0, 0, 38, 38.8, 3.9, "copper", 12, F)
    b.cylinder("master_cap", 0, 0, 40, 41.4, 2.2, "copper", 8, F)
    # ram (animated)
    b.group("ram", parent=F, origin=(0, 29, 0))
    b.cylinder("ram_rod", 0, 0, 21, 30.4, 1.3, "galvanized", 8, "ram")
    b.cube("ram_die", (-4.6, 17, -4.6), (4.6, 20.4, 4.6), "dark_steel", "ram")
    b.cube("ram_die_face", (-3.6, 16.2, -3.6), (3.6, 17, 3.6), "steel_plate", "ram")
    b.cube("ram_stripe", (-4.8, 18.2, -4.8), (4.8, 19.2, 4.8), "hazard_stripe", "ram")
    # shell under the press
    pg = b.group("pressed", parent=F)
    shell(b, "pshell", 0, 0, 7.5, pg, 5.5)

    # ---- one arm (+X): conveyor, shells, crate, corner accumulator + pipe, beacon -------------------
    arm = b.group("arm", parent=F)
    b.conveyor("arm", 7, 0, 12.6, 0, 6.6, 5.4, "rubber", "steel_plate", arm)
    b.cube("arm_haz_a", (7, 7.6, -2.9), (12.6, 8.2, -2.6), "warning_paint_yellow", arm)
    b.cube("arm_haz_b", (7, 7.6, 2.6), (12.6, 8.2, 2.9), "warning_paint_yellow", arm)
    sg = b.group("shells", parent=arm)
    for i, x in enumerate((8.4, 10.8)):
        shell(b, "ashell%d" % i, x, 0, 7.0, sg, 4.0)
    crate = b.group("crate", parent=arm, origin=(14.4, Y0, 0))
    b.cube("crate_box", (12.6, Y0, -3.6), (16, 6.2, 3.6), {"up": "dark_steel", "*": "wood_plank"}, crate)
    b.cube("crate_strap_a", (12.5, Y0, -2.4), (16.1, 6.3, -1.8), "steel_plate", crate)
    b.cube("crate_strap_b", (12.5, Y0, 1.8), (16.1, 6.3, 2.4), "steel_plate", crate)
    b.cube("crate_label", (13.6, 4.4, 3.6), (15, 5.6, 3.9), "warning_paint_yellow", crate)
    for i, z in enumerate((-2.2, 0, 2.2)):
        shell(b, "cshell%d" % i, 14.4, z, 6.2, crate, 3.0)
    # corner accumulator (+X,+Z) + hydraulic line to the column
    acc = b.group("acc", parent=arm)
    b.tank("acc_tank", 11, 11, Y0, 12, 3.4, "warning_paint_red", "dark_steel", 12, 2, acc)
    b.cylinder("acc_foot", 11, 11, Y0, Y0 + 1.2, 4.0, "dark_steel", 12, acc)
    b.cube("acc_gauge", (7.0, 8.4, 10.2), (7.9, 10.6, 11.8), "glow_amber", acc, hide={"down"})
    b.cube("acc_gauge_f", (6.8, 8.0, 9.8), (7.2, 11, 12.2), "dark_steel", acc, hide={"down"})
    b.pipe_run("acc_pipe", [(11, 14.2, 11), (11, 16.5, 11), (11, 16.5, 5.8), (7.4, 16.5, 5.8)], 0.8, "copper", "dark_steel", 8, acc)
    b.rivet_strip("acc_riv", (9.2, 5.4, 14.4), "south", 4, 2, 0, "galvanized", acc)
    # beacon on the crown corner
    bc = b.group("beacon", parent=F, origin=(8, 34, 8))
    b.cube("beacon_post", (7.4, 34, 7.4), (8.6, 35.2, 8.6), "dark_steel", bc)
    b.cube("beacon_lamp", (7.2, 35.2, 7.2), (8.8, 37, 8.8), "glow_red", bc)
    b.cube("beacon_cap", (7.0, 37, 7.0), (9.0, 37.6, 9.0), "steel_plate", bc)

    # ---- 4-fold ------------------------------------------------------------------------------------
    b.m.radial4([col], ("_1", "_2", "_3"))
    b.m.radial4([band], ("_e", "_s", "_w"))
    b.m.radial4([arm], ("_e", "_s", "_w"))
    b.m.radial4([bc], ("_e", "_s", "_w"))
    industrial_status_mast(b, 0, 0, 41.4)

    # ---- animation ---------------------------------------------------------------------------------
    b.piston("ram", "y", -5.0, 2.0)
    for k, s in enumerate(SUF):
        sgn, axis = ((1, "x"), (1, "z"), (-1, "x"), (-1, "z"))[k]
        b._add("shells" + s, "position", axis, "saw", lambda f, sg=sgn: sg * 2.4 * f, 2.0)
        b.pulse_scale("beacon" + s, 0.7, 1.35, 1.0, phase=0.25 * k)
    b.input_bones(["shells" + s for s in SUF])
    b.output_bones(["crate" + s for s in SUF])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
