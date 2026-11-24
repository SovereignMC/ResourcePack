#!/usr/bin/env python3
"""Industrial deep mine (structure_industrial_deep_mine): a steel drilling derrick with a rotary table, a spinning
kelly and a bobbing travelling block, four diesel power packs in the corners and four mud tanks on the sides.
4-fold symmetric.

    python3 tools/generate/structures/models/industrial_deep_mine.py     # writes bbmodels/structure_industrial_deep_mine.bbmodel
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_deep_mine.bbmodel")


def rot(x, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def build():
    b = Builder("industrial_deep_mine", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- derrick: three tapering lattice sections with safety-yellow landings -------------------------
    b.group("derrick", parent="frame")
    d = "derrick"
    b.truss("d1", -7, -7, 7, 7, Y0, 17, "steel_plate", 1.4, True, d, "warning_paint_yellow")
    b.truss("d2", -6, -6, 6, 6, 17, 29, "steel_plate", 1.2, True, d, "warning_paint_yellow")
    b.truss("d3", -5, -5, 5, 5, 29, 39, "steel_plate", 1.2, True, d, "warning_paint_yellow")
    # landing grates inside the lattice
    for i, y in enumerate((17, 29)):
        r = 5.8 - 1.0 * i
        b.cube("deck%d" % i, (-r, y - 0.5, -r), (r, y + 0.2, r), {"up": "grate", "*": "dark_steel"}, d)
    # crown: heavy cap with hazard rim
    b.cube("crown", (-6, 39, -6), (6, 41, 6), "dark_steel", d)
    b.cube("crown_top", (-5.2, 41, -5.2), (5.2, 41.6, 5.2), "steel_plate", d, hide={"down"})
    for i, (x, z) in enumerate(((-5.5, -5.5), (5.5, -5.5), (5.5, 5.5), (-5.5, 5.5))):
        b.cube("crown_corner%d" % i, (x - 0.5, 41, z - 0.5), (x + 0.5, 42.6, z + 0.5), "warning_paint_yellow", d, hide={"down"})
    # cable guides: four taut lines from the crown to the landing
    for i, (x, z) in enumerate(((-2.2, -2.2), (2.2, -2.2), (2.2, 2.2), (-2.2, 2.2))):
        b.cube("line%d" % i, (x - 0.3, 17.5, z - 0.3), (x + 0.3, 39, z + 0.3), "galvanized", d, hide={"down"})
    # ---- crown sheaves (4 gears around the status mast) ------------------------------------------------
    b.group("crown_gear", parent="frame")
    sheaves = []
    for nm, (x, z), ax in (("sh_e", (5.0, 0), "x"), ("sh_w", (-5.0, 0), "x"), ("sh_s", (0, 5.0), "z"), ("sh_n", (0, -5.0), "z")):
        b.cube(nm + "_bracket", (x - 0.8, 41.6, z - 0.8), (x + 0.8, 42.8, z + 0.8), "dark_steel", "crown_gear", hide={"down"})
        sheaves.append((nm, b.gear(nm, (x, 43.9, z), 2.4, 1.6, 8, ax, "dark_steel", "steel_plate", "brass", "crown_gear")))

    # ---- rotary table (spins) and kelly drive (spins) --------------------------------------------------
    b.cylinder("rt_base", 0, 0, Y0, Y0 + 1.6, 6.0, "dark_steel", 8, "frame")
    rt = b.gear("rtable", (0, Y0 + 2.8, 0), 4.6, 2.4, 8, "y", "steel_plate", "warning_paint_yellow", "dark_steel", "frame")
    b.group("kelly", parent="frame", origin=(0, 20, 0))
    b.cube("kelly_bar", (-1.2, Y0 + 3.4, -1.2), (1.2, 36, 1.2), {"*": "hazard_stripe", "up": "dark_steel"}, "kelly", hide={"down"})
    b.cylinder("kelly_collar", 0, 0, Y0 + 8, Y0 + 9.2, 1.9, "brass", 8, "kelly")
    b.cylinder("kelly_collar2", 0, 0, 29.5, 30.7, 1.9, "brass", 8, "kelly")
    # ---- travelling block (bobs) -----------------------------------------------------------------------
    b.group("travel", parent="frame", origin=(0, 25, 0))
    b.cube("blk_body", (-3.4, 23, -3.4), (3.4, 28, 3.4), "dark_steel", "travel")
    b.cube("blk_band", (-3.7, 24.4, -3.7), (3.7, 26.2, 3.7), "hazard_stripe", "travel")
    b.cylinder("blk_swivel", 0, 0, 28, 31, 1.8, "steel_plate", 8, "travel")
    b.cylinder("blk_cap", 0, 0, 31, 32, 2.4, "brass", 8, "travel")
    b.cube("blk_hook", (-0.8, 20.6, -0.8), (0.8, 23, 0.8), "galvanized", "travel", hide={"up"})
    for i, (x, z) in enumerate(((-3.4, 0), (3.4, 0), (0, -3.4), (0, 3.4))):
        b.cube("blk_lug%d" % i, (x - 0.5, 25, z - 0.5), (x + 0.5, 27.5, z + 0.5), "galvanized", "travel", hide={"down"})

    # ---- side module: mud tank, ladder, feed pipe -------------------------------------------------------
    side = b.group("side_n", parent="frame")
    b.cylinder("tank", 0, -11.4, Y0, 15, 3.7, "galvanized", 12, side)
    for i, y in enumerate((6.6, 10.4, 13.8)):
        b.cylinder("tank_band%d" % i, 0, -11.4, y, y + 0.9, 4.2, "dark_steel", 12, side)
    b.cylinder("tank_dome", 0, -11.4, 15, 16.2, 3.2, "steel_plate", 12, side)
    b.cylinder("tank_cap", 0, -11.4, 16.2, 17.2, 1.4, "copper", 8, side)
    b.cylinder("tank_foot", 0, -11.4, Y0, Y0 + 1.2, 4.4, "dark_steel", 12, side)
    b.cube("tank_glow", (-1.4, 8.2, -15.35), (1.4, 12.4, -15.0), "glow_amber", side, hide={"down", "up"})   # level window
    b.cube("tank_glow_f", (-1.8, 7.8, -15.5), (1.8, 12.8, -15.2), "dark_steel", side, hide={"down", "up"})
    b.pipe_run("mud", [(0, Y0 + 2.6, -7.7), (0, Y0 + 2.6, -5.9)], 1.0, "copper", "dark_steel", 8, side)
    b.cube("valve", (-1.3, Y0 + 4.4, -8.9), (1.3, Y0 + 5.0, -8.3), "warning_paint_red", side)
    b.cube("valve_stem", (-0.4, Y0 + 2.6, -8.7), (0.4, Y0 + 4.4, -8.5), "dark_steel", side)
    # railing + ladder on the side of the tank facing the corner slot
    b.ladder("ladder", (3.5, Y0, -11.4), 11, "east", 3.0, "galvanized", side)
    b.rivet_strip("rv", (-2.8, 4.8, -15.0), "north", 5.6, 2.8, 0, "galvanized", side)

    # ---- corner module: diesel power pack -------------------------------------------------------------
    cx = cz = 11.6
    en = b.group("engine", parent="frame")
    b.cube("pk_skid", (cx - 4, Y0, cz - 4), (cx + 4, Y0 + 1.2, cz + 4), "dark_steel", en)
    b.cube("pk_body", (cx - 3.5, Y0 + 1.2, cz - 3.5), (cx + 3.5, Y0 + 9, cz + 3.5), "steel_plate", en)
    b.cube("pk_haz", (cx - 3.7, Y0 + 1.2, cz - 3.7), (cx + 3.7, Y0 + 2.6, cz + 3.7), "hazard_stripe", en)
    b.cube("pk_roof", (cx - 3.9, Y0 + 9, cz - 3.9), (cx + 3.9, Y0 + 10, cz + 3.9), "dark_steel", en)
    # louvre panels on the two inner faces, glowing gauge on the other
    for i, y in enumerate((Y0 + 4.2, Y0 + 5.6, Y0 + 7.0)):
        b.cube("louvre%d" % i, (cx - 3.9, y, cz - 2.2), (cx - 3.5, y + 0.7, cz + 2.2), "dark_steel", en)
        b.cube("louvre%db" % i, (cx - 2.2, y, cz - 3.9), (cx + 2.2, y + 0.7, cz - 3.5), "dark_steel", en)
    b.cube("pk_gauge", (cx - 0.9, Y0 + 6.2, cz - 3.95), (cx + 0.9, Y0 + 8.0, cz - 3.5), "glow_amber", en, hide={"up", "down"})
    # piston rod pushing out of the inner face (x) at the base
    b.group("rod", parent=en, origin=(cx - 3.5, Y0 + 3.4, cz))
    b.cube("rod_bar", (cx - 6.2, Y0 + 2.9, cz - 0.5), (cx - 3.5, Y0 + 3.9, cz + 0.5), "galvanized", "rod")
    b.cube("rod_head", (cx - 6.8, Y0 + 2.5, cz - 1.0), (cx - 6.2, Y0 + 4.3, cz + 1.0), "brass", "rod")
    # radiator fan in a guard ring on the roof
    b.ring("fan_guard", cx, cz, Y0 + 10, Y0 + 11.2, 3.3, 2.7, "warning_paint_yellow", 8, en)
    fan = b.fan("pfan", (cx, Y0 + 10.7, cz), 2.7, 4, "y", "galvanized", "dark_steel", en)
    b.chimney("exh", cx + 2.3, cz + 2.3, Y0 + 10, 24, 1.1, 0.9, "rusted_steel", "dark_steel", 8, en)

    # ---- 4-fold ------------------------------------------------------------------------------------------
    b.m.radial4([side], ("_e", "_s", "_w"))
    b.m.radial4([en], ("_1", "_2", "_3"))
    # ---- animation ---------------------------------------------------------------------------------------
    b.spin("kelly", "y", 1.0)
    b.spin(rt, "y", 4.0, -1)
    b.bob("travel", 3.0, 2.0)
    for nm, g in sheaves:
        b.spin(g, "x" if nm in ("sh_e", "sh_w") else "z", 2.0, 1 if nm in ("sh_e", "sh_s") else -1)
    # rotation k of (x,z)->(-z,x): rod direction (-1,0) -> (0,-1) -> (1,0) -> (0,1)
    dirs = [("x", -1.6), ("z", -1.6), ("x", 1.6), ("z", 1.6)]
    for k, (ax, stroke) in enumerate(dirs):
        sfx = "" if k == 0 else "_%d" % k
        b.piston("rod" + sfx, ax, stroke, 0.5, phase=0.25 * k)
        b.spin("pfan" + sfx, "y", 0.5)
        x, z = rot(cx + 2.3, cz + 2.3, k)
        b.smoke("pk%d" % k, x, 24.2, z, puffs=3, rise=9, period=4.0, size=2.4, group="engine" + sfx)
    b.input_bones(["kelly"])
    b.output_bones(["side_n", "side_n_e", "side_n_s", "side_n_w"])
    industrial_status_mast(b, 0, 0, 41.6)
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
