#!/usr/bin/env python3
"""Blocky crusher (structure_crusher): an edge-runner (pan) mill, 4-fold symmetric.

A stone pan with a gravel floor, a central spruce shaft carrying four millstone runner wheels on radial axles,
held at the top by a timber frame. Raw ore heaps sit at the pad corners, dust sacks at the side middles.

    python3 tools/generate/structures/models/blocky_crusher.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_crusher.bbmodel")

COBBLE = "mc:block/cobblestone"
BRICKS = "mc:block/stone_bricks"
SMOOTH = "mc:block/smooth_stone"
STONE = "mc:block/stone"
GRAVEL = "mc:block/gravel"
LOG = {"up": "mc:block/spruce_log_top", "down": "mc:block/spruce_log_top", "*": "mc:block/spruce_log"}
PLANK = "mc:block/spruce_planks"
DARK = "mc:block/dark_oak_planks"


def rot(x, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def build():
    b = Builder("crusher", run_length=4.0)
    # ---- ground pad ----------------------------------------------------------------------
    b.cube("pad", (-16, 0, -16), (16, 2, 16), {"up": COBBLE, "*": COBBLE}, "frame")
    b.cube("pad_trim", (-15, 2, -15), (15, 2.4, 15), BRICKS, "frame", hide={"down"})
    # ---- pan: stone ring wall with a gravel floor ----------------------------------------
    b.group("pan", parent="frame")
    b.ring("pan_wall", 0, 0, 2.4, 7, 12.6, 10.8, BRICKS, 16, "pan")
    b.ring("pan_cap", 0, 0, 7, 7.8, 12.9, 10.6, SMOOTH, 16, "pan")
    b.cylinder("pan_floor", 0, 0, 2.4, 3.6, 11.0, {"*": GRAVEL}, 16, "pan")
    # ---- timber frame: 4 posts, ring beams, cross beams, bearing -------------------------
    b.group("timber", parent="frame")
    P, W = 11.5, 1.2
    for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        b.cube("post%d" % i, (sx * P - W, 2.4, sz * P - W), (sx * P + W, 33, sz * P + W), LOG, "timber")
        b.cube("foot%d" % i, (sx * P - 1.8, 2.4, sz * P - 1.8), (sx * P + 1.8, 4.4, sz * P + 1.8), COBBLE, "timber")
    inner = P - W
    for i, s in enumerate((-1, 1)):
        b.cube("beam_x%d" % i, (-inner, 29.8, s * P - W), (inner, 33, s * P + W), PLANK, "timber")
        b.cube("beam_z%d" % i, (s * P - W, 29.8, -inner), (s * P + W, 33, inner), PLANK, "timber")
    b.cube("cross_x", (-inner, 29.8, -1.4), (inner, 33, 1.4), PLANK, "timber")
    for i, (a, c) in enumerate(((-inner, -1.4), (1.4, inner))):
        b.cube("cross_z%d" % i, (-1.4, 29.8, a), (1.4, 33, c), PLANK, "timber")
    b.cube("bearing", (-2.6, 33, -2.6), (2.6, 35.4, 2.6), DARK, "timber")
    b.cube("bearing_cap", (-3.4, 35.4, -3.4), (3.4, 36, 3.4), LOG, "timber")
    # ---- runner assembly (spins): shaft, collar, axles, wheels ---------------------------
    b.group("runner", parent="frame", origin=(0, 0, 0))
    b.cylinder("shaft", 0, 0, 3.6, 30, 1.7, LOG, 8, "runner")
    b.cylinder("collar", 0, 0, 6.0, 10.4, 2.5, {"*": PLANK, "up": PLANK}, 8, "runner")
    WY, WR, WT, WX = 8.1, 4.5, 3.0, 7.2
    for k in range(4):
        axis = "x" if k % 2 == 0 else "z"
        sgn = 1 if k < 2 else -1
        ax, az = ((sgn, 0) if axis == "x" else (0, sgn))
        name = "wheel%d" % k
        # axle: from the collar out through the wheel
        lo, hi = 2.2, WX + WT / 2 + 0.6
        if axis == "x":
            frm, to = (min(sgn * lo, sgn * hi), WY - 0.8, -0.8), (max(sgn * lo, sgn * hi), WY + 0.8, 0.8)
        else:
            frm, to = (-0.8, WY - 0.8, min(sgn * lo, sgn * hi)), (0.8, WY + 0.8, max(sgn * lo, sgn * hi))
        b.cube("axle%d" % k, frm, to, LOG, "runner")
        centre = (ax * WX, WY, az * WX)
        outer = b.group(name, parent="runner", origin=centre)
        b.pipe(name + "_disc", centre, WT, WR, axis, {"*": STONE, "up": STONE}, 12, outer, cap_mat=SMOOTH)
        # hub cap on the outer face
        b.pipe(name + "_hub", (ax * (WX + WT / 2 + 0.3), WY, az * (WX + WT / 2 + 0.3)), 0.8, 1.5, axis, LOG, 8, outer,
               cap_mat="mc:block/spruce_log_top")
    # ---- ore heaps (corners, input) and dust sacks (side middles, output) ----------------
    b.group("heaps", parent="frame")
    for k in range(4):
        x, z = rot(14.3, 14.3, k)
        nm = "heap%d" % k
        b.cube(nm + "_a", (x - 1.6, 2, z - 1.6), (x + 1.6, 4.2, z + 1.6), {"*": "mc:block/raw_iron_block"}, "heaps")
        b.cube(nm + "_b", (x - 1.1, 4.2, z - 1.1), (x + 1.1, 5.6, z + 1.1), {"*": "mc:block/iron_ore"}, "heaps")
    b.group("sacks", parent="frame")
    for k in range(4):
        x, z = rot(14.3, 0, k)
        nm = "sack%d" % k
        if k % 2 == 0:
            b.cube(nm + "_a", (x - 1.5, 2, z - 2.8), (x + 1.5, 5, z - 0.2), "mc:block/white_wool", "sacks")
            b.cube(nm + "_b", (x - 1.5, 2, z + 0.4), (x + 1.5, 4.4, z + 3.0), "mc:block/white_wool", "sacks")
            b.cube(nm + "_c", (x - 1.1, 5, z - 2.3), (x + 1.1, 6.4, z - 0.4), "mc:block/white_wool", "sacks")
        else:
            b.cube(nm + "_a", (x - 2.8, 2, z - 1.5), (x - 0.2, 5, z + 1.5), "mc:block/white_wool", "sacks")
            b.cube(nm + "_b", (x + 0.4, 2, z - 1.5), (x + 3.0, 4.4, z + 1.5), "mc:block/white_wool", "sacks")
            b.cube(nm + "_c", (x - 2.3, 5, z - 1.1), (x - 0.4, 6.4, z + 1.1), "mc:block/white_wool", "sacks")
    # ---- animation -----------------------------------------------------------------------
    b.spin("runner", "y", period=4.0)
    for k in range(4):
        b.spin("wheel%d" % k, "x" if k % 2 == 0 else "z", period=2.0, direction=(-1 if k < 2 else 1))
    b.input_bones(["heaps"])
    b.output_bones(["sacks"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
