"""Dragunov SVD designated marksman rifle (PSO-1 scope on the left rail).

Scale 1 px = 55 mm (real length 1225 mm -> 22.3 px). Built around a local origin at the
receiver top-rear, then placed into the hip pose with m.place_gun().
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gunlib  # noqa: E402
from gunlib import GunModel, v_add  # noqa: E402

gunlib.MATERIALS["wood_ply"] = gunlib.Material("#8a5331", "wood", 0.04, -0.2, 0.0)

m = GunModel("dragunov", "Dragunov SVD")

# ------------------------------------------------------------------------------------
# Moving part bones (local coordinates, shifted by place_gun later)
# ------------------------------------------------------------------------------------
m.part("magazine", (0, -1.85, -2.65))
m.part("bolt", (0.5, -0.55, -2.5))
m.part("trigger", (0, -1.9, -0.9))

B = m.box
C = m.cbox

# ------------------------------------------------------------------------------------
# Receiver (z = 0 at the rear, muzzle toward -z)
# ------------------------------------------------------------------------------------
B("receiver", (-0.55, -1.7, -4.6), (0.55, -0.1, 0.0), "steel")
B("dust_cover", (-0.5, -0.1, -4.5), (0.5, 0.2, -0.15), "steel_dark")
for i, z in enumerate((-1.2, -2.2, -3.2)):
    B(f"dust_rib{i}", (-0.35, 0.2, z - 0.07), (0.35, 0.27, z + 0.07), "steel")
B("spring_cap", (-0.3, -0.3, -0.12), (0.3, 0.3, 0.3), "steel_dark")
B("ejection_port", (0.5, -0.9, -3.4), (0.58, -0.2, -1.5), "steel_dark")
B("rail_left", (-0.9, -1.3, -4.2), (-0.5, -0.25, -0.5), "steel_dark")
B("rail_rib", (-1.0, -0.95, -3.9), (-0.85, -0.55, -0.8), "steel")
B("magwell", (-0.6, -2.05, -3.55), (0.6, -1.65, -1.75), "steel")
B("selector", (0.52, -1.4, -3.5), (0.68, -1.25, -1.8), "gunmetal")
B("selector_head", (0.6, -1.5, -3.55), (0.75, -1.15, -3.3), "gunmetal")
for i, (x, y, z) in enumerate([(0.55, -1.5, -0.4), (0.55, -0.4, -0.4), (0.55, -1.5, -4.3), (0.55, -0.4, -4.3)]):
    B(f"rivet_r{i}", (x - 0.02, y - 0.06, z - 0.06), (x + 0.07, y + 0.06, z + 0.06), "gunmetal")
for i, (y, z) in enumerate([(-1.5, -0.4), (-1.5, -4.3)]):
    B(f"rivet_l{i}", (-0.62, y - 0.06, z - 0.06), (-0.53, y + 0.06, z + 0.06), "gunmetal")

# bolt carrier + charging handle (right side)
B("bolt_carrier", (0.4, -0.8, -3.2), (0.66, -0.3, -1.7), "gunmetal", group="bolt")
B("bolt_lug", (0.62, -0.8, -3.2), (0.7, -0.62, -2.7), "steel", group="bolt")
B("handle_stalk", (0.6, -0.65, -2.5), (0.85, -0.45, -2.25), "steel_dark", group="bolt")
B("handle_knob", (0.85, -0.75, -2.65), (1.15, -0.35, -2.1), "steel_dark", group="bolt")

# trigger group
B("trigger_guard_front", (-0.2, -2.75, -1.7), (0.2, -1.7, -1.5), "steel")
B("trigger_guard_bar", (-0.2, -2.8, -1.7), (0.2, -2.6, -0.2), "steel_dark")
B("trigger_blade", (-0.12, -2.55, -1.0), (0.12, -1.8, -0.8), "gunmetal", group="trigger")

# ------------------------------------------------------------------------------------
# Magazine (curved 10 round, stepped forward), pivot at the well
# ------------------------------------------------------------------------------------
G = "magazine"
B("mag_s1", (-0.45, -3.0, -3.35), (0.45, -1.85, -1.9), "parkerized", group=G)
B("mag_s2", (-0.45, -4.0, -3.65), (0.45, -3.0, -2.2), "parkerized", group=G)
B("mag_s3", (-0.45, -4.9, -3.95), (0.45, -4.0, -2.5), "parkerized", group=G)
B("mag_plate", (-0.5, -5.1, -4.05), (0.5, -4.85, -2.4), "steel_dark", group=G)
for i, (y0, y1, zc) in enumerate([(-3.5, -3.2, -2.9), (-4.4, -4.1, -3.2)]):
    for side, x0, x1 in (("r", 0.43, 0.5), ("l", -0.5, -0.43)):
        B(f"mag_rib_{side}{i}", (x0, y0, zc - 0.55), (x1, y1, zc + 0.55), "steel", group=G)
B("mag_lip", (-0.35, -1.95, -1.93), (0.35, -1.75, -1.85), "steel_dark", group=G)

# ------------------------------------------------------------------------------------
# Thumbhole stock: grip, top bar + cheek rest, lower bar, rear upright, butt plate
# ------------------------------------------------------------------------------------
B("grip_1", (-0.6, -2.8, -0.25), (0.6, -1.7, 1.25), "wood")
B("grip_2", (-0.6, -3.9, 0.0), (0.6, -2.8, 1.55), "wood")
B("grip_3", (-0.6, -4.9, 0.3), (0.6, -3.9, 1.85), "wood")
B("grip_cap", (-0.64, -5.05, 0.25), (0.64, -4.88, 1.9), "steel_dark")
B("grip_screw_r", (0.58, -3.4, 0.6), (0.66, -3.25, 0.75), "gunmetal")
B("grip_screw_l", (-0.66, -3.4, 0.6), (-0.58, -3.25, 0.75), "gunmetal")

B("stock_top", (-0.5, -1.0, -0.05), (0.5, -0.45, 5.4), "wood_ply")
B("cheek_1", (-0.55, -0.45, 1.0), (0.55, -0.15, 2.2), "wood")
B("cheek_2", (-0.55, -0.45, 2.2), (0.55, 0.1, 4.8), "wood")
B("cheek_3", (-0.55, -0.45, 4.8), (0.55, -0.15, 5.6), "wood")
B("stock_upright", (-0.52, -3.1, 5.2), (0.52, -0.3, 6.6), "wood_ply")
# lower bar steps up from the grip to the butt (skeleton / thumbhole stock)
B("stock_lower", (-0.5, -4.9, 1.7), (0.5, -4.35, 3.4), "wood")
B("stock_lower_b", (-0.5, -4.5, 3.3), (0.5, -3.95, 4.6), "wood")
B("stock_lower_c", (-0.5, -4.05, 4.5), (0.5, -3.5, 5.5), "wood")
B("stock_lower_d", (-0.5, -3.6, 5.0), (0.5, -3.05, 5.6), "wood")
B("butt_plate", (-0.6, -3.15, 6.55), (0.6, -0.4, 6.85), "rubber")
for i, (x, y) in enumerate([(0.52, -0.9), (0.52, -2.6), (-0.6, -0.9), (-0.6, -2.6)]):
    B(f"butt_screw{i}", (x, y - 0.08, 6.0), (x + 0.08, y + 0.08, 6.16), "gunmetal")
B("swivel_base", (-0.15, -3.4, 5.9), (0.15, -3.05, 6.25), "steel")
B("swivel_ring", (-0.12, -3.8, 5.85), (0.12, -3.4, 6.3), "steel_dark")

# ------------------------------------------------------------------------------------
# Ventilated wooden handguard
# ------------------------------------------------------------------------------------
B("hg_rear_cap", (-0.55, -1.5, -5.05), (0.55, 0.05, -4.5), "wood_light")
B("hg_bottom", (-0.5, -1.5, -9.5), (0.5, -1.1, -4.6), "wood_light")
B("hg_top", (-0.46, -0.4, -9.5), (0.46, 0.05, -4.6), "wood")
for i in range(5):
    zh = -5.0 - 0.8 * i
    B(f"hg_post{i}", (-0.44, -1.1, zh - 0.45), (0.44, -0.4, zh), "wood_light")
B("hg_front_ring", (-0.52, -1.45, -9.5), (0.52, 0.0, -9.05), "wood_dark")
for i in range(4):
    zs = -5.5 - 0.9 * i
    B(f"hg_vent{i}", (-0.18, 0.05, zs - 0.3), (0.18, 0.09, zs), "steel_dark")

# rear sight (tangent) on the handguard top
B("rear_sight_base", (-0.3, 0.05, -5.5), (0.3, 0.4, -4.8), "steel")
B("rear_sight_leaf", (-0.25, 0.4, -5.2), (0.25, 0.75, -5.05), "steel_dark")
B("rear_sight_notch", (-0.04, 0.55, -5.21), (0.04, 0.75, -5.04), "steel")

# ------------------------------------------------------------------------------------
# Barrel, gas block, front sight, slotted flash hider
# ------------------------------------------------------------------------------------
BY = -0.75
m.cylinder_z("barrel", (0, BY), 0.3, -13.5, -4.5, "steel_dark")
B("gas_block", (-0.36, -1.15, -10.3), (0.36, -0.1, -9.5), "steel")
B("gas_screw", (0.34, -0.7, -9.95), (0.42, -0.55, -9.8), "gunmetal")
B("sight_base", (-0.3, -1.1, -12.9), (0.3, 0.05, -12.1), "steel")
B("sight_post", (-0.07, 0.05, -12.65), (0.07, 0.75, -12.5), "steel_dark")
B("sight_ear_l", (-0.31, 0.05, -12.9), (-0.2, 0.8, -12.3), "steel")
B("sight_ear_r", (0.2, 0.05, -12.9), (0.31, 0.8, -12.3), "steel")
B("front_swivel", (-0.1, -1.5, -12.7), (0.1, -1.1, -12.5), "steel_dark")
m.cylinder_z("hider_base", (0, BY), 0.42, -13.8, -13.3, "steel_dark")
B("hider_top", (-0.12, BY + 0.18, -15.1), (0.12, BY + 0.4, -13.75), "steel_dark")
B("hider_bottom", (-0.12, BY - 0.4, -15.1), (0.12, BY - 0.18, -13.75), "steel_dark")
B("hider_left", (-0.4, BY - 0.12, -15.1), (-0.18, BY + 0.12, -13.75), "steel_dark")
B("hider_right", (0.18, BY - 0.12, -15.1), (0.4, BY + 0.12, -13.75), "steel_dark")
m.cylinder_z("hider_end", (0, BY), 0.42, -15.3, -15.05, "steel_dark")

# ------------------------------------------------------------------------------------
# PSO-1 scope on the left rail
# ------------------------------------------------------------------------------------
SX, SY = -1.55, 1.1
for i, (z0, z1) in enumerate(((-1.75, -0.95), (-3.55, -2.75))):
    B(f"scope_bracket{i}", (-1.3, -0.3, z0), (-0.45, 0.55, z1), "steel_dark")
    B(f"scope_saddle{i}", (-1.95, 0.4, z0), (-1.15, 0.75, z1), "steel")
    m.cylinder_z(f"scope_ring{i}", (SX, SY), 0.56, z0 + 0.05, z1 - 0.05, "steel")
m.cylinder_z("scope_tube", (SX, SY), 0.45, -4.3, -0.3, "steel_dark")
m.cylinder_z("scope_eyepiece", (SX, SY), 0.52, -0.3, 0.9, "steel_dark")
m.cylinder_z("scope_eyecup", (SX, SY), 0.62, 0.9, 1.4, "rubber")
C("scope_eye_glass", (SX, SY, 1.43), (0.6, 0.6, 0.06), "glass")
m.cylinder_z("scope_turret_body", (SX, SY), 0.56, -2.65, -2.0, "steel_dark")
C("elev_turret", (SX, SY + 0.7, -2.32), (0.55, 0.4, 0.55), "steel")
C("elev_cap", (SX, SY + 0.98, -2.32), (0.4, 0.16, 0.4), "gunmetal")
C("wind_turret", (SX + 0.7, SY, -2.32), (0.4, 0.5, 0.5), "steel")
C("wind_cap", (SX + 0.95, SY, -2.32), (0.16, 0.38, 0.38), "gunmetal")
C("lamp_cap", (SX - 0.72, SY, -2.32), (0.34, 0.42, 0.42), "gunmetal")
m.cylinder_z("scope_objective", (SX, SY), 0.65, -5.2, -4.0, "steel_dark")
m.cylinder_z("scope_shade", (SX, SY), 0.6, -5.6, -5.2, "steel")
C("scope_obj_glass", (SX, SY, -5.62), (0.7, 0.7, 0.04), "glass")
B("scope_clamp_screw", (-1.95, 0.45, -1.45), (-1.87, 0.65, -1.25), "gunmetal")

# ------------------------------------------------------------------------------------
# Points (local), place, then everything else
# ------------------------------------------------------------------------------------
m.point("grip", (0.0, -3.4, 0.8))
m.point("support", (0.0, -1.6, -6.3))
m.point("sight_rear", (SX, SY, 1.46))
m.point("sight_front", (SX, SY, -5.64))
m.point("muzzle", (0.0, BY, -15.3))

OFFSET = m.place_gun_at_hip()
m.muzzle_flash(size=2.4)
m.build_arms()

m.standard_animations(fire_interval=1.1, kick=0.7, climb=4.0, bolt="bolt", bolt_travel=1.3, eye_relief=3.0)

# trigger pull on shots
for nm in ("shoot", "aiming_shoot"):
    a = m.anims[nm]
    a.key("trigger", 0.0, rot=(0, 0, 0))
    a.key("trigger", 0.03, rot=(-18, 0, 0))
    a.ease("trigger", 0.03, 0.25, rot0=(-18, 0, 0), rot1=(0, 0, 0), curve="out")

MAG_PT = v_add((0.0, -3.3, -2.9), OFFSET)
HANDLE_PT = v_add((1.0, -0.55, -2.4), OFFSET)
ZERO = (0, 0, 0)


def path(a, bone, pts, curve="smooth"):
    """pts = [(t, rot, pos), ...] eased between consecutive waypoints."""
    for (t0, r0, p0), (t1, r1, p1) in zip(pts, pts[1:]):
        a.ease(bone, t0, t1, rot0=r0, rot1=r1, pos0=p0, pos1=p1, curve=curve)


def reload_seq(a, charge):
    T = a.length
    tc = 3.0  # time the new magazine is seated
    tilt = (-3, 0, 10)
    tpos = (-0.3, 1.3, -1.5)
    gun = [(0.0, ZERO, ZERO), (0.45, tilt, tpos), (tc + 0.2, tilt, tpos)]
    if charge:
        gun += [(T - 0.5, tilt, tpos), (T, ZERO, ZERO)]
    else:
        gun += [(T, ZERO, ZERO)]
    path(a, "gun", gun)
    # left hand: support -> magazine -> carry off-screen -> fresh magazine -> seat
    a.hand("left", 0.0, "support")
    a.hand("left", 0.5, ("bone", "magazine", MAG_PT))
    # magazine out
    path(a, "magazine", [
        (0.0, ZERO, ZERO), (0.5, ZERO, ZERO),
        (0.8, (22, 0, 0), (0, -0.8, 0.2)),
        (1.1, (22, 0, -6), (-0.8, -2.2, 0.6)),
        (1.55, (30, 0, -20), (-5.0, -8.0, 2.0)),
    ])
    a.key("magazine", 0.0, scale=1.0)
    a.key("magazine", 1.55, scale=1.0)
    a.key("magazine", 1.56, scale=0.0)
    a.key("magazine", 1.85, scale=0.0)
    a.key("magazine", 1.86, scale=1.0)
    path(a, "magazine", [
        (1.55, (30, 0, -20), (-5.0, -8.0, 2.0)),
        (1.86, (30, 0, -20), (-5.0, -8.0, 2.0)),
        (2.5, (22, 0, -6), (-0.6, -3.2, 0.6)),
        (2.8, (6, 0, 0), (0, -1.0, 0.1)),
        (tc, ZERO, (0, 0.12, 0)),
        (tc + 0.2, ZERO, ZERO),
        (T, ZERO, ZERO),
    ], curve="out")
    a.hand("left", tc + 0.05, ("bone", "magazine", MAG_PT))
    if not charge:
        a.hand("left", T, "support")
    else:
        a.hand("left", tc + 0.35, ("bone", "bolt", HANDLE_PT))
        a.hand("left", tc + 0.55, ("bone", "bolt", HANDLE_PT))
        path(a, "bolt", [(tc + 0.55, ZERO, ZERO), (tc + 0.85, ZERO, (0, 0, 1.6))])
        path(a, "bolt", [(tc + 0.85, ZERO, (0, 0, 1.6)), (tc + 1.05, ZERO, ZERO)], curve="in")
        a.hand("left", tc + 1.05, ("bone", "bolt", HANDLE_PT))
        a.hand("left", T, "support")
    a.key("magazine", T, rot=ZERO, pos=ZERO, scale=1.0)
    a.key("gun", T, rot=ZERO, pos=ZERO)


reload_a = m.anim("reload", 3.5, "once")
reload_seq(reload_a, False)
reload_e = m.anim("reload_empty", 4.5, "once")
reload_seq(reload_e, True)

# inspect: show the right side, then the scope side/top, then back
a = m.anim("inspect", 3.2, "once")
path(a, "gun", [
    (0.0, ZERO, ZERO),
    (0.7, (-4, -45, 6), (-4.5, 1.2, 1.0)),
    (1.4, (-4, -45, 6), (-4.5, 1.2, 1.0)),
    (2.2, (8, 40, -12), (-1.5, 1.8, 1.2)),
    (2.6, (8, 40, -12), (-1.5, 1.8, 1.2)),
    (3.2, ZERO, ZERO),
])
a.hand("left", 0.0, "support")
a.hand("left", 3.2, "support")
path(a, "magazine", [(0.0, ZERO, ZERO), (3.2, ZERO, ZERO)])
# small bolt pull to show the action while the gun faces the camera
path(a, "bolt", [(1.0, ZERO, ZERO), (1.2, ZERO, (0, 0, 1.4)), (1.5, ZERO, ZERO)])
a.key("bolt", 0.0, pos=ZERO, rot=ZERO)
a.key("bolt", 3.2, pos=ZERO, rot=ZERO)

# firearm (charging handle) 10 + 8 ticks = 0.9 s
a = m.anim("firearm", 0.9, "once")
a.key("bolt", 0.0, pos=ZERO)
path(a, "bolt", [(0.1, ZERO, ZERO), (0.5, ZERO, (0, 0, 1.6))])
path(a, "bolt", [(0.5, ZERO, (0, 0, 1.6)), (0.85, ZERO, ZERO)], curve="in")
a.key("bolt", 0.9, pos=ZERO)
a.hand("left", 0.0, "support")
a.hand("left", 0.15, ("bone", "bolt", HANDLE_PT))
a.hand("left", 0.7, ("bone", "bolt", HANDLE_PT))
a.hand("left", 0.9, "support")
path(a, "gun", [(0.0, ZERO, ZERO), (0.3, (-2, 0, 5), (0.1, 0.1, 0.2)), (0.6, (-2, 0, 5), (0.1, 0.1, 0.2)), (0.9, ZERO, ZERO)])

m.repivot_gun_keys()   # gun keys were tuned about the old pivot (local origin)
# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail()

m.write(item_name="dragunov")
