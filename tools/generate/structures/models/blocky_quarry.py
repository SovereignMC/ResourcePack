#!/usr/bin/env python3
"""Blocky quarry (structure_quarry): a terraced hillside stone quarry, 4-fold symmetric.

A stepped rock mass (three benches per side, gravel bench tops) with a cut shaft in the middle, a low spruce
hoist frame over the shaft raising and lowering a cut stone block on a rope, four winch drums on the frame and
cut stone stacks at the pad corners.

    python3 tools/generate/structures/models/blocky_quarry.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_quarry.bbmodel")

GRAVEL = "mc:block/gravel"
LOG = {"up": "mc:block/spruce_log_top", "down": "mc:block/spruce_log_top", "*": "mc:block/spruce_log"}
PLANK = "mc:block/spruce_planks"
ROPE = "mc:block/hay_block_side#a58f5a"


def rot(x, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def build():
    b = Builder("quarry", run_length=4.0)
    # ---- pad -------------------------------------------------------------------------------
    b.cube("pad", (-16, 0, -16), (16, 1.5, 16), "mc:block/coarse_dirt", "frame")
    # ---- rock mass: three benches, strata change per tier ----------------------------------
    b.group("rock", parent="frame")
    b.cube("tier0", (-12.5, 1.5, -12.5), (12.5, 7.5, 12.5), {"up": GRAVEL, "*": "mc:block/stone#d8c8a8"}, "rock")
    b.cube("tier1", (-9.5, 7.5, -9.5), (9.5, 13.5, 9.5), {"up": GRAVEL, "*": "mc:block/andesite#e0c8b0"}, "rock")
    # top tier is a box ring around the cut shaft (shaft floor = tier1 top)
    R, H = 6.5, 3.0
    top = {"up": GRAVEL, "*": "mc:block/cobblestone#d8c8a8"}
    b.cube("tier2_n", (-R, 13.5, -R), (R, 19.5, -H), top, "rock")
    b.cube("tier2_s", (-R, 13.5, H), (R, 19.5, R), top, "rock")
    b.cube("tier2_w", (-R, 13.5, -H), (-H, 19.5, H), top, "rock")
    b.cube("tier2_e", (H, 13.5, -H), (R, 19.5, H), top, "rock")
    # rubble on the benches and a stone drill-cut band on the lowest face
    b.group("rubble", parent="frame")
    for k in range(4):
        x, z = rot(10.9, 10.9, k)
        b.cube("rub0_%d" % k, (x - 1.3, 7.5, z - 1.3), (x + 1.3, 9.0, z + 1.3), "mc:block/cobblestone", "rubble")
        b.cube("rub0b_%d" % k, (x - 0.5 + (0.8 if x < 0 else -0.8) * 1.6, 7.5, z - 0.5), (x + 0.6 + (0.8 if x < 0 else -0.8) * 1.6, 8.2, z + 0.6),
               GRAVEL, "rubble")
        x, z = rot(7.9, 7.9, k)
        b.cube("rub1_%d" % k, (x - 1.0, 13.5, z - 1.0), (x + 1.0, 14.9, z + 1.0), "mc:block/stone", "rubble")
        # cut stone lying on the middle of the lowest bench
        x, z = rot(0, -11.0, k)
        if k % 2 == 0:
            b.cube("slab_%d" % k, (-2.4, 7.5, z - 1.2), (2.4, 9.3, z + 1.2), "mc:block/smooth_stone", "rubble")
        else:
            b.cube("slab_%d" % k, (x - 1.2, 7.5, -2.4), (x + 1.2, 9.3, 2.4), "mc:block/smooth_stone", "rubble")
    # ---- hoist frame ----------------------------------------------------------------------
    b.group("hoist", parent="frame")
    P, W = 5.0, 1.0
    for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        b.cube("leg%d" % i, (sx * P - W, 19.5, sz * P - W), (sx * P + W, 35.5, sz * P + W), LOG, "hoist")
    inner = P - W
    for i, s in enumerate((-1, 1)):
        b.cube("beam_x%d" % i, (-inner, 32.5, s * P - W), (inner, 35.5, s * P + W), PLANK, "hoist")
        b.cube("beam_z%d" % i, (s * P - W, 32.5, -inner), (s * P + W, 35.5, inner), PLANK, "hoist")
    b.cube("cross_x", (-inner, 32.5, -1.0), (inner, 35.5, 1.0), PLANK, "hoist")
    b.cube("cross_z0", (-1.0, 32.5, -inner), (1.0, 35.5, -1.0), PLANK, "hoist")
    b.cube("cross_z1", (-1.0, 32.5, 1.0), (1.0, 35.5, inner), PLANK, "hoist")
    b.cube("pulley", (-2.2, 35.5, -2.2), (2.2, 37.5, 2.2), "mc:block/dark_oak_planks", "hoist")
    # winch drums on the four beams (axis along the beam), all spinning
    for k in range(4):
        x, z = rot(0, -P, k)
        axis = "x" if k % 2 == 0 else "z"
        centre = (x, 37.1, z)
        outer = b.group("drum%d" % k, parent="hoist", origin=centre)
        b.pipe("drum%d_barrel" % k, centre, 5.0, 1.5, axis, LOG, 8, outer)
        for s, off in (("a", -2.3), ("b", 2.3)):
            c2 = (centre[0] + (off if axis == "x" else 0), 37.1, centre[2] + (off if axis == "z" else 0))
            b.pipe("drum%d_fl%s" % (k, s), c2, 0.8, 2.0, axis, PLANK, 8, outer)
    # ---- hoisted cut block on a rope (piston in Y) ----------------------------------------
    b.group("block", parent="frame", origin=(0, 13.5, 0))
    b.cube("block_stone", (-2.0, 13.5, -2.0), (2.0, 17.5, 2.0), {"*": "mc:block/stone_bricks", "up": "mc:block/smooth_stone"}, "block")
    b.cube("block_sling", (-2.4, 17.5, -0.5), (2.4, 18.3, 0.5), ROPE, "block")
    TOP = 37.0
    b.group("rope", parent="frame", origin=(0, TOP, 0))
    L = TOP - 18.3
    b.cube("rope", (-0.4, 18.3, -0.4), (0.4, TOP, 0.4), ROPE, "rope")
    # ---- cut stone stacks in the pad corners (output) -------------------------------------
    b.group("stacks", parent="frame")
    for k in range(4):
        x, z = rot(14.2, 14.2, k)
        n = "stack%d" % k
        b.cube(n + "_a", (x - 1.7, 1.5, z - 1.7), (x + 1.7, 4.7, z + 1.7), "mc:block/smooth_stone", "stacks")
        b.cube(n + "_b", (x - 1.6, 4.7, z - 1.6), (x + 1.6, 7.9, z + 1.6), "mc:block/stone_bricks", "stacks")
        b.cube(n + "_c", (x - 1.2, 7.9, z - 1.2), (x + 1.2, 10.1, z + 1.2), "mc:block/smooth_stone", "stacks")
    # ---- animation -------------------------------------------------------------------------
    S = 6.0
    b.piston("block", "y", S, 4.0)
    # rope shortens by S as the block rises: scale y about the top anchor
    b._add("rope", "scale", "y", "osc",
           lambda t, p=4.0: 1 - (S / (2 * L)) * (1 - math.cos(2 * math.pi * t / p)), 4.0)
    for k in range(4):
        b.spin("drum%d" % k, "x" if k % 2 == 0 else "z", period=4.0, direction=(1 if k < 2 else -1))
    b.input_bones(["block", "drum0", "drum1", "drum2", "drum3"])
    b.output_bones(["stacks"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
