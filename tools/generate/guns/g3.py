"""HK G3 battle rifle (1025 mm -> 18.6 px at 1 px = 55 mm).

WeaponMechanics: 2-round burst (fire_interval 0.1), reload 2.5 s, firearm (slide open 9 + close 9) 0.9 s,
zoom 1.7. Moving parts: magazine, charging_handle, bolt, trigger.
Run: python3 tools/generate/guns/g3.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gunlib  # noqa: E402
from gunlib import GunModel, Material  # noqa: E402

gunlib.MATERIALS["g3_polymer"] = Material("#222326", "polymer", 0.04, -0.18, 0.0)   # black furniture
gunlib.MATERIALS["g3_park"] = Material("#6b6e6c", "metal", 0.08, -0.2, 0.2)        # light parkerized stamped receiver
gunlib.MATERIALS["g3_mag"] = Material("#9a9fa6", "metal", 0.05, -0.15, 0.2)       # aluminium magazine

m = GunModel("g3", "G3")
B, C = m.box, m.cbox

for name, piv in (("magazine", (0, -2.5, -2.95)), ("charging_handle", (-0.9, 1.2, -4.9)),
                  ("bolt", (0.85, 0.4, -3.6)), ("trigger", (0, -1.3, -0.55))):
    m.part(name, piv)


def sym(name, x0, x1, y0, y1, z0, z1, mat, **kw):
    """Mirrored pair of boxes; x0 < x1 are positive distances from the centre plane."""
    B(name + "_r", (x0, y0, z0), (x1, y1, z1), mat, **kw)
    B(name + "_l", (-x1, y0, z0), (-x0, y1, z1), mat, **kw)


# ---------------------------------------------------------------- receiver
B("rec_upper", (-0.8, -0.3, -6.1), (0.8, 0.9, 0.4), "g3_park")
B("rec_lower", (-0.7, -0.95, -4.1), (0.7, -0.15, 1.4), "g3_park")
B("rec_rear_plate", (-0.86, -0.3, 0.3), (0.86, 0.95, 0.55), "steel_dark")
B("eject_port", (0.79, 0.08, -4.2), (0.83, 0.72, -0.8), "steel_dark")
for sx in (1, -1):
    for z, y in ((-5.6, 0.6), (-5.6, 0.0), (-0.25, 0.6), (-0.25, 0.0)):
        C(f"rivet_{'r' if sx > 0 else 'l'}_{z}_{y}", (sx * 0.825, y, z), (0.07, 0.14, 0.14), "gunmetal")

# cocking tube (long tube above the barrel) with slot and front collar
m.cylinder_z("tube", (0, 1.2), 0.5, -5.9, -0.4, "steel_dark")
B("tube_slot", (-0.52, 1.05, -5.3), (-0.44, 1.25, -0.9), "rubber")
m.cylinder_z("tube_collar", (0, 1.2), 0.58, -5.95, -5.75, "steel_dark")

# drum rotary rear sight
B("rs_base", (-0.55, 0.85, -0.45), (0.55, 1.35, 0.7), "steel_dark")
B("rs_floor", (-0.5, 1.3, 0.0), (0.5, 1.55, 0.6), "steel")
sym("rs_ear", 0.18, 0.5, 1.55, 2.3, 0.0, 0.6, "steel_dark")
B("rs_knob_l", (-0.72, 1.35, 0.1), (-0.45, 1.85, 0.5), "gunmetal")
B("rs_knob_r", (0.45, 1.35, 0.1), (0.72, 1.85, 0.5), "gunmetal")

# ---------------------------------------------------------------- handguard + barrel
B("hg_rear", (-1.0, -0.95, -8.2), (1.0, 1.1, -5.95), "g3_polymer")
B("hg_front", (-0.92, -0.9, -10.4), (0.92, 1.05, -8.15), "g3_polymer")
B("hg_cap", (-0.97, -0.95, -10.5), (0.97, 1.1, -10.35), "steel")
for i, z in enumerate((-10.1, -9.6, -9.1, -8.6)):
    sym(f"hg_vent{i}", 0.88, 0.96, -0.4, 0.5, z - 0.1, z + 0.1, "steel_dark")
for i, z in enumerate((-9.4, -8.7, -8.0, -7.3, -6.6)):
    B(f"hg_rib{i}", (-0.55, -1.13, z - 0.12), (0.55, -0.9, z + 0.12), "g3_polymer")
# front sling swivel
B("sling_f_a", (-0.08, -1.4, -10.15), (0.08, -0.9, -10.0), "steel")
B("sling_f_b", (-0.08, -1.4, -9.65), (0.08, -0.9, -9.5), "steel")
B("sling_f_c", (-0.08, -1.42, -10.15), (0.08, -1.28, -9.5), "steel")

m.cylinder_z("barrel", (0, 0), 0.45, -11.05, -10.3, "steel")
# front sight: base + hood ring + post
B("fs_base", (-0.3, 0.35, -10.95), (0.3, 1.0, -10.55), "steel")
B("fs_ring_bot", (-0.5, 0.9, -10.95), (0.5, 1.1, -10.55), "steel_dark")
B("fs_ring_top", (-0.5, 2.1, -10.95), (0.5, 2.3, -10.55), "steel_dark")
B("fs_ring_l", (-0.7, 0.9, -10.95), (-0.5, 2.3, -10.55), "steel_dark")
B("fs_ring_r", (0.5, 0.9, -10.95), (0.7, 2.3, -10.55), "steel_dark")
B("fs_post", (-0.08, 1.0, -10.85), (0.08, 1.9, -10.65), "steel")
# slotted flash hider (cage)
m.cylinder_z("fh_core", (0, 0), 0.38, -12.2, -11.0, "steel_dark")
B("fh_ring_rear", (-0.5, -0.5, -11.45), (0.5, 0.5, -11.0), "steel")
B("fh_ring_front", (-0.5, -0.5, -12.2), (0.5, 0.5, -11.95), "steel")
B("fh_bar_t", (-0.15, 0.3, -11.97), (0.15, 0.46, -11.43), "steel")
B("fh_bar_b", (-0.15, -0.46, -11.97), (0.15, -0.3, -11.43), "steel")
B("fh_bar_l", (-0.46, -0.15, -11.97), (-0.3, 0.15, -11.43), "steel")
B("fh_bar_r", (0.3, -0.15, -11.97), (0.46, 0.15, -11.43), "steel")

# ---------------------------------------------------------------- stock (fixed polymer)
B("st_neck", (-0.55, -0.3, 0.55), (0.55, 0.7, 2.05), "g3_polymer")
B("st_mid", (-0.62, -1.5, 2.0), (0.62, 0.6, 4.25), "g3_polymer")
B("st_rear", (-0.66, -2.1, 4.2), (0.66, 0.5, 5.95), "g3_polymer")
B("butt_pad", (-0.72, -2.35, 5.9), (0.72, 0.55, 6.4), "rubber")
C("butt_screw_a", (0, -0.1, 6.4), (0.22, 0.22, 0.1), "steel")
C("butt_screw_b", (0, -1.9, 6.4), (0.22, 0.22, 0.1), "steel")
sym("st_groove_a", 0.6, 0.66, -0.95, -0.85, 2.4, 4.0, "steel_dark")
sym("st_groove_b", 0.64, 0.7, -1.55, -1.45, 4.5, 5.7, "steel_dark")
B("sling_r_a", (-0.08, -2.5, 4.6), (0.08, -2.05, 4.75), "steel")
B("sling_r_b", (-0.08, -2.5, 5.2), (0.08, -2.05, 5.35), "steel")
B("sling_r_c", (-0.08, -2.52, 4.6), (0.08, -2.38, 5.35), "steel")

# ---------------------------------------------------------------- pistol grip / trigger group
GC = (0.0, -1.96, 1.36)   # grip centre; 2.4 long, hangs 2.2 below the receiver, raked 22.5 deg (bottom toward +Z)
GD = (0.0, -0.9239, 0.3827)   # down the grip


def galong(s):
    return (GC[0], GC[1] + GD[1] * s, GC[2] + GD[2] * s)


C("grip", GC, (0.7, 2.4, 1.2), "g3_polymer", rotation=(-22.5, 0, 0))
C("grip_panel_r", (0.37, galong(0.1)[1], galong(0.1)[2]), (0.08, 1.8, 0.95), "polymer", rotation=(-22.5, 0, 0))
C("grip_panel_l", (-0.37, galong(0.1)[1], galong(0.1)[2]), (0.08, 1.8, 0.95), "polymer", rotation=(-22.5, 0, 0))
C("grip_cap", galong(1.2), (0.8, 0.2, 1.3), "steel_dark", rotation=(-22.5, 0, 0))
B("tg_front", (-0.3, -2.2, -1.9), (0.3, -0.85, -1.78), "steel")
B("tg_bottom", (-0.3, -2.22, -1.85), (0.3, -2.08, 0.85), "steel_dark")
B("tr_a", (-0.1, -1.5, -0.62), (0.1, -0.9, -0.42), "steel", group="trigger")
B("tr_b", (-0.1, -1.95, -0.45), (0.1, -1.45, -0.25), "steel", group="trigger")
B("sel_base", (-0.78, -0.55, 0.05), (-0.68, -0.3, 0.3), "steel_dark")
B("sel_lever", (-0.92, -0.5, 0.1), (-0.76, -0.38, 0.8), "gunmetal")
sym("mag_release", 0.7, 0.78, -0.85, -0.55, -1.7, -1.3, "gunmetal")
B("pin_front", (-0.76, -0.8, -4.0), (0.76, -0.6, -3.85), "gunmetal")
B("pin_rear", (-0.76, -0.8, 0.95), (0.76, -0.6, 1.1), "gunmetal")

# ---------------------------------------------------------------- moving parts
B("ch_arm", (-0.9, 1.0, -5.2), (-0.4, 1.4, -4.6), "steel_dark", group="charging_handle")
B("ch_knob", (-1.4, 0.9, -5.3), (-0.95, 1.55, -4.5), "steel_dark", group="charging_handle")
for i, z in enumerate((-5.15, -4.9, -4.65)):
    B(f"ch_ridge{i}", (-1.46, 0.95, z - 0.04), (-1.38, 1.5, z + 0.04), "gunmetal", group="charging_handle")
B("bolt_body", (0.85, 0.2, -4.0), (0.92, 0.6, -3.3), "gunmetal", group="bolt")

B("mag_body", (-0.6, -4.25, -3.9), (0.6, -0.6, -2.0), "g3_mag", group="magazine")
B("mag_floor", (-0.68, -4.42, -4.0), (0.68, -4.2, -1.9), "steel_dark", group="magazine")
for i, zc in enumerate((-3.55, -2.95, -2.35)):
    sym(f"mag_rib{i}", 0.58, 0.66, -4.05, -1.3, zc - 0.1, zc + 0.1, "g3_mag", group="magazine")

# ---------------------------------------------------------------- points
m.point("grip", (0, -1.96, 1.36))
m.point("support", (-0.3, -1.15, -7.6))
m.point("sight_rear", (0, 1.9, 0.0))
m.point("sight_front", (0, 1.9, -10.75))
m.point("muzzle", (0, 0, -12.2))

OFF = m.place_gun_at_hip()
m.muzzle_flash()
m.build_arms()


def V(p):
    """Local (pre-place_gun) point -> viewmodel space."""
    return (p[0] + OFF[0], p[1] + OFF[1], p[2] + OFF[2])


MAG_PT = V((-0.2, -3.2, -2.95))
HANDLE_PT = V((-1.1, 1.25, -4.9))
FETCH = (-5.0, -8.0, -7.5)

m.standard_animations(fire_interval=0.1, kick=0.4, climb=1.8, bolt="bolt", bolt_travel=0.9, eye_relief=5.0)
for nm in ("shoot", "aiming_shoot"):
    a = m.anims[nm]
    a.key("trigger", 0.0, pos=(0, 0, 0))
    a.key("trigger", 0.02, pos=(0, 0, 0.35))
    a.key("trigger", 0.08, pos=(0, 0, 0.35))
    a.key("trigger", 0.1, pos=(0, 0, 0))


def track(a, bone, frames, curve="smooth"):
    """frames: [(t, rot, pos)] eased between consecutive entries."""
    for (t0, r0, p0), (t1, r1, p1) in zip(frames, frames[1:]):
        if t1 - t0 < 1e-6:
            continue
        a.ease(bone, t0, t1, rot0=r0, rot1=r1, pos0=p0, pos1=p1, curve=curve)


Z3 = (0.0, 0.0, 0.0)


def reload_motion(a, t0=0.0):
    T = lambda t: t0 + t  # noqa: E731
    tilt_r, tilt_p = (8, -6, -14), (0.2, 1.0, 1.4)
    track(a, "gun", [
        (T(0.0), Z3, Z3), (T(0.3), tilt_r, tilt_p), (T(1.9), tilt_r, tilt_p),
        (T(1.97), (11, -6, -14), (0.2, 1.0, 1.85)), (T(2.07), tilt_r, tilt_p), (T(2.5), Z3, Z3)])
    # old magazine out
    track(a, "magazine", [(T(0.0), None, Z3), (T(0.55), None, Z3), (T(0.7), None, (0, -0.4, 0)),
                          (T(0.95), None, (0, -3.8, 0.0)), (T(1.14), None, (-3.5, -7.5, 1.0))])
    a.key("magazine", T(1.14), scale=1.0)
    a.key("magazine", T(1.16), scale=0.0)
    # new magazine comes up from the fetch point
    a.key("magazine", T(1.25), scale=1.0)
    track(a, "magazine", [(T(1.25), None, (-8.0, -4.1, 2.0)), (T(1.65), None, (-1.5, -3.2, 0.3)),
                          (T(1.8), None, (0, -3.0, 0.0))])
    a.ease("magazine", T(1.8), T(1.95), pos0=(0, -3.0, 0), pos1=Z3, curve="in")
    a.key("magazine", T(2.5), pos=Z3, scale=1.0)
    a.hand("left", T(0.0), "support")
    a.hand("left", T(0.3), "support")
    a.hand("left", T(0.55), ("bone", "magazine", MAG_PT))
    a.hand("left", T(0.95), ("bone", "magazine", MAG_PT))
    a.hand("left", T(1.15), FETCH)
    a.hand("left", T(1.26), ("bone", "magazine", MAG_PT))
    a.hand("left", T(2.0), ("bone", "magazine", MAG_PT))
    a.hand("left", T(2.3), "support")


def fix_rot_keys(a):
    """magazine rotation channel never keyed; nothing to do (track passes rot None)."""


def firearm_motion(a, t0=0.0):
    T = lambda t: t0 + t  # noqa: E731
    pull = 2.4
    track(a, "charging_handle", [(T(0.0), (0, 0, 0), Z3), (T(0.12), (0, 0, 0), Z3)])
    a.ease("charging_handle", T(0.12), T(0.4), rot0=(0, 0, 0), rot1=(0, 0, -8), pos0=Z3, pos1=(0, 0, pull), curve="smooth")
    a.ease("charging_handle", T(0.4), T(0.5), rot0=(0, 0, -8), rot1=(0, 0, -8), pos0=(0, 0, pull), pos1=(0, 0, pull))
    a.ease("charging_handle", T(0.5), T(0.62), rot0=(0, 0, -8), rot1=(0, 0, 0), pos0=(0, 0, pull), pos1=Z3, curve="in")
    a.key("charging_handle", T(0.9), rot=(0, 0, 0), pos=Z3)
    a.ease("bolt", T(0.12), T(0.4), pos0=Z3, pos1=(0, 0, pull), curve="smooth")
    a.ease("bolt", T(0.4), T(0.5), pos0=(0, 0, pull), pos1=(0, 0, pull))
    a.ease("bolt", T(0.5), T(0.62), pos0=(0, 0, pull), pos1=Z3, curve="in")
    a.key("bolt", T(0.9), pos=Z3)
    track(a, "gun", [(T(0.0), Z3, Z3), (T(0.12), (2, 3, -3), (0, 0, 0.1)), (T(0.5), (2, 3, -3), (0, 0, 0.1)),
                     (T(0.62), (3, 1, -1), (0, -0.1, 0.35)), (T(0.9), Z3, Z3)])
    a.hand("left", T(0.0), "support")
    a.hand("left", T(0.14), ("bone", "charging_handle", HANDLE_PT))
    a.hand("left", T(0.66), ("bone", "charging_handle", HANDLE_PT))
    a.hand("left", T(0.9), "support")
    a.key("glow_flash", T(0.0), scale=0.0)


# ---- reload
a = m.anim("reload", 2.5, "once")
reload_motion(a)

# ---- reload_empty = reload + HK slap
a = m.anim("reload_empty", 3.4, "once")
reload_motion(a)
firearm_motion(a, 2.5)

# ---- inspect
a = m.anim("inspect", 3.0, "once")
IP = (-0.8, 1.0, 0.0)
track(a, "gun", [
    (0.0, Z3, Z3), (0.6, (-5, 0, 5), IP), (0.75, (-5, 0, 5), IP),
    (1.35, (-3, -40, 4), IP), (1.5, (-3, -40, 4), IP),
    (2.2, (-3, 40, 4), IP), (2.35, (-3, 40, 4), IP),
    (2.65, (-5, 0, 5), IP), (3.0, Z3, Z3)])
# the support hand lets go while the rifle is turned and waits at the rest handguard position
a.hand("left", 0.0, "support")
a.hand("left", 0.6, "support")
a.hand("left", 0.9, m.points["support"])
a.hand("left", 2.3, m.points["support"])
a.hand("left", 2.7, "support")
a.hand("left", 3.0, "support")

# ---- firearm (HK slap)
a = m.anim("firearm", 0.9, "once")
firearm_motion(a)

m.repivot_gun_keys()   # gun keys were tuned about the old pivot (local origin)
# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail()

m.write(item_name="g3")
