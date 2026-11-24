#!/usr/bin/env python3
"""Industrial armoury (structure_industrial_armoury), 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_armoury.py

A turning armour mannequin on a pedestal in the middle, a weapon rack wall (rifles, swords, shield; pinwheel so the
racks never overlap) on every side, and an anvil press with a hydraulic ram plus an ammo crate in each inner corner.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_armoury.bbmodel")
Y0 = 3.4


def build():
    b = Builder("industrial_armoury", run_length=4.0)
    industrial_plinth(b)
    fr = "frame"
    # ---- centre: pedestal + turning mannequin -----------------------------------------------------
    b.group("pedestal", parent=fr)
    b.cylinder("ped_base", 0, 0, Y0, 5.2, 5.6, "dark_steel", 8, "pedestal")
    b.cylinder("ped_ring", 0, 0, 4.2, 5.0, 6.0, "hazard_stripe", 8, "pedestal")
    b.cylinder("ped_top", 0, 0, 5.2, 6.0, 4.4, "steel_plate", 8, "pedestal", cap_mat="galvanized")
    st = b.group("stand", parent=fr, origin=(0, 6.0, 0))
    b.cube("st_pole", (-0.9, 6.0, -0.9), (0.9, 24.0, 0.9), "galvanized", st)
    b.cube("st_tasset", (-3.4, 9.0, -2.4), (3.4, 13.6, 2.4), "steel_plate", st)
    b.cube("st_tasset_trim", (-3.6, 9.0, -2.6), (3.6, 9.8, 2.6), "copper", st)
    b.cube("st_belt", (-3.6, 13.6, -2.6), (3.6, 15.0, 2.6), "hazard_stripe", st)
    b.cube("st_chest", (-3.8, 15.0, -2.8), (3.8, 23.4, 2.8), "steel_plate", st)
    b.cube("st_chest_hi", (-3.0, 20.6, -3.1), (3.0, 22.6, 3.1), "dark_steel", st)
    b.cube("st_core", (-1.0, 17.4, -3.0), (1.0, 19.4, -2.6), "glow_cyan", st, hide={"down", "up"})
    b.cube("st_core2", (-1.0, 17.4, 2.6), (1.0, 19.4, 3.0), "glow_cyan", st, hide={"down", "up"})
    b.cube("st_shoulders", (-6.8, 21.8, -2.2), (6.8, 23.4, 2.2), "dark_steel", st)
    for sx in (-1, 1):
        b.cube("st_pauldron%d" % sx, (sx * 5.2 - 1.8, 21.6, -3.0), (sx * 5.2 + 1.8, 25.2, 3.0), "galvanized", st)
        b.cube("st_pauldron_band%d" % sx, (sx * 5.2 - 2.0, 23.4, -3.2), (sx * 5.2 + 2.0, 24.2, 3.2), "warning_paint_yellow", st)
        b.cube("st_arm%d" % sx, (sx * 5.6 - 0.9, 13.0, -1.0), (sx * 5.6 + 0.9, 21.6, 1.0), "steel_plate", st)
    b.cube("st_helm", (-3.0, 24.0, -3.0), (3.0, 30.0, 3.0), "steel_plate", st)
    b.cube("st_helm_top", (-2.6, 30.0, -2.6), (2.6, 30.8, 2.6), "dark_steel", st, hide={"down"})
    for nm, f, t in (("n", (-2.2, 26.4, -3.4), (2.2, 27.6, -3.0)), ("s", (-2.2, 26.4, 3.0), (2.2, 27.6, 3.4)),
                     ("e", (3.0, 26.4, -2.2), (3.4, 27.6, 2.2)), ("w", (-3.4, 26.4, -2.2), (-3.0, 27.6, 2.2))):
        b.cube("st_visor_" + nm, f, t, "glow_amber", st, hide={"down", "up"})
    b.cube("st_plume", (-0.5, 30.8, -3.0), (0.5, 34.2, 3.0), "warning_paint_red", st)
    # ---- north module ---------------------------------------------------------------------------
    side = b.group("side_n", parent=fr)
    # rack frame: posts, kick plate, top beam, rails (pinwheel x -14 .. 10)
    for nm, x in (("l", -14.0), ("r", 8.6)):
        b.cube("rack_post_" + nm, (x, Y0, -14.0), (x + 1.6, 34.0, -11.0), "steel_plate", side)
        b.cube("rack_post_band_" + nm, (x - 0.2, 8.0, -14.2), (x + 1.8, 10.0, -10.8), "hazard_stripe", side)
        b.cube("rack_post_cap_" + nm, (x - 0.2, 34.0, -14.2), (x + 1.8, 35.0, -10.8), "dark_steel", side, hide={"down"})
    b.cube("rack_kick", (-12.4, Y0, -13.6), (8.6, 9.0, -11.4), {"up": "dark_steel", "*": "steel_plate"}, side)
    b.cube("rack_kick_strip", (-12.4, 8.0, -13.8), (8.6, 9.0, -11.2), "hazard_stripe", side, hide={"up", "down"})
    b.cube("rack_beam", (-12.4, 31.6, -14.0), (8.6, 34.0, -11.0), {"north": "hazard_stripe", "*": "dark_steel"}, side)
    b.cube("rack_light", (-12.4, 30.8, -13.2), (8.6, 31.6, -12.2), "glow_amber", side, hide={"up", "down"})
    for nm, y in (("hi", 25.0), ("lo", 15.4)):
        b.cube("rack_rail_" + nm, (-12.4, y, -13.4), (8.6, y + 0.9, -11.6), "galvanized", side)
    # rifles
    for i, x in enumerate((-10.6, -7.6, -4.6)):
        b.cube("rf%d_stock" % i, (x - 0.9, 9.6, -13.0), (x + 0.9, 16.4, -12.0), "wood_plank", side)
        b.cube("rf%d_recv" % i, (x - 0.9, 16.4, -13.1), (x + 0.9, 19.4, -11.9), "dark_steel", side)
        b.cube("rf%d_barrel" % i, (x - 0.5, 19.4, -12.8), (x + 0.5, 28.6, -12.2), "steel_plate", side)
        b.cube("rf%d_muzzle" % i, (x - 0.7, 28.6, -13.0), (x + 0.7, 29.6, -12.0), "dark_steel", side)
        b.cube("rf%d_sight" % i, (x - 0.3, 19.4, -13.5), (x + 0.3, 21.6, -13.1), "glow_red", side, hide={"down", "up"})
    # swords
    for i, x in enumerate((-0.6, 2.8)):
        b.cube("sw%d_blade" % i, (x - 0.7, 11.0, -12.9), (x + 0.7, 23.6, -12.3), "galvanized", side)
        b.cube("sw%d_tip" % i, (x - 0.4, 23.6, -12.8), (x + 0.4, 25.0, -12.4), "galvanized", side)
        b.cube("sw%d_guard" % i, (x - 2.2, 10.0, -13.1), (x + 2.2, 11.0, -12.1), "brass", side)
        b.cube("sw%d_grip" % i, (x - 0.5, 8.4, -12.8), (x + 0.5, 10.0, -12.4), "rubber", side)
        b.cube("sw%d_pommel" % i, (x - 0.8, 7.6, -13.0), (x + 0.8, 8.4, -12.2), "brass", side)
    # shield
    sx = 6.2
    b.cube("sh_a", (sx - 2.8, 13.0, -13.4), (sx + 2.8, 23.0, -12.6), "steel_plate", side)
    b.cube("sh_b", (sx - 2.8, 13.0, -13.4), (sx + 2.8, 23.0, -12.6), "steel_plate", side, rotation=(0, 0, 45), origin=(sx, 18, -13.0))
    b.cube("sh_face", (sx - 2.0, 15.0, -13.7), (sx + 2.0, 21.0, -13.3), "warning_paint_red", side)
    b.cube("sh_stripe", (sx - 0.5, 13.4, -13.8), (sx + 0.5, 22.6, -13.4), "warning_paint_yellow", side)
    b.cube("sh_boss", (sx - 1.0, 17.0, -14.0), (sx + 1.0, 19.0, -13.6), "brass", side)
    # inner corner: anvil press + hydraulic ram
    px, pz = 7.5, -7.5
    b.cube("pr_base", (px - 3.2, Y0, pz - 3.2), (px + 3.2, 5.6, pz + 3.2), "dark_steel", side)
    b.cube("pr_base_band", (px - 3.4, 4.4, pz - 3.4), (px + 3.4, 5.0, pz + 3.4), "hazard_stripe", side)
    b.cube("pr_anvil", (px - 2.6, 5.6, pz - 1.8), (px + 2.6, 7.4, pz + 1.8), "steel_plate", side)
    b.cube("pr_horn", (px - 4.4, 6.4, pz - 0.9), (px - 2.6, 7.4, pz + 0.9), "steel_plate", side)
    b.cube("pr_hot", (px - 1.6, 7.4, pz - 1.0), (px + 1.6, 7.8, pz + 1.0), {"up": "glow_amber", "*": "glow_amber"}, side, hide={"down"})
    for sgn, nm in ((-1, "a"), (1, "b")):
        b.cube("pr_post_" + nm, (px + sgn * 3.2 - 0.6, 5.6, pz - 0.6), (px + sgn * 3.2 + 0.6, 20.0, pz + 0.6), "steel_plate", side)
    b.cube("pr_head", (px - 3.8, 20.0, pz - 1.4), (px + 3.8, 22.0, pz + 1.4), {"north": "hazard_stripe", "*": "dark_steel"}, side)
    b.cube("pr_cyl", (px - 1.4, 22.0, pz - 1.4), (px + 1.4, 26.0, pz + 1.4), "copper", side, hide={"down"})
    b.cube("pr_cyl_cap", (px - 1.0, 26.0, pz - 1.0), (px + 1.0, 27.0, pz + 1.0), "brass", side, hide={"down"})
    b.cube("pr_gauge", (px - 0.6, 23.0, pz - 1.8), (px + 0.6, 24.6, pz - 1.4), "glow_cyan", side, hide={"down", "up"})
    ram = b.group("ram_n", parent=side, origin=(px, 8.0, pz))
    b.cube("ram_rod", (px - 0.6, 10.2, pz - 0.6), (px + 0.6, 21.0, pz + 0.6), "galvanized", ram)
    b.cube("ram_head", (px - 2.2, 8.0, pz - 1.6), (px + 2.2, 10.2, pz + 1.6), "dark_steel", ram)
    b.cube("ram_face", (px - 2.4, 8.0, pz - 1.8), (px + 2.4, 8.8, pz + 1.8), "hazard_stripe", ram)
    # ammo crate
    cr = b.group("crate_n", parent=side, origin=(-1.0, Y0, -7.8))
    b.cube("cr_box", (-3.4, Y0, -9.6), (1.4, 7.6, -6.0), {"up": "warning_paint_yellow", "*": "dark_steel"}, cr)
    b.cube("cr_band", (-3.5, 4.6, -9.7), (1.5, 5.4, -5.9), "warning_paint_yellow", cr, hide={"up", "down"})
    b.cube("cr_label", (-1.6, 5.8, -9.8), (-0.4, 7.0, -9.6), "warning_paint_red", cr, hide={"up", "down"})
    b.cube("cr_clasp", (-1.2, 7.6, -8.2), (-0.8, 8.0, -7.4), "brass", cr, hide={"down"})
    b.cube("cr_clasp2", (-0.6, 7.6, -8.2), (-0.2, 8.0, -7.4), "brass", cr, hide={"down"})
    # ---- 4-fold --------------------------------------------------------------------------------
    b.m.radial4([side], ("_e", "_s", "_w"))
    b.cube("cross_x", (-12.0, 35.0, -0.8), (12.0, 36.6, 0.8), "dark_steel", fr)
    b.cube("cross_z", (-0.8, 34.7, -12.0), (0.8, 36.3, 12.0), "dark_steel", fr)
    industrial_status_mast(b, 0, 0, 36.6)
    # ---- animation --------------------------------------------------------------------------------
    b.spin("stand", "y", 4.0)
    for n, ph in (("ram_n", 0.0), ("ram_n_e", 0.25), ("ram_n_s", 0.5), ("ram_n_w", 0.75)):
        b.piston(n, "y", 4.5, 2.0, ph)
    b.input_bones(["stand"])
    b.output_bones(["crate_n", "crate_n_e", "crate_n_s", "crate_n_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
