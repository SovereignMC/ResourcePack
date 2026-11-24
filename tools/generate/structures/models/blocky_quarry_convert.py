#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_quarry.bbmodel (git HEAD version) to a 4-way layout.

Chassis: four crawler tracks in a pinwheel around a square body; each side has a discharge conveyor and a stone
pile. Upper house (the swinging bone) is square, with a cab bay + vents per face and a pinwheel of four small
bucket-wheel booms on the roof. Built once for the -Z / -X sides and cloned with radial4.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mpqs_util import *  # noqa: F401,F403


def convert(m):
    C, U = "chassis", "upper"
    ce = lambda pred: els(m, C, pred)
    ue = lambda pred: [e for e in m.elements_in(U, recursive=False) if pred(e)]
    starts = lambda f, *p: f(lambda e: e["name"].startswith(p))
    # ---- chassis: delete the east track, shorten the west track to z -13..5
    east = ce(lambda e: e["name"].startswith("track_") and cx(e) > 0)
    m.delete(east)
    west = ce(lambda e: e["name"].startswith("track_"))
    belt = [e for e in west if e["name"] == "track_belt"][0]
    frame = [e for e in west if e["name"] == "track_frame"][0]
    setbox(m, belt, (-15, 0, -13), (-9, 5, 5))
    setbox(m, frame, (-15.2, 1, -11), (-8.8, 4, 3))
    cleats = [e for e in west if e["name"] == "track_cleat"]
    m.delete([e for e in cleats if e["from"][2] > 4])
    cleats = [e for e in cleats if e["from"][2] <= 4]
    wheels = [e for e in west if e["name"].startswith("track_wheel")]
    far = [e for e in wheels if cx(e, 2) > 0]
    m.translate(far, dz=-6.5)
    track = [belt, frame] + cleats + wheels
    (body,) = ce(lambda e: e["name"] == "chassis_body")
    setbox(m, body, (-9, 3, -9), (9, 7, 9))
    # discharge conveyor: shrink to 0.6, sit between the S track and the E track
    conv = starts(ce, "conveyor_")
    m.scale(conv, 0.6, about=(9, 7, 10))
    m.translate(conv, dx=-3.4)
    # stone piles in the pocket at the end of the west track
    piles = starts(ce, "stone_")
    place(m, piles, 0.55, -12, 7.5, y_floor=0)
    mod_c = track + conv + piles
    m.radial4(mod_c, ("_e", "_s", "_w"))

    # ---- upper house
    (house,) = ue(lambda e: e["name"] == "house_body")
    (roof,) = ue(lambda e: e["name"] == "house_roof")
    setbox(m, house, (-6, 8, -6), (6, 18, 6))
    setbox(m, roof, (-6.5, 18, -6.5), (6.5, 19, 6.5))
    m.delete(ue(lambda e: e["name"] == "counterweight"))
    # cab bay on the -Z face
    (cab,) = ue(lambda e: e["name"] == "cab_body")
    (win,) = ue(lambda e: e["name"] == "cab_window")
    (wside,) = ue(lambda e: e["name"] == "cab_window_side")
    (croof,) = ue(lambda e: e["name"] == "cab_roof")
    setbox(m, cab, (-3, 8, -9), (3, 15, -5.9))
    setbox(m, win, (-2.5, 10, -9.3), (2.5, 14, -9))
    setbox(m, wside, (3, 10, -8.5), (3.3, 14, -6.2))
    setbox(m, croof, (-3.5, 15, -9.5), (3.5, 15.8, -5.5))
    wside_m = m.clone([wside], mirror="x", suffix="_mx")[0]
    # vents flank the cab
    v3 = ue(lambda e: e["name"] == "house_vent_3")[0]
    m.delete(ue(lambda e: e["name"].startswith("house_vent") and e is not v3))
    setbox(m, v3, (3.6, 12, -6.4), (5.1, 15, -6.01))
    v3m = m.clone([v3], mirror="x", suffix="_mx")[0]
    # roof stack at the NW corner
    stk = ue(lambda e: e["name"].startswith("exhaust_stack"))
    m.translate(stk, dx=0.5, dz=-12.5)
    # booms: scale to 0.6, centre the boom on the face, pivot at the centre
    boom = m.group("boom")
    m.scale([boom], 0.5, about=(-2, 18, 6))
    m.translate([boom], dx=2, dz=-6.5)
    mod_u = [cab, win, wside, wside_m, croof, v3, v3m] + stk + [boom]
    m.radial4(mod_u, ("_e", "_s", "_w"))
    return m


def main():
    out = os.path.join(PACK, "bbmodels", "structure_quarry.bbmodel")
    m = load_head("quarry")
    convert(m)
    m.save(out)
    write_override("quarry", input_bones=["wheel", "wheel_e", "wheel_s", "wheel_w"],
                   output_bones=["boom", "boom_e", "boom_s", "boom_w"], lamp_at=[0, 0, 19.0])
    print("wrote", out)


if __name__ == "__main__":
    main()
