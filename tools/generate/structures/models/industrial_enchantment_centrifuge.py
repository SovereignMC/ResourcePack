#!/usr/bin/env python3
"""Industrial enchantment centrifuge (structure_industrial_enchantment_centrifuge): a bolted motor housing with a
steel bowl, a fast spinning rotor with four glowing enchant vials, a spindle carrying a bobbing crystal, a caged
copper ring and four tesla pylons. 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_enchantment_centrifuge.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_enchantment_centrifuge.bbmodel")


def build():
    b = Builder("industrial_enchantment_centrifuge", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- motor housing + bowl ---------------------------------------------------------------------------
    b.group("housing", parent="frame")
    h = "housing"
    b.cylinder("mot_foot", 0, 0, Y0, Y0 + 1.4, 12.6, "dark_steel", 8, h)
    b.cylinder("mot", 0, 0, Y0 + 1.4, 8, 11, "steel_plate", 8, h)
    b.cylinder("mot_haz", 0, 0, Y0 + 1.4, Y0 + 2.8, 11.5, "hazard_stripe", 8, h)
    b.cylinder("mot_band", 0, 0, 6.4, 7.4, 11.5, "dark_steel", 8, h)
    b.ring("bowl", 0, 0, 8, 15, 11.6, 9.6, "steel_plate", 8, h)
    b.ring("bowl_lip", 0, 0, 15, 16, 11.9, 9.3, "warning_paint_yellow", 8, h)
    b.cylinder("bowl_floor", 0, 0, 8, 8.8, 9.7, "dark_steel", 8, h)
    b.ring("bowl_glow", 0, 0, 8.8, 9.2, 9.2, 8.2, "glow_cyan", 8, h)
    # per-side detail: control panel with glow strip, vent slots, rivets
    side = b.group("side_n", parent="frame")
    b.panel("mp", (-3.2, Y0 + 3.4, -10.5), 6.4, 3.6, "north", "dark_steel", "steel_plate", 0.8, 0.6, side)
    b.cube("mp_glow", (-2.0, Y0 + 4.8, -11.2), (2.0, Y0 + 5.6, -10.9), "glow_amber", side, hide={"up", "down"})
    for i, x in enumerate((-8, -6.2, 6.2, 8)):
        b.cube("vent%d" % i, (x - 0.5, Y0 + 3, -10.6), (x + 0.5, 7, -10.1), "dark_steel", side)
    b.rivet_strip("rv", (-5, 7.8, -11.0), "north", 10, 2.5, 0, "galvanized", side)
    # pylon (corner): tesla coil with glowing orb
    st = b.group("pylon", parent="frame")
    cx = cz = 12.4
    b.cylinder("py_foot", cx, cz, Y0, Y0 + 1.4, 3.2, "dark_steel", 8, st)
    b.cylinder("py_body", cx, cz, Y0 + 1.4, 16, 2.4, "galvanized", 8, st)
    b.cylinder("py_haz", cx, cz, Y0 + 1.4, Y0 + 2.6, 2.7, "hazard_stripe", 8, st)
    for i, y in enumerate((8.4, 11.6)):
        b.cylinder("py_coil%d" % i, cx, cz, y, y + 1.6, 2.9, "copper", 8, st)
    b.cylinder("py_cap", cx, cz, 16, 17, 3.0, "dark_steel", 8, st)
    orb = b.group("orb", parent=st, origin=(cx, 18.6, cz))
    b.cylinder("py_orb", cx, cz, 17.4, 19.8, 1.7, "glow_cyan", 8, orb)
    b.cylinder("py_orb_cap", cx, cz, 19.8, 20.6, 0.9, "copper", 8, orb)
    # ---- rotor with vials -------------------------------------------------------------------------------
    rotor = b.group("rotor", parent="frame", origin=(0, 14, 0))
    b.cylinder("hub", 0, 0, 9, 17.2, 2.4, "dark_steel", 8, rotor)
    b.cylinder("hub_band", 0, 0, 12.8, 13.8, 2.9, "brass", 8, rotor)
    b.cylinder("hub_cap", 0, 0, 17.2, 18, 1.8, "copper", 8, rotor)
    arm = b.group("arm", parent=rotor)
    b.cube("arm_bar", (1.5, 13.4, -0.7), (7.6, 14.8, 0.7), "steel_plate", arm)
    b.cube("arm_haz", (3.4, 14.8, -0.7), (5.2, 15.1, 0.7), "hazard_stripe", arm, hide={"down"})
    b.cube("vial_cup", (6.4, 9.4, -1.6), (9.6, 10.6, 1.6), "dark_steel", arm)
    b.cylinder("vial", 8, 0, 10.6, 17.4, 1.3, "glow_cyan", 8, arm)
    b.cylinder("vial_band", 8, 0, 12.4, 13.0, 1.7, "dark_steel", 8, arm)
    b.cylinder("vial_cork", 8, 0, 17.4, 18.6, 1.0, "copper", 8, arm)
    b.cube("vial_clamp", (6.4, 13.8, -0.8), (9.6, 14.6, 0.8), "dark_steel", arm)
    # ---- spindle, cage ring, crystal --------------------------------------------------------------------
    b.cylinder("spindle", 0, 0, 18, 27, 1.1, "galvanized", 8, "frame")
    cage = b.group("cage", parent="frame")
    for i, (x, z) in enumerate(((6.6, 6.6), (-6.6, 6.6), (-6.6, -6.6), (6.6, -6.6))):
        b.cube("cg_post%d" % i, (x - 0.6, 16, z - 0.6), (x + 0.6, 26, z + 0.6), "warning_paint_yellow", cage, hide={"down"})
    b.ring("cg_ring", 0, 0, 24.4, 25.6, 10.4, 8.8, "copper", 8, cage)
    b.ring("cg_ring2", 0, 0, 20.2, 20.8, 10.3, 8.9, "dark_steel", 8, cage)
    for i, (dx, dz) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):   # spokes ring -> spindle
        a, c = (min(0, dx * 8.6) - (0.4 if not dx else 0), min(0, dz * 8.6) - (0.4 if not dz else 0)), \
               (max(0, dx * 8.6) + (0.4 if not dx else 0), max(0, dz * 8.6) + (0.4 if not dz else 0))
        b.cube("cg_spoke%d" % i, (a[0], 24.6, a[1]), (c[0], 25.4, c[1]), "dark_steel", cage)
    cry = b.group("crystal", parent="frame", origin=(0, 30, 0))
    b.cylinder("cry_collar", 0, 0, 26.4, 27.4, 2.0, "brass", 8, cry)
    b.taper("cry_a", 0, 0, 27.4, 31.4, 1.2, 3.4, "glow_cyan", 4, 8, cry)
    b.taper("cry_b", 0, 0, 31.4, 36, 3.4, 0.8, "glow_cyan", 4, 8, cry)
    b.cylinder("cry_tip", 0, 0, 36, 37.2, 0.5, "copper", 8, cry)
    b.cylinder("cry_belt", 0, 0, 31, 32, 3.7, "copper", 8, cry)

    # ---- 4-fold -----------------------------------------------------------------------------------------
    b.m.radial4([side], ("_e", "_s", "_w"))
    b.m.radial4([st], ("_1", "_2", "_3"))
    b.m.radial4([arm], ("_e", "_s", "_w"))
    # ---- animation --------------------------------------------------------------------------------------
    b.spin("rotor", "y", 0.5)
    b.spin("crystal", "y", 2.0, -1)
    b.bob("crystal", 0.8, 2.0)
    for k in range(4):
        sfx = "" if k == 0 else "_%d" % k
        b.pulse_scale("orb" + sfx, 0.85, 1.2, 1.0, phase=0.25 * k)
    b.smoke("ench", 0, 37.4, 0, puffs=3, rise=6, period=4.0, size=1.2, group="frame", mat="glow_cyan")
    b.input_bones(["rotor"])
    b.output_bones(["crystal"])
    industrial_status_mast(b, 0, 0, 37.2)
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
