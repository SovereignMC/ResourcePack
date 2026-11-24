#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_workshop.bbmodel to a 4-way symmetric layout.
Reads the ORIGINAL file (git HEAD version by default).

    python3 tools/generate/structures/models/blocky_workshop_convert.py [--src ORIG] [--out OUT]

Layout: the back pegboard wall becomes a central tool tower (tools on all four faces, canopy with a hanging lamp
at each corner) standing on a square workbench with a vise per side; a lathe (scaled 0.75) with toolbox and
shavings in front of every side and a drill press in every plinth corner. One module is built and cloned with
radial4.
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
NAME = "workshop"
SUF = ("_e", "_s", "_w")


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
        m.children_list(m.parent.get(e["uuid"])).remove(e["uuid"])
        node["children"].append(e["uuid"])
    m.reindex()
    return g


def convert(m):
    byf = lambda *pre: [e for e in m.elements_in("frame") if e["name"].startswith(pre)]
    # 1. central tower from the wall board; canopy from the wall beam
    m.delete(byf("wall_post"))
    (board,) = byf("wall_board")
    board["from"], board["to"] = [-5.6, 14, -5.6], [5.6, 27, 5.6]
    (beam,) = byf("wall_beam")
    beam["from"], beam["to"] = [-8.5, 27, -8.5], [8.5, 29, 8.5]
    # 2. tools on the four faces
    tools = byf("tool_", "peg")
    m.scale(tools, 0.43, about=(0, 23, 13))
    m.translate(tools, dy=-2.5, dz=-18.6)
    m.radial4(tools, SUF)
    # 3. lamps at the canopy corners
    lamp = m.group("lamp")
    m.translate(lamp, dx=-2.5, dy=-3, dz=-14.5)
    m.radial4([lamp], SUF)
    # 4. square bench in the middle with a vise per side
    (top,) = byf("bench_top")
    top["from"], top["to"] = [-7, 12, -7], [7, 14, 7]
    for e, (sx, sz) in zip(byf("bench_leg"), ((-1, -1), (1, -1), (-1, 1), (1, 1))):
        xs = sorted((sx * 5.2, sx * 6.8))
        zs = sorted((sz * 5.2, sz * 6.8))
        e["from"], e["to"] = [xs[0], 2, zs[0]], [xs[1], 12, zs[1]]
    (shelf,) = byf("bench_shelf")
    shelf["from"], shelf["to"] = [-6, 5, -6], [6, 6, 6]
    (planks,) = byf("bench_planks")
    planks["from"], planks["to"] = [-4, 6, -4], [4, 8, 4]
    vise = byf("vise_")
    m.translate(vise, dx=-3, dz=-9)
    m.radial4(vise, SUF)
    # 5. lathe (scaled) + toolbox + shavings in front of each side
    lathe = byf("lathe_") + [m.group("lathe_spindle")]
    m.scale(lathe, 0.75, about=(-6, 2, -9))
    m.translate(lathe, dx=6, dz=-1.5)
    m.radial4(lathe, SUF)
    tb = byf("toolbox") + byf("shavings")
    m.scale(byf("toolbox"), 0.6, about=(11, 2, -11.5))
    m.translate(byf("toolbox"), dx=-6.5, dz=-2.8)
    m.scale(byf("shavings"), 0.6, about=(-6, 2, -13.5))
    m.translate(byf("shavings"), dx=1.5, dz=-0.8)
    g = add_group(m, "toolbox_bone", "frame", (4.5, 2, -14.3), tb)
    m.radial4([g], SUF)
    # 6. drill press into the south-east corner
    drill = byf("drill_") + [m.group("drill_spindle")]
    m.scale(drill, 0.65, about=(11.5, 2, 2))
    m.translate(drill, dz=9.5)
    m.radial4(drill, SUF)
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
