#!/usr/bin/env python3
"""Industrial town hall (structure_industrial_town_hall): a steel-and-concrete civic block, 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_town_hall.py   # writes bbmodels/structure_industrial_town_hall.bbmodel

A square hall with a canopied entrance (door, windows, steps) on every side, a roof parapet with four vent stacks,
and a central clock tower with a lit clock face on each side and a rotating twin beacon under the status mast.
Banner poles stand in the four plinth corners. The north side is built once and cloned.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_town_hall.bbmodel")
SUF = ("_e", "_s", "_w")
NAMES = ["", "_e", "_s", "_w"]
# clock hand spin direction (clockwise seen from outside) for N, E, S, W
HAND_DIR = [1, -1, -1, 1]


def rot_pt(x, y, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, y, z


def build():
    b = Builder("industrial_town_hall", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4
    H = 9.5

    # ---- hall body, tower, roof -----------------------------------------------------------------
    b.group("hall", parent="frame")
    h = "hall"
    b.cube("hall_plinth", (-H - 0.3, Y0, -H - 0.3), (H + 0.3, 6.2, H + 0.3), {"*": "concrete", "up": "dark_steel"}, h)
    b.cube("hall_body", (-H, 6.2, -H), (H, 16, H), "steel_plate", h)
    b.cube("hall_haz", (-H - 0.2, 15.0, -H - 0.2), (H + 0.2, 16, H + 0.2), "hazard_stripe", h)
    b.cube("hall_cornice", (-H - 0.7, 16, -H - 0.7), (H + 0.7, 17.4, H + 0.7), "dark_steel", h)
    b.cube("hall_roof", (-H, 17.4, -H), (H, 18.0, H), "concrete", h)
    pil = b.cube("pilaster", (H - 1.6, 6.2, H - 1.6), (H + 0.2, 15.0, H + 0.2), "dark_steel", h)
    b.m.radial4([pil], ("_1", "_2", "_3"))
    # tower
    b.cube("tower", (-4.6, 18.0, -4.6), (4.6, 30, 4.6), "steel_plate", h)
    b.cube("tower_haz", (-4.9, 18.0, -4.9), (4.9, 19.4, 4.9), "hazard_stripe", h)
    b.cube("tower_band", (-4.8, 26.8, -4.8), (4.8, 27.4, 4.8), "dark_steel", h)
    b.cube("tower_cornice", (-5.6, 30, -5.6), (5.6, 31.4, 5.6), "dark_steel", h)
    b.cube("tower_cap", (-4.2, 31.4, -4.2), (4.2, 31.8, 4.2), "steel_plate", h)

    # ---- north side module ---------------------------------------------------------------------
    s = b.group("side_n", parent="frame")
    # door (group) with frame, leaves, light slit
    b.cube("door_frame", (-3.4, 6.2, -H - 0.5), (3.4, 13.4, -H), "dark_steel", s)
    d = b.group("door_n", parent=s, origin=(0, 6.2, -H - 0.5))
    b.cube("door_l", (-2.7, 6.2, -H - 0.9), (-0.15, 12.4, -H - 0.5), "galvanized", d)
    b.cube("door_r", (0.15, 6.2, -H - 0.9), (2.7, 12.4, -H - 0.5), "galvanized", d)
    b.cube("door_haz", (-2.7, 6.2, -H - 1.0), (2.7, 7.4, -H - 0.9), "hazard_stripe", d)
    b.cube("door_light_l", (-2.0, 9.6, -H - 1.0), (-0.7, 11.4, -H - 0.9), "glow_amber", d, hide={"down", "up"})
    b.cube("door_light_r", (0.7, 9.6, -H - 1.0), (2.0, 11.4, -H - 0.9), "glow_amber", d, hide={"down", "up"})
    b.cube("door_bar", (-0.9, 8.6, -H - 1.3), (0.9, 9.0, -H - 0.9), "brass", d)
    # windows
    for sgn, nm in ((-1, "l"), (1, "r")):
        x0, x1 = sorted((sgn * 4.6, sgn * 8.0))
        b.cube("win_frame_" + nm, (x0, 7.6, -H - 0.4), (x1, 13.6, -H), "dark_steel", s)
        b.cube("win_glass_" + nm, (x0 + 0.5, 8.1, -H - 0.7), (x1 - 0.5, 13.1, -H - 0.3), "glass", s, hide={"down", "up"})
        b.cube("win_mull_" + nm, ((x0 + x1) / 2 - 0.2, 8.1, -H - 0.9), ((x0 + x1) / 2 + 0.2, 13.1, -H - 0.3), "dark_steel", s)
        b.cube("win_sill_" + nm, (x0 - 0.3, 7.2, -H - 0.8), (x1 + 0.3, 7.8, -H), "galvanized", s)
    # canopy: slab, yellow edge, two I columns, steps
    b.cube("canopy", (-7.2, 13.6, -14.6), (7.2, 14.6, -H), "steel_plate", s)
    b.cube("canopy_edge", (-7.2, 14.6, -14.8), (7.2, 15.0, -14.4), "warning_paint_yellow", s)
    b.cube("canopy_under", (-6.4, 13.4, -14.2), (6.4, 13.6, -H), "dark_steel", s)
    for sgn, nm in ((-1, "l"), (1, "r")):
        x = sgn * 6.0
        b.cube("col_" + nm, (x - 0.7, Y0, -14.1), (x + 0.7, 13.6, -12.9), "steel_plate", s, hide={"down"})
        b.cube("col_foot_" + nm, (x - 1.2, Y0, -14.5), (x + 1.2, Y0 + 1.2, -12.5), "dark_steel", s)
        b.cube("col_band_" + nm, (x - 0.9, 9.4, -14.3), (x + 0.9, 10.4, -12.7), "hazard_stripe", s)
    b.cube("step1", (-4.8, Y0, -13.4), (4.8, 4.8, -H), "concrete", s)
    b.cube("step2", (-4.2, 4.8, -11.8), (4.2, 6.0, -H), "concrete", s)
    b.cube("step_nose1", (-4.8, 4.2, -13.7), (4.8, 4.8, -13.4), "warning_paint_yellow", s)
    b.cube("step_nose2", (-4.2, 5.4, -12.1), (4.2, 6.0, -11.8), "warning_paint_yellow", s)
    b.rivet_strip("hall_riv", (-8.2, 14.2, -H), "north", 16.4, 2.7, 0, "galvanized", s)
    # clock on the tower: face, frame, ticks, hand
    b.cube("clock_frame", (-3.2, 21.8, -5.4), (3.2, 28.2, -4.6), "dark_steel", s)
    b.cube("clock_face", (-2.7, 22.3, -5.6), (2.7, 27.7, -5.2), "glow_amber", s, hide={"down", "up"})
    for nm, (a, c) in {"t12": ((-0.3, 26.7), (0.3, 27.6)), "t6": ((-0.3, 22.4), (0.3, 23.3)),
                       "t3": ((1.8, 24.7), (2.6, 25.3)), "t9": ((-2.6, 24.7), (-1.8, 25.3))}.items():
        b.cube("clock_" + nm, (a[0], a[1], -5.8), (c[0], c[1], -5.6), "dark_steel", s, hide={"down", "up"})
    hd = b.group("hand_n", parent=s, origin=(0, 25.0, -5.9))
    b.cube("hand", (-0.35, 24.7, -6.3), (0.35, 27.0, -5.9), "dark_steel", hd, hide={"down", "up"})
    b.cube("hand_tail", (-0.35, 23.6, -6.3), (0.35, 24.7, -5.9), "rusted_steel", hd, hide={"down", "up"})
    b.cube("hand_hub", (-0.7, 24.3, -6.5), (0.7, 25.7, -6.1), "brass", hd)
    # roof parapet (north slab) and corner vent stack
    b.cube("parapet", (-H - 0.4, 18.0, -H - 0.4), (H - 0.4, 19.4, -H + 0.8), "dark_steel", s)
    b.cube("parapet_stripe", (-H - 0.4, 19.4, -H - 0.1), (H - 0.4, 19.8, -H + 0.5), "warning_paint_yellow", s)
    b.chimney("vent", -7.0, -6.8, 19.4, 24.5, 1.5, 1.0, "galvanized", "dark_steel", 8, s)
    b.cylinder("vent_band", -7.0, -6.8, 21.0, 21.8, 1.8, "hazard_stripe", 8, s)
    b.m.radial4([s], SUF)
    # ---- beacon + status mast --------------------------------------------------------------------
    bc = b.group("beacon", parent="frame", origin=(0, 31.8, 0))
    b.cube("beacon_arm", (-4.4, 31.8, -0.5), (4.4, 32.4, 0.5), "steel_plate", bc)
    for sgn, nm in ((-1, "a"), (1, "b")):
        b.cube("beacon_lamp_" + nm, (sgn * 4.4 - 0.8, 31.8, -0.8), (sgn * 4.4 + 0.8, 33.4, 0.8), "glow_amber", bc, hide={"down"})
    industrial_status_mast(b, 0, 0, 32.4)
    # ---- banner poles (corners) ---------------------------------------------------------------
    pole = b.group("pole", parent="frame")
    px = -14.2
    b.cube("pole_base", (px - 1.0, 3.8, px - 1.0), (px + 1.0, 5.0, px + 1.0), "dark_steel", pole)
    b.cube("pole_mast", (px - 0.45, 5.0, px - 0.45), (px + 0.45, 28, px + 0.45), "galvanized", pole)
    b.cube("pole_band1", (px - 0.7, 8.0, px - 0.7), (px + 0.7, 9.0, px + 0.7), "hazard_stripe", pole)
    b.cube("pole_band2", (px - 0.7, 14.0, px - 0.7), (px + 0.7, 15.0, px + 0.7), "hazard_stripe", pole)
    b.cube("pole_tip", (px - 0.8, 28, px - 0.8), (px + 0.8, 29.4, px + 0.8), "brass", pole)
    fl = b.group("flag", parent=pole, origin=(px, 24, px))
    b.cube("flag_cloth", (px + 0.5, 20.6, px - 0.25), (px + 6.2, 26.6, px + 0.25), "warning_paint_red", fl)
    b.cube("flag_stripe", (px + 0.5, 22.8, px - 0.3), (px + 6.2, 24.0, px + 0.3), "warning_paint_yellow", fl)
    b.cube("flag_arm", (px + 0.3, 26.2, px - 0.3), (px + 6.4, 26.8, px + 0.3), "dark_steel", fl)
    b.m.radial4([pole], ("_1", "_2", "_3"))

    # ---- animation -------------------------------------------------------------------------
    b.spin("beacon", "y", 2.0)
    axes = ["z", "x", "z", "x"]
    for k, nm in enumerate(NAMES):
        b.spin("hand_n" + nm, axes[k], 4.0, HAND_DIR[k])
        sfx = ["", "_1", "_2", "_3"][k]
        b.oscillate("flag" + sfx, "rotation", "y", 14, 2.0, phase=0.25 * k)
        x, y, z = rot_pt(-7.0, 25.0, -6.8, k)
        b.smoke("vent%d" % k, x, y, z, puffs=3, rise=7, period=4.0, size=2.0, group="side_n" + nm)
    b.input_bones(["door_n" + n for n in NAMES])
    b.output_bones(["flag", "flag_1", "flag_2", "flag_3"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
