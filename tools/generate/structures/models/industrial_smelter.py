#!/usr/bin/env python3
"""Industrial blast furnace (structure_industrial_smelter), 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_smelter.py            # writes bbmodels/structure_industrial_smelter.bbmodel
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_smelter.bbmodel")


def rot(x, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def build():
    b = Builder("industrial_smelter", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- central furnace --------------------------------------------------------------- group furnace
    b.group("furnace", parent="frame")
    f = "furnace"
    b.cylinder("hearth", 0, 0, Y0, 11, 8.6, {"*": "dark_steel", "up": "dark_steel"}, 8, f)
    b.cylinder("hearth_foot", 0, 0, Y0, Y0 + 1.6, 9.4, "steel_plate", 8, f)
    for i, y in enumerate((6.4, 9.0)):
        b.cylinder("cool%d" % i, 0, 0, y, y + 1.0, 9.1, "copper", 8, f)
    b.taper("bosh", 0, 0, 11, 15, 8.6, 10, "steel_plate", 4, 8, f)
    b.cylinder("belly", 0, 0, 15, 19, 10, "rusted_steel", 8, f)
    b.cylinder("belly_band", 0, 0, 16.6, 17.6, 10.5, "dark_steel", 8, f)
    b.cylinder("haz_band", 0, 0, 19, 20.2, 10.4, "hazard_stripe", 8, f)
    b.taper("stack", 0, 0, 20.2, 31, 10, 6.5, "steel_plate", 6, 8, f)
    b.cylinder("stack_band", 0, 0, 25, 26, 9, "dark_steel", 8, f)
    b.cylinder("throat", 0, 0, 31, 34, 6.8, "dark_steel", 8, f)
    b.cylinder("throat_band", 0, 0, 32.2, 33.2, 7.3, "copper", 8, f)
    bell = b.group("bell", parent=f, origin=(0, 34, 0))
    b.taper("hopper", 0, 0, 34, 37.4, 6.2, 3.6, "galvanized", 4, 8, bell)
    b.cylinder("hopper_cap", 0, 0, 37.4, 38, 3.2, "dark_steel", 8, bell)
    # bustle ring + tuyeres + sight glasses (per side, built once and rotated)
    b.ring("bustle", 0, 0, 12, 14.4, 11.6, 10.2, "galvanized", 8, f)
    b.ring("bustle_hoop", 0, 0, 14.4, 15, 11.9, 10.0, "dark_steel", 8, f)
    side = b.group("side_n", parent="frame")
    # tap casing, tap hole, cooling frame
    b.cube("tap_casing", (-3.6, Y0, -10.8), (3.6, 9.6, -7.6), "steel_plate", side)
    b.cube("tap_cap", (-4, 9.6, -11.2), (4, 10.4, -7.6), "dark_steel", side)
    b.cube("tap_post_l", (-3.2, 4.0, -11.4), (-1.9, 8.6, -10.8), "brass", side)
    b.cube("tap_post_r", (1.9, 4.0, -11.4), (3.2, 8.6, -10.8), "brass", side)
    b.cube("tap_lintel", (-3.2, 8.2, -11.4), (3.2, 8.9, -10.8), "brass", side)
    b.cube("tap_sill", (-3.2, 3.9, -11.4), (3.2, 4.4, -10.8), "brass", side)
    b.cube("tap_glow", (-1.9, 4.4, -11.0), (1.9, 8.2, -10.5), "glow_amber", side, hide={"down", "up"})
    # spout trough (sloped) and drip lip
    b.cube("spout", (-1.5, 4.0, -14.6), (1.5, 4.9, -11.0), {"up": "glow_amber", "*": "rusted_steel"}, side,
           rotation=(-9, 0, 0), origin=(0, 4.4, -12.8))
    b.cube("spout_wall_l", (-2.1, 3.9, -14.6), (-1.5, 5.4, -11.0), "dark_steel", side, rotation=(-9, 0, 0), origin=(0, 4.4, -12.8))
    b.cube("spout_wall_r", (1.5, 3.9, -14.6), (2.1, 5.4, -11.0), "dark_steel", side, rotation=(-9, 0, 0), origin=(0, 4.4, -12.8))
    # ingot mould tray with hot and cooled ingots
    b.cube("tray_base", (-6, Y0, -15.8), (6, 4.2, -11.6), "dark_steel", side)
    for nm, (a, c) in {"f": ((-6, -15.8), (6, -15)), "b": ((-6, -12.4), (6, -11.6))}.items():
        b.cube("tray_wall_" + nm, (a[0], 4.2, a[1]), (c[0], 5.2, c[1]), "steel_plate", side)
    for nm, (x0, x1) in {"l": (-6, -5.2), "r": (5.2, 6)}.items():
        b.cube("tray_end_" + nm, (x0, 4.2, -15), (x1, 5.2, -12.4), "steel_plate", side)
    for i, (x, m) in enumerate(((-4.4, "glow_amber"), (-1.0, "glow_amber"), (2.4, "galvanized"))):
        b.cube("ingot%d" % i, (x, 4.2, -14.6), (x + 2.8, 5.0, -12.8), {"up": m, "*": "dark_steel"}, side)
    # tuyere stub + sight glass on the bustle ring
    b.cube("tuyere", (-1.2, 12.4, -11.4), (1.2, 14.0, -9.2), "copper", side)
    b.cube("sight", (-0.7, 12.8, -11.9), (0.7, 13.7, -11.4), "glow_amber", side, hide={"down"})
    # ladder on the belly/stack up to the platform
    b.ladder("ladder", (0, 15, -9.3), 10.4, "north", 3.2, "galvanized", side)
    # platform: grate ring, kerb, handrail ring and posts (built once, not rotated)
    b.ring("platform", 0, 0, 25.0, 25.5, 12.0, 7.6, "grate", 8, f)
    b.ring("kerb", 0, 0, 25.5, 26.3, 12.0, 11.4, "warning_paint_yellow", 8, f)
    b.ring("rail_top", 0, 0, 28.6, 29.2, 12.0, 11.4, "warning_paint_yellow", 8, f)
    b.ring("rail_mid", 0, 0, 27.2, 27.7, 12.0, 11.4, "warning_paint_yellow", 8, f)
    for i in range(8):
        a = math.radians(i * 45)
        x, z = 11.7 * math.cos(a), 11.7 * math.sin(a)
        b.cube("rail_post%d" % i, (x - 0.4, 25.5, z - 0.4), (x + 0.4, 29.2, z + 0.4), "warning_paint_yellow", f, hide={"down"})
    # ---- stove module (corner) --------------------------------------------------------------
    st = b.group("stove", parent="frame")
    cx = cz = 12.0
    b.cylinder("st_foot", cx, cz, Y0, Y0 + 1.6, 4.4, "dark_steel", 8, st)
    b.cylinder("st_body", cx, cz, Y0 + 1.6, 23.5, 3.8, "galvanized", 8, st)
    for i, y in enumerate((8, 14, 19)):
        b.cylinder("st_band%d" % i, cx, cz, y, y + 1, 4.1, "dark_steel", 8, st)
    b.cylinder("st_hoop", cx, cz, 22.2, 23.2, 4.1, "copper", 8, st)
    b.taper("st_dome", cx, cz, 23.5, 27.5, 3.8, 1.9, "steel_plate", 3, 8, st)
    d = 2.45
    b.chimney("st_stack", cx + d, cz + d, 22.5, 33, 1.5, 1.1, "rusted_steel", "dark_steel", 8, st)
    b.cube("st_port", (cx - 1.5, 4.6, cz - 4.6), (cx + 1.5, 7.2, cz - 3.4), "dark_steel", st)
    b.cube("st_glow", (cx - 0.9, 5.2, cz - 4.9), (cx + 0.9, 6.6, cz - 4.6), "glow_amber", st, hide={"down"})
    b.cube("st_glow2", (cx - 4.9, 5.2, cz - 0.9), (cx - 4.6, 6.6, cz + 0.9), "glow_amber", st, hide={"down"})
    b.cube("st_port2", (cx - 4.6, 4.6, cz - 1.5), (cx - 3.4, 7.2, cz + 1.5), "dark_steel", st)
    # hot-blast main from the stove top to the middle of the neighbouring side, with a valve stem
    b.pipe_run("main", [(cx, 27.0, cz), (cx, 31.5, cz), (cx, 31.5, 0), (7.2, 31.5, 0)], 1.2, "galvanized", "dark_steel", 8, st)
    b.cube("main_valve", (cx - 1.8, 32.7, 3.0), (cx + 1.8, 34.0, 6.2), "brass", st)
    # duct from the corner towards the bustle ring (rotated 45 deg)
    c = 8.9
    b.cube("duct", (c - 1.7, 12.2, c - 1.0), (c + 1.7, 14.2, c + 1.0), "copper", st, rotation=(0, 45, 0), origin=(c, 13.2, c))
    # ---- 4-fold: rotate the side module and the stove module ------------------------------
    b.m.radial4([side], ("_e", "_s", "_w"))
    b.m.radial4([st], ("_1", "_2", "_3"))
    industrial_status_mast(b, 0, 0, 38.0)
    # ---- animation -------------------------------------------------------------------------
    b.bob("bell", 0.7, 2.0)
    for k in range(4):
        x, z = rot(cx + 2.45, cz + 2.45, k)
        b.smoke("st%d" % k, x, 33.0, z, puffs=3, rise=9, period=4.0, size=2.6, group="stove" + ("" if k == 0 else "_%d" % k))
    b.input_bones(["bell"])
    b.output_bones(["side_n", "side_n_e", "side_n_s", "side_n_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
