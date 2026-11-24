#!/usr/bin/env python3
"""One-shot conversion of bbmodels/structure_crop_farm.bbmodel to a 4-way symmetric layout.
Reads the git HEAD version unless --src is given.

Layout: the water-pump windmill tower stands in the centre with a small rotor and a spout + trough on each of its four
sides; a ring of wheat beds (pinwheel, 2 wheat patches each) surrounds it with a scarecrow and crow in the gap of
each side. The north module is built once and cloned with radial4.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _blocky_set_a import els, box, run  # noqa: E402

TX, TZ = 9.5, 10.0  # old tower centre


def convert(m):
    (ground,) = els(m, "ground_grass")
    # --- drop the second bed, the irrigation channel and the vane ----------------------------------
    m.delete([g for g in m.child_groups(m.group("frame")) if g["name"].startswith("wheat_1_")] + [m.group("wheat_0_2")])
    f0, f1 = els(m, "bed_frame"); s0, s1 = els(m, "bed_soil")
    m.delete([f1, s1] + els(m, "irrigation") + els(m, "mill_tail"))
    # --- centre: tower + pump -------------------------------------------------------------------
    tower = els(m, "mill_leg") + els(m, "mill_brace") + els(m, "mill_platform") + els(m, "mill_gearbox") + \
        els(m, "pump_head") + [m.group("pump_rod")]
    m.translate(tower, dx=-TX, dz=-TZ)
    (gb,) = els(m, "mill_gearbox"); box(gb, (-2, 30.8, -2), (2, 33.2, 2))
    # --- north module ----------------------------------------------------------------------------
    spout = els(m, "pump_spout"); trough = els(m, "trough"); water = els(m, "trough_water")
    m.translate(spout + trough + water, dx=-TX, dz=-TZ)
    box(trough[0], (-3, 2, -6), (3, 4.5, -3.5)); box(water[0], (-2.6, 4, -5.6), (2.6, 4.3, -3.9))
    for e in spout:
        e["from"][0], e["to"][0] = -0.5, 0.5
        e["from"][2] = -4.4
        e["to"][2] = -1.5
    # axle boom toward the rotor
    (boom,) = els(m, "mill_tailboom"); box(boom, (-0.3, 31.7, -5.4), (0.3, 32.3, -1))
    rotor = m.group("mill_rotor")
    m.scale(rotor, 0.62, about=(TX, 32, 7.6))
    m.translate(rotor, dx=-TX, dz=-5.7 - 7.6)
    # beds: shorten the bed to two wheat patches, rotate to the north strip
    box(f0, (-14, 2, -15), (-6, 5, -3.5)); box(s0, (-13.4, 5, -14.4), (-6.6, 5.3, -4.1))
    wheat = [m.group("wheat_0_0"), m.group("wheat_0_1")]
    bed = [f0, s0] + wheat
    m.rotate(bed, 90)
    # scarecrow + crow in the gap
    sc = m.group("scarecrow"); cr = m.group("crow")
    m.translate([sc, cr], dx=-20, dz=9.5)
    m.rotate([sc, cr], 90)
    module = els(m, "bed_frame") + els(m, "bed_soil") + [m.group("wheat_0_0"), m.group("wheat_0_1"), m.group("scarecrow"),
                                                          m.group("crow"), rotor, boom] + spout + trough + water
    m.radial4(module, ("_e", "_s", "_w"))
    return m


if __name__ == "__main__":
    run("crop_farm", convert)
