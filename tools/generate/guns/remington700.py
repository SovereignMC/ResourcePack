#!/usr/bin/env python3
"""Remington 700 (.30-06 bolt-action hunting rifle with a variable scope).

Local build space: bore axis = Z axis (y = 0, x = 0), muzzle toward -Z, butt toward +Z.
Real length ~1060 mm -> 19.3 px at 1 px = 55 mm. The gun is built around the local origin
and then moved by place_gun() so the grip lands at the hip pose.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gunlib  # noqa: E402
from gunlib import GunModel  # noqa: E402

m = GunModel("remington700", "Remington 700")
box, cbox = m.box, m.cbox


def cyl(name, cx, cy, r, z0, z1, mat, group="gun"):
    m.cylinder_z(name, (cx, cy), r, z0, z1, mat, group=group)


SY = 1.35  # scope axis height above the bore

# ------------------------------------------------------------------ moving part bones
m.part("bolt", (0.0, 0.0, 3.6))
m.part("trigger", (0.0, -1.45, 2.7))
m.part("cartridges", (0.6, 0.6, 2.0), hidden=True)

# ------------------------------------------------------------------ stock (walnut)
box("forend_front", (-0.4, -0.95, -5.9), (0.4, -0.12, -3.2), "walnut")
box("forend_rear", (-0.5, -1.1, -3.2), (0.5, -0.12, -0.55), "walnut")
box("forend_tip", (-0.42, -0.97, -6.25), (0.42, -0.04, -5.9), "polymer")
box("stock_action", (-0.5, -1.4, -0.55), (0.5, -0.3, 4.25), "walnut")
box("stock_wrist", (-0.45, -1.5, 4.25), (0.45, -0.3, 5.4), "walnut")
box("grip_lower", (-0.42, -2.35, 4.45), (0.42, -1.5, 5.4), "walnut")   # modest pistol-grip swell ~0.85 below the wrist
box("grip_cap", (-0.45, -2.5, 4.4), (0.45, -2.35, 5.45), "polymer")
box("grip_spacer", (-0.4, -2.37, 4.43), (0.4, -2.34, 5.42), "birch")
box("butt_1", (-0.45, -1.75, 5.4), (0.45, -0.15, 6.1), "walnut")
box("butt_2", (-0.45, -1.85, 6.1), (0.45, 0.05, 6.7), "walnut")
box("butt_3", (-0.45, -2.0, 6.7), (0.45, 0.25, 7.3), "walnut")
box("butt_4", (-0.45, -2.15, 7.3), (0.45, 0.45, 8.15), "walnut")
box("recoil_pad", (-0.47, -2.3, 8.15), (0.47, 0.5, 8.45), "rubber")
for s in (-1, 1):
    box(f"cheek_{s}", (0.45 * s if s > 0 else -0.51, 0.02, 6.55), (0.51 if s > 0 else -0.45, 0.42, 7.7), "wood_light")
    box(f"pad_screw_{s}", (0.26 * s - 0.06, -2.1, 8.45), (0.26 * s + 0.06, -1.98, 8.49), "steel")

# sling swivel studs
box("stud_front", (-0.07, -1.2, -4.27), (0.07, -0.95, -4.13), "steel")
box("stud_front_ring", (-0.2, -1.32, -4.3), (0.2, -1.2, -4.1), "steel_dark")
box("stud_rear", (-0.07, -2.12, 6.93), (0.07, -2.0, 7.07), "steel")
box("stud_rear_ring", (-0.2, -2.24, 6.9), (0.2, -2.12, 7.1), "steel_dark")

# checkering panels: dark panel 0.02 proud of the stock side, vertical ridges 0.05 proud of the panel
# surface and horizontal ridges 0.01 further out (so the crossings do not share a plane)
def sx(s, a, b):
    """x range for side s (+1/-1) from distances a < b off the centre plane."""
    return (a, b) if s > 0 else (-b, -a)


for s in (-1, 1):
    box(f"wrist_check_{s}", (sx(s, 0.47, 0.52)[0], -1.4, 4.4), (sx(s, 0.47, 0.52)[1], -0.45, 5.3), "wood_dark")
    for i, z in enumerate((4.62, 4.88, 5.14)):
        x0, x1 = sx(s, 0.52, 0.57)
        box(f"wrist_rv_{s}_{i}", (x0, -1.35, z), (x1, -0.5, z + 0.05), "wood")
    for i, y in enumerate((-1.2, -0.95, -0.7)):
        x0, x1 = sx(s, 0.53, 0.58)
        box(f"wrist_rh_{s}_{i}", (x0, y, 4.45), (x1, y + 0.05, 5.25), "wood")
    x0, x1 = sx(s, 0.52, 0.57)
    box(f"fore_check_{s}", (x0, -0.95, -2.9), (x1, -0.3, -1.0), "wood_dark")
    for i, z in enumerate((-2.6, -2.1, -1.6, -1.2)):
        x0, x1 = sx(s, 0.57, 0.62)
        box(f"fore_rv_{s}_{i}", (x0, -0.9, z), (x1, -0.35, z + 0.05), "wood")

# ------------------------------------------------------------------ barrel and sights
cyl("barrel_muzzle", 0, 0, 0.3, -11.0, -7.5, "steel_dark")
cyl("barrel_mid", 0, 0, 0.34, -7.5, -3.5, "steel_dark")
cyl("barrel_breech", 0, 0, 0.4, -3.5, -0.5, "steel_dark")
cyl("crown", 0, 0, 0.33, -11.1, -10.9, "steel")
box("front_ramp", (-0.07, 0.3, -10.5), (0.07, 0.52, -9.8), "steel_dark")
box("front_bead", (-0.05, 0.52, -10.4), (0.05, 0.62, -10.3), "brass")
box("rear_sight_leaf", (-0.16, 0.38, -2.6), (0.16, 0.5, -2.2), "steel")

# ------------------------------------------------------------------ receiver
cyl("receiver", 0, 0, 0.5, -0.5, 4.0, "steel")
cyl("receiver_ring", 0, 0, 0.55, -0.6, 0.6, "steel_dark")
cyl("receiver_bridge", 0, 0, 0.54, 3.5, 4.0, "steel_dark")
box("ejection_port", (0.4, -0.18, 1.0), (0.49, 0.28, 2.9), "steel_dark")
box("bolt_stop", (-0.6, -0.08, 3.1), (-0.5, 0.14, 3.6), "steel_dark")

# ------------------------------------------------------------------ floorplate, guard, trigger
box("floorplate", (-0.36, -1.47, -0.1), (0.36, -1.4, 1.35), "steel")
box("floorplate_latch", (-0.1, -1.54, 1.15), (0.1, -1.47, 1.35), "steel_dark")
box("guard_front", (-0.12, -1.95, 1.45), (0.12, -1.4, 1.7), "steel")
box("guard_bar", (-0.12, -1.95, 1.45), (0.12, -1.72, 4.5), "steel")
box("guard_rear", (-0.12, -1.95, 3.85), (0.12, -1.4, 4.5), "steel")
box("trigger_plate", (-0.2, -1.47, 2.3), (0.2, -1.4, 3.3), "steel_dark")
box("trigger_blade", (-0.07, -1.7, 2.62), (0.07, -1.47, 2.76), "steel", group="trigger")
box("trigger_hook", (-0.07, -1.78, 2.45), (0.07, -1.62, 2.7), "steel", group="trigger")

# ------------------------------------------------------------------ bolt
cyl("bolt_collar", 0, 0, 0.6, 3.2, 3.85, "steel", group="bolt")
cyl("bolt_body", 0, 0, 0.4, 3.85, 4.9, "steel", group="bolt")
cyl("bolt_shroud", 0, 0, 0.3, 4.9, 5.45, "steel_dark", group="bolt")
box("cocking_piece", (-0.06, 0.1, 5.45), (0.06, 0.3, 5.75), "steel", group="bolt")
box("safety", (0.1, 0.2, 4.95), (0.45, 0.3, 5.3), "steel", group="bolt")
box("handle_root", (0.45, -0.12, 3.4), (1.15, 0.12, 3.7), "steel", group="bolt")
cbox("handle_stem", (1.5, 0.0, 3.95), (1.15, 0.24, 0.24), "steel", group="bolt", rotation=(0, -45, 0))
cbox("handle_knob", (2.0, -0.15, 4.45), (0.5, 0.5, 0.5), "steel_dark", group="bolt")
cbox("handle_knob_r", (2.0, -0.15, 4.45), (0.44, 0.44, 0.44), "steel_dark", group="bolt", rotation=(0, 45, 0))

# ------------------------------------------------------------------ scope
cyl("scope_tube", 0, SY, 0.4, -1.4, 2.95, "steel_dark")
cyl("scope_shoulder", 0, SY, 0.52, -2.0, -1.4, "steel_dark")
cyl("scope_objective", 0, SY, 0.64, -3.3, -2.0, "steel_dark")
box("objective_glass", (-0.5, SY - 0.5, -3.34), (0.5, SY + 0.5, -3.3), "glass")
cyl("scope_power_ring", 0, SY, 0.5, 2.95, 3.3, "steel")
cyl("scope_eyepiece", 0, SY, 0.44, 3.3, 3.55, "steel_dark")
box("eyepiece_glass", (-0.3, SY - 0.3, 3.55), (0.3, SY + 0.3, 3.58), "glass")
box("turret_body", (-0.3, SY + 0.3, 0.05), (0.3, SY + 0.5, 0.75), "steel_dark")
cbox("elev_turret", (0.0, SY + 0.62, 0.4), (0.4, 0.26, 0.4), "steel", item_model=True)
cbox("elev_turret_cap", (0.0, SY + 0.82, 0.4), (0.3, 0.14, 0.3), "steel_dark")
cbox("wind_turret", (0.55, SY, 0.4), (0.26, 0.4, 0.4), "steel")
cbox("wind_turret_cap", (0.72, SY, 0.4), (0.12, 0.3, 0.3), "steel_dark")
for name, z0 in (("front", 0.2), ("rear", 2.4)):
    box(f"ring_base_{name}", (-0.28, 0.4, z0), (0.28, 1.0, z0 + 0.4), "steel")
    box(f"ring_band_{name}", (-0.5, 0.95, z0 - 0.02), (0.5, 1.78, z0 + 0.42), "gunmetal")
    for s in (-1, 1):
        cbox(f"ring_screw_{name}_{s}", (0.53 * s, 1.55, z0 + 0.2), (0.08, 0.16, 0.16), "steel_dark")

# ------------------------------------------------------------------ cartridges (reload prop)
for i, (cx, cy) in enumerate(((0.45, 0.5), (0.78, 0.5), (0.61, 0.8))):
    box(f"round_case_{i}", (cx - 0.12, cy - 0.12, 1.5), (cx + 0.12, cy + 0.12, 2.55), "brass",
        group="cartridges", item_model=False)
    box(f"round_bullet_{i}", (cx - 0.09, cy - 0.09, 1.15), (cx + 0.09, cy + 0.09, 1.5), "copper",
        group="cartridges", item_model=False)

# ------------------------------------------------------------------ points
m.point("grip", (0.05, -0.95, 4.8))
m.point("support", (0.0, -1.2, -1.2))
m.point("sight_rear", (0.0, SY, 3.57))
m.point("sight_front", (0.0, SY, -3.0))
m.point("muzzle", (0.0, 0.0, -11.15))
m.point("knob", (2.0, -0.15, 4.45))
m.point("cart_center", (0.6, 0.6, 2.0))

OFFSET = m.place_gun_at_hip()
m.muzzle_flash()
m.build_arms()

EYE_RELIEF = 3.0
m.standard_animations(fire_interval=1.0, kick=0.7, climb=4.0, bolt=None, eye_relief=EYE_RELIEF)

# trigger squeeze in both shoot animations
for nm in ("shoot", "aiming_shoot"):
    a = m.anims[nm]
    a.key("trigger", 0.0, rot=(-20, 0, 0))
    a.key("trigger", 0.12, rot=(-20, 0, 0))
    a.ease("trigger", 0.12, 0.3, rot0=(-20, 0, 0), rot1=(0, 0, 0))
    a.key("trigger", a.length, rot=(0, 0, 0))

KNOB = m.points["knob"]
CART = m.points["cart_center"]
LIFT = 70.0
PULL = 1.5


def zero(a, *bones):
    for b in bones:
        a.key(b, 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
        a.key(b, a.length, rot=(0, 0, 0), pos=(0, 0, 0))


def cycle(a, t_open, t_close):
    """Bolt cycle: lift+pull from t_open (0.28 s), hold, push+turn down from t_close (0.27 s)."""
    a.key("bolt", t_open, rot=(0, 0, 0), pos=(0, 0, 0))
    a.ease("bolt", t_open, t_open + 0.15, rot0=(0, 0, 0), rot1=(0, 0, LIFT))
    a.ease("bolt", t_open + 0.15, t_open + 0.28, pos0=(0, 0, 0), pos1=(0, 0, PULL))
    a.key("bolt", t_open + 0.28, rot=(0, 0, LIFT), pos=(0, 0, PULL))
    a.key("bolt", t_close, rot=(0, 0, LIFT), pos=(0, 0, PULL))
    a.ease("bolt", t_close, t_close + 0.12, pos0=(0, 0, PULL), pos1=(0, 0, 0), curve="in")
    a.ease("bolt", t_close + 0.12, t_close + 0.27, rot0=(0, 0, LIFT), rot1=(0, 0, 0))


# ------------------------------------------------------------------ firearm (bolt cycle, 0.75 s)
a = m.anim("firearm", 0.75, "once")
zero(a, "bolt")
a.hand("right", 0.0, "grip")
a.hand("right", 0.12, ("bone", "bolt", KNOB))
a.hand("right", 0.62, ("bone", "bolt", KNOB))
a.hand("right", 0.75, "grip")
cycle(a, 0.12, 0.40)  # lift 0.12-0.27, pull -0.40, push 0.40-0.52, down -0.67

# ------------------------------------------------------------------ reload (2.0 s)
a = m.anim("reload", 2.0, "once")
zero(a, "bolt", "gun", "cartridges")
# gun roll to show the ejection port
ROLL = (5.0, -6.0, 22.0)
ROLL_P = (-0.5, -0.2, 1.0)   # drawn slightly in toward the shoulders so the left hand reaches the port
a.ease("gun", 0.0, 0.3, rot0=(0, 0, 0), rot1=ROLL, pos0=(0, 0, 0), pos1=ROLL_P)
a.key("gun", 1.6, rot=ROLL, pos=ROLL_P)
a.ease("gun", 1.6, 2.0, rot0=ROLL, rot1=(0, 0, 0), pos0=ROLL_P, pos1=(0, 0, 0))
# right hand to the bolt
a.hand("right", 0.0, "grip")
a.hand("right", 0.18, "grip")
a.hand("right", 0.4, ("bone", "bolt", KNOB))
a.hand("right", 1.65, ("bone", "bolt", KNOB))
a.hand("right", 1.92, "grip")
cycle(a, 0.3, 1.4)
# left hand fetches cartridges
LOW = (1.0, -4.5, 3.5)
HOVER = (1.1, 1.0, 0.0)
INS = (0.0, 0.0, 0.0)
a.hand("left", 0.0, "support")
a.hand("left", 0.45, "support")
a.hand("left", 0.82, ("bone", "cartridges", CART))
a.hand("left", 1.4, ("bone", "cartridges", CART))
a.hand("left", 1.68, "support")
a.key("cartridges", 0.0, scale=0.0, pos=LOW)
a.key("cartridges", 0.77, scale=0.0, pos=LOW)
a.key("cartridges", 0.8, scale=1.0, pos=LOW)
a.ease("cartridges", 0.8, 0.95, pos0=LOW, pos1=HOVER)
a.ease("cartridges", 0.95, 1.08, pos0=HOVER, pos1=INS)
a.key("cartridges", 1.08, scale=1.0)
a.key("cartridges", 1.1, scale=0.0)
a.ease("cartridges", 1.1, 1.22, pos0=INS, pos1=HOVER)
a.key("cartridges", 1.21, scale=0.0)
a.key("cartridges", 1.23, scale=1.0)
a.ease("cartridges", 1.23, 1.36, pos0=HOVER, pos1=INS)
a.key("cartridges", 1.37, scale=1.0)
a.key("cartridges", 1.39, scale=0.0)
a.key("cartridges", 2.0, scale=0.0, pos=INS)

# ------------------------------------------------------------------ inspect (3.0 s)
a = m.anim("inspect", 3.0, "once")
zero(a, "bolt", "gun")
POSE_R = ((-4.0, -35.0, 8.0), (-0.6, 0.6, 2.2))
POSE_L = ((-4.0, 25.0, -8.0), (0.5, 0.8, 0.5))
a.ease("gun", 0.0, 0.5, rot0=(0, 0, 0), rot1=POSE_R[0], pos0=(0, 0, 0), pos1=POSE_R[1])
a.key("gun", 1.7, rot=POSE_R[0], pos=POSE_R[1])
a.ease("gun", 1.7, 2.3, rot0=POSE_R[0], rot1=POSE_L[0], pos0=POSE_R[1], pos1=POSE_L[1])
a.key("gun", 2.55, rot=POSE_L[0], pos=POSE_L[1])
a.ease("gun", 2.55, 3.0, rot0=POSE_L[0], rot1=(0, 0, 0), pos0=POSE_L[1], pos1=(0, 0, 0))
a.hand("right", 0.0, "grip")
a.hand("right", 0.5, "grip")
a.hand("right", 0.68, ("bone", "bolt", KNOB))
a.hand("right", 1.55, ("bone", "bolt", KNOB))
a.hand("right", 1.8, "grip")
cycle(a, 0.7, 1.1)

m.repivot_gun_keys()   # gun keys were tuned about the old pivot (local origin)
m.write(item_name="remington")
