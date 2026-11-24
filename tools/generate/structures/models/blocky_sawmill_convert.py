#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_sawmill.bbmodel (git HEAD version) to a 4-way layout.

Square pavilion with a hipped roof on four corner posts, a ring of water channels with a water wheel in each
(pinwheel), and four saw benches (blade, guard, log, drive belt from the wheel axle) in a pinwheel inside; a plank
pile in the middle. The south module is built once and cloned with radial4.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mpqs_util import *  # noqa: F401,F403


def convert(m):
    F = "frame"
    fe = lambda pred: els(m, F, pred)
    named = lambda n: fe(lambda e: e["name"] == n)
    (floor,) = named("base_floor")
    setbox(m, floor, (-10, 0, -10), (10, 2, 10))
    # channels (south module: x -16..10)
    (ch,) = named("water_channel")
    (ws,) = named("water_surface")
    (cw,) = named("channel_wall")
    setx(ch, -16, 10)
    setx(ws, -15.5, 9.5)
    setx(cw, -16, 10)
    # posts / beams / roof
    posts = named("roof_post")
    m.delete(posts[1:])
    beams = named("roof_beam")
    m.delete(beams[1:])
    setx(beams[0], -15, 13)
    slopes = named("roof_slope")
    south_slope = [e for e in slopes if e["rotation"][0] > 0][0]
    m.delete([e for e in slopes if e is not south_slope])
    m.translate([south_slope], dz=7.5)
    (ridge,) = named("roof_ridge")
    setbox(m, ridge, (-4.5, 31.9, -4.5), (4.5, 33.3, 4.5))
    # bench
    (table,) = named("saw_table")
    setbox(m, table, (-10, 9, 3.5), (2, 11, 9.5))
    legs = named("table_leg")
    for e, (x0, z0) in zip(legs, ((-9.8, 4), (-9.8, 7.4), (0.2, 4), (0.2, 7.4))):
        setbox(m, e, (x0, 2, z0), (x0 + 1.6, 9, z0 + 1.6))
    (slot,) = named("table_slot")
    setbox(m, slot, (-3.9, 10.99, 3.45), (-3.1, 11.05, 9.55))
    (guard,) = named("blade_guard")
    (garm,) = named("blade_guard_arm")
    setbox(m, guard, (-7, 16.5, 5.5), (0, 17.5, 7.5))
    setbox(m, garm, (-1, 11, 5.5), (0, 17.5, 7.5))
    blade = m.group("saw_blade")
    m.translate([blade], dx=-3.5, dz=9.5)
    # log
    log = m.group("log")
    m.scale([log], 0.6, about=(-9, 11, -3))
    m.translate([log], dx=2.3, dz=9.5)
    scale_anim(m, "log", "position", "x", 0.5)
    # wheel drive
    sup = named("wheel_support")
    axle = fe(lambda e: e["name"].startswith("wheel_axle"))
    for e in axle:
        e["from"][2], e["to"][2] = 9.0, 11.6
    (belt,) = named("drive_belt")
    setbox(m, belt, (-6.2, 10.2, 9.5), (-3.5, 10.8, 10.1))
    wheel = m.group("water_wheel")
    # plank pile in the centre
    planks = named("plank_stack")
    place(m, planks, 0.6, 0, 0)
    m.rotate([planks[1]], 90)
    make_group(m, "plank_pile", F, (0, 2, 0), fe(lambda e: e["name"].startswith("plank_stack")))
    mod = [ch, ws, cw, posts[0], beams[0], south_slope, table] + legs + [slot, guard, garm, blade, log, wheel] + sup + axle + [belt]
    m.radial4(mod, ("_e", "_s", "_w"))
    return m


def main():
    out = os.path.join(PACK, "bbmodels", "structure_sawmill.bbmodel")
    m = load_head("sawmill")
    convert(m)
    m.save(out)
    write_override("sawmill", input_bones=["log", "log_e", "log_s", "log_w"],
                   output_bones=["plank_pile"], lamp_at=[0, 0, 33.3])
    print("wrote", out)


if __name__ == "__main__":
    main()
