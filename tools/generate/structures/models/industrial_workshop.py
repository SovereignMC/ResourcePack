#!/usr/bin/env python3
"""Industrial workshop (structure_industrial_workshop): a machining cell, 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_workshop.py   # writes bbmodels/structure_industrial_workshop.bbmodel

A central tool-changer carousel (rotating drum of tool holders) stands on a square bench with a vise on each side.
In front of every side sits a lathe (spinning chuck + work piece) with a tool chest, and a drill press with a
descending spinning bit stands in every corner. The north side and the north-east drill are built once and cloned.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_workshop.bbmodel")
SUF = ("_e", "_s", "_w")
NAMES = ["", "_e", "_s", "_w"]


def rot_pt(x, y, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, y, z


def build():
    b = Builder("industrial_workshop", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- bench + carousel ----------------------------------------------------------------------
    b.group("bench", parent="frame")
    be = "bench"
    b.cube("bench_body", (-6.6, Y0, -6.6), (6.6, 10.8, 6.6), "dark_steel", be)
    b.cube("bench_top", (-7.6, 10.8, -7.6), (7.6, 12.0, 7.6), "steel_plate", be)
    b.cube("bench_foot", (-7.2, Y0, -7.2), (7.2, Y0 + 1.2, 7.2), "steel_plate", be)
    b.cube("bench_haz", (-6.8, 8.2, -6.8), (6.8, 9.2, 6.8), "hazard_stripe", be)
    b.cylinder("car_base", 0, 0, 12.0, 14.0, 5.4, "steel_plate", 8, be)
    car = b.group("carousel", parent="frame", origin=(0, 20, 0))
    b.cylinder("car_drum", 0, 0, 14.0, 26.0, 4.2, "galvanized", 8, car)
    b.cylinder("car_band", 0, 0, 19.4, 20.6, 4.6, "dark_steel", 8, car)
    b.cylinder("car_top", 0, 0, 26.0, 27.2, 5.0, "hazard_stripe", 8, car)
    b.cylinder("car_hub", 0, 0, 27.2, 29.2, 1.5, "brass", 8, car)
    for i in range(8):
        phi = i * 45
        m = "brass" if i % 2 else "copper"
        b.cube("tool%d" % i, (4.1, 15.0, -0.7), (5.9, 25.0, 0.7), "steel_plate", car, rotation=(0, phi, 0), origin=(0, 20, 0))
        b.cube("tool_tip%d" % i, (5.0, 14.2, -0.45), (5.6, 15.0, 0.45), m, car, rotation=(0, phi, 0), origin=(0, 20, 0))
        b.cube("tool_glow%d" % i, (4.0, 25.0, -0.5), (4.6, 25.8, 0.5), "glow_amber", car, rotation=(0, phi, 0), origin=(0, 20, 0), hide={"down"})
    industrial_status_mast(b, 0, 0, 29.2)

    # ---- north side: vise, drawer panel, lathe, tool chest -------------------------------------
    s = b.group("side_n", parent="frame")
    b.panel("drawer", (-4, 5.0, -6.6), 8, 3.4, "north", "galvanized", "dark_steel", group=s)
    b.cube("vise_body", (4.2, 12.0, -7.2), (7.0, 14.6, -4.6), "rusted_steel", s)
    b.cube("vise_jaw", (4.4, 14.6, -7.4), (6.8, 15.6, -6.6), "dark_steel", s)
    b.cube("vise_screw", (5.2, 12.8, -8.6), (6.0, 13.6, -7.2), "brass", s)
    LZ = -10.6
    b.cube("lathe_bed", (-7.2, 8.4, LZ - 2.4), (7.2, 10.2, LZ + 2.4), "dark_steel", s)
    for sgn, nm in ((-1, "l"), (1, "r")):
        x0, x1 = sorted((sgn * 4.0, sgn * 7.2))
        b.cube("lathe_cab_" + nm, (x0, Y0, LZ - 2.4), (x1, 8.4, LZ + 2.4), "steel_plate", s)
        b.cube("lathe_cab_haz_" + nm, (x0 - 0.1, 4.4, LZ - 2.5), (x1 + 0.1, 5.2, LZ + 2.5), "hazard_stripe", s)
    b.cube("headstock", (-7.2, 10.2, LZ - 2.4), (-2.8, 15.4, LZ + 2.4), "rusted_steel", s)
    b.cube("headstock_cap", (-7.4, 15.4, LZ - 2.6), (-2.6, 16.2, LZ + 2.6), "steel_plate", s)
    b.cube("headstock_light", (-6.0, 12.0, LZ - 2.6), (-4.0, 13.4, LZ - 2.4), "glow_amber", s, hide={"down", "up"})
    b.cube("tailstock", (4.0, 10.2, LZ - 1.4), (6.8, 14.2, LZ + 1.4), "steel_plate", s)
    b.cube("tailstock_pin", (3.0, 12.0, LZ - 0.4), (4.0, 12.8, LZ + 0.4), "brass", s)
    b.cube("toolpost", (-0.6, 10.2, LZ + 1.0), (1.6, 12.4, LZ + 2.4), "copper", s)
    b.cube("toolpost_tip", (0.0, 11.0, LZ + 0.2), (0.8, 11.6, LZ + 1.0), "galvanized", s)
    wk = b.group("work_n", parent=s, origin=(-1.0, 12.4, LZ))
    b.gear("chuck_n", (-2.0, 12.4, LZ), 1.9, 1.2, 6, "x", "dark_steel", "steel_plate", "brass", wk)
    b.pipe("work_bar", (0.7, 12.4, LZ), 5.6, 0.9, "x", "galvanized", 8, wk)
    b.cube("work_mark", (-0.2, 13.2, LZ - 0.4), (0.6, 13.5, LZ + 0.4), "copper", wk)
    tc = b.group("chest_n", parent=s, origin=(-3, 5, -14.6))
    b.cube("chest", (-5.4, Y0, -15.8), (-0.6, 7.4, -13.2), "warning_paint_red", tc)
    b.cube("chest_lid", (-5.6, 7.4, -16.0), (-0.4, 8.0, -13.0), "dark_steel", tc)
    b.cube("chest_handle", (-3.6, 6.0, -16.2), (-2.4, 6.6, -15.8), "brass", tc)
    b.cube("chest_latch", (-3.2, 6.8, -16.1), (-2.8, 7.4, -15.8), "galvanized", tc)
    b.m.radial4([s], SUF)

    # ---- drill press (north-east corner) ---------------------------------------------------------
    CX, CZ = 11.5, -11.5
    dr = b.group("drill", parent="frame")
    b.cube("dr_base", (CX - 2.8, Y0, CZ - 2.8), (CX + 2.8, 5.0, CZ + 2.8), "dark_steel", dr)
    b.cube("dr_col", (CX - 1.0, 5.0, CZ - 1.0), (CX + 1.0, 21.0, CZ + 1.0), "galvanized", dr)
    b.cube("dr_col_haz", (CX - 1.3, 8.0, CZ - 1.3), (CX + 1.3, 9.0, CZ + 1.3), "hazard_stripe", dr)
    b.cube("dr_table", (CX - 2.6, 9.4, CZ - 2.6), (CX + 2.6, 10.4, CZ + 2.6), "steel_plate", dr)
    b.cube("dr_work", (CX - 1.0, 10.4, CZ - 1.0), (CX + 1.0, 11.6, CZ + 1.0), "copper", dr)
    b.cube("dr_head", (CX - 2.6, 18.0, CZ - 2.6), (CX + 2.6, 23.0, CZ + 2.6), "rusted_steel", dr)
    b.cube("dr_head_cap", (CX - 2.8, 23.0, CZ - 2.8), (CX + 2.8, 23.8, CZ + 2.8), "dark_steel", dr)
    b.cylinder("dr_motor", CX, CZ, 23.8, 26.0, 1.6, "copper", 8, dr)
    b.cube("dr_light", (CX - 1.0, 19.6, CZ - 2.8), (CX + 1.0, 21.4, CZ - 2.6), "glow_amber", dr, hide={"down", "up"})
    sp = b.group("spindle", parent=dr, origin=(CX, 18, CZ))
    b.cylinder("dr_chuck", CX, CZ, 16.4, 18.0, 0.9, "dark_steel", 8, sp)
    b.cylinder("dr_bit", CX, CZ, 12.4, 16.4, 0.35, "galvanized", 4, sp)
    b.m.radial4([dr], ("_1", "_2", "_3"))

    # ---- animation -------------------------------------------------------------------------
    b.spin("carousel", "y", 4.0)
    for k, nm in enumerate(NAMES):
        b.spin("work_n" + nm, "x" if k % 2 == 0 else "z", 0.5, 1 if k < 2 else -1)
        sfx = ["", "_1", "_2", "_3"][k]
        b.piston("spindle" + sfx, "y", -2.0, 2.0, phase=0.25 * k)
        b.spin("spindle" + sfx, "y", 0.5)
    b.input_bones(["carousel"])
    b.output_bones(["chest_n" + n for n in NAMES])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
