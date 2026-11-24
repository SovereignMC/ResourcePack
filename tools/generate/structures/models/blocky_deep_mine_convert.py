#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_deep_mine.bbmodel to a 4-way symmetric layout.
Reads the ORIGINAL file (git HEAD version by default) and writes the result.

    python3 tools/generate/structures/models/blocky_deep_mine_convert.py [--src ORIG] [--out OUT]

The derrick tower is already 4-fold. Everything on the deck becomes one north-strip module cloned with
radial4: engine + flywheel in the NW corner, a drum and a drill-pipe rack towards the middle. Skids, deck
planks, crown sheaves and hoist cables are made 4-fold as well (pinwheel layouts so nothing overlaps).
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
SFX = ("_e", "_s", "_w")


def box(e, frm=None, to=None):
    """Set an axis-aligned element's box and re-centre its origin (only for unrotated cubes)."""
    if frm:
        e["from"] = list(frm)
    if to:
        e["to"] = list(to)
    e["origin"] = [(a + b) / 2 for a, b in zip(e["from"], e["to"])]


def convert(m):
    fr = m.elements_in("frame")
    nm = lambda n: [e for e in fr if e["name"] == n]

    # 1. skids: pinwheel frame (N skid x -14..16, z -16..-14 after one rotation)
    (skl,) = nm("base_skid_l")
    m.delete(nm("base_skid_r"))
    box(skl, (-16, 0, -16), (-14, 3, 14))
    skl["origin"] = [-15, 1.5, -1]
    m.radial4([skl], SFX)

    # 2. deck planks: pinwheel ring at radius 11
    planks = nm("deck_plank_-11")
    keep = planks[0]
    m.delete([e for e in fr if e["name"].startswith("deck_plank") and e is not keep])
    box(keep, (-14, 2, -12), (10, 2.4, -10))
    m.radial4([keep], SFX)

    # 3. crown: square block, sheaves on every side
    (cb,) = nm("crown_block")
    box(cb, (-3, 41.5, -3), (3, 44, 3))
    (sl,) = nm("crown_sheave_l")
    m.delete(nm("crown_sheave_r"))
    m.radial4([sl], SFX)

    # 4. hoist cables on all four sides, square travelling block
    (cl,) = nm("cable_l")
    m.delete(nm("cable_r"))
    m.radial4([cl], SFX)
    (tb,) = [e for e in m.elements_in("travel_block") if e["name"] == "travel_block_body"]
    box(tb, (-2.2, 20, -2.2), (2.2, 24, 2.2))

    # 5. deck module in the north strip
    eng = [e for e in fr if e["name"].startswith(("engine_", "exhaust_"))] + [m.group("flywheel")]
    mod = list(m.rotate(eng, 180))                       # engine + flywheel -> NW corner
    barrel = [e for e in fr if e["name"].startswith("barrel_a")]
    m.delete([e for e in fr if e["name"].startswith("barrel_b")])
    m.translate(barrel, dx=-12)
    mod += barrel
    posts = nm("rack_post")
    pipes = [e for e in fr if e["name"].startswith("rack_pipe")]
    for e in pipes:
        sx = lambda x: 1.8 + (x + 15) * 5 / 11
        e["from"][0], e["to"][0] = round(sx(e["from"][0]), 3), round(sx(e["to"][0]), 3)
        e["origin"][0] = round(sx(e["origin"][0]), 3)
    m.translate(posts, dx=16.3)
    mod += pipes + posts
    m.radial4(mod, SFX)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(PACK, "bbmodels", "structure_deep_mine.bbmodel"))
    a = ap.parse_args()
    if a.src:
        m = bblib.Model.load(a.src)
    else:
        raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_deep_mine.bbmodel"])
        m = bblib.Model(json.loads(raw))
    convert(m)
    m.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
