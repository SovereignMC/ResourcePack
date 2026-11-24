#!/usr/bin/env python3
"""M14 battle rifle (1118 mm -> 20.3 px at 55 mm/px).

Local build space: z = -d where d is the distance from the butt plate (muzzle at d = 20.3),
bore axis at y = 0.05, receiver top at y = 0.55.  place_gun() then moves it to the hip pose.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gunlib import GunModel, MATERIALS  # noqa: E402

m = GunModel("m14", "M14")
BY = 0.05  # bore height


def B(name, d0, d1, x0, x1, y0, y1, mat, g="gun", **kw):
    """Box by distance-from-butt d0<d1, x range, y range."""
    return m.box(name, (x0, y0, -d1), (x1, y1, -d0), mat, group=g, **kw)


def CY(name, y_x, d0, d1, r, mat, g="gun"):
    return m.cylinder_z(name, y_x, r, -d1, -d0, mat, group=g)


# moving parts
m.part("magazine", (0, -1.8, -10.4))
m.part("bolt", (0, 0.1, -9.1))
m.part("trigger", (0, -1.6, -6.95))

# ---------------------------------------------------------------- stock (walnut)
# profile (side view): comb line straight at y = 0.15; wrist 1.25 tall behind the receiver, pistol-grip
# dip under it, stepped drop down to the 2.7 tall butt
B("butt_plate", 0.0, 0.35, -0.75, 0.75, -2.62, 0.2, "steel_dark")
B("butt_trapdoor", -0.05, 0.1, -0.3, 0.3, -1.8, -0.4, "steel")
B("butt_screw_t", -0.07, 0.1, -0.1, 0.1, -0.1, 0.08, "brass")
B("butt_screw_b", -0.07, 0.1, -0.1, 0.1, -2.3, -2.15, "brass")
B("stock_butt", 0.35, 2.2, -0.72, 0.72, -2.55, 0.15, "walnut")
B("drop_a", 2.2, 3.0, -0.72, 0.72, -2.05, 0.15, "walnut")
B("drop_b", 3.0, 3.8, -0.72, 0.72, -1.6, 0.15, "walnut")
B("stock_wrist", 3.8, 6.2, -0.72, 0.72, -1.1, 0.15, "walnut")
B("comb_ridge", 0.5, 3.4, -0.5, 0.5, 0.14, 0.2, "wood_light")
B("grip_back", 4.5, 5.2, -0.76, 0.76, -3.05, -1.05, "wood_dark")   # pistol-grip dip ~1.95 below the wrist line
B("grip_front", 5.2, 5.9, -0.76, 0.76, -2.8, -1.05, "wood_dark")
B("stock_mid", 6.2, 11.2, -0.8, 0.8, -1.8, -0.1, "walnut")
B("stock_mid_edge_l", 6.2, 11.2, -0.83, -0.78, -1.75, -1.45, "wood_dark")
B("stock_mid_edge_r", 6.2, 11.2, 0.78, 0.83, -1.75, -1.45, "wood_dark")
B("forend", 11.2, 16.85, -0.78, 0.78, -1.55, -0.1, "walnut")
B("forend_tip", 16.4, 17.15, -0.5, 0.5, -1.35, -0.3, "wood_dark")
B("handguard", 11.0, 16.0, -0.66, 0.66, -0.15, 0.5, "wood_light")
B("handguard_cap", 15.85, 16.3, -0.7, 0.7, -0.1, 0.56, "steel")
B("handguard_ret", 10.8, 11.1, -0.72, 0.72, -0.1, 0.5, "steel")
for i, d in enumerate((11.9, 12.8, 13.7, 14.6)):
    B(f"hg_vent_l{i}", d, d + 0.5, -0.4, -0.12, 0.49, 0.53, "steel_dark")
    B(f"hg_vent_r{i}", d, d + 0.5, 0.12, 0.4, 0.49, 0.53, "steel_dark")
B("front_band", 16.4, 16.9, -0.88, 0.88, -1.62, 0.62, "steel")
B("band_screw", 16.5, 16.8, 0.86, 0.93, -0.5, -0.2, "steel_dark")
# sling swivels
B("swivel_front", 16.5, 16.8, -0.2, 0.2, -2.0, -1.55, "steel")
B("swivel_f_ring_a", 16.4, 16.9, -0.04, 0.04, -2.35, -2.0, "steel")
B("swivel_f_ring_b", 16.4, 16.9, -0.04, 0.04, -2.4, -2.33, "steel")
B("swivel_rear", 1.1, 1.6, -0.18, 0.18, -2.8, -2.5, "steel")
B("swivel_r_ring", 1.2, 1.5, -0.04, 0.04, -3.1, -2.78, "steel")
B("buttstock_swivel_b", 1.1, 1.6, -0.18, 0.18, -3.15, -3.07, "steel")

# ---------------------------------------------------------------- receiver (parkerized steel)
B("receiver", 6.2, 11.0, -0.7, 0.7, -0.9, 0.68, "parkerized")
B("recv_top_rib", 7.7, 10.5, -0.35, 0.35, 0.68, 0.75, "gunmetal")
B("recv_rear_ring", 6.2, 6.55, -0.74, 0.74, -0.2, 0.6, "gunmetal")
B("port_recess", 7.0, 8.8, 0.7, 0.73, 0.05, 0.5, "steel_dark")
B("oprod_slot", 7.2, 11.0, 0.7, 0.73, -0.5, -0.1, "steel_dark")
B("serial_plate", 8.2, 10.0, -0.74, -0.7, -0.3, 0.2, "steel")
B("clip_guide", 8.9, 10.3, -0.55, -0.3, 0.68, 0.85, "gunmetal")
# (the lower rivets would sit inside the stock_mid sides, so only the upper ones are modelled)
for i, d in enumerate((6.7, 10.5)):
    B(f"rivet_r{i}", d, d + 0.2, 0.7, 0.77, 0.2, 0.4, "steel")
    B(f"rivet_l{i}", d, d + 0.2, -0.77, -0.7, 0.2, 0.4, "steel")
# rear aperture sight
B("rsight_base", 5.7, 6.6, -0.42, 0.42, 0.12, 0.9, "steel")
B("rsight_ear_l", 5.8, 6.3, -0.56, -0.4, 0.88, 1.9, "steel_dark")
B("rsight_ear_r", 5.8, 6.3, 0.4, 0.56, 0.88, 1.9, "steel_dark")
B("rsight_ap_bot", 5.92, 6.12, -0.3, 0.3, 0.88, 1.28, "steel")
B("rsight_ap_top", 5.92, 6.12, -0.3, 0.3, 1.62, 1.78, "steel")
B("rsight_ap_l", 5.92, 6.12, -0.3, -0.12, 1.26, 1.64, "steel")
B("rsight_ap_r", 5.92, 6.12, 0.12, 0.3, 1.26, 1.64, "steel")
B("windage_knob", 5.85, 6.2, 0.54, 0.9, 0.95, 1.3, "steel_dark")
B("windage_ring", 5.8, 6.25, 0.88, 0.95, 0.92, 1.33, "steel")
B("elev_knob", 5.85, 6.2, -0.9, -0.54, 0.45, 0.8, "steel_dark")
B("elev_ring", 5.8, 6.25, -0.95, -0.88, 0.42, 0.83, "steel")
# trigger guard + safety
B("tg_bottom", 5.9, 8.2, -0.2, 0.2, -2.45, -2.27, "steel")
B("tg_rear", 5.9, 6.1, -0.2, 0.2, -2.45, -1.7, "steel")
B("tg_front", 8.0, 8.2, -0.2, 0.2, -2.45, -1.7, "steel")
B("safety", 7.75, 8.0, -0.12, 0.12, -2.25, -1.8, "steel_dark")
B("tg_plate", 6.0, 8.3, -0.55, 0.55, -1.9, -1.75, "steel")
B("mag_catch", 8.2, 8.55, -0.1, 0.1, -1.9, -1.5, "steel")

# ---------------------------------------------------------------- barrel, gas system, muzzle
CY("barrel", (0, BY), 11.0, 19.1, 0.38, "steel")
CY("gas_cyl", (0, -0.62), 16.9, 18.4, 0.3, "steel_dark")
CY("gas_plug", (0, -0.62), 18.4, 18.75, 0.36, "steel")
B("gas_lock", 16.9, 17.3, -0.2, 0.2, -0.92, -0.5, "steel")
CY("fs_ring", (0, BY), 19.0, 19.4, 0.46, "steel_dark")
CY("fs_body", (0, BY), 19.4, 20.05, 0.4, "steel")
for nm, (cx, cy, sx, sy) in {"t": (0, 0.37, 0.1, 0.12), "b": (0, -0.27, 0.1, 0.12),
                              "l": (-0.32, BY, 0.12, 0.1), "r": (0.32, BY, 0.12, 0.1)}.items():
    B(f"fs_prong_{nm}", 20.0, 20.3, cx - sx, cx + sx, cy - sy, cy + sy, "steel_dark")
B("fs_slot_t", 19.55, 19.95, -0.1, 0.1, 0.44, 0.5, "steel_dark")
B("fs_slot_b", 19.55, 19.95, -0.1, 0.1, -0.39, -0.33, "steel_dark")
# front sight with ears
B("fsight_base", 18.75, 19.3, -0.3, 0.3, 0.3, 0.8, "steel")
B("fsight_post", 18.93, 19.07, -0.06, 0.06, 0.78, 1.45, "steel_dark")
B("fsight_ear_l", 18.75, 19.25, -0.42, -0.26, 0.45, 1.75, "steel")
B("fsight_ear_r", 18.75, 19.25, 0.26, 0.42, 0.45, 1.75, "steel")

# ---------------------------------------------------------------- moving: trigger
B("trigger_blade", 6.85, 7.05, -0.1, 0.1, -2.15, -1.4, "steel_dark", g="trigger", rotation=(-22.5, 0, 0),
  origin=(0, -1.6, -6.95))

# ---------------------------------------------------------------- moving: bolt + op-rod handle
B("oprod_bar", 9.1, 11.0, 0.74, 0.98, -0.45, -0.15, "steel", g="bolt")
B("oprod_stem", 9.1, 9.5, 0.74, 1.5, -0.2, 0.15, "steel", g="bolt")
B("oprod_knob", 9.0, 9.65, 1.5, 1.95, -0.3, 0.3, "steel_dark", g="bolt")
B("oprod_knob_ring", 9.05, 9.6, 1.95, 2.0, -0.2, 0.2, "steel", g="bolt")
B("bolt_lug", 7.4, 8.2, 0.69, 0.76, 0.08, 0.34, "gunmetal", g="bolt")
B("bolt_roller", 7.5, 7.7, 0.74, 0.82, 0.1, 0.3, "steel", g="bolt")

# ---------------------------------------------------------------- moving: magazine
B("mag_body", 8.35, 10.1, -0.46, 0.46, -4.75, -1.6, "steel_dark", g="magazine")
B("mag_floor", 8.28, 10.18, -0.52, 0.52, -4.97, -4.75, "steel", g="magazine")
B("mag_lug", 8.25, 8.4, -0.2, 0.2, -2.3, -1.95, "steel", g="magazine")
B("mag_rear_lip", 10.05, 10.25, -0.3, 0.3, -2.2, -1.8, "steel", g="magazine")
for i, y in enumerate((-2.8, -3.3, -3.8)):
    B(f"mag_rib_l{i}", 8.55, 9.9, -0.5, -0.46, y, y + 0.1, "gunmetal", g="magazine")
    B(f"mag_rib_r{i}", 8.55, 9.9, 0.46, 0.5, y, y + 0.1, "gunmetal", g="magazine")
B("mag_hole_a", 9.0, 9.4, 0.5, 0.54, -4.5, -4.35, "steel_dark", g="magazine")
B("mag_hole_b", 9.0, 9.4, -0.54, -0.5, -4.5, -4.35, "steel_dark", g="magazine")

# ---------------------------------------------------------------- points
m.point("grip", (0.0, -1.75, -5.2))
m.point("support", (0.0, -1.75, -13.4))
m.point("sight_rear", (0.0, 1.45, -6.02))
m.point("sight_front", (0.0, 1.45, -19.0))
m.point("muzzle", (0.0, BY, -20.3))
MAG_PT = (0.0, -3.3, -9.2)
HANDLE_PT = (1.75, 0.0, -9.3)

# ---------------------------------------------------------------- place
m.casing((0.75, 0.3, -7.9))   # ejection port, right side of the receiver (local build space)
OFFSET = m.place_gun_at_hip()
m.muzzle_flash(size=2.0)
m.build_arms()
P = lambda p: tuple(p[i] + OFFSET[i] for i in range(3))  # noqa: E731
MAG_PT, HANDLE_PT = P(MAG_PT), P(HANDLE_PT)

m.standard_animations(fire_interval=0.45, kick=0.9, climb=4.5, roll=1.0, casing=True, bolt="bolt", bolt_travel=1.2,
                      eye_relief=5.0)

LREST = (-4.0, -5.5, -8.0)    # relaxed left hand
OFF = (-5.5, -11.0, -4.5)      # off-screen, down-left: "magazine pouch"
GP = 1.6                      # gun pulled toward the shoulder during the cycle
BT = 1.2                       # bolt travel (+z = rearward)


# ---------------------------------------------------------------- reload (3.25 s)
def reload_anim(a, length):
    g = "gun"
    # raise + cant the gun so the magazine well is on screen
    UP_R, UP_P = (-8, 22, -32), (-0.5, 3.6, 0.6)
    Z3 = (0, 0, 0)
    a.ease(g, 0.0, 0.5, rot0=Z3, rot1=UP_R, pos0=Z3, pos1=UP_P, curve="smooth")
    a.key(g, 2.45, rot=UP_R, pos=UP_P)
    a.ease(g, 2.45, 3.0, rot0=UP_R, rot1=(2, -2, -4), pos0=UP_P, pos1=(-0.2, 0.6, 0.1), curve="smooth")
    a.ease(g, 3.0, 3.25, rot0=(2, -2, -4), rot1=Z3, pos0=(-0.2, 0.6, 0.1), pos1=Z3, curve="smooth")
    a.hand("left", 0.0, "support")
    a.hand("left", 0.5, ("bone", "magazine", MAG_PT))
    a.hand("left", 0.8, ("bone", "magazine", MAG_PT))          # thumb on the release, grip
    # magazine drops out of the well, then goes off-screen with the hand
    a.key("magazine", 0.0, pos=(0, 0, 0), rot=(0, 0, 0), scale=1)
    a.key("magazine", 0.8, pos=(0, 0, 0), rot=(0, 0, 0))
    a.ease("magazine", 0.8, 1.05, pos0=(0, 0, 0), pos1=(0, -1.4, 0), curve="in")
    a.ease("magazine", 1.05, 1.6, pos0=(0, -1.4, 0), pos1=(-5.5, -7.5, 1.0),
           rot0=(0, 0, 0), rot1=(0, 0, 25), curve="smooth")
    a.key("magazine", 1.6, scale=1)
    a.key("magazine", 1.61, scale=0)
    a.key("magazine", 1.62, pos=(-5.5, -7.5, 1.0), rot=(0, 0, 25))
    # hand fetches a fresh magazine
    a.hand("left", 1.6, ("bone", "magazine", MAG_PT))
    a.hand("left", 1.9, OFF)
    a.hand("left", 2.05, OFF)
    a.key("magazine", 2.0, scale=0, pos=(-5.5, -7.5, 1.0), rot=(0, 0, 25))
    a.key("magazine", 2.05, scale=1, pos=(-5.5, -7.5, 1.0), rot=(0, 0, 25))
    a.hand("left", 2.1, ("bone", "magazine", MAG_PT))
    a.ease("magazine", 2.1, 2.55, pos0=(-5.5, -7.5, 1.0), pos1=(0, -1.9, 0.5),
           rot0=(0, 0, 25), rot1=(25, 0, 0), curve="smooth")
    # front lug first ...
    a.ease("magazine", 2.55, 2.75, pos0=(0, -1.9, 0.5), pos1=(0, -0.2, 0.1),
           rot0=(25, 0, 0), rot1=(22, 0, 0), curve="out")
    # ... rock it back until it clicks
    a.ease("magazine", 2.75, 2.95, pos0=(0, -0.2, 0.1), pos1=(0, 0, 0),
           rot0=(22, 0, 0), rot1=(0, 0, 0), curve="in")
    a.key("magazine", 3.05, pos=(0, 0.0, 0), rot=(0, 0, 0))
    a.key("magazine", 3.0, pos=(0, 0, 0), rot=(0, 0, 0))
    a.hand("left", 2.95, ("bone", "magazine", MAG_PT))
    a.hand("left", 3.25, "support")
    a.key("magazine", length, pos=(0, 0, 0), rot=(0, 0, 0), scale=1)


a = m.anim("reload", 3.25, "once")
reload_anim(a, 3.25)


# ---------------------------------------------------------------- charging cycle
def cycle(a, t0):
    a.hand("right", t0, "grip")
    a.hand("right", t0 + 0.18, ("bone", "bolt", HANDLE_PT))
    a.hand("right", t0 + 0.2, ("bone", "bolt", HANDLE_PT))
    a.hand("right", t0 + 0.72, ("bone", "bolt", HANDLE_PT))
    a.hand("right", t0 + 0.94, "grip")
    a.key("bolt", t0, pos=(0, 0, 0))
    a.key("bolt", t0 + 0.2, pos=(0, 0, 0))
    a.ease("bolt", t0 + 0.2, t0 + 0.5, pos0=(0, 0, 0), pos1=(0, 0, BT), curve="smooth")
    a.key("bolt", t0 + 0.55, pos=(0, 0, BT))
    a.ease("bolt", t0 + 0.55, t0 + 0.72, pos0=(0, 0, BT), pos1=(0, 0, 0), curve="in")
    a.key("bolt", t0 + 1.0, pos=(0, 0, 0))
    # the rifle is drawn back toward the shoulder while the right hand works the op rod, with a
    # small jolt on release
    PB = (-0.3, 0.0, GP)
    a.key("gun", t0, rot=(0, 0, 0), pos=(0, 0, 0))
    a.key("gun", t0 + 0.1, rot=(0, 0, 0), pos=PB)
    a.key("gun", t0 + 0.2, rot=(0, 0, 0), pos=PB)
    a.key("gun", t0 + 0.5, rot=(0.8, 0, -1.2), pos=(PB[0], PB[1], PB[2] + 0.15))
    a.key("gun", t0 + 0.72, rot=(-0.6, 0, 0.4), pos=(PB[0], PB[1], PB[2] + 0.3))
    a.key("gun", t0 + 1.0, rot=(0, 0, 0), pos=(0, 0, 0))


a = m.anim("reload_empty", 4.25, "once")
reload_anim(a, 3.25)
# keep every channel valid to the end of the longer clip
for (bone, chn), ch in list(a.channels.items()):
    if bone in ("magazine", "gun") and ch.keys and ch.keys[-1][0] < 4.25:
        ch.add(4.25, ch.keys[-1][1])
a.hand("right", 3.25, "grip")
a.hand("left", 4.25, "support")
a.key("gun", 3.25, rot=(0, 0, 0), pos=(0, 0, 0))
cycle(a, 3.25)

a = m.anim("firearm", 1.0, "once")
cycle(a, 0.0)

# ---------------------------------------------------------------- inspect (3.2 s)
a = m.anim("inspect", 3.2, "once")
g = "gun"
a.key(g, 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
a.ease(g, 0.0, 0.8, rot0=(0, 0, 0), rot1=(6, -55, 14), pos0=(0, 0, 0), pos1=(-1.8, 1.6, -0.6), curve="smooth")
a.key(g, 1.5, rot=(6, -55, 14), pos=(-1.8, 1.6, -0.6))
a.ease(g, 1.5, 2.2, rot0=(6, -55, 14), rot1=(-5, -28, -28), pos0=(-1.8, 1.6, -0.6), pos1=(-1.2, 1.8, -0.4), curve="smooth")
a.key(g, 2.4, rot=(-5, -28, -28), pos=(-1.2, 1.8, -0.4))
a.ease(g, 2.4, 3.2, rot0=(-5, -28, -28), rot1=(0, 0, 0), pos0=(-1.2, 1.8, -0.4), pos1=(0, 0, 0), curve="smooth")
# op rod shown working while the gun is turned
a.key("bolt", 0.0, pos=(0, 0, 0))
a.key("bolt", 0.95, pos=(0, 0, 0))
a.ease("bolt", 0.95, 1.2, pos0=(0, 0, 0), pos1=(0, 0, BT), curve="smooth")
a.ease("bolt", 1.3, 1.42, pos0=(0, 0, BT), pos1=(0, 0, 0), curve="in")
a.key("bolt", 3.2, pos=(0, 0, 0))
# left hand lets go and cups the magazine well while the gun is tilted, then re-grips
a.hand("left", 0.0, "support")
a.hand("left", 0.3, LREST)     # left hand lets go and drops near its shoulder while the rifle swings out
a.hand("left", 1.5, LREST)
a.hand("left", 1.85, ("bone", "magazine", MAG_PT))
a.hand("left", 2.35, ("bone", "magazine", MAG_PT))
a.hand("left", 2.9, "support")
a.key("magazine", 0.0, pos=(0, 0, 0))
a.key("magazine", 3.2, pos=(0, 0, 0))

# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail()

m.write(item_name="m14")
