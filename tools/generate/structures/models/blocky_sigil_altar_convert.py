#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_sigil_altar.bbmodel to a 4-way symmetric layout.
Reads the ORIGINAL file (git HEAD version by default).

    python3 tools/generate/structures/models/blocky_sigil_altar_convert.py [--src ORIG] [--out OUT]

Changes: the cloth becomes a cross with a hanging drape on every side, the fourth candle and flame are added, the
single book becomes four tomes (group `tomes`, one per side) and the glyph ring gets a perpendicular twin so the
spinning sigil is face-on from all four sides. Obelisks, runes and the orb were already 4-fold.
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
NAME = "sigil_altar"


def add_group(m, name, parent, origin, elems=()):
    """Create a bone under `parent` and move `elems` (dicts) into it."""
    u = m._fresh("grp", name)
    g = {"name": name, "uuid": u, "export": True, "locked": False, "scope": 0, "selected": False,
         "visibility": True, "_static": {"properties": {}, "temp_data": {}}, "origin": list(origin),
         "rotation": [0, 0, 0], "color": 0, "children": [], "reset": False, "shade": True, "mirror_uv": False,
         "autouv": 0, "isOpen": False, "primary_selected": False}
    m.d["groups"].append(g)
    node = {"uuid": u, "isOpen": False, "children": []}
    m.node[m.group(parent)["uuid"]]["children"].append(node)
    m.reindex()
    for e in elems:
        lst = m.children_list(m.parent.get(e["uuid"]))
        lst.remove(e["uuid"])
        node["children"].append(e["uuid"])
    m.reindex()
    return g


def convert(m):
    fr = m.elements_in("frame")
    by = lambda n: [e for e in fr if e["name"] == n]
    # cloth -> centre square + north arm (radial4) + drape (radial4)
    (cloth,) = by("altar_cloth")
    (hang,) = by("altar_cloth_hang")
    (arm,) = m.clone(cloth, suffix="_arm")
    cloth["from"] = [-4.5, 13.5, -4.5]
    cloth["to"] = [4.5, 13.8, 4.5]
    arm["from"] = [-4.5, 13.5, -6.5]
    arm["to"] = [4.5, 13.8, -4.5]
    m.radial4([arm, hang], ("_e", "_s", "_w"))
    # fourth candle and flame
    for nm in ("candle", "flame_core"):
        src = [e for e in m.elements_in("frame" if nm == "candle" else "flames") if e["name"] == nm]
        ne = [e for e in src if e["from"][0] < 0 and e["from"][2] < 0][0]
        m.clone(ne, suffix="_nw2", offset=(0, 0, 7))
    # one tome per side
    (book,) = by("book_closed")
    book["from"], book["to"] = [-1.3, 13.8, -4.2], [1.3, 14.8, -1.4]
    book["origin"] = [0, 14.3, -2.8]
    book["rotation"] = [0, 12, 0]
    add_group(m, "tomes", "frame", (0, 14, 0), [book])
    m.radial4([book], ("_e", "_s", "_w"))
    # glyph ring: perpendicular twin inside the same spinning bone
    m.clone(m.elements_in("sigil_ring"), rot=90, into="sigil_ring")
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
