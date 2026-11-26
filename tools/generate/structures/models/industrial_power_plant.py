#!/usr/bin/env python3
"""Industrial power plant (structure_industrial_power_plant): a coal-fired thermal power station.

A central boiler house (brick base, steel upper walls) with a tall red-banded concrete chimney carrying the status mast,
a coal bunker on every roof edge, four hyperboloid cooling towers at the plinth corners with steam, and between them on
every side a turbine hall with a transformer (fins + copper bushings). 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_power_plant.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_power_plant.bbmodel")
TC = 10.4                                   # cooling tower centre offset on both axes
TR = [5.5, 4.8, 4.2, 4.0, 4.4, 4.7]   # hyperboloid profile, bottom to top


def build():
    b = Builder("industrial_power_plant", run_length=4.0)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- boiler house (octagonal so the cooling towers fit at the corners) -------------------------
    b.group("boiler", parent="frame")
    f = "boiler"
    b.cylinder("brick_base", 0, 0, Y0, 8.2, 8.7, "brick", 8, f)
    b.cylinder("base_cap", 0, 0, 8.2, 9.0, 8.9, "dark_steel", 8, f)
    b.cylinder("shell", 0, 0, 9.0, 23.6, 8.5, "steel_plate", 8, f)
    for i, y in enumerate((13.2, 18.4)):
        b.cylinder("shell_band%d" % i, 0, 0, y, y + 1.0, 8.8, "dark_steel", 8, f)
    b.cylinder("shell_hazard", 0, 0, 9.0, 10.0, 8.7, "hazard_stripe", 8, f)
    b.cylinder("eave", 0, 0, 23.6, 24.6, 9.0, "dark_steel", 8, f)
    b.cylinder("roof", 0, 0, 24.6, 25.0, 8.2, "galvanized", 8, f)
    # chimney: concrete with red warning bands, rim and mast base
    b.taper("chimney", 0, 0, 25.0, 37.5, 3.7, 2.5, "concrete", 6, 8, f)
    for i, (y0, y1) in enumerate(((27.0, 29.0), (31.6, 33.6), (36.0, 37.5))):
        r = 3.7 + (2.5 - 3.7) * ((y0 + y1) / 2 - 25.0) / 12.5 + 0.25
        b.cylinder("chim_band%d" % i, 0, 0, y0, y1, r, "warning_paint_red", 8, f)
    b.cylinder("chim_rim", 0, 0, 37.5, 38.4, 3.1, "dark_steel", 8, f)

    # ---- one side module: boiler windows, coal bunker, turbine hall + transformer (north, then x4) ---
    side = b.group("side_n", parent="frame")
    for i, x in enumerate((-4.2, 0, 4.2)):
        b.cube("win%d" % i, (x - 1.3, 15.0, -8.8), (x + 1.3, 22.0, -8.3), "glass", side, hide={"down", "up"})
    b.cube("door_frame", (-1.8, 9.2, -9.2), (1.8, 13.0, -8.4), "dark_steel", side, hide={"down"})
    b.cube("door_glow", (-1.2, 9.6, -9.4), (1.2, 12.4, -9.1), "glow_amber", side, hide={"down", "up"})
    b.ladder("ladder", (5.6, 9.0, -8.7), 14.0, "north", 2.6, "galvanized", side)
    b.pipe_run("steam", [(-6.4, 20.5, -8.7), (-6.4, 25.0, -8.7)], 0.8, "galvanized", "dark_steel", 8, side)
    hop = b.group("hop_n", parent=side)
    b.cube("bunker_body", (-3.4, 25.0, -7.6), (3.4, 28.2, -3.9), {"*": "galvanized", "up": "dark_steel"}, hop)
    b.cube("bunker_band", (-3.6, 26.0, -7.8), (3.6, 26.8, -3.7), "hazard_stripe", hop, hide={"up", "down"})
    b.cube("bunker_coal", (-2.6, 28.2, -6.8), (2.6, 29.4, -4.7), {"*": "dark_steel", "up": "dark_steel"}, hop, hide={"down"})
    b.cube("bunker_rim_f", (-3.6, 28.2, -7.8), (3.6, 28.8, -7.4), "steel_plate", hop)
    b.cube("bunker_rim_b", (-3.6, 28.2, -4.1), (3.6, 28.8, -3.7), "steel_plate", hop)
    # turbine / generator hall
    b.cube("hall", (-4.6, Y0, -12.4), (4.6, 9.2, -8.2), "steel_plate", side)
    b.cube("hall_roof", (-5.0, 9.2, -12.8), (5.0, 9.9, -8.2), "dark_steel", side)
    b.cube("hall_stripe", (-4.7, 4.4, -12.5), (4.7, 5.2, -8.3), "warning_paint_yellow", side, hide={"up", "down"})
    for i, x in enumerate((-2.6, 2.6)):
        b.cube("hall_win%d" % i, (x - 1.0, 6.4, -12.6), (x + 1.0, 8.4, -12.3), "glass", side, hide={"up", "down"})
    b.pipe("turbine", (0, 11.0, -10.4), 8.0, 1.1, "x", "galvanized", 8, side)
    b.cube("turbine_cradle_l", (-3.6, 9.9, -11.0), (-2.8, 10.6, -9.8), "dark_steel", side, hide={"down"})
    b.cube("turbine_cradle_r", (2.8, 9.9, -11.0), (3.6, 10.6, -9.8), "dark_steel", side, hide={"down"})
    # transformer (output)
    tr = b.group("trafo_n", parent=side)
    b.cube("trafo_pad", (-4.0, Y0, -15.8), (4.0, Y0 + 0.8, -12.4), "concrete", tr)
    b.cube("trafo_tank", (-3.3, Y0 + 0.8, -15.4), (3.3, 8.8, -12.6), "dark_steel", tr)
    b.cube("trafo_lid", (-3.5, 8.8, -15.6), (3.5, 9.4, -12.4), "steel_plate", tr)
    for i in range(5):
        x = -2.6 + 1.3 * i
        b.cube("fin%d" % i, (x - 0.35, 4.8, -16.4), (x + 0.35, 8.4, -15.4), "galvanized", tr, hide={"down"})
    for i, x in enumerate((-2.0, 0, 2.0)):
        b.cylinder("bush%d" % i, x, -14.0, 9.4, 11.6, 0.6, "copper", 8, tr)
        b.cylinder("bush_cap%d" % i, x, -14.0, 11.6, 12.1, 0.9, "dark_steel", 8, tr)
    # ---- cooling tower (one corner, then x4) ----------------------------------------------------
    tw = b.group("tower_a", parent="frame")
    h = 2.9
    for i, r in enumerate(TR):
        y0 = Y0 + 0.6 + i * h
        if i < len(TR) - 1:
            b.cylinder("tower_ring%d" % i, TC, TC, y0, y0 + h, r, "concrete", 8, tw, hide={"up"})
        else:
            b.ring("tower_ring%d" % i, TC, TC, y0, y0 + h, r, r - 0.9, "concrete", 8, tw)
    b.cylinder("tower_foot", TC, TC, Y0, Y0 + 0.6, 5.7, "dark_steel", 8, tw)
    ytop = Y0 + 0.6 + len(TR) * h
    b.ring("tower_rim", TC, TC, ytop, ytop + 0.7, 4.9, 3.7, "dark_steel", 8, tw)
    b.cylinder("tower_water", TC, TC, ytop - 1.4, ytop - 1.0, 3.8, "water", 8, tw)
    b.cylinder("tower_band", TC, TC, Y0 + 0.6 + 3 * h - 0.3, Y0 + 0.6 + 3 * h + 0.5, 4.3, "warning_paint_red", 8, tw)
    # ---- 4-fold ------------------------------------------------------------------------------
    b.m.radial4([side], ("_e", "_s", "_w"))
    b.m.radial4([tw], ("_1", "_2", "_3"))
    industrial_status_mast(b, 0, 0, 38.4)

    # ---- animation: smoke from the cooling towers ----------------------------------------------------
    cx, cz = TC, TC
    for k in range(4):
        x, z = cx, cz
        for _ in range(k):
            x, z = -z, x
        b.smoke("tower%d" % k, x, ytop + 0.4, z, puffs=3, rise=8, period=4.0, size=3.2, group="tower_a" + ("" if k == 0 else "_%d" % k), mat="galvanized")
    b.input_bones(["hop_n", "hop_n_e", "hop_n_s", "hop_n_w"])
    b.output_bones(["trafo_n", "trafo_n_e", "trafo_n_s", "trafo_n_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
