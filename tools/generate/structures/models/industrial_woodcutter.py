#!/usr/bin/env python3
"""Industrial wood cutter (structure_industrial_woodcutter): a mechanised timber yard / tree plantation.

Four young conifers grow in concrete planters at the plinth corners, four stacked log piles (end grain visible, held by
steel stakes) lie along the sides, and a pedestal-mounted slewing log-loader crane with a grapple holding a log stands in
the centre; in `running` it works a pick-and-place cycle: lower at a corner log bunk, pick the log, slew to the next pile,
lower and drop it, then on to the next corner (four deliveries per 16 s loop). The status mast sits on the fixed column through the turntable.
Everything is 4-fold symmetric except the crane boom (the one accepted exception).

    python3 tools/generate/structures/models/industrial_woodcutter.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402
import states  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_woodcutter.bbmodel")
END = "mc:block/spruce_log_top"


RUN = 16.0          # four deliveries of SEG seconds, one per pile
SEG = 4.0
FEED_R = 8.8        # grapple radius when lowered (where the bunk logs lie)
FEED_Y = 12.2       # log centre height on the bunks and on top of the piles
LOWER = -26.0       # arm rotation (deg about z) that lowers the grapple by ~3 px
# corner bunk of each segment, in the order the crane visits them: slew 45/135/225/315 = NE, NW, SW, SE
# (feed_log_a is SE; radial4 clones turn clockwise: _1 SW, _2 NW, _3 NE)
FEED_ORDER = ("feed_log_a_3", "feed_log_a_2", "feed_log_a_1", "feed_log_a")


def work_cycle(b):
    """Running loop: per SEG the crane lowers at a corner bunk, picks the log, raises, slews +45 to the next log pile,
    lowers, drops the log on the pile, raises and slews +45 to the next corner. Written as explicit keyframes."""
    keys = {}  # (bone, channel) -> [(t, (x, y, z), interp)]

    def k(bone, channel, t, v, interp="linear"):
        keys.setdefault((bone, channel), []).append((round(t, 4), v, interp))

    for s in range(4):
        t0, a = s * SEG, 45.0 + 90.0 * s
        # slew: hold at the corner, swing to the pile, hold, swing to the next corner
        for u, ang in ((0.0, a), (1.2, a), (2.2, a + 45), (3.4, a + 45)):
            k("slew", "rotation", t0 + u, (0, ang, 0))
        # arm: down at the bunk, up, down at the pile, up
        for u, r in ((0.0, 0), (0.6, LOWER), (1.2, 0), (2.2, 0), (2.8, LOWER), (3.4, 0)):
            k("arm", "rotation", t0 + u, (0, 0, r))
            k("grapple", "rotation", t0 + u, (0, 0, -r))
        # the held log appears when it is picked and disappears when it is dropped on the pile
        k("held_log", "scale", t0, (0, 0, 0), "step")
        k("held_log", "scale", t0 + 0.6, (1, 1, 1), "step")
        k("held_log", "scale", t0 + 2.8, (0, 0, 0), "step")
        # the picked bunk log is gone while the crane carries it, then the next cut log is ready
        fb = FEED_ORDER[s]
        k(fb, "scale", 0.0, (1, 1, 1), "step")
        k(fb, "scale", t0 + 0.6, (0, 0, 0), "step")
        k(fb, "scale", t0 + 2.8, (1, 1, 1), "step")
    k("slew", "rotation", RUN, (0, 360.0 + 45.0, 0))
    for bone in ("arm", "grapple"):
        k(bone, "rotation", RUN, (0, 0, 0))
    k("held_log", "scale", RUN, (0, 0, 0), "step")

    orig = b._build_running

    def build_running():
        orig()
        anim = b.m.d["animations"][0]
        by_name = {g["name"]: g["uuid"] for g in b.m.d["groups"]}
        for (bone, channel), lst in keys.items():
            an = anim["animators"][by_name[bone]]
            kfs = an.setdefault("keyframes", [])
            base = len(kfs)
            for i, (t, v, interp) in enumerate(sorted(lst, key=lambda e: e[0])):
                x, y, z = (float(c) for c in v)
                kfs.append(states.kf_make(channel, x, y, z, t, interp, bone, "running", base + i,
                                          uniform=(x == y == z) if channel == "scale" else None))
    b._build_running = build_running


def build():
    b = Builder("industrial_woodcutter", run_length=RUN)
    industrial_plinth(b)
    Y0 = 3.4

    # ---- planter with a young conifer (corner, then x4) -----------------------------------------
    tree = b.group("tree_a", parent="frame")
    c = 11.6
    b.cube("planter", (c - 3.8, Y0, c - 3.8), (c + 3.8, 6.4, c + 3.8), "concrete", tree, hide={"up"})
    b.cube("planter_soil", (c - 3.2, 5.6, c - 3.2), (c + 3.2, 6.6, c + 3.2), "dirt", tree, hide={"down"})
    b.cube("planter_rim", (c - 4.0, 6.0, c - 4.0), (c + 4.0, 6.6, c + 4.0), "dark_steel", tree, hide={"up", "down"})
    b.cube("planter_stripe", (c - 3.9, Y0 + 0.6, c - 3.9), (c + 3.9, Y0 + 1.5, c + 3.9), "warning_paint_yellow", tree, hide={"up", "down"})
    b.cylinder("trunk", c, c, 6.6, 20.0, 0.9, "wood_plank", 8, tree)
    tiers = [(10.0, 14.0, 7.2), (13.4, 17.4, 6.2), (16.8, 20.8, 5.2), (20.2, 24.2, 4.2), (23.6, 27.6, 3.2), (27.0, 30.0, 2.0)]
    for i, (y0, y1, w) in enumerate(tiers):
        b.cube("tier%d" % i, (c - w / 2, y0, c - w / 2), (c + w / 2, y1, c + w / 2), "leaves", tree,
               rotation=(0, 45, 0) if i % 2 else None)

    # ---- log pile along the north side (then x4) --------------------------------------------------
    pile = b.group("pile_n", parent="frame")
    L = 12.0
    rows = [(4.8, (-14.2, -11.4, -8.6)), (7.2, (-12.8, -10.0)), (9.6, (-11.4,))]
    k = 0
    for y, zs in rows:
        for z in zs:
            b.pipe("log%d" % k, (0, y, z), L, 1.4, "x", "wood_plank", 8, pile, cap_mat=END)
            k += 1
    for i, (x, z) in enumerate(((-6.9, -15.6), (6.9, -15.6), (-6.9, -7.6), (6.9, -7.6))):
        b.cube("stake%d" % i, (x - 0.5, Y0, z - 0.5), (x + 0.5, 11.6, z + 0.5), "dark_steel", pile)
        b.cube("stake_cap%d" % i, (x - 0.7, 11.6, z - 0.7), (x + 0.7, 12.2, z + 0.7), "warning_paint_yellow", pile, hide={"down"})
    b.cube("pile_sleeper", (-6.2, Y0, -15.2), (6.2, Y0 + 0.8, -7.8), "wood_plank", pile, hide={"down"})
    # log bunk in front of the planter: the crane picks a cut log here (feed_a, then x4)
    feed = b.group("feed_a", parent="frame")
    fx = fz = FEED_R / 2 ** 0.5
    for i, (u, v) in enumerate(((1.6, -1.6), (-1.6, 1.6))):
        x, z = fx + u, fz + v
        b.cube("bunk_post%d" % i, (x - 0.5, Y0, z - 0.5), (x + 0.5, FEED_Y - 1.2, z + 0.5), "dark_steel", feed)
        b.cube("bunk_cradle%d" % i, (x - 0.9, FEED_Y - 1.6, z - 0.9), (x + 0.9, FEED_Y - 1.1, z + 0.9), "warning_paint_yellow", feed)
    rest = b.group("feed_log_a", parent=feed, origin=(fx, FEED_Y, fz), rotation=(0, -45, 0))
    b.pipe("feed_log", (fx, FEED_Y, fz), 5.0, 1.2, "z", "wood_plank", 8, rest, cap_mat=END)
    b.m.radial4([tree, pile, feed], ("_1", "_2", "_3"))
    # ---- crane: fixed pedestal and column, rotating upper structure ----------------------------
    b.group("pedestal", parent="frame")
    p = "pedestal"
    b.cylinder("ped_base", 0, 0, Y0, 7.0, 4.8, "concrete", 8, p)
    b.cylinder("ped_hazard", 0, 0, 6.0, 6.9, 4.95, "hazard_stripe", 8, p)
    b.cylinder("ped_body", 0, 0, 7.0, 12.0, 3.4, "steel_plate", 8, p)
    b.cylinder("ped_ring", 0, 0, 11.0, 12.0, 3.9, "dark_steel", 8, p)
    b.cube("column", (-1.1, 12.0, -1.1), (1.1, 23.0, 1.1), "galvanized", p)
    slew = b.group("slew", parent="frame", origin=(0, 12.0, 0))
    b.cylinder("turntable", 0, 0, 12.0, 13.0, 4.2, "dark_steel", 8, slew)
    b.cylinder("turntable_rim", 0, 0, 13.0, 13.5, 4.5, "brass", 8, slew)
    # cab and counterweight on the -x side
    b.cube("cab", (-5.0, 13.5, -2.6), (-1.5, 18.0, 2.6), "warning_paint_yellow", slew)
    b.cube("cab_roof", (-5.3, 18.0, -2.9), (-1.3, 18.7, 2.9), "dark_steel", slew)
    b.cube("cab_glass", (-1.6, 14.4, -1.9), (-1.2, 17.2, 1.9), "glass", slew, hide={"up", "down"})
    b.cube("cab_vent", (-4.6, 18.7, -1.2), (-2.4, 19.3, 1.2), "grate", slew, hide={"down"})
    b.cube("counterweight", (-6.8, 13.5, -2.4), (-5.0, 17.0, 2.4), "dark_steel", slew)
    b.cube("cw_stripe", (-6.9, 14.6, -2.5), (-6.7, 15.4, 2.5), "hazard_stripe", slew, hide={"up", "down"})
    # boom foot bracket, main boom, knuckle, jib, hydraulics
    b.cube("boom_foot", (1.4, 13.5, -2.0), (4.2, 16.0, 2.0), "dark_steel", slew)
    b.cube("boom_pin", (1.6, 15.0, -2.4), (3.4, 16.6, 2.4), "brass", slew)
    # the arm (boom, knuckle, jib, grapple) pivots on the boom pin to lower the grapple
    arm = b.group("arm", parent=slew, origin=(2.5, 15.8, 0))
    b.strut("boom_main", (2.6, 15.8, 0), (6.4, 22.2, 0), 1.8, 2.2, "warning_paint_yellow", arm)
    b.strut("boom_ram", (1.6, 14.4, -1.4), (5.0, 19.8, -1.4), 0.7, 0.7, "galvanized", arm)
    b.strut("boom_ram2", (1.6, 14.4, 1.4), (5.0, 19.8, 1.4), 0.7, 0.7, "galvanized", arm)
    b.cube("knuckle", (5.4, 21.0, -1.5), (7.4, 23.2, 1.5), "dark_steel", arm)
    b.strut("jib", (6.4, 22.0, 0), (9.3, 19.0, 0), 1.5, 1.8, "warning_paint_yellow", arm)
    b.strut("jib_ram", (6.0, 23.4, 0), (9.0, 20.2, 0), 0.6, 0.6, "galvanized", arm)
    # grapple (input) holding a log; it counter-rotates so it always hangs straight down
    gp = b.group("grapple", parent=arm, origin=(9.5, 19.0, 0))
    b.cube("rotator", (8.7, 18.0, -0.8), (10.3, 19.4, 0.8), "brass", gp)
    b.cube("grapple_head", (7.8, 16.9, -1.1), (11.2, 18.0, 1.1), "dark_steel", gp)
    for i, z in enumerate((-1.2, 1.2)):
        b.cube("claw_a%d" % i, (7.8, 14.4, z - 0.45), (8.5, 16.9, z + 0.45), "steel_plate", gp)
        b.cube("claw_b%d" % i, (10.5, 14.4, z - 0.45), (11.2, 16.9, z + 0.45), "steel_plate", gp)
    log = b.group("held_log", parent=gp, origin=(9.5, 15.3, 0))
    b.pipe("held_log_body", (9.5, 15.3, 0), 5.0, 1.2, "z", "wood_plank", 8, log, cap_mat=END)
    industrial_status_mast(b, 0, 0, 23.0)

    # ---- animation -----------------------------------------------------------------------
    work_cycle(b)
    # idle/no_power replay the same pick-and-place, only slower: keep the arm stroke and the 0/1 log toggles
    b.full_amplitude(["arm", "grapple", "held_log", "feed_log_a", "feed_log_a_1", "feed_log_a_2", "feed_log_a_3"])
    b.input_bones(["grapple"])
    b.output_bones(["pile_n", "pile_n_1", "pile_n_2", "pile_n_3"])
    return b


if __name__ == "__main__":
    b = build()
    b.save(OUT)
