#!/usr/bin/env python3
"""Industrial mud pit (structure_industrial_mud_pit): a dredged clay pit.

A concrete retaining-wall basin of wet mud with puddles, a four-leg steel gantry with a trolley and a four-petal grab
bucket on cables that lowers into the mud while the petals open and close, a slurry pump with a pipe over the wall on
every side and clay heaps at the plinth corners. 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_mud_pit.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_mud_pit.bbmodel")


def build():
    b = Builder("industrial_mud_pit", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4
    D = 4.0           # the grab hangs this much lower than its first draft
    W = 12.0          # basin outer half-width
    WT = 9.4          # wall top

    # ---- mud surface (centre, 4-fold) ------------------------------------------------------
    b.group("mud", parent="frame")
    b.cube("mud_bed", (-10.2, Y0, -10.2), (10.2, 7.0, 10.2), {"up": "dirt", "*": "dirt"}, "mud", hide={"north", "south", "east", "west"})
    # rutted churned bands and puddles, placed pinwheel-wise so every side looks the same
    b.cube("mud_wet", (-9.2, 7.0, -9.2), (9.2, 7.3, 9.2), {"up": "rusted_steel", "*": "dirt"}, "mud", hide={"down"})
    pud = []
    for i, (x0, z0, x1, z1) in enumerate(((-8.8, -8.8, -4.6, -5.2), (-8.8, 4.0, -5.2, 8.8), (5.0, 5.2, 8.8, 8.8), (4.4, -8.8, 8.8, -5.0))):
        pud.append(b.cube("puddle%d" % i, (x0, 7.3, z0), (x1, 7.6, z1), {"up": "water", "*": "water"}, "mud", hide={"down"}))
    for i, (x, z, s) in enumerate(((-7.4, 0.8, 2.6), (7.4, -0.8, 2.6), (0.8, 7.4, 2.6), (-0.8, -7.4, 2.6))):
        b.cube("clod%d" % i, (x - s / 2, 7.3, z - s / 2), (x + s / 2, 8.4, z + s / 2), {"up": "dirt", "*": "dirt"}, "mud", hide={"down"})
    # dug crater under the grab: dark wet ring
    b.cube("crater", (-3.0, 7.3, -3.0), (3.0, 7.55, 3.0), {"up": "dark_steel", "*": "dark_steel"}, "mud", hide={"down"})

    # ---- one side module: wall, pump, girder (built north, then 4-fold) ------------------------
    side = b.group("side_n", parent="frame")
    b.cube("wall", (-W, Y0, -W), (W - 2, WT, -W + 2), {"up": "dark_steel", "*": "concrete"}, side)
    b.cube("wall_band", (-W, WT - 3.4, -W - 0.3), (W - 2, WT - 2.6, -W), "dark_steel", side, hide={"down"})
    b.cube("wall_foot", (-W - 0.3, Y0, -W - 0.3), (W - 1.7, Y0 + 1.2, -W), "concrete", side, hide={"down"})
    # slurry pump housing outside the wall
    b.cube("pump_base", (-5, Y0, -15.7), (5, Y0 + 1.0, -W), "dark_steel", side)
    b.cube("pump_body", (-4.2, Y0 + 1.0, -15.2), (1.2, 8.4, -W - 0.4), "galvanized", side)
    b.cube("pump_cap", (-4.6, 8.4, -15.5), (1.6, 9.0, -W - 0.2), "steel_plate", side)
    b.cylinder("pump_motor", 3.2, -13.4, Y0 + 1.0, 8.2, 1.7, "steel_plate", 8, side)
    b.cylinder("motor_band", 3.2, -13.4, 5.4, 6.2, 1.95, "dark_steel", 8, side)
    b.cylinder("motor_cap", 3.2, -13.4, 8.2, 8.8, 1.3, "dark_steel", 8, side)
    b.cube("pump_vent", (-3.4, 5.0, -15.5), (0.4, 7.4, -15.2), "grate", side, hide={"down", "up"})
    b.cube("pump_hazard", (-4.2, Y0 + 1.0, -15.4), (1.2, 4.6, -15.2), "hazard_stripe", side, hide={"down", "up"})
    b.pipe_run("slurry", [(-1.6, 9.0, -13.6), (-1.6, 12.4, -13.6), (-1.6, 12.4, -9.0), (-1.6, 9.6, -9.0)], 0.9,
               "galvanized", "dark_steel", 8, side)
    b.cube("slurry_nozzle", (-2.5, 8.6, -9.8), (-0.7, 9.6, -8.2), "dark_steel", side, hide={"up"})
    # gantry girders along the side: lower cross girder and top girder
    b.beam("girder_low", (-W + 3.0, 21.0, -10.4), (W - 3.0, 22.2, -10.4), 1.6, 1.2, "steel_plate", "box", side)
    b.beam("girder_top", (-W, 29.0, -10.4), (W, 31.0, -10.4), 2.4, 2.0, "galvanized", "I", side)

    # ---- corner leg (truss leg, clay heap beside it) -------------------------------------
    leg = b.group("leg_nw", parent="frame")
    b.truss("leg", -W, -W, -W + 3.2, -W + 3.2, WT, 29.0, "steel_plate", 1.0, True, leg, rail_mat="dark_steel")
    b.cube("leg_shoe", (-W - 0.4, WT, -W - 0.4), (-W + 3.6, WT + 0.8, -W + 3.6), "dark_steel", leg, hide={"down"})
    b.cube("leg_cap", (-W - 0.4, 28.2, -W - 0.4), (-W + 3.6, 29.0, -W + 3.6), "dark_steel", leg)
    b.cube("wall_corner", (-W, Y0, -W), (-W + 2, WT, -W + 2), {"up": "dark_steel", "*": "concrete"}, leg)
    # clay heap outside the wall corner
    heap = b.group("clay_heap", parent="frame")
    hx = -13.6
    b.cube("heap_pad", (hx - 2.3, Y0, hx - 2.3), (hx + 2.3, Y0 + 0.5, hx + 2.3), "dark_steel", heap)
    b.taper("heap_lo", hx, hx, Y0 + 0.5, Y0 + 3.0, 2.9, 2.2, "brick", 2, 8, heap)
    b.taper("heap_mid", hx, hx, Y0 + 3.0, Y0 + 5.2, 2.2, 1.2, "dirt", 2, 8, heap)
    b.cylinder("heap_top", hx, hx, Y0 + 5.2, Y0 + 6.0, 0.7, "brick", 8, heap)
    b.m.radial4([side, leg, heap], ("_e", "_s", "_w"))

    # ---- central cross girders, trolley, cables and grab -----------------------------------------
    b.group("gantry_top", parent="frame")
    g = "gantry_top"
    b.cube("cross_x", (-W + 2.4, 29.0, -1.2), (W - 2.4, 31.0, 1.2), "galvanized", g)
    b.cube("cross_z1", (-1.2, 29.0, -W + 2.4), (1.2, 31.0, -1.2), "galvanized", g)
    b.cube("cross_z2", (-1.2, 29.0, 1.2), (1.2, 31.0, W - 2.4), "galvanized", g)
    b.cube("trolley", (-3.4, 26.4, -3.4), (3.4, 29.0, 3.4), "dark_steel", g)
    b.cube("trolley_motor", (-2.4, 28.4, -2.4), (2.4, 29.0, 2.4), "steel_plate", g, hide={"up"})
    for i, (x, z) in enumerate(((-3.0, -3.0), (3.0, -3.0), (3.0, 3.0), (-3.0, 3.0))):
        b.cube("trolley_wheel%d" % i, (x - 0.8, 26.4, z - 0.8), (x + 0.8, 27.4, z + 0.8), "brass", g, hide={"up"})
    b.cube("trolley_hazard", (-3.5, 26.4, -3.5), (3.5, 26.9, 3.5), "hazard_stripe", g, hide={"up", "down"})

    b.group("cables", parent="frame", origin=(0, 26.4, 0))
    for i, (x, z) in enumerate(((-1.6, 0), (1.6, 0), (0, -1.6), (0, 1.6))):
        b.cube("cable%d" % i, (x - 0.3, 22.6 - D, z - 0.3), (x + 0.3, 26.4, z + 0.3), "dark_steel", "cables")

    grab = b.group("grab", parent="frame", origin=(0, 22.6 - D, 0))
    b.cube("grab_head", (-2.6, 20.0 - D, -2.6), (2.6, 22.6 - D, 2.6), "steel_plate", grab)
    b.cube("grab_cap", (-2.0, 22.6 - D, -2.0), (2.0, 23.2 - D, 2.0), "dark_steel", grab, hide={"down"})
    b.cube("grab_stripe", (-2.7, 20.6 - D, -2.7), (2.7, 21.4 - D, 2.7), "warning_paint_yellow", grab, hide={"up", "down"})
    # four petals hinged at the bottom of the head, each tilted inward when closed
    for nm, (hx_, hz_), axis in (("n", (0, -2.4), "x"), ("e", (2.4, 0), "z"), ("s", (0, 2.4), "x"), ("w", (-2.4, 0), "z")):
        pg = b.group("jaw_" + nm, parent=grab, origin=(hx_, 20.0 - D, hz_))
        if axis == "x":
            b.cube("jaw_" + nm, (-1.8, 14.6 - D, hz_ - 0.5), (1.8, 20.0 - D, hz_ + 0.5), "dark_steel", pg)
            b.cube("jaw_tip_" + nm, (-1.8, 14.6 - D, hz_ - 0.7), (1.8, 15.8 - D, hz_ + 0.7), "steel_plate", pg)
        else:
            b.cube("jaw_" + nm, (hx_ - 0.5, 14.6 - D, -1.8), (hx_ + 0.5, 20.0 - D, 1.8), "dark_steel", pg)
            b.cube("jaw_tip_" + nm, (hx_ - 0.7, 14.6 - D, -1.8), (hx_ + 0.7, 15.8 - D, 1.8), "steel_plate", pg)
    industrial_status_mast(b, 0, 0, 31.0)

    # ---- animation ------------------------------------------------------------------------
    T = 4.0
    b.piston("grab", "y", -7.0, T)
    s = 7.0 / (26.4 - (22.6 - D))
    b._add("cables", "scale", "y", "osc", lambda t, p=T, k=s: 1 + k * (1 - math.cos(2 * math.pi * t / p)) / 2, T)
    for nm, ax, sg in (("n", "x", 1), ("s", "x", -1), ("e", "z", -1), ("w", "z", 1)):
        # petals swing open as the grab hits the mud (phase offset half a cycle) and close while it rises
        b.oscillate("jaw_" + nm, "rotation", ax, 28.0 * sg, T, 0.25)
    b.input_bones(["grab"])
    b.output_bones(["clay_heap", "clay_heap_e", "clay_heap_s", "clay_heap_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
