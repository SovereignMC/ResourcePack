#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_town_hall.bbmodel to a 4-way symmetric layout.
Reads the ORIGINAL file (git HEAD version by default).

    python3 tools/generate/structures/models/blocky_town_hall_convert.py [--src ORIG] [--out OUT]

Layout: a square hall with a (0.8 scale) columned portico, door, windows and pediment clock on every side, a stepped
pyramid roof and the bell tower with a clock on all four faces moved to the centre. Flag poles with short flags and
shrubs sit in the four plinth corners. The north module is built once and cloned with radial4.
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
NAME = "town_hall"
H = 9.5          # half width of the hall
WALL_OLD = -8.0  # north wall plane of the original hall


def convert(m):
    fr = m.elements_in("frame")
    by = lambda *pre: [e for e in m.elements_in("frame") if e["name"].startswith(pre)]
    # 1. square hall, cornice, stepped roof
    for e in by("hall_walls"):
        e["from"], e["to"] = [-H, 2, -H], [H, 16, H]
    for e in by("hall_cornice"):
        e["from"], e["to"] = [-H - 0.6, 16, -H - 0.6], [H + 0.6, 17.2, H + 0.6]
    for e, hw in zip(by("roof_step"), (H + 0.6, 8.4, 6.7, 5.0)):
        e["from"] = [-hw, e["from"][1], -hw]
        e["to"] = [hw, e["to"][1], hw]
    # 2. north portico module (portico + door + front windows + pediment), scaled and pushed to the new wall plane
    side_windows = [e for e in by("hall_window") if abs(e["from"][0]) > 12]
    m.delete(side_windows)
    mod = by("portico", "column", "pediment", "steps", "hall_door") + \
        [e for e in by("hall_window") if e["to"][2] < WALL_OLD + 0.1]
    m.scale(mod, 0.8, about=(0, 2, WALL_OLD))
    m.translate(mod, dz=-(H + WALL_OLD))  # wall plane -8 -> -H
    m.radial4(mod, ("_e", "_s", "_w"))
    # 3. tower to the centre, clocks on all four faces
    tower = by("tower_", "bell_beam")
    bell, hand = m.group("bell"), m.group("clock_hand")
    m.translate(tower + [bell, hand], dz=-7)
    face = by("tower_clock_face")
    m.radial4(face + [hand], ("_e", "_s", "_w"))
    # 4. corner flag poles (shorter, short flags) and shrubs
    pole, tip, flag = by("flag_pole")[0], by("flag_pole_tip")[0], m.group("flag_1")
    m.scale([pole, tip, flag], 0.7, about=(-14, 2, -14))
    f = m.group("flag_1")
    m.scale(f, 0.5, about=tuple(f["origin"]))
    bushes = by("bush")
    m.radial4([pole, tip, flag] + bushes, ("_e", "_s", "_w"))
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
