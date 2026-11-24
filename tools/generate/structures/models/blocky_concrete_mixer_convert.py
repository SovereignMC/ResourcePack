#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_concrete_mixer.bbmodel to a 4-way symmetric layout.
Reads the git HEAD version unless --src is given.

Layout: the drum stands upright in the centre (mouth up, still spinning about its axis, the old tilt is removed) and
is held by four A-frame cradles (one per side, axle stub pointing at the drum). Per side (built on the west and
cloned with radial4): the cradle with its axle, a motor with its turning pulley in the clockwise-next corner and a
small pile of cement bags. The wheelbarrow is dropped (no room for a fourth fixture).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _blocky_set_a import els, box, run  # noqa: E402


def convert(m):
    # base: square skid, rails as a pinwheel
    (skid,) = els(m, "base_skid"); box(skid, (-15, 0, -15), (15, 2, 15))
    r_w, r_e = els(m, "base_rail")
    box(r_w, (-15, 0, -15), (-13, 3, 13)); m.delete(r_e)
    # drum upright
    tilt = m.group("drum_tilt")
    tilt["rotation"] = [0, 0, 0]
    # cradle: the west A-frame, axle stub toward the drum
    legs = [e for e in els(m, "cradle_leg") if e["to"][0] < 0]
    pivot = [e for e in els(m, "cradle_pivot") if e["to"][0] < 0]
    m.delete([e for e in els(m, "cradle_leg") if e["to"][0] > 0] + [e for e in els(m, "cradle_pivot") if e["to"][0] > 0])
    axle = els(m, "cradle_axle")
    for e in axle:
        e["from"][0] = -13.0 + (0.015 * (e["name"] != "cradle_axle"))
        e["to"][0] = -6.6
    # motor: SE corner -> rotated to the SW corner
    motor = els(m, "motor_") + [m.group("motor_pulley")]
    motor = m.rotate(motor, 90)
    # bags: scaled down, in the NW corner, shifted so they clear the rotated motor of the next module
    bags = els(m, "cement_bag")
    m.scale(bags, 0.55, about=(-9, 2, -8))
    m.translate(bags, dx=-3.0, dz=-5.6)
    # wheelbarrow dropped
    m.delete(els(m, "barrow_"))
    module = [r_w] + legs + pivot + axle + motor + bags
    m.radial4(module, ("_e", "_s", "_w"))
    return m


if __name__ == "__main__":
    run("concrete_mixer", convert)
