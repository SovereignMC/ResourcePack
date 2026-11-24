#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_power_plant.bbmodel (git HEAD version) to a 4-way layout.

Cross-shaped boiler: a hub with the steam dome in the centre and four boiler arms, each ending in a firebox with a
chimney. One arm (-X) is built once together with a small engine (flywheel + piston) in its NW corner and a dynamo
with insulators in its SW corner, then cloned with radial4.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mpqs_util import *  # noqa: F401,F403


def convert(m):
    F = "frame"
    fe = lambda pred: els(m, F, pred)
    starts = lambda *p: fe(lambda e: e["name"].startswith(p))
    # square floor
    (fl,) = fe(lambda e: e["name"] == "base_floor")
    setbox(m, fl, (-16, 0, -16), (16, 2, 16))
    # --- arm: everything of the boiler/firebox/stack shifted to z=0
    shell = starts("boiler_shell")
    hub = m.clone(shell, suffix="_hub")
    for e in hub:
        setx(e, -3, 3)
    arm = shell + starts("boiler_band", "boiler_saddle", "firebox", "stack") + [m.group("smoke")]
    m.translate(arm, dz=-8)
    for e in shell:
        setx(e, -12, -3)
    for e in hub:
        e["from"][2] -= 8
        e["to"][2] -= 8
        e["origin"][2] -= 8
    # bands: keep the one at -11 and the one at -2 (moved to -7); drop the one at +7
    bands = starts("boiler_band")
    m.delete([e for e in bands if cx(e) > 5])
    m.translate([e for e in bands if -4 < cx(e) < 0], dx=-5)
    sad = starts("boiler_saddle")
    m.translate([e for e in sad if cx(e) > 0], dx=-11)
    # centre: steam dome + header pipes
    dome = starts("steam_dome")
    m.translate(dome, dz=-8)
    p1, p2 = starts("steam_pipe")
    setbox(m, p1, (-9, 17.8, -0.7), (0, 19.2, 0.7))
    setbox(m, p2, (-9.7, 15, -0.7), (-8.3, 19, 0.7))
    m.delete(starts("gauge_"))
    # --- engine in the NW corner, dynamo set in the SW corner
    eng = starts("piston_cyl", "crosshead_guide", "flywheel_pedestal") + [m.group("piston"), m.group("flywheel")]
    place(m, eng, 0.42, -10.5, -10.5)
    dyn = starts("dynamo_", "insulator_", "wire") + [m.group("spark")]
    place(m, dyn, 0.7, -10.5, 10.5)
    m.delete(starts("coal_pile"))
    mod = arm + hub + [p1, p2] + eng + dyn
    m.radial4(mod, ("_e", "_s", "_w"))
    return m


def main():
    out = os.path.join(PACK, "bbmodels", "structure_power_plant.bbmodel")
    m = load_head("power_plant")
    convert(m)
    m.save(out)
    write_override("power_plant", input_bones=["flywheel", "flywheel_e", "flywheel_s", "flywheel_w"],
                   output_bones=["spark", "spark_e", "spark_s", "spark_w"], lamp_at=[0, 0, 19.4])
    print("wrote", out)


if __name__ == "__main__":
    main()
