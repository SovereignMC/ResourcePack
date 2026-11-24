#!/usr/bin/env python3
"""Industrial stamp mill (structure_industrial_crusher), 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_crusher.py

A square steel mortar in the middle, five heavy stamps (one per side plus one in the centre) guided by a
hazard-striped girder cross, four cam shafts with flywheels (pinwheel), a feed bin with chute and a gravel pile
per side, corner I-beam posts and a ring of top beams.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_crusher.bbmodel")
Y0 = 3.4


def build():
    b = Builder("industrial_crusher", run_length=4.0)
    industrial_plinth(b)
    fr = "frame"
    # ---- central mortar (square, 4-fold by itself) ----------------------------------------------
    b.group("mortar", parent=fr)
    mt = "mortar"
    b.cube("m_body", (-9.2, Y0, -9.2), (9.2, 9.4, 9.2), {"up": "dark_steel", "*": "steel_plate"}, mt)
    b.cube("m_foot", (-9.8, Y0, -9.8), (9.8, Y0 + 1.6, 9.8), "dark_steel", mt)
    b.cube("m_band", (-9.6, 6.4, -9.6), (9.6, 7.4, 9.6), "copper", mt)
    b.cube("m_ore", (-8.0, 9.4, -8.0), (8.0, 10.0, 8.0), {"up": "stone", "*": "rusted_steel"}, mt)
    for i, (x, z, s) in enumerate(((-3.5, 2.0, 2.2), (4.0, -3.0, 2.6), (1.0, 5.2, 1.8), (-5.0, -4.5, 2.0), (5.8, 4.6, 1.6))):
        b.cube("m_rock%d" % i, (x - s / 2, 10.0, z - s / 2), (x + s / 2, 10.0 + s * 0.7, z + s / 2), "stone", mt,
               rotation=(0, 20 + i * 17, 0))
    # ---- centre stamp -------------------------------------------------------------------------
    def stamp(name, cx, cz, tappet=False):
        g = b.group(name, parent=fr, origin=(cx, 10.4, cz))
        b.cube(name + "_shoe", (cx - 2.4, 10.4, cz - 2.4), (cx + 2.4, 11.6, cz + 2.4), "hazard_stripe", g)
        b.cube(name + "_head", (cx - 2.2, 11.6, cz - 2.2), (cx + 2.2, 16.4, cz + 2.2), "dark_steel", g)
        b.cube(name + "_collar", (cx - 2.6, 14.0, cz - 2.6), (cx + 2.6, 15.0, cz + 2.6), "copper", g)
        b.cube(name + "_rod", (cx - 1.0, 16.4, cz - 1.0), (cx + 1.0, 29.0, cz + 1.0), "galvanized", g)
        b.cube(name + "_cap", (cx - 1.5, 29.0, cz - 1.5), (cx + 1.5, 30.2, cz + 1.5), "dark_steel", g, hide={"down"})
        return g
    stamp("stamp_c", 0, 0)
    # ---- girder cross at y 22..24 (centre block; arms are part of the side module) -----------------
    b.cube("cross_c", (-1.9, 22.0, -1.9), (1.9, 23.6, 1.9), {"up": "hazard_stripe", "*": "steel_plate"}, fr)
    # ---- north module --------------------------------------------------------------------------
    side = b.group("side_n", parent=fr)
    # guide arm of the cross (up to the ring beam), stamp, camshaft, ring beam, feed bin + pile
    b.cube("arm_n", (-1.9, 22.0, -11.8), (1.9, 23.6, -1.9), {"up": "hazard_stripe", "*": "steel_plate"}, side)
    b.cube("arm_n_rivet0", (-1.4, 23.6, -9.0), (-0.6, 24.1, -8.2), "galvanized", side, hide={"down"})
    b.cube("arm_n_rivet1", (0.6, 23.6, -9.0), (1.4, 24.1, -8.2), "galvanized", side, hide={"down"})
    # ring beam between the posts (pinwheel not needed: it stops short of the posts)
    b.cube("ring_n", (-11.8, 34.6, -13.2), (11.8, 36.5, -11.8), {"north": "hazard_stripe", "*": "dark_steel"}, side)
    b.cube("ring_n_low", (-11.8, 18.0, -12.6), (11.8, 19.2, -11.8), "steel_plate", side)
    # corner post (north-west one; clones give the other three)
    b.beam("post_n", (-12.6, Y0, -12.6), (-12.6, 36.5, -12.6), 2.4, 2.4, "steel_plate", "I", side)
    b.cube("post_n_foot", (-14.0, Y0, -14.0), (-11.2, 5.0, -11.2), "dark_steel", side)
    b.cube("post_n_band", (-13.9, 10.0, -13.9), (-11.3, 12.0, -11.3), "hazard_stripe", side)
    b.cube("post_n_band2", (-13.9, 28.0, -13.9), (-11.3, 30.0, -11.3), "hazard_stripe", side)
    b.cube("post_n_cap", (-13.8, 36.5, -13.8), (-11.4, 37.3, -11.4), "dark_steel", side, hide={"down"})
    for k, y in enumerate((20, 26, 32)):
        b.cube("post_n_gus%d" % k, (-11.2, y, -12.0), (-10.4, y + 2.2, -11.4), "steel_plate", side)
    # stamp north (mid-side) with tappet toward the camshaft
    sg = stamp("stamp_n", 0, -5.2)
    b.cube("stamp_n_tappet", (-1.3, 24.4, -10.6), (1.3, 25.8, -6.2), "brass", sg)
    # camshaft (spins), lobes, flywheel gear on the +x end
    cam = b.group("cam_n", parent=side, origin=(0, 25.0, -10.9))
    b.cube("cam_n_axle", (-11.6, 24.2, -11.7), (15.2, 25.8, -10.1), "galvanized", cam)
    for k, x in enumerate((0.0, -6.5)):
        b.cube("cam_n_lobe%d" % k, (x - 1.3, 21.8, -11.5), (x + 1.3, 28.2, -10.3), "brass", cam)
    gear = b.gear("cam_n_fly", (14.6, 25.0, -10.9), 3.9, 2.0, 8, "x", "dark_steel", "steel_plate", "brass", cam)
    for x in (-12.6, 12.6):
        b.cube("cam_n_bearing%s" % ("l" if x < 0 else "r"), (x - 0.9, 23.2, -12.4), (x + 0.9, 26.8, -9.4), "brass", side)
    b.cube("cam_n_bearing_cap", (11.7, 26.8, -12.0), (13.5, 27.4, -9.8), "dark_steel", side, hide={"down"})
    # feed bin + chute
    bin_ = b.group("bin_n", parent=side, origin=(-4.5, Y0, -12.6))
    b.cube("bin_n_body", (-7.0, Y0, -14.8), (-2.2, 10.6, -10.4), {"up": "stone", "*": "galvanized"}, bin_)
    b.cube("bin_n_band", (-7.2, 6.0, -15.0), (-2.0, 7.0, -10.2), "hazard_stripe", bin_)
    b.cube("bin_n_rim", (-7.4, 10.6, -15.2), (-1.8, 11.4, -10.0), "dark_steel", bin_)
    b.cube("bin_n_fill", (-6.8, 11.4, -14.6), (-2.4, 12.0, -10.6), {"up": "stone", "*": "rusted_steel"}, bin_)
    b.cube("bin_n_chute", (-6.0, 9.4, -10.6), (-3.2, 10.2, -7.6), "dark_steel", bin_, rotation=(-14, 0, 0))
    b.cube("bin_n_chute_l", (-6.4, 9.4, -10.6), (-6.0, 11.0, -8.0), "steel_plate", bin_)
    b.cube("bin_n_chute_r", (-3.2, 9.4, -10.6), (-2.8, 11.0, -8.0), "steel_plate", bin_)
    b.cube("bin_n_glow", (-6.0, 7.6, -10.45), (-3.2, 8.4, -10.15), "glow_amber", bin_, hide={"down", "up"})
    pile = b.group("pile_n", parent=side, origin=(5.5, Y0, -12.5))
    for k, (x, z, s, y) in enumerate(((3.6, -13.8, 3.4, 0), (6.6, -13.0, 3.0, 0), (5.0, -11.8, 2.6, 0), (4.8, -13.2, 2.2, 2.2))):
        b.cube("pile_n_r%d" % k, (x - s / 2, Y0 + y, z - s / 2), (x + s / 2, Y0 + y + s * 0.8, z + s / 2), "stone", pile,
               rotation=(0, 15 + 23 * k, 0))
    # mortar side detail: rivets, gauge, hazard stripe
    b.rivet_strip("m_riv_n", (-7, 4.6, -9.2), "north", 14, 3.5, 0, "galvanized", side)
    b.cube("m_gauge", (5.4, 4.2, -9.8), (8.2, 7.0, -9.2), "dark_steel", side)
    b.cube("m_gauge_g", (6.0, 4.8, -10.0), (7.6, 6.4, -9.8), "glow_cyan", side, hide={"down", "up"})
    # oil line on the post
    b.cube("oil_n", (-10.9, 12.0, -11.3), (-10.3, 33.0, -10.7), "copper", side, hide={"down"})
    # ---- 4-fold ------------------------------------------------------------------------------
    b.m.radial4([side, sg], ("_e", "_s", "_w"))
    industrial_status_mast(b, 0, 0, 36.5)
    # centre cross fixture on top (carries the mast)
    b.cube("cross_top_x", (-11.8, 34.6, -0.8), (11.8, 36.2, 0.8), "dark_steel", fr)
    b.cube("cross_top_z", (-0.8, 34.3, -11.8), (0.8, 35.9, 11.8), "dark_steel", fr)
    b.smoke("dust", 0, 10.4, 0, puffs=3, rise=11, period=2.0, size=3.2, group="mortar")
    # ---- animation ----------------------------------------------------------------------------
    for n, ph in (("stamp_n", 0.0), ("stamp_n_e", 0.25), ("stamp_n_s", 0.5), ("stamp_n_w", 0.75), ("stamp_c", 0.125)):
        b.piston(n, "y", 4.0, 2.0, ph)
    for n, ax, d in (("cam_n", "x", 1), ("cam_n_e", "z", 1), ("cam_n_s", "x", -1), ("cam_n_w", "z", -1)):
        b.spin(n, ax, 2.0, d)
    b.input_bones(["bin_n", "bin_n_e", "bin_n_s", "bin_n_w"])
    b.output_bones(["pile_n", "pile_n_e", "pile_n_s", "pile_n_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
