#!/usr/bin/env python3
"""Industrial sigil altar (structure_industrial_sigil_altar): a plasma-containment altar, 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_sigil_altar.py   # writes bbmodels/structure_industrial_sigil_altar.bbmodel

A stepped steel pedestal with glowing rune inlays carries a turbine disc and a floating plasma core; two gimbal
rings (perpendicular, brass with glow nodes) and an equator ring spin around it. A Tesla pylon stands on every
side and feeds the central hub through a copper conduit; capacitor banks with vent stacks sit in the corners.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_sigil_altar.bbmodel")
SUF = ("_e", "_s", "_w")


def rot_pt(x, y, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, y, z


def build():
    b = Builder("industrial_sigil_altar", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4
    CY = 25.0  # core / gimbal centre

    # ---- pedestal -----------------------------------------------------------------------------
    b.group("pedestal", parent="frame")
    p = "pedestal"
    b.cylinder("ped_foot", 0, 0, Y0, 5.2, 10.4, "dark_steel", 8, p)
    b.cylinder("ped_haz", 0, 0, 5.2, 6.2, 10.0, "hazard_stripe", 8, p)
    b.cylinder("ped_mid", 0, 0, 6.2, 9.4, 8.6, "steel_plate", 8, p)
    b.ring("ped_rune_ring", 0, 0, 9.4, 10.0, 8.9, 7.2, "glow_cyan", 8, p)
    b.cylinder("ped_top", 0, 0, 10.0, 11.4, 7.6, "dark_steel", 8, p)
    b.cylinder("ped_col", 0, 0, 11.4, 13.6, 4.6, "galvanized", 8, p)
    b.cylinder("ped_col_band", 0, 0, 12.2, 12.8, 5.0, "copper", 8, p)
    b.cylinder("ped_plate", 0, 0, 13.6, 14.8, 6.2, "steel_plate", 8, p, cap_mat="dark_steel")
    rn = b.group("rune_n", parent="frame")
    b.cube("rune_a", (-1.0, 6.7, -8.9), (1.0, 8.9, -8.5), "glow_cyan", rn, hide={"down", "up"})
    b.cube("rune_b", (-3.4, 7.5, -8.4), (-2.2, 8.1, -7.8), "glow_cyan", rn, hide={"down"}, rotation=(0, -22.5, 0))
    b.cube("rune_c", (2.2, 7.5, -8.4), (3.4, 8.1, -7.8), "glow_cyan", rn, hide={"down"}, rotation=(0, 22.5, 0))
    b.cube("rune_frame", (-1.6, 6.4, -8.7), (1.6, 6.9, -8.4), "brass", rn)
    b.m.radial4([rn], SUF)

    # ---- turbine disc, beam, core ---------------------------------------------------------------
    b.gear("turbine", (0, 15.4, 0), 5.0, 1.0, 12, "y", "dark_steel", "steel_plate", "brass", "frame")
    b.cylinder("beam", 0, 0, 16.1, CY - 2.0, 0.6, "glow_cyan", 4, "frame")
    orb = b.group("orb", parent="frame", origin=(0, CY, 0))
    b.cylinder("orb_mid", 0, 0, CY - 1.4, CY + 1.4, 2.3, "glow_cyan", 8, orb)
    b.cylinder("orb_lo", 0, 0, CY - 2.2, CY - 1.4, 1.5, "glow_cyan", 8, orb)
    b.cylinder("orb_hi", 0, 0, CY + 1.4, CY + 2.2, 1.5, "glow_cyan", 8, orb)
    b.cylinder("orb_core", 0, 0, CY - 0.8, CY + 0.8, 2.6, "glow_amber", 4, orb)

    # ---- gimbal rings (vertical, perpendicular) + equator ring ----------------------------------
    b.group("gimbal", parent="frame", origin=(0, CY, 0))
    for nm, r in (("ringA", (90, 0, 0)), ("ringB", (0, 0, 90))):
        sg = b.group(nm, parent="gimbal", origin=(0, CY, 0), rotation=r)
        b.ring(nm + "_r", 0, 0, CY - 0.8, CY + 0.8, 8.0, 7.1, "brass", 12, sg)
        for i in range(4):
            x, z = rot_pt(7.55, 0, 0, i)[0], rot_pt(7.55, 0, 0, i)[2]
            b.cube("%s_node%d" % (nm, i), (x - 0.9, CY - 1.1, z - 0.9), (x + 0.9, CY + 1.1, z + 0.9), "glow_cyan", sg)
        for i in range(4):
            x, z = rot_pt(5.4, 0, 5.4, i)[0], rot_pt(5.4, 0, 5.4, i)[2]
            b.cube("%s_clamp%d" % (nm, i), (x - 1.0, CY - 1.0, z - 1.0), (x + 1.0, CY + 1.0, z + 1.0), "dark_steel", sg)
    b.group("equator", parent="frame", origin=(0, CY, 0))
    b.ring("eq", 0, 0, CY - 0.5, CY + 0.5, 5.2, 4.4, "copper", 8, "equator")
    for i in range(4):
        x, z = rot_pt(4.8, 0, 0, i)[0], rot_pt(4.8, 0, 0, i)[2]
        b.cube("eq_node%d" % i, (x - 0.8, CY - 0.8, z - 0.8), (x + 0.8, CY + 0.8, z + 0.8), "glow_amber", "equator")

    # ---- Tesla pylon (north) with conduit ------------------------------------------------------
    pl = b.group("pylon_n", parent="frame")
    PZ = -11.6
    b.cube("pyl_base", (-2.6, Y0, PZ - 2.6), (2.6, 7.2, PZ + 2.6), "dark_steel", pl)
    b.cube("pyl_base_top", (-3.0, 7.2, PZ - 3.0), (3.0, 8.0, PZ + 3.0), "steel_plate", pl)
    b.cube("pyl_hazard", (-2.8, 4.4, PZ - 2.8), (2.8, 5.2, PZ + 2.8), "hazard_stripe", pl)
    b.cube("pyl_slit", (-0.5, 5.6, PZ - 2.9), (0.5, 7.0, PZ - 2.6), "glow_cyan", pl, hide={"down", "up"})
    y = 8.0
    for i in range(7):
        b.cylinder("coil%d" % i, 0, PZ, y, y + 1.7, 2.1, "copper", 8, pl)
        b.cylinder("ins%d" % i, 0, PZ, y + 1.7, y + 2.5, 1.5, "dark_steel", 8, pl)
        y += 2.5
    b.cylinder("pyl_cap", 0, PZ, y, y + 1.4, 2.4, "dark_steel", 8, pl)
    b.cylinder("pyl_tip", 0, PZ, y + 1.4, y + 2.6, 1.3, "glow_cyan", 8, pl)
    top = y + 2.6
    b.pipe_run("conduit", [(0, top - 0.3, PZ), (0, 34.0, PZ), (0, 34.0, -2.0)], 0.9, "copper", "brass", 8, pl)
    b.m.radial4([pl], SUF)

    # ---- hub + capacitor banks ------------------------------------------------------------------
    b.cube("hub", (-2.4, 32.6, -2.4), (2.4, 35.2, 2.4), "dark_steel", "frame")
    b.cube("hub_band", (-2.7, 33.5, -2.7), (2.7, 34.3, 2.7), "warning_paint_yellow", "frame")
    cell = b.group("cell", parent="frame")
    CX = 12.0
    b.cube("cell_body", (CX - 2.8, Y0, CX - 2.8), (CX + 2.8, 8.4, CX + 2.8), "steel_plate", cell)
    b.cube("cell_hazard", (CX - 3.0, 6.2, CX - 3.0), (CX + 3.0, 7.0, CX + 3.0), "hazard_stripe", cell)
    b.cube("cell_lid", (CX - 3.2, 8.4, CX - 3.2), (CX + 3.2, 9.2, CX + 3.2), "dark_steel", cell)
    b.cube("cell_glow_a", (CX - 1.2, 4.2, CX - 3.0), (CX + 1.2, 5.6, CX - 2.8), "glow_amber", cell, hide={"down", "up"})
    b.cube("cell_glow_b", (CX - 3.0, 4.2, CX - 1.2), (CX - 2.8, 5.6, CX + 1.2), "glow_amber", cell, hide={"down", "up"})
    b.chimney("cell_stack", CX, CX, 9.2, 14.5, 1.3, 0.9, "rusted_steel", "dark_steel", 8, cell)
    b.m.radial4([cell], ("_1", "_2", "_3"))
    industrial_status_mast(b, 0, 0, 35.2)

    # ---- animation -------------------------------------------------------------------------
    b.spin("gimbal", "y", 4.0)
    b.spin("equator", "y", 2.0, -1)
    b.spin("turbine", "y", 1.0, -1)
    b.bob("orb", 0.9, 2.0)
    b.pulse_scale("orb", 0.92, 1.08, 1.0)
    for k, nm in enumerate(("cell", "cell_1", "cell_2", "cell_3")):
        x, y_, z = rot_pt(CX, 14.5, CX, k)
        b.smoke("cell%d" % k, x, y_ + 0.3, z, puffs=3, rise=7, period=4.0, size=1.8, group=nm, mat="galvanized")
    b.input_bones(["orb"])
    b.output_bones(["cell", "cell_1", "cell_2", "cell_3"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
