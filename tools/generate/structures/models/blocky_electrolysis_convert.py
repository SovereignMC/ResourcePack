#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_electrolysis.bbmodel to a 4-way symmetric layout.
Reads the ORIGINAL file (git HEAD version by default) and writes the result.

    python3 tools/generate/structures/models/blocky_electrolysis_convert.py [--src ORIG] [--out OUT]

Layout: the original right-hand cell (with its bubbles, electrodes, terminals and gas pipe) is squeezed into the
north-east quadrant and cloned into all four quadrants as a pinwheel (bubble face outwards). The rectifier
becomes a central 8x8 block with fins, indicator lamps and a coil on every side, and the gas collector sits on
four legs above it, fed by a header from every cell.
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

CELL_NAMES = ("cell_floor", "cell_liquid_core", "cell_corner", "cell_lid", "electrode_anode", "electrode_cathode",
              "terminal_red", "terminal_black", "gas_pipe", "cell_rail", "cable_red", "cable_black")
# cell box maps x 0.4..13.6 -> 5..14.5 and z -9.6..5.6 -> -14.5..-5
SX, SZ = 9.5 / 13.2, 9.5 / 15.2
fx = lambda x: round(5 + (x - 0.4) * SX, 3)
fz = lambda z: round(-14.5 + (z + 9.6) * SZ, 3)


def box(e, frm, to):
    e["from"], e["to"] = list(frm), list(to)
    e["origin"] = [(a + b) / 2 for a, b in zip(frm, to)]


def convert(m):
    cx = lambda e: (e["from"][0] + e["to"][0]) / 2
    nm = lambda *n: [e for e in m.elements_in("frame") if e["name"] in n]

    # plinth square
    for n, h in (("base_plinth", 15), ("base_trim", 15.5)):
        (e,) = nm(n)
        e["from"][2], e["to"][2] = -h, h
    # keep the right-hand cell (+ bubbles), delete the left one
    m.delete([e for e in nm(*CELL_NAMES) if cx(e) < 0] + m.find_all("bubbles_0", "group"))
    cell = [e for e in nm(*CELL_NAMES) if cx(e) > 0]
    bub = m.find_all("bubbles_1", "group")
    bub_el = [e for g in bub for e in m.elements_in(g)]
    for e in cell + bub_el:
        e["from"] = [fx(e["from"][0]), e["from"][1], fz(e["from"][2])]
        e["to"] = [fx(e["to"][0]), e["to"][1], fz(e["to"][2])]
        e["origin"] = [fx(e["origin"][0]), e["origin"][1], fz(e["origin"][2])]
    for g in bub:
        g["origin"] = [fx(g["origin"][0]), g["origin"][1], fz(g["origin"][2])]
    # header from the gas pipe: x-leg towards the middle, then a z-leg to the collector (pinwheel)
    (gp,) = nm("gas_pipe")
    px, pz = (gp["from"][0] + gp["to"][0]) / 2, (gp["from"][2] + gp["to"][2]) / 2
    (hx,) = nm("gas_header")
    (hxb,) = nm("gas_header_b")
    box(hx, (0.0, 27.2, pz - 0.77), (px + 0.77, 28.8, pz + 0.77))
    box(hxb, (0.01, 27.2, pz - 0.76), (px + 0.76, 28.8, pz + 0.76))
    hz = m.clone([hx, hxb], rot=0, suffix="_z")
    box(hz[0], (-0.77, 27.2, pz - 0.77), (0.77, 28.8, 0.0))
    box(hz[1], (-0.76, 27.2, pz - 0.76), (0.76, 28.8, 0.0))
    # rectifier: central block with fins on every side
    (rb,) = nm("rectifier_box")
    box(rb, (-4, 2, -4), (4, 12, 4))
    fins = nm("rectifier_fin")
    m.delete(fins[4:])
    for e, x in zip(fins[:4], (-3.9, -1.7, 0.5, 2.7)):
        box(e, (x, 4, -4.8), (x + 1.2, 10, -4.0))
    # coil: square block with ribs on every side
    (cb,) = nm("coil_body")
    box(cb, (-2.5, 12, -2.5), (2.5, 16, 2.5))
    winds = nm("coil_wind")
    m.delete(winds[4:])
    for e, x in zip(winds[:4], (-1.9, -0.65, 0.6, 1.85)):
        box(e, (x, 11.6, -3.0), (x + 0.8, 16.4, -2.5))
    # indicator lamps on top of the rectifier, in the north strip
    lamps = []
    for g, x in ((m.group("lamp_a"), -2.8), (m.group("lamp_b"), 2.8)):
        (core,) = m.elements_in(g)
        box(core, (x - 0.7, 12.3, -3.9), (x + 0.7, 13.7, -2.7))
        g["origin"] = [x, 13, -3.3]
        lamps.append(g)
    # collector centred on the middle, one leg per corner, gauge on every side touching the tank
    col = m.group("collector")
    m.translate(col, dz=-6)
    gauge = [e for e in m.elements_in(col) if e["name"].startswith(("collector_gauge", "gauge_needle"))]
    m.translate(gauge, dz=1.27)
    legs = nm("collector_leg")
    m.delete(legs[1:] + nm("collector_pipe"))
    box(legs[0], (2.5, 12, 2.5), (3.5, 29, 3.5))
    # clone the north-east quadrant module (cell, bubbles, headers, fins, ribs, lamps) and the single-piece parts
    mod = cell + bub + [hx, hxb] + hz + fins + winds + lamps
    m.radial4(mod, SFX)
    m.radial4(gauge, SFX)
    m.radial4([legs[0]], SFX)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(PACK, "bbmodels", "structure_electrolysis.bbmodel"))
    a = ap.parse_args()
    if a.src:
        m = bblib.Model.load(a.src)
    else:
        raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_electrolysis.bbmodel"])
        m = bblib.Model(json.loads(raw))
    convert(m)
    m.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
