#!/usr/bin/env python3
"""Blocky crop farm (structure_crop_farm): four raised crop beds around a wooden water tower, 4-fold symmetric.

    python3 tools/generate/structures/models/blocky_crop_farm.py            # writes bbmodels/structure_crop_farm.bbmodel
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_crop_farm.bbmodel")

SPRUCE = "mc:block/spruce_planks"
OAK = "mc:block/oak_planks"
DARK = "mc:block/dark_oak_planks"
IRON = "mc:block/iron_block#8a8a8a"
WATER = "mc:block/water_still#3f76e4"
WHEAT = "mc:block/wheat_stage7"
SFX = ("_e", "_s", "_w")
G = 2.0                      # ground top


def plane(b, name, x0, z0, x1, z1, y0, y1, group):
    """Cut-out wheat plane along x or z (a 0.1 thin box showing the two big faces only)."""
    if abs(z1 - z0) < 0.01:
        b.cube(name, (x0, y0, z0 - 0.05), (x1, y1, z0 + 0.05), WHEAT, group, hide={"up", "down", "east", "west"})
    else:
        b.cube(name, (x0 - 0.05, y0, z0), (x0 + 0.05, y1, z1), WHEAT, group, hide={"up", "down", "north", "south"})


def build():
    b = Builder("crop_farm", run_length=4.0)
    b.group("farm", parent="frame")
    b.cube("pad", (-16, 0, -16), (16, G, 16), {"up": "mc:block/grass_block_top#79c05a", "*": "mc:block/dirt"}, "farm")
    # tower foundation (cobble) + path
    b.cube("foot", (-6.4, G, -6.4), (6.4, 3.4, 6.4), "mc:block/cobblestone", "farm", hide={"down"})

    # ---- tower: four spruce legs, braces, tank on a plank deck, conical roof -------------------------------
    t = b.group("tower", parent="frame")
    for i, (x, z) in enumerate(((-4.8, -4.8), (3.4, -4.8), (-4.8, 3.4), (3.4, 3.4))):
        b.cube("leg%d" % i, (x, 3.4, z), (x + 1.4, 21.0, z + 1.4), "mc:block/stripped_spruce_log", t, hide={"down"})
    for y, w in ((9.0, 0.8), (15.0, 0.8)):          # horizontal rails
        for nm, f, to in (("n", (-4.8, y, -4.8), (4.8, y + w, -4.0)), ("s", (-4.8, y, 4.0), (4.8, y + w, 4.8)),
                          ("w", (-4.8, y, -4.0), (-4.0, y + w, 4.0)), ("e", (4.0, y, -4.0), (4.8, y + w, 4.0))):
            b.cube("rail_%s_%d" % (nm, int(y)), f, to, SPRUCE, t)
    for nm, a, c in (("n", (-3.4, 9.8, -4.4), (3.4, 15.0, -4.4)), ("s", (3.4, 9.8, 4.4), (-3.4, 15.0, 4.4))):
        b.strut("xbrace_%s_a" % nm, a, c, 0.8, 0.7, SPRUCE, t)
        b.strut("xbrace_%s_b" % nm, (a[0], 15.0, a[2]), (c[0], 9.8, c[2]), 0.8, 0.7, SPRUCE, t)
    for nm, x in (("w", -4.4), ("e", 4.4)):
        b.strut("zbrace_%s_a" % nm, (x, 9.8, -3.4), (x, 15.0, 3.4), 0.8, 0.7, SPRUCE, t)
        b.strut("zbrace_%s_b" % nm, (x, 15.0, -3.4), (x, 9.8, 3.4), 0.8, 0.7, SPRUCE, t)
    b.cube("deck", (-6.0, 21.0, -6.0), (6.0, 22.4, 6.0), DARK, t, hide={"down"})
    tank = b.group("tank", parent="frame")
    b.cylinder("barrel", 0, 0, 22.4, 31.6, 6.0, {"*": "mc:block/barrel_side", "up": "mc:block/barrel_top"}, 12, tank)
    for i, y in enumerate((23.6, 29.2)):
        b.cylinder("hoop%d" % i, 0, 0, y, y + 1.0, 6.5, IRON, 12, tank, cap_mat=IRON)
    b.cylinder("belly_hoop", 0, 0, 26.4, 27.4, 6.5, IRON, 12, tank, cap_mat=IRON)
    b.taper("roof", 0, 0, 31.6, 36.0, 6.9, 1.4, SPRUCE, 4, 12, tank)
    b.cube("finial", (-0.5, 36.0, -0.5), (0.5, 37.4, 0.5), IRON, tank)
    # spouts + drip per side: chute from the tank over the trough, falling drop (built once then cloned)
    q = b.group("side", parent="frame")
    # trough running north from the tower base
    b.cube("trough_floor", (-2.5, G, -14.8), (2.5, 3.0, -7.0), DARK, q, hide={"down"})
    b.cube("trough_l", (-2.5, 3.0, -14.8), (-1.6, 5.0, -7.0), OAK, q)
    b.cube("trough_r", (1.6, 3.0, -14.8), (2.5, 5.0, -7.0), OAK, q)
    b.cube("trough_end", (-1.6, 3.0, -14.8), (1.6, 5.0, -14.0), OAK, q)
    b.cube("trough_water", (-1.6, 3.0, -14.0), (1.6, 4.4, -7.0), WATER, q, hide={"down", "north", "south", "east", "west"})
    for i, z in enumerate((-13.0, -9.5)):             # legs under the trough lip
        b.cube("trough_brace%d" % i, (-2.9, G, z), (2.9, 3.0, z + 0.8), DARK, q, hide={"down"})
    b.cube("channel", (2.5, 3.0, -10.4), (4.2, 4.2, -8.8), WATER, q, hide={"down", "north", "south", "east", "west"})
    b.cube("spout", (-0.8, 24.0, -8.2), (0.8, 25.4, -5.6), OAK, q)
    b.cube("spout_lip", (-1.2, 23.2, -8.6), (1.2, 25.4, -7.6), OAK, q, hide={"down"})
    dr = b.group("drip", parent=q, origin=(0, 22.6, -8.0))
    b.cube("drip_drop", (-0.45, 21.6, -8.45), (0.45, 22.8, -7.55), WATER, dr)
    # raised crop bed in the NE corner
    bed = b.group("bed", parent=q)
    b.cube("bed_soil", (4.4, G, -15.4), (15.4, 5.6, -4.4), {"up": "mc:block/farmland_moist", "*": "mc:block/dirt"}, bed, hide={"down"})
    b.cube("bed_rim_n", (4.4, G, -15.6), (15.6, 6.2, -14.4), OAK, bed, hide={"down"})
    b.cube("bed_rim_s", (3.8, G, -5.6), (15.6, 6.2, -4.2), OAK, bed, hide={"down"})
    b.cube("bed_rim_w", (3.8, G, -14.4), (5.0, 6.2, -5.6), OAK, bed, hide={"down"})
    b.cube("bed_rim_e", (14.4, G, -14.4), (15.6, 6.2, -5.6), OAK, bed, hide={"down"})
    b.cube("bed_soil2", (5.0, 5.6, -14.4), (14.4, 5.9, -5.6), {"up": "mc:block/farmland_moist", "*": "mc:block/farmland_moist"}, bed, hide={"down"})
    wh = b.group("wheat", parent=bed, origin=(9.9, 5.9, -9.9))
    for i, d in enumerate((-3.4, 3.4)):
        plane(b, "wheat_x%d" % i, 5.6, -9.9 + d, 14.2, -9.9 + d, 5.9, 13.2, wh)
        plane(b, "wheat_z%d" % i, 9.9 + d, -14.2, 9.9 + d, -5.6, 5.9, 13.2, wh)
    # scarecrow in the middle of the #
    sc = b.group("scarecrow", parent=bed)
    b.cube("sc_post", (9.4, 5.9, -10.4), (10.4, 19.0, -9.4), OAK, sc)
    b.cube("sc_arms", (6.4, 14.0, -10.2), (13.4, 15.0, -9.6), OAK, sc)
    b.cube("sc_body", (8.4, 10.0, -11.0), (11.4, 14.8, -8.8), "mc:block/red_wool", sc)
    b.cube("sc_sleeve_l", (6.0, 12.8, -10.6), (7.8, 14.4, -9.2), "mc:block/red_wool", sc)
    b.cube("sc_sleeve_r", (11.8, 12.8, -10.6), (13.6, 14.4, -9.2), "mc:block/red_wool", sc)
    b.cube("sc_head", (8.6, 14.8, -11.2), (11.4, 17.4, -8.6), "mc:block/hay_block_side", sc)
    b.cube("sc_hat", (7.8, 17.4, -12.0), (12.2, 18.0, -8.0), "mc:block/dark_oak_planks", sc)
    b.cube("sc_hat_top", (8.8, 18.0, -11.0), (11.2, 19.6, -9.0), "mc:block/dark_oak_planks", sc)
    b.m.radial4([q], SFX)

    # ---- animation ---------------------------------------------------------------------------------------------
    for i, sfx in enumerate(("",) + SFX):
        b.oscillate("wheat" + sfx, "rotation", "x", 2.0, 2.0, phase=i * 0.25)
        b.oscillate("wheat" + sfx, "rotation", "z", 1.5, 2.0, phase=i * 0.25 + 0.25)
        b.rise("drip" + sfx, -16.0, 1.0, phase=i * 0.25, scale_from=1.0, scale_to=1.0)
    b.input_bones(["tank"])
    b.output_bones(["wheat", "wheat_e", "wheat_s", "wheat_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
