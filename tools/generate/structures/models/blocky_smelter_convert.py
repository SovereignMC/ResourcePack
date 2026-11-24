#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_smelter.bbmodel to a 4-way symmetric layout (example for
bblib.Model editing). Reads the ORIGINAL file (git HEAD version by default) and writes the result.

    python3 tools/generate/structures/models/blocky_smelter_convert.py [--src ORIG] [--out OUT]

Layout: furnace re-centred and squared; per side a mouth (centre), a bellows pointing at the mouth and a coal
heap in the front strip, and a crucible + mould tray (scaled down) in the clockwise-next corner. The north
module is built once and cloned with radial4.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bblib  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def convert(m):
    F = m.group("frame")
    by = lambda n: [e for e in m.elements_in("frame") if e["name"] == n]
    # 1. re-centre the furnace (front was z=-4, centre z=4) and make it square
    body = [e for e in m.elements_in("frame") if e["name"].startswith(("furnace", "chimney", "mouth"))]
    smoke = m.group("smoke")
    m.translate(body + [smoke], dz=-4)
    for n in ("furnace_lower", "furnace_band", "furnace_mid", "furnace_upper"):
        for e in by(n):
            half = max(abs(e["from"][2]), abs(e["to"][2]))
            e["from"][0], e["to"][0] = -half, half
            e["origin"][0] = 0
    # 2. tuyeres are replaced by the bellows nozzles
    m.delete([e for e in m.elements_in("frame") if e["name"].startswith("tuyere")] + by("ingot_stack"))
    # 3. north module pieces
    mouth = [e for e in m.elements_in("frame") if e["name"].startswith("mouth")]
    # bellows: nozzle toward +z in front of the mouth, scaled down, in the right half of the front strip
    bell = m.group("bellows")
    (bell,) = m.rotate(bell, 270, suffix="")
    m.scale(bell, 0.6, about=(6, 2, -13.75))
    m.translate(bell, dx=-0.5, dz=2.6)
    # coal heap: small, left half of the front strip
    coal = by("coal_pile")
    m.scale(coal, 0.5, about=(10, 2, -11))
    m.translate(coal, dx=-16, dz=0.5)
    # crucible + mould tray assembly: scaled, moved into the NW corner
    asm = [e for e in m.elements_in("frame")
           if e["name"].startswith(("crucible_stand", "crucible_axle", "mold_"))] + [m.group("crucible"), m.group("pour")]
    m.scale(asm, 0.65, about=(-10.5, 2, -10))
    m.translate(asm, dx=-1.5, dz=-2.2)
    module = mouth + coal + asm + [bell]
    m.radial4(module, ("_e", "_s", "_w"))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(PACK, "bbmodels", "structure_smelter.bbmodel"))
    a = ap.parse_args()
    if a.src:
        m = bblib.Model.load(a.src)
    else:
        raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_smelter.bbmodel"])
        import json
        m = bblib.Model(json.loads(raw))
    convert(m)
    m.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
