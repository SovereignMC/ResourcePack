#!/usr/bin/env python3
"""M3 "Grease Gun" submachine gun (757 mm, stock extended -> 13.8 px at 1 px = 55 mm).

Local build space: receiver rear face at z=0, receiver axis at x=y=0, muzzle toward -Z.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gunlib  # noqa: E402
from gunlib import GunModel, Material  # noqa: E402

gunlib.MATERIALS["parker"] = Material("#60685b", "metal", 0.07, -0.2, 0.25)
gunlib.MATERIALS["parker_dark"] = Material("#4e5549", "metal", 0.06, -0.22, 0.2)
gunlib.MATERIALS["parker_light"] = Material("#6c7560", "metal", 0.06, -0.18, 0.3)

m = GunModel("m3", "M3 Grease Gun")
P, PD, PL, ST, SD = "parker", "parker_dark", "parker_light", "steel", "steel_dark"

# ---------------------------------------------------------------- receiver (cylinder)
m.cylinder_z("receiver", (0, 0), 0.78, -6.2, 0.0, P)
m.cylinder_z("rear_cap", (0, 0), 0.84, 0.0, 0.3, PL)
m.box("rear_cap_plate", (-0.4, -0.4, 0.3), (0.4, 0.4, 0.42), SD)
m.cylinder_z("ring_rear", (0, 0), 0.84, -1.0, -0.8, PL)
m.cylinder_z("ring_mid", (0, 0), 0.84, -5.5, -5.3, PL)
m.box("seam_rib", (-0.1, 0.95, -5.2), (0.1, 1.03, -1.6), PD)

# ---------------------------------------------------------------- barrel collar + barrel
m.cylinder_z("collar", (0, 0), 0.66, -7.4, -6.1, PD)
for i, z in enumerate((-6.5, -6.85, -7.2)):
    m.cylinder_z(f"knurl{i}", (0, 0), 0.72, z - 0.1, z + 0.1, ST)
m.cylinder_z("barrel", (0, 0), 0.3, -10.2, -7.3, SD)
m.cylinder_z("muzzle_nut", (0, 0), 0.38, -10.4, -9.8, ST)
m.box("muzzle_bore", (-0.12, -0.12, -10.42), (0.12, 0.12, -10.4), "steel_dark")

# ---------------------------------------------------------------- sights (line of sight y=1.9)
m.box("peep_base", (-0.4, 0.9, -1.2), (0.4, 1.3, -0.85), PD)
m.box("peep_ear_l", (-0.5, 1.3, -1.2), (-0.16, 2.4, -0.85), P)
m.box("peep_ear_r", (0.16, 1.3, -1.2), (0.5, 2.4, -0.85), P)
m.box("peep_bottom", (-0.16, 1.3, -1.2), (0.16, 1.65, -0.85), P)
m.box("peep_top", (-0.5, 2.15, -1.2), (0.5, 2.4, -0.85), P)
m.box("front_base", (-0.32, 0.9, -6.0), (0.32, 1.25, -5.5), PD)
m.box("front_blade", (-0.09, 1.2, -5.9), (0.09, 1.9, -5.65), SD)
m.box("front_ear_l", (-0.46, 0.95, -6.0), (-0.33, 1.7, -5.6), P)
m.box("front_ear_r", (0.33, 0.95, -6.0), (0.46, 1.7, -5.6), P)

# ---------------------------------------------------------------- ejection port + dust cover
m.box("port", (0.7, 0.28, -4.5), (0.78, 0.7, -2.3), SD)
m.box("port_rim_f", (0.73, 0.23, -4.65), (0.82, 0.75, -4.5), PD)
m.box("port_rim_r", (0.73, 0.23, -2.3), (0.82, 0.75, -2.15), PD)
m.part("dust_cover", (0.85, 0.74, -3.4))
m.box("cover_plate", (0.8, 0.26, -4.5), (0.9, 0.72, -2.3), PL, group="dust_cover")
m.box("cover_hinge", (0.77, 0.68, -4.55), (0.95, 0.8, -2.25), PD, group="dust_cover")
m.box("cover_tab", (0.9, 0.3, -2.6), (1.0, 0.5, -2.3), ST, group="dust_cover")
m.box("cover_rib", (0.9, 0.4, -4.3), (0.95, 0.62, -2.75), P, group="dust_cover")

# ---------------------------------------------------------------- cocking crank (right, lower)
m.box("crank_boss", (0.7, -0.7, -3.6), (1.15, -0.15, -2.95), PD)
m.box("crank_pin", (1.15, -0.5, -3.4), (1.25, -0.3, -3.2), ST)
m.part("cocking_crank", (1.35, -0.4, -3.25))
m.box("crank_arm", (1.25, -0.5, -4.7), (1.45, -0.3, -3.15), ST, group="cocking_crank")
m.box("crank_knob", (1.25, -0.68, -5.05), (1.75, -0.12, -4.55), SD, group="cocking_crank")
m.box("crank_cap", (1.75, -0.6, -4.95), (1.85, -0.2, -4.65), ST, group="cocking_crank")

# ---------------------------------------------------------------- pistol grip + trigger guard
m.box("grip_top", (-0.5, -1.5, -2.55), (0.5, -0.6, -1.35), PD)
m.box("grip_mid", (-0.5, -2.4, -2.35), (0.5, -1.5, -1.15), PD)
m.box("grip_low", (-0.5, -3.3, -2.15), (0.5, -2.4, -0.95), PD)
m.box("grip_panel_l", (-0.57, -3.1, -2.2), (-0.5, -0.9, -1.2), P)
m.box("grip_panel_r", (0.5, -3.1, -2.2), (0.57, -0.9, -1.2), P)
for i, (y, zc) in enumerate(((-1.05, -1.95), (-1.95, -1.75), (-2.85, -1.55))):
    m.cbox(f"grip_rivet_r{i}", (0.61, y, zc), (0.1, 0.1, 0.1), ST)
    m.cbox(f"grip_rivet_l{i}", (-0.61, y, zc), (0.1, 0.1, 0.1), ST)
m.box("grip_cap", (-0.45, -3.45, -2.05), (0.45, -3.3, -0.9), SD)
m.box("guard_bottom", (-0.12, -2.0, -3.9), (0.12, -1.85, -2.2), PD)
m.box("guard_front", (-0.12, -2.0, -3.9), (0.12, -0.6, -3.7), PD)
m.part("trigger", (0, -0.8, -2.85))
m.box("trigger_blade", (-0.1, -1.6, -3.05), (0.1, -0.8, -2.85), SD, group="trigger")
m.box("trigger_face", (-0.1, -1.45, -3.15), (0.1, -1.25, -3.05), SD, group="trigger")

# ---------------------------------------------------------------- magazine housing + magazine
m.box("housing", (-0.65, -2.6, -5.6), (0.65, -0.65, -3.9), PD)
m.box("housing_lip", (-0.72, -2.7, -5.7), (0.72, -2.55, -3.8), PL)
m.box("housing_rib_l", (-0.7, -2.3, -5.0), (-0.65, -0.85, -4.5), P)
m.box("housing_rib_r", (0.65, -2.3, -5.0), (0.7, -0.85, -4.5), P)
m.box("housing_rivet_f", (-0.1, -1.3, -5.65), (0.1, -1.1, -5.6), ST)
m.box("housing_release", (-0.3, -2.25, -3.95), (0.3, -2.0, -3.82), ST)
m.box("swivel_mount", (-0.2, -0.67, -5.55), (0.2, -0.35, -5.2), ST)
m.box("swivel_ring", (-0.04, -0.55, -5.8), (0.04, -0.25, -5.55), ST)

m.part("magazine", (0, -2.7, -4.75))
m.box("mag_body", (-0.45, -6.3, -5.3), (0.45, -1.9, -4.2), P, group="magazine")
m.box("mag_rib_f", (-0.36, -6.0, -5.38), (0.36, -2.7, -5.3), PL, group="magazine")
m.box("mag_rib_b", (-0.36, -6.0, -4.2), (0.36, -2.7, -4.12), PL, group="magazine")
m.box("mag_ridge_l", (-0.5, -5.8, -4.95), (-0.45, -2.9, -4.55), PD, group="magazine")
m.box("mag_ridge_r", (0.45, -5.8, -4.95), (0.5, -2.9, -4.55), PD, group="magazine")
m.box("mag_base", (-0.55, -6.55, -5.4), (0.55, -6.3, -4.1), SD, group="magazine")
m.box("mag_follow", (-0.28, -2.0, -5.05), (0.28, -1.9, -4.45), ST, group="magazine")

# ---------------------------------------------------------------- wire stock (extended)
for sx, s in (("r", 1), ("l", -1)):
    x = 0.55 * s
    m.box(f"stock_top_{sx}", (x - 0.07, -0.25, 0.25), (x + 0.07, -0.11, 3.45), ST)
    m.cbox(f"stock_low_{sx}", (x, -1.5, 1.8), (0.14, 0.14, 3.3), ST, rotation=(22.5, 0, 0))
    m.box(f"stock_post_{sx}", (x - 0.07, -2.25, 3.2), (x + 0.07, -0.11, 3.4), ST)
    m.box(f"stock_mount_{sx}", (x - 0.12, -1.0, 0.0), (x + 0.12, -0.15, 0.6), PD)
m.box("butt_plate", (-0.7, -2.4, 3.4), (0.7, -0.1, 3.62), PD)
m.box("butt_pad", (-0.58, -2.25, 3.62), (0.58, -0.25, 3.7), SD)
m.box("stock_cross", (-0.55, -0.25, 1.8), (0.55, -0.11, 1.94), ST)

# ---------------------------------------------------------------- points
m.point("grip", (0, -1.9, -1.75))
m.point("support", (0, -1.6, -4.75))
m.point("sight_rear", (0, 1.9, -1.02))
m.point("sight_front", (0, 1.9, -5.775))
m.point("muzzle", (0, 0, -10.45))

m.casing((0.85, 0.5, -3.4))   # ejection port, right side of the receiver (local build space)
OFF = m.place_gun_at_hip()
m.muzzle_flash(2.0)
m.build_arms()


def L(x, y, z):
    """local build-space point -> placed rest space"""
    return (x + OFF[0], y + OFF[1], z + OFF[2])


MAG_GRAB = L(0, -4.4, -4.75)
MAG_HOUSING = L(0, -1.6, -4.75)

m.standard_animations(fire_interval=0.2, kick=0.5, climb=2.2, roll=0.8, casing=True, eye_relief=5.0)

CRANK_PULL = (-80, 0, 0)


# ---------------------------------------------------------------- reload
def reload_anim(name, length, cock):
    a = m.anim(name, length, "once")
    g = "gun"
    # lift and tilt the gun so the housing and magazine come on screen
    UPR, UPP = (8, 48, 6), (-1.5, 3.4, -0.5)
    SLR, SLP = (6, 44, 4), (-1.3, 3.2, 0.0)
    a.ease(g, 0.0, 0.25, rot0=(0, 0, 0), rot1=UPR, pos0=(0, 0, 0), pos1=UPP, curve="smooth")
    a.key(g, 0.95, rot=UPR, pos=UPP)
    a.ease(g, 0.95, 1.1, rot0=UPR, rot1=SLR, pos0=UPP, pos1=SLP, curve="out")   # slap
    a.ease(g, 1.1, 1.5, rot0=SLR, rot1=(0, 0, 0), pos0=SLP, pos1=(0, 0, 0), curve="smooth")
    a.key(g, 1.55, rot=(0, 0, 0), pos=(0, 0, 0))

    # old magazine: pulled out by the hand and dropped
    mg = "magazine"
    out_pos = (0, -4.2, 0)
    a.key(mg, 0.0, pos=(0, 0, 0), scale=1.0)
    a.key(mg, 0.2, pos=(0, 0, 0), scale=1.0)
    a.ease(mg, 0.2, 0.42, pos0=(0, 0, 0), pos1=out_pos, curve="smooth")
    a.ease(mg, 0.42, 0.6, pos0=out_pos, pos1=(-1.0, -12.0, 1.5), curve="in")
    a.key(mg, 0.42, scale=1.0)
    a.key(mg, 0.59, scale=1.0)
    a.key(mg, 0.6, scale=0.0)
    # fresh magazine appears in the fetching hand, then goes in
    fetch = (-3.5, -10.5, -6.0)              # off-screen down-left (viewmodel space)
    fresh_pos = (fetch[0] - MAG_GRAB[0], fetch[1] - MAG_GRAB[1], fetch[2] - MAG_GRAB[2])
    a.key(mg, 0.74, scale=0.0, pos=fresh_pos)
    a.key(mg, 0.75, scale=1.0, pos=fresh_pos)
    under = (0, -3.4, 0)
    a.ease(mg, 0.75, 0.97, pos0=fresh_pos, pos1=under, curve="smooth")
    a.ease(mg, 0.97, 1.1, pos0=under, pos1=(0, 0, 0), curve="in")
    a.key(mg, 1.55, pos=(0, 0, 0), scale=1.0)

    # left hand: housing -> magazine -> pull -> fetch -> fresh magazine -> housing
    a.hand("left", 0.0, "support")
    a.hand("left", 0.2, ("bone", mg, MAG_GRAB))
    a.hand("left", 0.42, ("bone", mg, MAG_GRAB))
    a.hand("left", 0.6, fetch)
    a.hand("left", 0.75, ("bone", mg, MAG_GRAB))
    a.hand("left", 1.1, ("bone", mg, MAG_GRAB))
    a.hand("left", 1.4, "support")

    # trigger/crank untouched in plain reload
    if cock:
        t0 = 1.55
        a.key("cocking_crank", 0.0, rot=(0, 0, 0))
        a.key("cocking_crank", t0, rot=(0, 0, 0))
        a.ease("cocking_crank", t0, t0 + 0.2, rot0=(0, 0, 0), rot1=CRANK_PULL, curve="smooth")
        a.key("cocking_crank", t0 + 0.3, rot=CRANK_PULL)
        a.ease("cocking_crank", t0 + 0.3, t0 + 0.45, rot0=CRANK_PULL, rot1=(0, 0, 0), curve="out")
        a.key("dust_cover", 0.0, rot=(0, 0, 0))
        a.key("dust_cover", t0, rot=(0, 0, 0))
        a.ease("dust_cover", t0, t0 + 0.1, rot0=(0, 0, 0), rot1=(0, 0, 70), curve="out")
        a.key("dust_cover", t0 + 0.3, rot=(0, 0, 70))
        a.ease("dust_cover", t0 + 0.3, t0 + 0.45, rot0=(0, 0, 70), rot1=(0, 0, 0), curve="in")
        a.key(g, t0 + 0.01, pos=(0, 0, 0), rot=(0, 0, 0))
        a.key(g, t0 + 0.2, pos=(0, 0, 0.15), rot=(0, 0, -2))
        a.key(g, t0 + 0.3, pos=(0, 0, 0.15), rot=(0, 0, -2))
        a.ease(g, t0 + 0.3, length, pos0=(0, 0, 0.15), pos1=(0, 0, 0), rot0=(0, 0, -2), rot1=(0, 0, 0), curve="out")
    return a


reload_anim("reload", 1.55, False)
reload_anim("reload_empty", 2.1, True)

# ---------------------------------------------------------------- firearm (SLIDE 5+5 ticks)
a = m.anim("firearm", 0.5, "once")
a.key("cocking_crank", 0.0, rot=(0, 0, 0))
a.ease("cocking_crank", 0.0, 0.2, rot0=(0, 0, 0), rot1=CRANK_PULL, curve="smooth")
a.key("cocking_crank", 0.25, rot=CRANK_PULL)
a.ease("cocking_crank", 0.25, 0.4, rot0=CRANK_PULL, rot1=(0, 0, 0), curve="out")
a.key("cocking_crank", 0.5, rot=(0, 0, 0))
a.ease("dust_cover", 0.0, 0.08, rot0=(0, 0, 0), rot1=(0, 0, 70), curve="out")
a.key("dust_cover", 0.3, rot=(0, 0, 70))
a.ease("dust_cover", 0.3, 0.45, rot0=(0, 0, 70), rot1=(0, 0, 0), curve="in")
a.key("dust_cover", 0.5, rot=(0, 0, 0))
a.ease("gun", 0.0, 0.2, rot0=(0, 0, 0), rot1=(1.5, -2, 3), pos0=(0, 0, 0), pos1=(0, 0, 0.15))
a.key("gun", 0.25, rot=(1.5, -2, 3), pos=(0, 0, 0.15))
a.ease("gun", 0.25, 0.5, rot0=(1.5, -2, 3), rot1=(0, 0, 0), pos0=(0, 0, 0.15), pos1=(0, 0, 0), curve="out")

# ---------------------------------------------------------------- inspect
a = m.anim("inspect", 3.2, "once")
g = "gun"
a.ease(g, 0.0, 0.6, rot0=(0, 0, 0), rot1=(4, -62, 6), pos0=(0, 0, 0), pos1=(-2.5, 0.8, 1.0))
a.key(g, 1.2, rot=(4, -62, 6), pos=(-2.5, 0.8, 1.0))
a.ease(g, 1.2, 1.8, rot0=(4, -62, 6), rot1=(2, 55, -4), pos0=(-2.5, 0.8, 1.0), pos1=(-1.8, 0.8, 1.2))
a.key(g, 2.3, rot=(2, 55, -4), pos=(-1.8, 0.8, 1.2))
a.ease(g, 2.3, 3.0, rot0=(2, 55, -4), rot1=(0, 0, 0), pos0=(-1.8, 0.8, 1.2), pos1=(0, 0, 0))
a.key(g, 3.2, rot=(0, 0, 0), pos=(0, 0, 0))
# flip the dust cover while the right side faces the camera
a.key("dust_cover", 0.0, rot=(0, 0, 0))
a.ease("dust_cover", 0.7, 0.85, rot0=(0, 0, 0), rot1=(0, 0, 70), curve="out")
a.key("dust_cover", 1.15, rot=(0, 0, 70))
a.ease("dust_cover", 1.15, 1.3, rot0=(0, 0, 70), rot1=(0, 0, 0), curve="in")
a.key("dust_cover", 3.2, rot=(0, 0, 0))
a.key("cocking_crank", 0.0, rot=(0, 0, 0))
a.ease("cocking_crank", 0.8, 1.0, rot0=(0, 0, 0), rot1=CRANK_PULL)
a.ease("cocking_crank", 1.0, 1.25, rot0=CRANK_PULL, rot1=(0, 0, 0), curve="out")
a.key("cocking_crank", 3.2, rot=(0, 0, 0))
a.key("trigger", 0.0, rot=(0, 0, 0))
a.ease("trigger", 1.9, 2.0, rot0=(0, 0, 0), rot1=(18, 0, 0))
a.ease("trigger", 2.0, 2.1, rot0=(18, 0, 0), rot1=(0, 0, 0))
a.key("trigger", 3.2, rot=(0, 0, 0))
# the magazine pops half out while the left side is shown
a.key("magazine", 0.0, pos=(0, 0, 0))
a.key("magazine", 1.9, pos=(0, 0, 0))
a.ease("magazine", 1.9, 2.05, pos0=(0, 0, 0), pos1=(0, -1.0, 0), curve="out")
a.ease("magazine", 2.25, 2.4, pos0=(0, -1.0, 0), pos1=(0, 0, 0), curve="in")
a.key("magazine", 3.2, pos=(0, 0, 0))

# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail()

m.write(item_name="m3_grease_gun")
