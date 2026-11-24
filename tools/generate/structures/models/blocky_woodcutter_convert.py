#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_woodcutter.bbmodel to a 4-way symmetric layout.
Reads the ORIGINAL file (git HEAD version by default).

    python3 tools/generate/structures/models/blocky_woodcutter_convert.py [--src ORIG] [--out OUT]

Layout: the tree moves to the centre (roots, branch, axe notch and a leaf clump on all four sides), and one chopping
station (dirt patch, stump, split log, swinging axe, chips) per side in a pinwheel, with a small log pile in each
plinth corner and a falling leaf per side. The north-east station / pile are built once and cloned with radial4.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bblib  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
NAME = "woodcutter"
SUF = ("_e", "_s", "_w")


def convert(m):
    byf = lambda *pre: [e for e in m.elements_in("frame") if e["name"].startswith(pre)]
    # tree to the centre, made 4-fold
    tree = m.group("tree")
    m.translate([tree, m.group("falling_leaf")], dx=8, dz=-6)
    te = m.elements_in("tree")
    by = lambda n: [e for e in te if e["name"] == n]
    roots, leaves = by("tree_root"), by("tree_leaves")
    m.delete(roots[1:] + [leaves[4]])
    m.radial4([roots[0], by("tree_branch")[0], by("tree_axe_cut")[0], leaves[3]], SUF)
    m.radial4([m.group("falling_leaf")], SUF)
    # chopping station (north-east) + pinwheel
    (patch,) = byf("ground_dirt_patch")
    patch["from"], patch["to"] = [0, 2, -12], [13, 2.2, -3.5]
    station = byf("stump") + [patch] + [m.group("log_halves"), m.group("axe"), m.group("chips")]
    m.radial4(station, SUF)
    # log pile into the north-east corner
    pile = byf("pile_")
    m.scale(pile, 0.55, about=(9, 2, 9))
    m.translate(pile, dx=3.4, dz=-22.1)
    m.radial4(pile, SUF)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(PACK, "bbmodels", "structure_%s.bbmodel" % NAME))
    a = ap.parse_args()
    if a.src:
        m = bblib.Model.load(a.src)
    else:
        raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_%s.bbmodel" % NAME])
        m = bblib.Model(json.loads(raw))
    convert(m)
    m.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
