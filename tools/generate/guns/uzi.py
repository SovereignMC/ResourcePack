"""IMI Uzi submachine gun (stock extended), 650 mm = 11.8 px at 1 px = 55 mm.

Local origin = top-rear of the receiver cover. Muzzle -Z, gun's own right side +X.
WeaponMechanics: 10 shots/s, reload 25 ticks (1.25 s), SLIDE open 5 + close 5 (0.5 s), zoom 1.3.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gunlib  # noqa: E402
from gunlib import GunModel  # noqa: E402

gunlib.MATERIALS["uzi_grip"] = gunlib.Material("#1e1f22", "polymer", 0.04, -0.18, 0.0)

m = GunModel("uzi", "Uzi")

# ---------------------------------------------------------------- moving part bones
m.part("magazine", (0, -4.0, -2.6))
m.part("bolt", (0, 0.0, -4.15))
m.part("trigger", (0, -2.3, -3.9))

# ---------------------------------------------------------------- receiver
gunlib.MATERIALS["uzi_park"] = gunlib.Material("#787c79", "metal", 0.08, -0.2, 0.2)   # lighter parkerized stamped body
R = "uzi_park"
m.box("receiver", (-0.9, -2.2, -6.2), (0.9, -0.2, -0.4), R)
m.box("top_cover", (-0.78, -0.2, -5.9), (0.78, 0.0, -0.4), "steel")
m.box("front_cap", (-0.82, -2.1, -6.5), (0.82, -0.3, -6.2), "steel")
m.box("rear_cap", (-0.82, -2.1, -0.4), (0.82, -0.3, 0.2), "steel")
m.box("cap_latch", (-0.3, -1.3, 0.2), (0.3, -0.7, 0.35), "steel")
m.box("cap_latch_screw", (-0.1, -1.1, 0.35), (0.1, -0.9, 0.42), "gunmetal")
m.box("grip_frame", (-0.8, -2.55, -3.5), (0.8, -2.2, -1.7), "steel_dark")
m.box("bottom_plate", (-0.7, -2.3, -6.0), (0.7, -2.2, -3.5), "steel_dark")

# stamped ribs on both sides: horizontal at the rear, vertical at the front
for sx in (1, -1):
    for i, y in enumerate((-0.75, -1.65)):
        a, b = sorted((sx * 0.9, sx * 0.96))
        m.box(f"rib_h{i}_{sx}", (a, y, -4.6), (b, y + 0.14, -0.9), R)
    for i, z in enumerate((-5.9, -5.55, -5.2, -4.85)):
        a, b = sorted((sx * 0.9, sx * 0.98))
        m.box(f"rib_v{i}_{sx}", (a, -2.0, z), (b, -0.4, z + 0.14), R)
# ejection port (right side) and dust flap
m.box("eject_port", (0.9, -1.55, -3.7), (0.94, -0.45, -2.3), "steel_dark")
m.box("eject_lip", (0.94, -0.55, -3.7), (0.97, -0.45, -2.3), "gunmetal")
# top cover details: cocking slot + rivets
m.box("cover_slot", (-0.14, 0.0, -5.1), (0.14, 0.03, -1.6), "steel_dark")
for i, (x, z) in enumerate(((-0.6, -5.6), (0.6, -5.6), (-0.6, -3.0), (0.6, -3.0), (-0.6, -0.8), (0.6, -0.8))):
    m.cbox(f"cover_rivet{i}", (x, 0.03, z), (0.14, 0.06, 0.14), "gunmetal")
for i, z in enumerate((-5.6, -3.0, -0.9)):
    m.cbox(f"body_rivet{i}", (-0.93, -0.35, z), (0.06, 0.14, 0.14), "gunmetal")

# ---------------------------------------------------------------- bolt (top cocking knob)
m.box("knob_stem", (-0.18, 0.03, -4.4), (0.18, 0.35, -3.9), "steel_dark", group="bolt")
m.box("knob_head", (-0.4, 0.35, -4.55), (0.4, 0.62, -3.75), "steel", group="bolt")
m.box("knob_grip", (-0.43, 0.42, -4.4), (0.43, 0.55, -3.9), "steel", group="bolt")
m.box("bolt_block", (-0.1, -0.15, -4.25), (0.1, -0.02, -4.05), "steel_dark", group="bolt", faces_off=("up",))

# ---------------------------------------------------------------- barrel, nut, front sight
BY = -1.0
m.cylinder_z("barrel_nut", (0, BY), 0.66, -7.3, -6.5, "steel")
m.cylinder_z("nut_knurl", (0, BY), 0.74, -7.05, -6.85, "gunmetal")
m.cylinder_z("barrel", (0, BY), 0.3, -8.4, -7.3, "steel_dark")
m.cylinder_z("muzzle_ring", (0, BY), 0.4, -8.5, -8.3, "steel")
m.box("bore", (-0.14, BY - 0.14, -8.53), (0.14, BY + 0.14, -8.5), "steel_dark")

m.box("fs_housing", (-0.5, -0.2, -6.35), (0.5, 0.35, -5.75), "steel")
m.box("fs_ear_l", (-0.42, 0.35, -6.25), (-0.3, 1.0, -5.9), "steel")
m.box("fs_ear_r", (0.3, 0.35, -6.25), (0.42, 1.0, -5.9), "steel")
m.box("fs_post", (-0.06, 0.35, -6.15), (0.06, 0.8, -6.0), "gunmetal")
m.box("fs_screw", (-0.5, 0.0, -6.15), (-0.55, 0.2, -5.95), "gunmetal")

# ---------------------------------------------------------------- rear flip sight
m.box("rs_base", (-0.5, 0.0, -1.2), (0.5, 0.55, -0.6), "steel")
m.box("rs_post_l", (-0.5, 0.55, -1.1), (-0.28, 1.2, -0.7), "steel_dark")
m.box("rs_post_r", (0.28, 0.55, -1.1), (0.5, 1.2, -0.7), "steel_dark")
m.box("rs_bar", (-0.5, 1.0, -1.1), (0.5, 1.2, -0.7), "steel_dark")
m.box("rs_pin", (-0.56, 0.2, -0.95), (0.56, 0.35, -0.85), "gunmetal")

# ---------------------------------------------------------------- pistol grip + magazine
for sx in (1, -1):
    a, b = sorted((sx * 0.5, sx * 0.78))
    m.box(f"grip_panel_{sx}", (a, -5.2, -3.4), (b, -2.55, -1.8), "polymer")
    for i, y in enumerate((-2.95, -3.5, -4.05, -4.6)):
        a2, b2 = sorted((sx * 0.78, sx * 0.84))
        m.box(f"grip_rib{i}_{sx}", (a2, y, -3.3), (b2, y + 0.14, -1.9), "polymer")
m.box("grip_front", (-0.5, -5.2, -3.4), (0.5, -2.55, -3.1), "steel_dark")
m.box("grip_back", (-0.5, -5.2, -2.1), (0.5, -2.55, -1.8), "steel_dark")
m.box("mag_catch", (-0.9, -4.8, -2.15), (-0.78, -4.5, -1.85), "steel")
m.box("mag_catch_pin", (-0.92, -4.72, -2.05), (-0.9, -4.58, -1.95), "gunmetal")
# grip safety on the back of the grip
m.box("gsafety", (-0.35, -4.3, -1.8), (0.35, -2.5, -1.5), "steel")
m.box("gsafety_lug", (-0.3, -2.7, -1.5), (0.3, -2.4, -1.3), "steel_dark")
m.box("gsafety_pad", (-0.25, -4.0, -1.5), (0.25, -3.1, -1.46), "gunmetal")

m.box("mag_body", (-0.48, -6.0, -3.08), (0.48, -2.6, -2.12), "steel_dark", group="magazine")
m.box("mag_ribs", (-0.52, -5.9, -3.0), (0.52, -5.75, -2.2), "steel", group="magazine")
m.box("mag_base", (-0.8, -6.35, -3.4), (0.8, -6.0, -1.8), "steel", group="magazine")
m.box("mag_base_pad", (-0.7, -6.5, -3.3), (0.7, -6.35, -1.9), "uzi_grip", group="magazine")
m.box("mag_base_lip", (-0.86, -6.25, -3.2), (-0.8, -6.05, -2.0), "gunmetal", group="magazine")

# ---------------------------------------------------------------- trigger group
m.box("guard_front", (-0.15, -3.3, -4.8), (0.15, -2.2, -4.55), "steel")
m.box("guard_bottom", (-0.15, -3.3, -4.8), (0.15, -3.05, -3.4), "steel")
m.box("trigger_upper", (-0.1, -2.65, -4.0), (0.1, -2.2, -3.8), "gunmetal", group="trigger")
m.box("trigger_lower", (-0.1, -3.0, -3.95), (0.1, -2.65, -3.7), "gunmetal", group="trigger")

# fire selector, left top of the grip
m.box("sel_plate", (-0.88, -2.5, -2.95), (-0.8, -2.25, -2.6), "steel_dark")
m.box("sel_lever", (-0.96, -2.45, -2.85), (-0.88, -2.33, -2.2), "gunmetal")
m.box("sel_tip", (-1.02, -2.5, -2.4), (-0.96, -2.28, -2.2), "steel")


# ---------------------------------------------------------------- sling swivels (left)
def swivel(name, z, y, mat="gunmetal"):
    m.box(f"{name}_mount", (-1.0, y - 0.15, z - 0.15), (-0.9, y + 0.15, z + 0.15), "steel")
    m.box(f"{name}_ring_a", (-1.25, y - 0.32, z - 0.05), (-1.15, y + 0.28, z + 0.05), mat)
    m.box(f"{name}_ring_b", (-1.25, y - 0.32, z - 0.28), (-1.15, y - 0.22, z + 0.28), mat)
    m.box(f"{name}_ring_c", (-1.25, y + 0.18, z - 0.28), (-1.15, y + 0.28, z + 0.28), mat)
    m.box(f"{name}_pin", (-1.15, y - 0.07, z - 0.07), (-1.0, y + 0.07, z + 0.07), mat)


swivel("swivel_f", -5.0, -0.5)
m.box("swivel_r_mount", (-0.9, -0.95, -0.35), (-1.0, -0.65, -0.05), "steel")
m.box("swivel_r_ring", (-1.25, -1.0, -0.3), (-1.0, -0.55, -0.1), "gunmetal", faces_off=())

# ---------------------------------------------------------------- folding stock (extended)
for sx in (1, -1):
    a, b = sorted((sx * 0.58, sx * 0.78))
    m.box(f"stock_hinge_{sx}", (min(sx * 0.5, sx * 0.88), -2.0, 0.2), (max(sx * 0.5, sx * 0.88), -1.35, 0.65), "steel")
    m.box(f"stock_strut_{sx}", (a, -1.9, 0.65), (b, -1.5, 3.3), "steel_dark")
    m.box(f"stock_strut_edge_{sx}", (a, -1.95, 1.2), (b, -1.9, 3.0), "gunmetal")
m.box("stock_cross", (-0.76, -1.75, 2.85), (0.76, -1.55, 3.05), "steel_dark")
m.box("butt_plate", (-0.85, -3.1, 3.3), (0.85, -0.5, 3.6), "steel_dark")
m.box("butt_lip_top", (-0.85, -0.6, 3.0), (0.85, -0.5, 3.3), "steel")
m.box("butt_lip_bot", (-0.85, -3.1, 3.0), (0.85, -3.0, 3.3), "steel")
for sx in (1, -1):
    a, b = sorted((sx * 0.85, sx * 0.93))
    m.box(f"butt_side_{sx}", (a, -3.1, 3.2), (b, -0.5, 3.6), "steel_dark")
m.box("butt_pad", (-0.6, -2.7, 3.6), (0.6, -0.9, 3.7), "rubber")

# ---------------------------------------------------------------- points (rest space)
m.point("grip", (0, -3.7, -2.6))
m.point("support", (0, -2.9, -5.9))
m.point("sight_rear", (0, 0.78, -0.9))
m.point("sight_front", (0, 0.78, -6.07))
m.point("muzzle", (0, BY, -8.55))
m.point("mag_base", (-1.4, -5.6, -2.6))
m.point("knob", (-0.95, 0.5, -4.15))

OFFSET = m.place_gun_at_hip()

m.muzzle_flash(size=2.0)
m.build_arms()

m.standard_animations(fire_interval=0.1, kick=0.3, climb=1.5, bolt="bolt", bolt_travel=1.0,
                      eye_relief=5.0, sprint_style="pistol")
for nm in ("shoot", "aiming_shoot"):
    a = m.anims[nm]
    a.key("trigger", 0.0, pos=(0, 0, 0.3))
    a.key("trigger", a.length * 0.7, pos=(0, 0, 0.3))
    a.key("trigger", a.length, pos=(0, 0, 0))

P = m.points["mag_base"]
KNOB = m.points["knob"]
H_FETCH = (-7.0, -13.0, -6.0)   # off-screen down-left, where the new magazine comes from
GUN = "gun"


def cock(a, t0, pull=0.17, hold=0.02, back=0.05, travel=2.4):
    """Left hand grabs the top cocking knob, pulls it back and lets go."""
    a.hand("left", t0, ("bone", "bolt", KNOB))
    a.ease("bolt", t0, t0 + pull, pos0=(0, 0, 0), pos1=(0, 0, travel), curve="out")
    a.key("bolt", t0 + pull + hold, pos=(0, 0, travel))
    a.ease("bolt", t0 + pull + hold, t0 + pull + hold + back, pos0=(0, 0, travel), pos1=(0, 0, 0), curve="in")
    return t0 + pull + hold + back


def build_reload(name, length, extra_cock=False):
    a = m.anim(name, length, "once")
    a.pole("right", (1.0, -0.2, 0.3))
    # gun rolls its magwell toward the left hand
    TILT = (6, 14, -8)
    TP = (-1.0, 2.7, -1.0)
    a.ease(GUN, 0.0, 0.2, rot0=(0, 0, 0), rot1=TILT, pos0=(0, 0, 0), pos1=TP)
    a.key(GUN, 0.92, rot=TILT, pos=TP)
    a.key(GUN, 0.95, rot=(TILT[0] - 2, 0, TILT[2] + 1), pos=(TP[0], TP[1] - 0.3, TP[2] + 0.4))
    a.ease(GUN, 0.95, 1.25, rot0=(TILT[0] - 2, 0, TILT[2] + 1), rot1=(0, 0, 0), pos0=(TP[0], TP[1] - 0.3, TP[2] + 0.4), pos1=(0, 0, 0))
    # old mag out
    a.key("magazine", 0.0, pos=(0, 0, 0), scale=1)
    a.key("magazine", 0.2, pos=(0, 0, 0))
    a.ease("magazine", 0.2, 0.42, pos0=(0, 0, 0), pos1=(0, -4.5, 0), curve="smooth")
    a.ease("magazine", 0.42, 0.6, pos0=(0, -4.5, 0), pos1=(-4, -18, 0), curve="in")
    a.key("magazine", 0.0, scale=1)
    a.key("magazine", 0.6, scale=1)
    a.key("magazine", 0.61, scale=0)
    a.key("magazine", 0.63, scale=0)
    a.key("magazine", 0.64, scale=1)
    # new mag appears in the left hand, off-screen down-left
    t = 0.64
    xf = m.bone_xf(m.gun, a, t, m.viewmodel)
    inv = gunlib.m_t(xf.r)
    hl = gunlib.m_vec(inv, gunlib.v_sub(H_FETCH, xf.t))
    fetch = gunlib.v_sub(hl, P)
    a.key("magazine", 0.63, pos=fetch)
    a.key("magazine", 0.64, pos=fetch)
    a.ease("magazine", 0.64, 0.86, pos0=fetch, pos1=(0, -4.5, 0), curve="smooth")
    a.ease("magazine", 0.86, 0.95, pos0=(0, -4.5, 0), pos1=(0, 0, 0), curve="in")
    a.key("magazine", length, pos=(0, 0, 0), scale=1)
    # left hand
    a.hand("left", 0.0, "support")
    a.hand("left", 0.18, ("bone", "magazine", P))
    a.hand("left", 0.42, ("bone", "magazine", P))
    a.hand("left", 0.62, H_FETCH)
    a.hand("left", 0.64, ("bone", "magazine", P))
    a.hand("left", 0.95, ("bone", "magazine", P))
    if extra_cock:
        a.pole("left", (-1, -0.8, 0.2))
        a.hand("left", 1.1, "support")
        end = cock(a, 1.3)
        a.hand("left", end + 0.02, ("bone", "bolt", KNOB))
        a.hand("left", length, "support")
    else:
        a.hand("left", 1.25, "support")
    return a


build_reload("reload", 1.25)
build_reload("reload_empty", 2.0, extra_cock=True)

# ---------------------------------------------------------------- inspect (3.2 s)
a = m.anim("inspect", 3.2, "once")
a.ease(GUN, 0.0, 0.5, rot0=(0, 0, 0), rot1=(-6, 0, 6), pos0=(0, 0, 0), pos1=(-1.0, 1.4, -0.8), curve="smooth")
a.ease(GUN, 0.5, 1.2, rot0=(-6, 0, 6), rot1=(-4, 24, 8), pos0=(-1.0, 1.4, -0.8), pos1=(-1.4, 1.4, -0.8))
a.key(GUN, 1.6, rot=(-4, 24, 8), pos=(-1.4, 1.4, -0.8))
a.ease(GUN, 1.6, 2.4, rot0=(-4, 24, 8), rot1=(-4, -28, -6), pos0=(-1.4, 1.4, -0.8), pos1=(-0.9, 1.4, -0.8))
a.key(GUN, 2.6, rot=(-4, -28, -6), pos=(-0.9, 1.4, -0.8))
a.ease(GUN, 2.6, 3.2, rot0=(-4, -28, -6), rot1=(0, 0, 0), pos0=(-0.9, 1.4, -0.8), pos1=(0, 0, 0))
# cycle the knob while the gun is turned
a.ease("bolt", 1.1, 1.3, pos0=(0, 0, 0), pos1=(0, 0, 2.0), curve="out")
a.ease("bolt", 1.3, 1.4, pos0=(0, 0, 2.0), pos1=(0, 0, 0), curve="in")
a.key("bolt", 3.2, pos=(0, 0, 0))
# magazine tapped out a little and seated again
a.ease("magazine", 2.65, 2.8, pos0=(0, 0, 0), pos1=(0, -0.5, 0), curve="out")
a.ease("magazine", 2.8, 2.9, pos0=(0, -0.5, 0), pos1=(0, 0, 0), curve="in")
a.key("magazine", 3.2, pos=(0, 0, 0))

# ---------------------------------------------------------------- firearm (SLIDE open 5 + close 5 = 0.5 s)
a = m.anim("firearm", 0.5, "once")
a.pole("left", (-1, -0.8, 0.2))
a.hand("left", 0.0, "support")
a.hand("left", 0.08, ("bone", "bolt", KNOB))
a.hand("left", 0.3, ("bone", "bolt", KNOB))
a.hand("left", 0.5, "support")
a.key("bolt", 0.0, pos=(0, 0, 0))
a.key("bolt", 0.08, pos=(0, 0, 0))
a.ease("bolt", 0.08, 0.25, pos0=(0, 0, 0), pos1=(0, 0, 2.4), curve="out")
a.key("bolt", 0.27, pos=(0, 0, 2.4))
a.ease("bolt", 0.27, 0.33, pos0=(0, 0, 2.4), pos1=(0, 0, 0), curve="in")
a.key("bolt", 0.5, pos=(0, 0, 0))

# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail()

m.write(item_name="uzi")
