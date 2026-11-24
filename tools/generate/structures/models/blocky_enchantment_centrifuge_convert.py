#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_enchantment_centrifuge.bbmodel for exact 4-fold symmetry.
Reads the ORIGINAL file (git HEAD version by default) and writes the result.

    python3 tools/generate/structures/models/blocky_enchantment_centrifuge_convert.py [--src ORIG] [--out OUT]

The machine is already nearly 4-fold; the repeated parts (pylons, runes, cradle rings and struts, rotor vials,
sparkles) are replaced by radial4 clones of one quarter so that textures, not just boxes, rotate with the
machine. The cradle struts (only on +-X) gain their +-Z partners.
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
    def of(group, *prefix):
        return [e for e in m.elements_in(group) if e["name"].startswith(prefix)]

    # pylons: keep the north-west one, clone it into the other corners
    pyl = of("frame", "pylon_")
    keep = [e for e in pyl if e["from"][0] < 0 and e["from"][2] < 0]
    m.delete([e for e in pyl if e not in keep])
    m.radial4(keep, SFX)
    # rune cores on the east side (two rotated bars) and cradle rings: east pair cloned round
    runes = [e for e in of("frame", "base_rune_core_") if e["from"][0] > 10]
    m.delete([e for e in of("frame", "base_rune_core_") if e not in runes])
    m.radial4(runes, SFX)
    rings = [e for e in of("frame", "cradle_ring_") if e["from"][0] > 3]
    m.delete([e for e in of("frame", "cradle_ring_") if e not in rings])
    m.radial4(rings, SFX)
    # cradle struts: +x one cloned round
    st = [e for e in of("frame", "cradle_strut") if e["from"][0] > 0]
    m.delete([e for e in of("frame", "cradle_strut") if e not in st])
    m.radial4(st, SFX)
    # vials on the rotor and sparkles
    vial = [e for e in of("rotor", "vial_") if e["from"][0] > 5]
    m.delete([e for e in of("rotor", "vial_") if e not in vial])
    m.radial4(vial, SFX)
    sp = [e for e in of("sparkles", "sparkle_core_") if e["from"][0] > 5]
    m.delete([e for e in of("sparkles", "sparkle_core_") if e not in sp])
    m.radial4(sp, SFX)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(PACK, "bbmodels", "structure_enchantment_centrifuge.bbmodel"))
    a = ap.parse_args()
    if a.src:
        m = bblib.Model.load(a.src)
    else:
        raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_enchantment_centrifuge.bbmodel"])
        m = bblib.Model(json.loads(raw))
    convert(m)
    m.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
