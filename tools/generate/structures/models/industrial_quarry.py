#!/usr/bin/env python3
"""Industrial open-pit quarry with a blast-hole drill rig (structure_industrial_quarry), 4-fold symmetric.

    python3 tools/generate/structures/models/industrial_quarry.py

A three-bench stone mesa with hazard-striped bench lips and yellow railings carries a drill rig on the top bench:
a lattice mast with four power-pack housings around its foot, a rotary head that slides along the mast and a
spinning drill rod. Blasted-rock piles sit on the plinth corners. Running: the head travels down the mast while
the rod spins.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bblib import Builder, industrial_plinth, industrial_status_mast  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(PACK, "bbmodels", "structure_industrial_quarry.bbmodel")
SUF = ("", "_e", "_s", "_w")
Y0 = 3.4
BENCH = ((12.5, 3.4, 8.6), (9.5, 8.6, 13.8), (6.5, 13.8, 19.0))  # half-width, y0, top


def build():
    b = Builder("industrial_quarry", run_length=4.0)
    industrial_plinth(b)
    F = "frame"
    b.group("mesa", parent=F)
    for i, (h, y0, y1) in enumerate(BENCH):
        b.cube("bench%d" % i, (-h, y0 if i == 0 else y0 - 0.2, -h), (h, y1, h), {"up": "dirt", "*": "stone"}, "mesa")
        # hazard-striped lip: four thin strips on the bench top edge
        lip = {"up": "hazard_stripe", "*": "hazard_stripe"}
        e = 0.7
        b.cube("lip%d_n" % i, (-h, y1, -h), (h, y1 + 0.4, -h + e), lip, "mesa", hide={"down"})
        b.cube("lip%d_s" % i, (-h, y1, h - e), (h, y1 + 0.4, h), lip, "mesa", hide={"down"})
        b.cube("lip%d_w" % i, (-h, y1, -h + e), (-h + e, y1 + 0.4, h - e), lip, "mesa", hide={"down"})
        b.cube("lip%d_e" % i, (h - e, y1, -h + e), (h, y1 + 0.4, h - e), lip, "mesa", hide={"down"})
    # loose rocks on the bench tops and floodlight poles on the lower bench corners
    for i, (h, y0, y1) in enumerate(BENCH[:2]):
        for k, (sx, sz) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
            b.cube("rock%d_%d" % (i, k), (sx * (h - 2.2) - 0.8, y1, sz * (h - 2.2) - 0.8),
                   (sx * (h - 2.2) + 0.8, y1 + 1.4, sz * (h - 2.2) + 0.8), "stone", "mesa", rotation=(0, 20 + 30 * k, 0), hide={"down"})
    for k, (sx, sz) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        px, pz = sx * 10.9, sz * 10.9
        b.cube("flood%d_pole" % k, (px - 0.5, 8.6, pz - 0.5), (px + 0.5, 17.0, pz + 0.5), "galvanized", "mesa", hide={"down"})
        b.cube("flood%d_head" % k, (px - 1.4, 17.0, pz - 1.4), (px + 1.4, 18.4, pz + 1.4), "dark_steel", "mesa", hide={"down"})
        b.cube("flood%d_lamp" % k, (px - 1.6, 17.2, pz - 1.6), (px + 1.6, 18.0, pz + 1.6), "glow_amber", "mesa", hide={"up", "down"})
    # railings on the two upper benches
    for i in (1, 2):
        h, _, y1 = BENCH[i]
        k = h - 0.8
        b.railing("rail%d_n" % i, (-k, y1 + 0.4, -k), (k, y1 + 0.4, -k), 3.0, 0.6, 7.0, group="mesa")
        b.railing("rail%d_s" % i, (-k, y1 + 0.4, k), (k, y1 + 0.4, k), 3.0, 0.6, 7.0, group="mesa")
        b.railing("rail%d_w" % i, (-k, y1 + 0.4, -k), (-k, y1 + 0.4, k), 3.0, 0.6, 7.0, group="mesa")
        b.railing("rail%d_e" % i, (k, y1 + 0.4, -k), (k, y1 + 0.4, k), 3.0, 0.6, 7.0, group="mesa")
    # ---- drill rig ----------------------------------------------------------------------------------------
    rig = b.group("rig", parent=F)
    T = 19.4
    # four power packs around the mast foot (louvred housings with a hazard band and a stack)
    for i, (dx, dz) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
        cx, cz = dx * 3.9, dz * 3.9
        w, d = (2.4, 1.2) if dx == 0 else (1.2, 2.4)
        b.cube("pack%d" % i, (cx - w, T, cz - d), (cx + w, T + 4.6, cz + d), "galvanized", rig)
        b.cube("pack%d_haz" % i, (cx - w - 0.2, T + 3.4, cz - d - 0.2), (cx + w + 0.2, T + 4.2, cz + d + 0.2), "hazard_stripe", rig)
        b.cube("pack%d_top" % i, (cx - w - 0.3, T + 4.6, cz - d - 0.3), (cx + w + 0.3, T + 5.2, cz + d + 0.3), "dark_steel", rig)
        for j in (-1, 1):
            lx = cx + (j * 1.4 if dx == 0 else 0)
            lz = cz + (j * 1.4 if dx != 0 else 0)
            fx = cx + dx * (1.2 + 0.1) if dx else lx
            fz = cz + dz * (1.2 + 0.1) if dz else lz
            b.cube("pack%d_lv%d" % (i, j), (fx - (0.7 if dz else 0.15), T + 1.0, fz - (0.7 if dx else 0.15)),
                   (fx + (0.7 if dz else 0.15), T + 3.0, fz + (0.7 if dx else 0.15)), "dark_steel", rig)
    # base plate
    b.cube("mast_base", (-3.0, T, -3.0), (3.0, T + 1.0, 3.0), "dark_steel", rig)
    b.truss("mast", -2.4, -2.4, 2.4, 2.4, T + 1.0, 38.0, "warning_paint_yellow", 0.8, True, rig, "dark_steel")
    for i, y in enumerate((T + 10.0, T + 17.0)):
        b.cube("collar%d" % i, (-2.8, y, -2.8), (2.8, y + 0.8, 2.8), "dark_steel", rig, hide={"down"} if False else ())
    b.cube("crown", (-3.0, 38.0, -3.0), (3.0, 38.8, 3.0), "dark_steel", rig)
    b.cube("crown_cap", (-2.2, 38.8, -2.2), (2.2, 39.2, 2.2), "steel_plate", rig, hide={"down"})
    # rotary head + drill rod (head slides on Y)
    H = 26.0
    head = b.group("head", parent=rig, origin=(0, H, 0))
    b.cube("head_body", (-3.0, H, -3.0), (3.0, H + 3.4, 3.0), "dark_steel", head)
    b.cube("head_haz", (-3.3, H + 1.6, -3.3), (3.3, H + 2.4, 3.3), "hazard_stripe", head)
    b.cube("head_motor", (-2.0, H + 3.4, -2.0), (2.0, H + 4.8, 2.0), "steel_plate", head, hide={"down"})
    b.cube("head_eye_x", (-3.6, H + 0.4, -0.8), (3.6, H + 1.2, 0.8), "galvanized", head)
    b.cube("head_eye_z", (-0.8, H + 0.4, -3.6), (0.8, H + 1.2, 3.6), "galvanized", head)
    rod = b.group("rod", parent=head, origin=(0, H, 0))
    b.cylinder("rod_t", 0, 0, 20.9, H, 0.9, "galvanized", 8, rod)
    b.cube("rod_vane_x", (-1.5, 21.8, -0.3), (1.5, H, 0.3), "steel_plate", rod)
    b.cube("rod_vane_z", (-0.3, 21.8, -1.5), (0.3, H, 1.5), "steel_plate", rod)
    b.cube("rod_bit", (-1.4, 20.5, -1.4), (1.4, 21.5, 1.4), "dark_steel", rod)
    # ---- corner blast-rock pile (NE, cloned 4x) ---------------------------------------------------------------
    pile = b.group("pile", parent=F, origin=(13.2, Y0, -13.2))
    b.taper("pile_t", 13.2, -13.2, Y0, 8.6, 3.6, 1.0, "stone", 4, 8, pile)
    for i, (x, z, s, r) in enumerate(((10.6, -11.2, 1.2, 20), (15.2, -10.8, 1.1, 50), (10.8, -15.4, 1.1, 70), (15.0, -15.0, 0.9, 35))):
        b.cube("pchunk%d" % i, (x - s, Y0, z - s), (x + s, Y0 + 1.7 * s, z + s), "stone", pile, rotation=(0, r, 0))
    b.cube("pile_haz", (9.8, Y0, -16.2), (16.4, Y0 + 0.6, -15.7), "hazard_stripe", pile)
    b.radial4([pile], ("_e", "_s", "_w"))
    industrial_status_mast(b, 0, 0, 39.2)
    # ---- animation ----------------------------------------------------------------------------------------------
    b.piston("head", "y", 5.0, 4.0)
    b.spin("rod", "y", 0.5)
    b.input_bones(["head"])
    b.output_bones(["pile" + s for s in SUF])
    return b


if __name__ == "__main__":
    build().save(OUT)
