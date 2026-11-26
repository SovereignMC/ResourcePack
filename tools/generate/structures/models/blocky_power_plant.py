#!/usr/bin/env python3
"""Blocky power plant (structure_power_plant): early steam / dynamo power house, 4-fold symmetric.

    python3 tools/generate/structures/models/blocky_power_plant.py            # writes bbmodels/structure_power_plant.bbmodel
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_power_plant.bbmodel")

BRICK = "mc:block/bricks"
STONE = "mc:block/stone_bricks"
ROOF = "mc:block/deepslate_tiles"
IRON = "mc:block/iron_block#707070"
BELT = "mc:block/black_wool"
COPPER = "mc:block/copper_block"
COAL = "mc:block/coal_block"
SFX = ("_e", "_s", "_w")
WY, WR, WX = 8.0, 5.6, -3.5          # flywheel centre height, radius, x offset along the wall
WZ = -11.0                           # flywheel plane (north wall at z = -9)
PX, PY, PR = 4.4, 4.7, 1.6           # dynamo pulley


def sq_ring(b, name, y0, y1, ro, ri, mat, group):
    """Square ring from four pinwheel boxes (no overlap)."""
    w = ro - ri
    b.cube(name + "_n", (-ro, y0, -ro), (ro - w, y1, -ri), mat, group)
    b.cube(name + "_e", (ri, y0, -ro), (ro, y1, ro - w), mat, group)
    b.cube(name + "_s", (-(ro - w), y0, ri), (ro, y1, ro), mat, group)
    b.cube(name + "_w", (-ro, y0, -(ro - w)), (-ri, y1, ro), mat, group)


LT = 24.5  # status lamp housing base (lenses at LT+4..LT+6 on the chimney collar)


def build():
    b = Builder("power_plant", run_length=4.0)
    b.group("hall", parent="frame")
    # stone-brick plinth with a cobble kerb
    b.cube("plinth", (-16, 0, -16), (16, 2, 16), {"up": STONE, "*": STONE}, "hall")

    # boiler house
    b.cube("house", (-9, 2, -9), (9, 14, 9), {"*": BRICK, "up": BRICK}, "hall", hide={"down"})
    b.cube("roof1", (-10.6, 14, -10.6), (10.6, 15.6, 10.6), ROOF, "hall", hide={"down"})
    b.cube("roof2", (-8.2, 15.6, -8.2), (8.2, 17.2, 8.2), ROOF, "hall", hide={"down"})
    b.cube("roof3", (-5.6, 17.2, -5.6), (5.6, 18.8, 5.6), ROOF, "hall", hide={"down"})
    # chimney
    ch = b.group("chimney", parent="frame")
    for nm, y0, y1, r in (("ch1", 18.8, 25, 3.5), ("ch2", 25, LT + 3, 3.0), ("ch2b", LT + 7, 32, 3.0),
                          ("ch3", 32, 38, 2.5)):
        b.cube(nm, (-r, y0, -r), (r, y1, r), BRICK, ch, hide={"down"})
    # status lamps: a dark iron collar round the chimney (lenses on its four faces, gold hoods above them)
    b.status_lamps(0, 0, LT)
    b.cube("lamp_collar", (-3.0, LT + 3, -3.0), (3.0, LT + 7, 3.0), "mc:block/iron_block#444444", ch, hide={"down", "up"})
    for nm, f, t in (("n", (-2, LT + 6.3, -3.7), (2, LT + 6.9, -3)), ("s", (-2, LT + 6.3, 3), (2, LT + 6.9, 3.7)),
                     ("e", (3, LT + 6.3, -2), (3.7, LT + 6.9, 2)), ("w", (-3.7, LT + 6.3, -2), (-3, LT + 6.9, 2))):
        b.cube("lamp_hood_" + nm, f, t, "mc:block/gold_block", ch)
    b.cube("ch_band1", (-3.2, 24.4, -3.2), (3.2, 25.4, 3.2), STONE, ch)
    b.cube("ch_band2", (-2.7, 31.4, -2.7), (2.7, 32.4, 2.7), STONE, ch)
    sq_ring(b, "ch_rim", 38, 40, 3.2, 1.8, "mc:block/blackstone", ch)
    sq_ring(b, "ch_rim2", 37.4, 38, 3.0, 2.2, "mc:block/blackstone", ch)
    b.cube("ch_soot", (-1.8, 36, -1.8), (1.8, 39.4, 1.8), "mc:block/black_wool", ch, hide={"down", "north", "south", "east", "west"})

    # ---- north module: corner quoins, window, flywheel + belt + dynamo, coal heap ---------------------------
    m = b.group("side", parent="frame")
    b.cube("quoin", (7.4, 2, -9.4), (9.4, 14.4, -7.4), STONE, m, hide={"down"})
    b.cube("quoin_foot", (7.0, 2, -9.8), (9.8, 3.4, -7.0), "mc:block/cobblestone", m, hide={"down"})
    b.cube("win_frame", (4.4, 8.6, -9.5), (8.2, 13.0, -8.6), "mc:block/dark_oak_planks", m)
    b.cube("win_glow", (5.0, 9.2, -9.8), (7.6, 12.4, -9.4), "mc:block/glowstone", m, hide={"down", "up"})
    b.cube("win_bar", (6.1, 9.2, -9.95), (6.5, 12.4, -9.8), "mc:block/dark_oak_planks", m)
    b.cube("win_sill", (4.0, 8.2, -10.1), (8.6, 8.8, -9.0), STONE, m)
    # flywheel (spins about z): 12-sided rim, hub, 8 spokes, axle through the wall
    b.group("wheel", parent=m, origin=(WX, WY, WZ))
    inner = b.group("wheel_t", parent="wheel", origin=(WX, WY, WZ), rotation=(90, 0, 0))
    b.ring("wheel_rim", WX, WZ, WY - 0.8, WY + 0.8, WR, WR - 1.3, IRON, 12, inner)
    for i, ang in enumerate((0, 45, 90, 135)):
        b.cube("wheel_spoke%d" % i, (WX - WR + 0.6, WY - 0.55, WZ - 0.55), (WX + WR - 0.6, WY + 0.55, WZ + 0.55), IRON,
               inner, rotation=(0, ang, 0) if ang else None, origin=(WX, WY, WZ))
    b.cylinder("wheel_hub", WX, WZ, WY - 1.1, WY + 1.1, 1.7, "mc:block/gold_block", 8, inner)
    # axle through the wall bearing (static part of the bone)
    b.cube("axle", (WX - 0.7, WY - 0.7, WZ + 0.8), (WX + 0.7, WY + 0.7, -8.6), IRON, "wheel")
    b.cube("bearing", (WX - 1.5, WY - 1.5, -9.7), (WX + 1.5, WY + 1.5, -9.0), STONE, m)
    # dynamo with pulley and belt
    dy = b.group("dynamo", parent=m, origin=(7.4, 4.3, WZ))
    b.cube("dyn_body", (5.8, 2, WZ - 1.9), (9.2, 6.6, WZ + 1.9), COPPER, dy)
    b.cube("dyn_band", (6.6, 6.6, WZ - 2.1), (8.4, 6.9, WZ + 2.1), IRON, dy, hide={"down"})
    b.cube("dyn_band2", (5.6, 3.0, WZ - 2.1), (9.4, 3.5, WZ + 2.1), IRON, dy, hide={"down"})
    b.cube("dyn_cap", (6.2, 6.6, WZ - 1.5), (8.8, 7.4, WZ + 1.5), "mc:block/iron_block#444444", dy, hide={"down"})
    b.cube("dyn_post", (7.0, 7.4, WZ - 0.4), (7.6, 8.4, WZ + 0.4), COPPER, dy)
    b.cube("dyn_shaft", (PX + PR - 0.4, PY - 0.5, WZ - 0.5), (5.8, PY + 0.5, WZ + 0.5), IRON, dy)
    b.group("pulley", parent=dy, origin=(PX, PY, WZ))
    pin = b.group("pulley_t", parent="pulley", origin=(PX, PY, WZ), rotation=(90, 0, 0))
    b.cylinder("pulley_body", PX, WZ, PY - 0.9, PY + 0.9, PR, IRON, 8, pin)
    # belt: open belt, two tangent strands
    d = math.hypot(PX - WX, PY - WY)
    base = math.atan2(PY - WY, PX - WX)
    beta = math.acos((WR - PR) / d)
    for nm, sgn in (("belt_hi", 1), ("belt_lo", -1)):
        th = base + sgn * beta
        p1 = (WX + WR * math.cos(th), WY + WR * math.sin(th))
        p2 = (PX + PR * math.cos(th), PY + PR * math.sin(th))
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        ang = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
        c = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        b.cube(nm, (c[0] - L / 2, c[1] - 0.35, WZ - 0.7), (c[0] + L / 2, c[1] + 0.35, WZ + 0.7), BELT, m,
               rotation=(0, 0, ang), origin=(c[0], c[1], WZ))
    # coal heap in the NE corner
    hp = b.group("heap", parent=m, origin=(12.7, 2, -12.7))
    b.cube("heap_a", (10.0, 2, -15.4), (15.4, 4.2, -10.0), COAL, hp, hide={"down"})
    b.cube("heap_b", (10.9, 4.2, -14.5), (14.5, 6.0, -10.9), COAL, hp)
    b.cube("heap_c", (11.8, 6.0, -13.6), (13.6, 7.2, -11.8), COAL, hp)
    b.cube("heap_lump", (14.4, 2, -9.9), (15.8, 3.3, -8.7), COAL, hp, hide={"down"})
    b.cube("heap_lump2", (9.4, 2, -15.8), (10.6, 3.1, -14.6), COAL, hp, hide={"down"})
    b.m.radial4([m], SFX)


    # ---- animation -------------------------------------------------------------------------------------------
    for sfx, ax, d in (("", "z", 1), ("_e", "x", -1), ("_s", "z", -1), ("_w", "x", 1)):
        b.spin("wheel" + sfx, ax, 4.0, d)
        b.spin("pulley" + sfx, ax, 1.0, d)
    b.smoke("ch", 0, 40.0, 0, puffs=3, rise=8, period=4.0, size=3.0, group="chimney", mat="mc:block/light_gray_wool")
    b.input_bones(["heap", "heap_e", "heap_s", "heap_w"])
    b.output_bones(["dynamo", "dynamo_e", "dynamo_s", "dynamo_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
