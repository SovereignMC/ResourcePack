"""Steyr SSG 69 bolt-action sniper rifle (Kahles ZF69 scope, Cycolac stock).

Local build space: bore on the Z axis at x=0, y=0, muzzle toward -Z, butt at +Z.
Length ~20.8 px (real 1140 mm at 55 mm/px).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gunlib  # noqa: E402
from gunlib import GunModel, Material  # noqa: E402

M = gunlib.MATERIALS
M["cycolac"] = Material("#7d8858", "polymer", 0.05, -0.18, 0.0)
M["cycolac_dark"] = Material("#5c6642", "polymer", 0.05, -0.18, 0.0)
M["mag_smoke"] = Material("#59656a", "glass", 0.02, -0.12, 0.0)
M["black"] = Material("#060606", "metal", 0.0, 0.0, 0.0)
M["lens"] = Material("#243e5c", "glass", 0.0, 0.0, 0.0)

m = GunModel("ssg69", "SSG 69")

SY = 1.95   # scope axis height above the bore


# ---------------------------------------------------------------- moving parts (bones)
m.part("bolt", (0, 0, 2.6))
m.part("magazine", (0, -1.8, 0.2))
m.part("trigger", (0, -2.4, 1.9))

# ---------------------------------------------------------------- barrel
m.octa("barrel", 0, 0, 0.5, -10.6, -2.0, "steel_dark")
m.octa("crown", 0, 0, 0.6, -11.0, -10.55, "steel")
m.box("bore", (-0.2, -0.2, -11.04), (0.2, 0.2, -11.0), "black")
for i in range(8):   # cold-hammer-forged spiral hint: bands twisting by 22.5 deg
    z = -10.25 + i * 0.45
    m.box(f"hf_band{i}", (-0.52, -0.52, z - 0.1), (0.52, 0.52, z + 0.1), "steel", rotation=(0, 0, 22.5 * (i % 3)))
# iron front sight (under the scope line)
m.box("fs_base", (-0.2, 0.4, -10.3), (0.2, 0.75, -9.7), "steel_dark")
m.box("fs_blade", (-0.06, 0.74, -10.1), (0.06, 1.0, -9.95), "steel_dark")
m.box("fs_hood_l", (-0.34, 0.4, -10.35), (-0.2, 1.05, -9.65), "steel_dark")
m.box("fs_hood_r", (0.2, 0.4, -10.35), (0.34, 1.05, -9.65), "steel_dark")

# ---------------------------------------------------------------- receiver
m.octa("receiver", 0, 0, 0.78, -2.2, 3.2, "parkerized")
m.octa("barrel_nut", 0, 0, 0.88, -2.75, -2.2, "steel")
m.box("eject_port", (0.78, 0.0, 0.2), (0.81, 0.42, 1.5), "black")
m.box("rear_bridge", (-0.3, 0.74, 2.0), (0.3, 0.92, 3.0), "steel_dark")

# ---------------------------------------------------------------- scope (Kahles ZF69)
m.octa("scope_tube", 0, SY, 0.55, -3.1, 0.9, "steel")
m.octa("scope_eye", 0, SY, 0.72, 0.9, 1.9, "steel")
m.octa("scope_eye_lip", 0, SY, 0.82, 1.9, 2.15, "gunmetal")
m.box("scope_lens_rear", (-0.5, SY - 0.5, 2.15), (0.5, SY + 0.5, 2.18), "lens")
m.octa("scope_taper", 0, SY, 0.75, -3.6, -3.1, "steel")
m.octa("scope_bell", 0, SY, 0.98, -5.35, -3.6, "steel")
m.box("scope_lens_front", (-0.8, SY - 0.8, -5.38), (0.8, SY + 0.8, -5.35), "lens")
for nm, z0, z1 in (("ring_f", -2.6, -2.1), ("ring_r", 0.0, 0.5)):
    m.octa(nm, 0, SY, 0.82, z0, z1, "gunmetal")
    m.box(f"{nm}_base", (-0.5, 0.62, z0), (0.5, SY - 0.7, z1), "steel")
    for j, dz in enumerate((0.13, 0.37)):
        m.box(f"{nm}_screw{j}", (0.82, SY - 0.12, z0 + dz - 0.07), (0.9, SY + 0.12, z0 + dz + 0.07), "steel_dark")
# turrets: elevation on top, windage on the right
m.box("elev_stem", (-0.22, SY + 0.5, -1.35), (0.22, SY + 0.9, -0.75), "steel")
m.box("elev_cap", (-0.34, SY + 0.9, -1.4), (0.34, SY + 1.2, -0.7), "steel_dark")
m.box("elev_cap_r", (-0.34, SY + 0.9, -1.4), (0.34, SY + 1.2, -0.7), "steel_dark", rotation=(0, 45, 0))
m.box("wind_stem", (0.5, SY - 0.22, -1.35), (0.9, SY + 0.22, -0.75), "steel")
m.box("wind_cap", (0.9, SY - 0.34, -1.4), (1.2, SY + 0.34, -0.7), "steel_dark")
m.box("wind_cap_r", (0.9, SY - 0.34, -1.4), (1.2, SY + 0.34, -0.7), "steel_dark", rotation=(45, 0, 0))

# ---------------------------------------------------------------- stock (Cycolac)
# forend
m.box("forend", (-0.9, -1.8, -6.6), (0.9, -0.5, -1.4), "cycolac")
m.box("forend_cheek_l", (-0.86, -0.55, -6.45), (-0.52, 0.1, -1.4), "cycolac")
m.box("forend_cheek_r", (0.52, -0.55, -6.45), (0.86, 0.1, -1.4), "cycolac")
m.box("forend_tip", (-0.95, -1.9, -6.95), (0.95, 0.1, -6.6), "polymer")
for nm, sx in (("l", -1), ("r", 1)):
    for j, (z, y) in enumerate(((-3.0, -1.1), (-5.6, -1.1))):
        x0, x1 = (0.9, 0.96) if sx > 0 else (-0.96, -0.9)
        m.box(f"forend_screw_{nm}{j}", (x0, y - 0.1, z - 0.1), (x1, y + 0.1, z + 0.1), "aluminium")
# action stock
m.box("action_stock", (-0.9, -2.4, -1.4), (0.9, -0.6, 3.4), "cycolac")
m.box("action_cheek_l", (-0.88, -0.65, -1.4), (-0.74, 0.0, 3.4), "cycolac")
m.box("action_cheek_r", (0.74, -0.65, -1.4), (0.88, 0.0, 1.9), "cycolac")
# pistol grip (raked back 22.5 deg, 2.7 long, hangs ~2.2 below the stock)
GC = (0.0, -3.35, 3.82)
D = (0.0, -math.cos(math.radians(22.5)), math.sin(math.radians(22.5)))   # down the grip


def along(s):
    return (GC[0], GC[1] + D[1] * s, GC[2] + D[2] * s)


m.cbox("grip", GC, (0.7, 2.7, 1.2), "cycolac", rotation=(-22.5, 0, 0))
m.cbox("grip_cap", along(1.42), (0.8, 0.22, 1.3), "cycolac_dark", rotation=(-22.5, 0, 0))
for i, s in enumerate((-0.7, -0.15, 0.4, 0.95)):
    m.cbox(f"grip_groove{i}", along(s), (0.76, 0.09, 1.0), "cycolac_dark", rotation=(-22.5, 0, 0))
# buttstock (slim synthetic profile: wrist ~1.2 deep, butt ~2.5 deep, top/cheek line unchanged)
m.box("stock_wrist", (-0.8, -1.95, 3.4), (0.8, -0.75, 5.0), "cycolac")
m.box("stock_mid", (-0.82, -2.5, 5.0), (0.82, -0.75, 6.6), "cycolac")
m.box("stock_butt", (-0.8, -3.1, 6.6), (0.8, -0.95, 9.0), "cycolac")
m.box("stock_comb", (-0.55, -0.95, 5.0), (0.55, -0.72, 8.2), "cycolac_dark")
m.box("spacer1", (-0.86, -3.2, 9.0), (0.86, -0.85, 9.2), "polymer")
m.box("spacer2", (-0.88, -3.25, 9.2), (0.88, -0.8, 9.38), "cycolac_dark")
m.box("butt_pad", (-0.9, -3.3, 9.38), (0.9, -0.7, 9.8), "rubber")
for i, (x, y) in enumerate(((-0.45, -1.3), (0.45, -2.8))):
    m.box(f"butt_screw{i}", (x - 0.1, y - 0.1, 9.8), (x + 0.1, y + 0.1, 9.86), "aluminium")
# sling swivels
for nm, z, ybot in (("f", -5.0, -1.8), ("r", 5.8, -2.5)):
    m.box(f"swivel_{nm}_stud", (-0.12, ybot - 0.3, z - 0.12), (0.12, ybot, z + 0.12), "steel")
    m.box(f"swivel_{nm}_bar", (-0.1, ybot - 0.62, z - 0.5), (0.1, ybot - 0.47, z + 0.5), "steel")
    m.box(f"swivel_{nm}_a", (-0.1, ybot - 0.62, z - 0.5), (0.1, ybot - 0.3, z - 0.36), "steel")
    m.box(f"swivel_{nm}_b", (-0.1, ybot - 0.62, z + 0.36), (0.1, ybot - 0.3, z + 0.5), "steel")

# ---------------------------------------------------------------- trigger + guard
m.box("trigger_blade", (-0.13, -3.0, 1.75), (0.13, -2.3, 2.05), "steel_dark", group="trigger")
m.box("trigger_tip", (-0.13, -3.3, 1.6), (0.13, -3.0, 1.9), "steel_dark", group="trigger")
m.box("guard_bottom", (-0.2, -3.7, 1.1), (0.2, -3.52, 3.45), "steel_dark")
m.box("guard_front", (-0.2, -3.7, 1.1), (0.2, -2.4, 1.28), "steel_dark")

# ---------------------------------------------------------------- magazine (5-round rotary)
m.box("mag_body", (-0.93, -2.4, -0.6), (0.93, -1.15, 1.0), "mag_smoke", group="magazine")
for nm, x0, x1 in (("l", -0.97, -0.93), ("r", 0.93, 0.97)):
    for j, z in enumerate((-0.25, 0.4)):
        m.box(f"mag_round_{nm}{j}", (x0, -2.1, z - 0.2), (x1, -1.45, z + 0.2), "brass", group="magazine")
m.box("mag_cap", (-0.7, -2.62, -0.45), (0.7, -2.4, 0.85), "steel", group="magazine")
m.box("mag_cap_r", (-0.5, -2.64, -0.3), (0.5, -2.42, 0.7), "steel_dark", group="magazine", rotation=(0, 45, 0))
m.box("mag_well", (-0.6, -2.43, -0.4), (0.6, -2.38, 0.8), "black")

# ---------------------------------------------------------------- bolt (handle + body)
m.cylinder_z("bolt_body", (0, 0), 0.42, 0.8, 3.9, "steel", group="bolt")
m.box("bolt_cock", (-0.3, -0.3, 3.9), (0.3, 0.3, 4.4), "steel_dark", group="bolt")
m.box("bolt_collar", (0.3, -0.3, 2.35), (0.75, 0.2, 2.85), "steel", group="bolt")
m.box("bolt_stalk", (0.7, -0.24, 2.47), (2.0, 0.08, 2.75), "steel", group="bolt")
m.cbox("bolt_knob", (2.5, -0.2, 2.61), (0.9, 0.9, 0.9), "polymer", group="bolt")
m.cbox("bolt_knob_r", (2.5, -0.2, 2.61), (0.9, 0.9, 0.9), "polymer", group="bolt", rotation=(0, 45, 0))

KNOB = (2.5, -0.2, 2.61)
MAGPT = (0.0, -2.7, 0.2)

# ---------------------------------------------------------------- points
m.point("grip", (0.0, -3.3, 3.8))
m.point("support", (0.0, -1.6, -3.0))
m.point("sight_rear", (0.0, SY, 2.17))
m.point("sight_front", (0.0, SY, -5.38))
m.point("muzzle", (0.0, 0.0, -11.05))

gun_cubes = len(m.cubes)
OFFSET = m.place_gun_at_hip()
m.muzzle_flash(size=2.6)
m.build_arms()


def P(p):   # local point -> placed space
    return tuple(p[i] + OFFSET[i] for i in range(3))


KNOB = P(KNOB)
MAGPT = P(MAGPT)
MAG_PIVOT = m.groups["magazine"].origin
ER = 3.0
m.standard_animations(fire_interval=1.7, kick=1.3, climb=7.0, roll=1.8, bolt=None, eye_relief=ER)

# trigger pull in both shots
for nm in ("shoot", "aiming_shoot"):
    a = m.anims[nm]
    a.key("trigger", 0.0, pos=(0, 0, 0.3))
    a.key("trigger", 0.12, pos=(0, 0, 0.3))
    a.key("trigger", 0.3, pos=(0, 0, 0))


def go(a, bone, t0, t1, rot0=(0, 0, 0), rot1=(0, 0, 0), pos0=(0, 0, 0), pos1=(0, 0, 0), curve="smooth"):
    a.ease(bone, t0, t1, rot0=rot0, rot1=rot1, pos0=pos0, pos1=pos1, curve=curve)


BOLT_UP = (0, 0, 60)   # +Z rotation swings the right-hand handle up
BOLT_BACK = (0, 0, 2.2)


def bolt_cycle(a, t0, up=0.25, back=0.25, fwd=0.25, down=0.25):
    t1, t2, t3, t4 = t0 + up, t0 + up + back, t0 + up + back + fwd, t0 + up + back + fwd + down
    go(a, "bolt", t0, t1, rot0=(0, 0, 0), rot1=BOLT_UP, pos0=(0, 0, 0), pos1=(0, 0, 0))
    go(a, "bolt", t1, t2, rot0=BOLT_UP, rot1=BOLT_UP, pos0=(0, 0, 0), pos1=BOLT_BACK)
    go(a, "bolt", t2, t3, rot0=BOLT_UP, rot1=BOLT_UP, pos0=BOLT_BACK, pos1=(0, 0, 0))
    go(a, "bolt", t3, t4, rot0=BOLT_UP, rot1=(0, 0, 0), pos0=(0, 0, 0), pos1=(0, 0, 0))
    return t4


# ---------------------------------------------------------------- firearm (bolt cycle, 1.0 s)
a = m.anim("firearm", 1.0, "once")
a.key("bolt", 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
bolt_cycle(a, 0.12, 0.2, 0.2, 0.2, 0.2)
a.key("bolt", 1.0, rot=(0, 0, 0), pos=(0, 0, 0))
a.hand("right", 0.0, "grip")
a.hand("right", 0.12, ("bone", "bolt", KNOB))
a.hand("right", 0.92, ("bone", "bolt", KNOB))
a.hand("right", 1.0, "grip")
# the rifle rocks a little as the bolt is worked
a.key("gun", 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
a.key("gun", 0.3, rot=(0.8, 0, 6.0), pos=(0, -1.7, 0.9))
a.key("gun", 0.75, rot=(0.8, 0, 6.0), pos=(0, -1.7, 0.9))
a.key("gun", 1.0, rot=(0, 0, 0), pos=(0, 0, 0))

# ---------------------------------------------------------------- reload (2.5 s, bolt closed)
a = m.anim("reload", 2.5, "once")
TILT = (8, 0, -30)
TPOS = (-1.0, 2.0, 0.0)
a.key("gun", 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
go(a, "gun", 0.0, 0.35, rot1=TILT, pos1=TPOS)
a.key("gun", 1.95, rot=TILT, pos=TPOS)
a.key("gun", 2.0, rot=(TILT[0] - 1.5, 0, TILT[2]), pos=(TPOS[0], TPOS[1] - 0.2, TPOS[2] + 0.3))     # mag click
go(a, "gun", 2.0, 2.45, rot0=(TILT[0] - 1.5, 0, TILT[2]), rot1=(0, 0, 0), pos0=(TPOS[0], TPOS[1] - 0.2, TPOS[2] + 0.3), pos1=(0, 0, 0))
a.key("gun", 2.5, rot=(0, 0, 0), pos=(0, 0, 0))
OFFSCR = (-11.0, -6.5, 7.5)
DOWN = (0, -3.4, 0)
a.key("magazine", 0.0, pos=(0, 0, 0), scale=1)
a.key("magazine", 0.4, pos=(0, 0, 0))
go(a, "magazine", 0.4, 0.75, pos0=(0, 0, 0), pos1=DOWN, curve="out")
go(a, "magazine", 0.75, 1.08, pos0=DOWN, pos1=OFFSCR)
a.key("magazine", 1.09, pos=OFFSCR, scale=0)
a.key("magazine", 1.28, pos=OFFSCR, scale=0)
a.key("magazine", 1.29, pos=OFFSCR, scale=1)
go(a, "magazine", 1.29, 1.78, pos0=OFFSCR, pos1=(0, -3.4, 0.0))
go(a, "magazine", 1.78, 1.98, pos0=(0, -3.4, 0.0), pos1=(0, 0, 0), curve="in")
a.key("magazine", 2.5, pos=(0, 0, 0), scale=1)
a.hand("left", 0.0, "support")
a.hand("left", 0.38, ("bone", "magazine", MAGPT))
a.hand("left", 1.98, ("bone", "magazine", MAGPT))
a.hand("left", 2.35, "support")

# ---------------------------------------------------------------- inspect (3.5 s)
a = m.anim("inspect", 3.5, "once")
R_SIDE = (-4, -32, 8)     # muzzle to the right: right side (bolt) toward the camera
L_SIDE = (4, 32, -4)      # muzzle to the left: left side
P_R = (-1.0, -1.2, 0.5)
P_L = (1.0, 0.5, 0.0)
a.key("gun", 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
go(a, "gun", 0.0, 0.55, rot1=R_SIDE, pos1=P_R)
a.key("gun", 1.9, rot=R_SIDE, pos=P_R)
go(a, "gun", 1.9, 2.55, rot0=R_SIDE, rot1=L_SIDE, pos0=P_R, pos1=P_L)
a.key("gun", 2.85, rot=L_SIDE, pos=P_L)
go(a, "gun", 2.85, 3.4, rot0=L_SIDE, rot1=(0, 0, 0), pos0=P_L, pos1=(0, 0, 0))
a.key("gun", 3.5, rot=(0, 0, 0), pos=(0, 0, 0))
a.key("bolt", 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
bolt_cycle(a, 0.7, 0.22, 0.22, 0.22, 0.22)
a.key("bolt", 3.5, rot=(0, 0, 0), pos=(0, 0, 0))
a.hand("right", 0.0, "grip")
a.hand("right", 0.55, "grip")
a.hand("right", 0.7, ("bone", "bolt", KNOB))
a.hand("right", 1.58, ("bone", "bolt", KNOB))
a.hand("right", 1.85, "grip")
a.key("trigger", 0.0, pos=(0, 0, 0))

# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail(cant_rot=(8.0, 0.0, -20.0), cant_pos=(-0.7, 1.4, 0.0))

m.write(item_name="ssg_69")
