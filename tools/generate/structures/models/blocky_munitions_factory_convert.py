#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_munitions_factory.bbmodel (git HEAD version) to a 4-way layout.

Press stays in the centre; the single conveyor becomes four arms (radial4) that each end in a shell crate, with a
control panel beside the arm and a pump box in every corner; lamps on all four press columns.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mpqs_util import *  # noqa: F401,F403


def convert(m):
    F = "frame"
    fe = lambda pred: els(m, F, pred)
    nm = lambda n: (lambda e: e["name"] == n)
    # --- conveyor: centre pad + one +X arm
    (bed,) = fe(nm("conveyor_bed"))
    sides = fe(nm("conveyor_side"))
    legs = fe(nm("conveyor_leg"))
    arm_bed = m.clone([bed], suffix="_arm")[0]
    setbox(m, bed, (-4, 6, -4), (4, 8, 4))
    setbox(m, arm_bed, (4, 6, -4), (10, 8, 4))
    arm_sides = []
    for s in sides:
        arm_sides.append(m.clone([s], suffix="_arm")[0])
    for s, a in zip(sides, arm_sides):
        setbox(m, a, (4, s["from"][1], s["from"][2]), (10, s["to"][1], s["to"][2]))
    m.delete(sides)
    keep = [l for l in legs if 5 < cx(l) < 7]
    m.delete([l for l in legs if l not in keep])
    extra = m.clone(keep, offset=(3.4, 0, 0), suffix="_b")
    arm_legs = keep + extra
    # rollers: centre pair (-2, 2) stays, arm rollers at 6 and 8
    rn = lambda i: m.group("roller_%d" % i)
    m.delete([rn(0), rn(1), rn(2), rn(7)])
    m.translate(rn(6), dx=-2)
    arm_rollers = [rn(5), rn(6)]
    # --- crate at the arm end (scaled, lowered shells inside)
    crate = fe(lambda e: e["name"].startswith(("crate", )))
    m.scale(crate, 0.7, about=(-11, 2, -11.5))
    m.translate(crate, dx=12.5 + 11, dz=11.5)
    crate_grp = make_group(m, "crate", F, (12.5, 2, 0), crate)
    # --- panel beside the arm
    panel = fe(lambda e: e["name"].startswith("panel_"))
    m.scale(panel, 0.8, about=(12.5, 2, -15))
    m.translate(panel, dx=-0.5, dz=7.2)
    # --- pump + hydraulic line in the corner
    pump = fe(lambda e: e["name"].startswith("pump_"))
    hyd = fe(lambda e: e["name"].startswith("hydraulic_line"))
    # --- shells: two per arm, shorter travel
    sh = m.group("shells")
    shells = list(m.elements_in(sh))
    first = [e for e in shells if cx(e) < -12]
    second = [e for e in shells if -12 <= cx(e) < -4]
    third = [e for e in shells if cx(e) >= -4]
    m.delete(third)
    m.translate(first, dx=21.5)
    m.translate(second, dx=16.5)
    scale_anim(m, "shells", "position", "x", 3 / 8)
    # --- 4-fold
    mod = [arm_bed] + arm_sides + arm_legs + arm_rollers + [crate_grp] + panel + pump + hyd + [sh]
    m.radial4(mod, ("_e", "_s", "_w"))
    m.radial4([m.group("lamp")], ("_e", "_s", "_w"))
    return m


def main():
    out = os.path.join(PACK, "bbmodels", "structure_munitions_factory.bbmodel")
    m = load_head("munitions_factory")
    convert(m)
    m.save(out)
    write_override("munitions_factory", input_bones=["shells", "shells_e", "shells_s", "shells_w"],
                   output_bones=["crate", "crate_e", "crate_s", "crate_w"])
    print("wrote", out)


if __name__ == "__main__":
    main()
