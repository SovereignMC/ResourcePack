"""AK-47 (AKM style) gun model generator. Run: python3 tools/generate/guns/ak47.py

Local build space: receiver dust-cover top at y = 0, butt plate at z = 0, muzzle toward -Z.
Helper B()/S() take distances `d` from the butt plate (z = -d) in model px (1 px = 55 mm).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gunlib  # noqa: E402
from gunlib import GunModel, Material, v_add  # noqa: E402

gunlib.MATERIALS["bakelite_red"] = Material("#8f3a22", "polymer", 0.05, -0.2, 0.0)
gunlib.MATERIALS["mag_steel"] = Material("#34373c", "metal", 0.07, -0.22, 0.4)

m = GunModel("ak47", "AK-47")


def B(name, x0, x1, y0, y1, d0, d1, mat, group="gun", **kw):
    return m.box(name, (x0, y0, -d1), (x1, y1, -d0), mat, group=group, **kw)


def S(name, x0, x1, y0, y1, d0, d1, mat, group="gun", **kw):
    """Right (+x) and left (-x) copies."""
    B(name + "_r", x0, x1, y0, y1, d0, d1, mat, group, **kw)
    B(name + "_l", -x1, -x0, y0, y1, d0, d1, mat, group, **kw)


# ---------------------------------------------------------------- stock
B("butt_plate", -0.46, 0.46, -3.2, -0.7, 0.0, 0.15, "steel_dark")
B("stock_a", -0.42, 0.42, -3.05, -0.75, 0.1, 1.7, "wood")
B("stock_b", -0.40, 0.40, -2.7, -0.6, 1.65, 3.1, "wood_light")
B("stock_c", -0.38, 0.38, -2.35, -0.45, 3.05, 4.5, "wood")
B("butt_screw_t", 0.2, 0.34, -1.1, -0.96, -0.06, 0.0, "steel")
B("butt_screw_b", -0.34, -0.2, -2.9, -2.76, -0.06, 0.0, "steel")
B("stock_swivel", -0.05, 0.05, -3.3, -3.05, 0.8, 1.1, "steel_dark")
B("stock_swivel_ring", -0.03, 0.03, -3.55, -3.3, 0.75, 1.15, "steel")
B("tang_screw", -0.07, 0.07, -0.5, -0.45, 3.7, 3.85, "steel_dark")

# ---------------------------------------------------------------- receiver
B("recv_body", -0.5, 0.5, -1.7, -0.35, 4.4, 10.2, "parkerized")
B("recv_rear", -0.52, 0.52, -1.65, -0.4, 4.3, 4.95, "steel_dark")
B("dust_cover", -0.56, 0.56, -0.4, 0.0, 4.7, 9.0, "parkerized")
B("spring_cap", -0.25, 0.25, -0.3, -0.1, 4.5, 4.72, "steel_dark")
B("cover_rib", -0.09, 0.09, 0.0, 0.07, 5.0, 8.8, "gunmetal")
for i, d in enumerate((5.6, 6.4, 7.2)):
    B(f"cover_cross_rib{i}", -0.5, 0.5, 0.0, 0.05, d, d + 0.15, "gunmetal")
B("trunnion", -0.56, 0.56, -1.75, -0.3, 9.9, 10.5, "steel_dark")
S("magwell_side", 0.46, 0.54, -2.0, -1.65, 8.5, 10.3, "steel_dark")
B("port_panel", 0.5, 0.53, -1.0, -0.45, 6.0, 8.8, "steel_dark")
for sx in (1, -1):
    for i, (d, y) in enumerate(((5.3, -0.9), (5.3, -1.5), (9.5, -0.9), (9.5, -1.5))):
        x0, x1 = (0.5, 0.58) if sx > 0 else (-0.58, -0.5)
        B(f"rivet_{'r' if sx > 0 else 'l'}{i}", x0, x1, y - 0.08, y + 0.08, d - 0.08, d + 0.08, "steel")

# selector (moving)
m.part("selector", (0.55, -1.27, -6.9))
B("selector_blade", 0.49, 0.56, -1.35, -1.2, 6.3, 7.4, "steel", group="selector")
B("selector_tab", 0.49, 0.68, -1.55, -1.2, 6.2, 6.5, "steel", group="selector")
B("selector_pin", 0.56, 0.62, -1.3, -1.25, 6.85, 6.95, "steel_dark", group="selector")

# trigger guard + trigger
B("guard_bottom", -0.2, 0.2, -2.35, -2.2, 7.4, 8.6, "steel_dark")
B("guard_front", -0.2, 0.2, -2.35, -1.65, 8.45, 8.6, "steel_dark")
B("guard_rear", -0.2, 0.2, -2.35, -1.65, 7.4, 7.55, "steel_dark")
m.part("trigger", (0.0, -1.7, -7.95))
m.cbox("trigger", (0.0, -1.9, -7.95), (0.2, 0.45, 0.2), "steel", group="trigger", rotation=(-22.5, 0, 0))

# pistol grip
m.cbox("grip", (0.0, -2.7, -6.55), (0.9, 2.0, 1.15), "bakelite_red", rotation=(-22.5, 0, 0))
m.cbox("grip_cap", (0.0, -3.7, -6.15), (1.0, 0.18, 1.1), "steel_dark", rotation=(-22.5, 0, 0))
m.cbox("grip_screw_r", (0.47, -3.3, -6.3), (0.1, 0.22, 0.22), "steel")
m.cbox("grip_screw_l", (-0.47, -3.3, -6.3), (0.1, 0.22, 0.22), "steel")

# ---------------------------------------------------------------- front end
B("upper_hg", -0.46, 0.46, -0.8, -0.05, 10.3, 13.2, "wood_light")
B("lower_hg", -0.55, 0.55, -1.9, -0.72, 10.5, 13.2, "wood")
for i, d in enumerate((11.0, 11.45, 11.9, 12.35)):
    S(f"hg_groove{i}", 0.55, 0.6, -1.75, -1.05, d, d + 0.1, "wood_dark")
B("hg_ring", -0.6, 0.6, -1.95, 0.0, 13.15, 13.5, "steel_dark")
B("gas_block", -0.4, 0.4, -1.4, -0.25, 13.55, 14.4, "steel_dark")
B("gas_swivel", -0.05, 0.05, -1.7, -1.4, 13.95, 14.25, "steel")
B("gas_swivel_ring", -0.03, 0.03, -1.95, -1.7, 13.9, 14.3, "steel_dark")
B("cleaning_rod", -0.07, 0.07, -1.4, -1.25, 14.3, 14.9, "steel")
m.cylinder_z("barrel", (0.0, -0.95), 0.28, -15.45, -13.1, "steel")
m.cylinder_z("muzzle_nut", (0.0, -0.95), 0.37, -15.2, -15.0, "steel_dark")
m.cylinder_z("brake", (0.0, -0.95), 0.33, -15.2, -15.65, "parkerized")
B("brake_low", -0.3, 0.3, -1.27, -0.95, 15.2, 16.0, "parkerized")
B("brake_up", -0.3, 0.3, -0.95, -0.64, 15.2, 15.6, "parkerized")
m.cbox("brake_slant", (0.0, -0.78, -15.85), (0.56, 0.2, 0.55), "steel_dark", rotation=(22.5, 0, 0))
B("brake_slot", -0.08, 0.08, -0.64, -0.6, 15.3, 15.55, "steel_dark")
# front sight (post + ears)
B("fs_base", -0.3, 0.3, -0.3, 0.02, 13.8, 14.5, "steel_dark")
B("fs_post", -0.08, 0.08, 0.0, 0.4, 14.1, 14.3, "steel_dark")
S("fs_ear", 0.21, 0.28, 0.0, 0.32, 14.0, 14.4, "steel_dark")

# rear sight (tangent)
B("rs_base", -0.47, 0.47, -0.45, 0.15, 9.1, 10.3, "steel")
B("rs_leaf", -0.3, 0.3, 0.15, 0.3, 8.5, 9.95, "steel_dark")
S("rs_ear", 0.12, 0.28, 0.28, 0.5, 8.5, 8.9, "steel_dark")
B("rs_slider", -0.35, 0.35, 0.1, 0.34, 9.5, 9.8, "steel")

# ---------------------------------------------------------------- magazine (curved, moving)
m.part("magazine", (0.0, -1.7, -10.1))
seg_dc = (9.4, 9.6, 10.0, 10.6, 11.3)
for k, dc in enumerate(seg_dc):
    yt = -1.65 - 0.9 * k
    hw = 0.40 if k % 2 == 0 else 0.42
    B(f"mag_seg{k}", -hw, hw, yt - 0.95, yt, dc - 0.72, dc + 0.72, "mag_steel", group="magazine")
    yc = yt - 0.47
    S(f"mag_rib{k}", hw - 0.01, hw + 0.05, yc - 0.06, yc + 0.06, dc - 0.55, dc + 0.55, "gunmetal", group="magazine")
B("mag_base", -0.46, 0.46, -6.3, -6.15, 10.5, 12.1, "steel_dark", group="magazine")
B("mag_lug_rear", -0.2, 0.2, -1.85, -1.55, 8.55, 8.7, "steel_dark", group="magazine")
B("mag_lug_front", -0.2, 0.2, -1.85, -1.55, 10.1, 10.3, "steel_dark", group="magazine")

# ---------------------------------------------------------------- bolt carrier + charging handle (moving)
m.part("bolt", (0.6, -0.7, -7.4))
B("bolt_carrier", 0.54, 0.64, -0.85, -0.55, 6.4, 8.2, "gunmetal", group="bolt")
B("handle_stalk", 0.64, 1.0, -0.76, -0.62, 7.3, 7.6, "steel", group="bolt")
B("handle_knob", 1.0, 1.3, -0.95, -0.45, 7.15, 7.75, "steel_dark", group="bolt")

# ---------------------------------------------------------------- points + placement
m.point("grip", (0.0, -2.7, -6.55))
m.point("support", (0.0, -1.55, -11.4))
m.point("sight_rear", (0.0, 0.4, -8.7))
m.point("sight_front", (0.0, 0.4, -14.2))
m.point("muzzle", (0.0, -0.95, -16.0))

m.casing((0.58, -0.6, -7.4))   # ejection port, right side of the receiver (local build space)
OFF = m.place_gun_at_hip()
m.muzzle_flash()
m.build_arms()


def P(p):
    return v_add(p, OFF)


m.standard_animations(fire_interval=0.2, kick=0.8, climb=3.5, roll=1.2, casing=True, bolt="bolt", bolt_travel=1.8, eye_relief=5.0)

MAG_PT = P((0.0, -4.6, -10.3))
HANDLE_PT = P((1.15, -0.7, -7.45))
Z3 = (0.0, 0.0, 0.0)


def reload_seq(a):
    """Rock-in AK reload, 2.85 s: tilt, left hand takes the mag, rocks it out, fetches a new one,
    hooks it in at the front and rocks it back."""
    cant_r, cant_p = (10.0, 36.0, -6.0), (1.2, 3.0, -1.2)
    a.ease("gun", 0.0, 0.35, rot0=Z3, rot1=cant_r, pos0=Z3, pos1=cant_p)
    a.key("gun", 2.15, rot=cant_r, pos=cant_p)
    a.key("gun", 2.32, rot=cant_r, pos=(cant_p[0], cant_p[1] - 0.4, cant_p[2]))
    a.key("gun", 2.4, rot=cant_r, pos=cant_p)
    a.ease("gun", 2.4, 2.85, rot0=cant_r, rot1=Z3, pos0=cant_p, pos1=Z3)

    a.key("magazine", 0.0, rot=Z3, pos=Z3)
    a.ease("magazine", 0.4, 0.65, rot0=Z3, rot1=(26, 0, 0), pos0=Z3, pos1=Z3)
    a.ease("magazine", 0.65, 1.05, rot0=(26, 0, 0), rot1=(40, 0, 12), pos0=Z3, pos1=(-7, -9, 0.8), curve="in")
    a.key("magazine", 0.0, scale=1.0)
    a.key("magazine", 1.05, scale=1.0)
    a.key("magazine", 1.06, scale=0.0)
    a.key("magazine", 1.44, scale=0.0)
    a.key("magazine", 1.45, scale=1.0)
    a.ease("magazine", 1.45, 2.05, rot0=(40, 0, 12), rot1=(26, 0, 0), pos0=(-7, -9, 0.8), pos1=(0, -0.4, 0), curve="out")
    a.ease("magazine", 2.05, 2.35, rot0=(26, 0, 0), rot1=Z3, pos0=(0, -0.4, 0), pos1=Z3)
    a.key("magazine", 2.85, rot=Z3, pos=Z3, scale=1.0)

    a.hand("left", 0.0, "support")
    a.hand("left", 0.38, ("bone", "magazine", MAG_PT))
    a.hand("left", 2.4, ("bone", "magazine", MAG_PT))
    a.hand("left", 2.85, "support")


def cycle_seq(a, t0):
    """Charging handle pulled and released by the right hand (0.8 s)."""
    a.hand("right", t0, "grip")
    a.hand("right", t0 + 0.14, ("bone", "bolt", HANDLE_PT))
    a.hand("right", t0 + 0.56, ("bone", "bolt", HANDLE_PT))
    a.hand("right", t0 + 0.8, "grip")
    a.key("bolt", t0, pos=Z3)
    a.key("bolt", t0 + 0.14, pos=Z3)
    a.ease("bolt", t0 + 0.14, t0 + 0.4, pos0=Z3, pos1=(0, 0, 1.8), rot0=Z3, rot1=Z3, curve="smooth")
    a.key("bolt", t0 + 0.46, pos=(0, 0, 1.8), rot=Z3)
    a.ease("bolt", t0 + 0.46, t0 + 0.58, pos0=(0, 0, 1.8), pos1=Z3, rot0=Z3, rot1=Z3, curve="in")
    a.key("bolt", t0 + 0.8, pos=Z3, rot=Z3)
    # little gun jolt when the carrier slams home
    a.key("gun", t0, pos=Z3)
    a.key("gun", t0 + 0.56, pos=Z3)
    a.key("gun", t0 + 0.6, pos=(0, 0.05, 0.15))
    a.key("gun", t0 + 0.72, pos=Z3)
    a.key("gun", t0 + 0.8, pos=Z3)


a = m.anim("reload", 2.85, "once")
reload_seq(a)

a = m.anim("reload_empty", 3.65, "once")
reload_seq(a)
cycle_seq(a, 2.85)

a = m.anim("firearm", 0.8, "once")
cycle_seq(a, 0.0)

# inspect: show the right side (selector, charging handle), the top, then back
a = m.anim("inspect", 3.0, "once")
poses = [
    (0.0, (0, 0, 0), (0, 0, 0)),
    (0.55, (6, -32, 8), (-1.8, 1.0, 0.6)),
    (1.3, (6, -40, 6), (-2.0, 1.2, 0.8)),
    (1.95, (4, 38, -8), (1.0, 1.6, -1.5)),
    (2.4, (4, 34, -6), (1.0, 1.5, -1.5)),
    (3.0, (0, 0, 0), (0, 0, 0)),
]
for (t0, r0, p0), (t1, r1, p1) in zip(poses, poses[1:]):
    a.ease("gun", t0, t1, rot0=r0, rot1=r1, pos0=p0, pos1=p1)
a.key("bolt", 0.0, pos=Z3)
a.key("bolt", 0.7, pos=Z3)
a.ease("bolt", 0.7, 0.92, pos0=Z3, pos1=(0, 0, 1.8), rot0=Z3, rot1=Z3, curve="out")
a.key("bolt", 1.02, pos=(0, 0, 1.8), rot=Z3)
a.ease("bolt", 1.02, 1.12, pos0=(0, 0, 1.8), pos1=Z3, rot0=Z3, rot1=Z3, curve="in")
a.key("bolt", 3.0, pos=Z3, rot=Z3)
a.key("selector", 0.0, rot=Z3)
a.key("selector", 1.35, rot=Z3)
a.ease("selector", 1.35, 1.5, rot0=Z3, rot1=(40, 0, 0), curve="out")
a.ease("selector", 1.7, 1.85, rot0=(40, 0, 0), rot1=Z3, curve="smooth")
a.key("selector", 3.0, rot=Z3)
a.key("trigger", 0.0, rot=Z3)
a.key("trigger", 2.45, rot=Z3)
a.ease("trigger", 2.45, 2.55, rot0=Z3, rot1=(-18, 0, 0))
a.ease("trigger", 2.6, 2.7, rot0=(-18, 0, 0), rot1=Z3)
a.key("trigger", 3.0, rot=Z3)

# trigger squeeze on every shot
for nm in ("shoot", "aiming_shoot"):
    s = m.anims[nm]
    s.key("trigger", 0.0, rot=(-15, 0, 0))
    s.key("trigger", s.length, rot=(-15, 0, 0))

# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail(cant_rot=(10.0, 36.0, -6.0), cant_pos=(1.2, 3.0, -1.2))

m.write(item_name="ak47")
