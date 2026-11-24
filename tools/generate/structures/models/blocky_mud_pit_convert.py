#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_mud_pit.bbmodel to a 4-way symmetric layout.
Reads the ORIGINAL file (git HEAD version by default) and writes the result.

    python3 tools/generate/structures/models/blocky_mud_pit_convert.py [--src ORIG] [--out OUT]

The single A-frame becomes two crossed A-frames (a four-legged gantry with a cross beam). A windlass crank,
a clay heap, a mud bubble pair and a shovel are cloned onto all four sides; wall trims go all round, the
pulley and bucket handle are crossed so they look the same from every side.
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


def convert(m):
    nm = lambda *n: [e for e in m.elements_in("pit") if e["name"] in n]

    # wall trims: keep the two on the north wall, clone round
    trims = nm("wall_trim")
    north = [e for e in trims if e["from"][2] < 0]
    m.delete([e for e in trims if e not in north])
    m.radial4(north, SFX)

    # crossed A-frames: clone legs + braces turned by 90, cross beam in two halves butted against the first beam
    frame = nm("aframe_leg", "aframe_brace")
    m.clone(frame, rot=90, suffix="_x")
    (beam,) = nm("aframe_beam")
    for z0, z1 in ((-15, -1.1), (1.1, 15)):
        (c,) = m.clone([beam], rot=90, suffix="_x" + ("n" if z0 < 0 else "s"))
        c["from"][2], c["to"][2] = z0, z1
        c["origin"][2] = (z0 + z1) / 2
    # crossed pulley wheel + crossed bucket handle
    m.clone([m.group("pulley")], rot=90, suffix="_x")
    (h,) = [e for e in m.elements_in("bucket") if e["name"] == "bucket_handle"]
    m.clone([h], rot=90, suffix="_x")

    # one clay heap (two lumps) towards the east arm, third lump dropped
    lumps = nm("clay_lump")
    m.delete(lumps[2:])
    pile = lumps[:2]
    m.translate(pile, dz=-4)
    # bubbles: a and b, c dropped
    m.delete(m.group("bubble_c"))
    mod = pile + [m.group("bubble_a"), m.group("bubble_b"), m.group("shovel"), m.group("crank")]
    m.radial4(mod, SFX)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(PACK, "bbmodels", "structure_mud_pit.bbmodel"))
    a = ap.parse_args()
    if a.src:
        m = bblib.Model.load(a.src)
    else:
        raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_mud_pit.bbmodel"])
        m = bblib.Model(json.loads(raw))
    convert(m)
    m.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
