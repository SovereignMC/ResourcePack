#!/usr/bin/env python3
"""Blocky mud pit (structure_mud_pit): a clay pit with a horse-gin pug mill, 4-fold symmetric.

    python3 tools/generate/structures/models/blocky_mud_pit.py            # writes bbmodels/structure_mud_pit.bbmodel
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_mud_pit.bbmodel")

LOG = {"*": "mc:block/spruce_log", "east": "mc:block/spruce_log_top", "west": "mc:block/spruce_log_top"}
LOG_Z = {"*": "mc:block/spruce_log", "north": "mc:block/spruce_log_top", "south": "mc:block/spruce_log_top"}
PLANK = "mc:block/spruce_planks"
IRON = "mc:block/iron_block#8a8a8a"
WATER = "mc:block/water_still#3f76e4"
SFX = ("_e", "_s", "_w")


def build():
    b = Builder("mud_pit", run_length=8.0)
    # ground pad + sunken mud floor
    b.group("pit", parent="frame")
    b.cube("pad", (-16, 0, -16), (16, 1.5, 16), {"up": "mc:block/coarse_dirt", "*": "mc:block/dirt"}, "pit")
    b.cube("mud", (-11, 1.5, -11), (11, 3.0, 11), {"up": "mc:block/mud", "*": "mc:block/mud"}, "pit")

    # ---- one quarter (north side + NE corner), cloned 4x ----------------------------------------------
    q = b.group("quarter", parent="frame")
    # retaining rim of spruce logs, pinwheel so every corner is closed
    b.cube("rim_log", (-14, 1.5, -14), (11, 4.4, -11), LOG, q)
    b.cube("rim_log_lo", (-14, 4.4, -13.4), (11, 5.2, -11.6), "mc:block/stripped_spruce_log", q, hide={"east", "west"})
    for i, x in enumerate((-9, -1.5, 6)):          # staples / pegs through the log
        b.cube("rim_peg%d" % i, (x, 4.4, -13.2), (x + 1.2, 5.5, -12.0), "mc:block/dark_oak_planks", q)
    b.cube("rim_post", (9.6, 4.4, -14.0), (12.4, 7.4, -11.0), "mc:block/stripped_spruce_log", q, hide={"down"})
    b.cube("rim_post_cap", (9.2, 7.4, -14.4), (12.8, 8.1, -10.6), "mc:block/dark_oak_planks", q, hide={"down"})
    # drying pallet with stacked clay blocks and mud bricks (the output)
    out = b.group("stack", parent=q, origin=(8.5, 3, -8.5))
    b.cube("pallet", (5.6, 3.0, -11.0), (11.0, 3.9, -6.0), PLANK, out)
    for i, (x, z) in enumerate(((5.8, -10.8), (8.9, -10.8), (5.8, -7.0), (8.9, -7.0))):
        b.cube("pallet_foot%d" % i, (x, 1.5, z), (x + 1.8, 3.0, z + 1.2), "mc:block/dark_oak_planks", out)
    b.cube("clay_a", (5.9, 3.9, -10.8), (8.4, 6.0, -8.3), "mc:block/clay", out)
    b.cube("clay_b", (8.5, 3.9, -10.8), (10.8, 6.0, -8.3), "mc:block/clay", out)
    b.cube("brick_a", (5.9, 3.9, -8.2), (8.4, 5.7, -6.2), "mc:block/mud_bricks", out)
    b.cube("brick_b", (8.5, 3.9, -8.2), (10.8, 5.7, -6.2), "mc:block/mud_bricks", out)
    b.cube("clay_top", (6.8, 6.0, -10.2), (9.9, 7.9, -8.6), "mc:block/clay", out)
    b.cube("brick_top", (6.8, 5.7, -8.1), (9.9, 7.3, -6.5), "mc:block/packed_mud", out)
    # water puddle, wet clay lumps
    b.cube("puddle", (5.4, 3.0, -4.6), (9.0, 3.25, -1.6), WATER, q, hide={"north", "south", "east", "west", "down"})
    b.cube("puddle2", (8.0, 3.0, -1.4), (9.6, 3.2, 0.6), WATER, q, hide={"north", "south", "east", "west", "down"})
    b.cube("lump_a", (5.6, 3.0, -6.0), (7.4, 4.2, -4.8), "mc:block/clay", q)
    b.cube("lump_b", (2.6, 3.0, -9.6), (4.6, 4.4, -7.8), "mc:block/clay", q)
    b.cube("lump_c", (3.4, 3.0, -7.6), (5.0, 3.9, -6.2), "mc:block/clay", q)
    # bucket (iron) with a wooden carry handle, standing in the mud
    bk = b.group("bucket", parent=q, origin=(2.8, 3, -2.6))
    b.cube("bucket_body", (1.8, 3.0, -3.6), (3.8, 6.0, -1.6), IRON, bk)
    b.cube("bucket_mud", (2.0, 5.9, -3.4), (3.6, 6.1, -1.8), {"*": "mc:block/mud"}, bk, hide={"down"})
    b.cube("bucket_rim", (1.6, 5.4, -3.8), (4.0, 6.0, -1.4), IRON, bk, hide={"up", "down"})
    b.cube("bucket_handle", (1.9, 6.0, -2.7), (3.7, 6.8, -2.5), "mc:block/dark_oak_planks", bk)
    # long-handled shovel leaning on the rim log
    sh = b.group("shovel", parent=q, origin=(-6, 3, -9.5))
    b.cube("shovel_blade", (-8.0, 3.0, -10.7), (-5.0, 3.5, -8.7), "mc:block/iron_block#b0b0b0", sh)
    b.cube("shovel_shaft", (-6.8, 3.0, -10.1), (-6.2, 3.6, -3.6), "mc:block/oak_planks", sh)
    b.cube("shovel_grip", (-7.4, 3.0, -4.2), (-5.6, 3.9, -3.2), "mc:block/dark_oak_planks", sh)
    b.m.radial4([q], SFX)

    # ---- pug mill in the centre --------------------------------------------------------------------------
    mill = b.group("mill", parent="frame")
    b.cylinder("tub", 0, 0, 1.5, 9.0, 5.2, {"*": PLANK, "up": PLANK}, 12, mill)
    for i, y in enumerate((2.6, 6.6)):
        b.cylinder("tub_band%d" % i, 0, 0, y, y + 1.0, 5.6, IRON, 12, mill, cap_mat=IRON)
    b.ring("tub_rim", 0, 0, 9.0, 10.4, 5.7, 4.3, "mc:block/dark_oak_planks", 12, mill)
    b.cylinder("tub_mud", 0, 0, 9.0, 9.9, 4.4, "mc:block/mud", 12, mill)
    b.cylinder("tub_water", 0, 0, 9.9, 10.0, 2.6, WATER, 8, mill, hide={"down"})
    # fixed centre post with a cap; the sweeps turn around it
    b.cube("post", (-1.2, 9.9, -1.2), (1.2, 17.0, 1.2), "mc:block/stripped_spruce_log", mill, hide={"down"})
    b.cube("post_cap", (-2.0, 17.0, -2.0), (2.0, 18.0, 2.0), "mc:block/dark_oak_planks", mill)
    sw = b.group("sweeps", parent="frame", origin=(0, 13, 0))
    b.cylinder("sweep_hub", 0, 0, 11.6, 14.8, 2.5, "mc:block/dark_oak_planks", 8, sw)
    arm = b.group("sweep", parent=sw, origin=(0, 13, 0))
    b.cube("sweep_pole", (2.0, 11.9, -0.9), (10.8, 13.5, 0.9), LOG, arm)
    b.cube("sweep_cross", (9.6, 11.4, -3.4), (10.9, 13.9, 3.4), "mc:block/oak_planks", arm)
    b.cube("sweep_yoke", (9.6, 13.9, -0.5), (10.9, 15.2, 0.5), "mc:block/oak_planks", arm)
    b.strut("sweep_brace", (1.6, 15.8, 0), (8.8, 13.5, 0), 0.9, 1.0, "mc:block/spruce_planks", arm)
    b.m.radial4([arm], SFX)
    b.spin("sweeps", "y", 8.0)

    b.input_bones(["bucket", "bucket_e", "bucket_s", "bucket_w"])
    b.output_bones(["stack", "stack_e", "stack_s", "stack_w"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
