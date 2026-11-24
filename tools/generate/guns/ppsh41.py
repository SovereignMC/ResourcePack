"""PPSh-41 submachine gun (full wooden stock, perforated shroud, 71-round drum).

1 px = 55 mm. Local origin: bore axis at y = 0, x = 0; z = 0 at the receiver rear, muzzle toward -Z.
Run: python3 tools/generate/guns/ppsh41.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gunlib import GunModel  # noqa: E402

m = GunModel("ppsh41", "PPSh-41")
B = m.box


# ---------------------------------------------------------------- parts / bones
m.part("magazine", (0, -1.6, -3.5))
m.part("bolt", (1.2, 0.25, -3.0))
m.part("trigger", (0, -1.9, -0.2))

# ---------------------------------------------------------------- receiver
m.rod("receiver", 0.95, -4.6, 0.9, "parkerized", ch=0.3)
B("cover_plate", (-0.6, 0.95, -4.2), (0.6, 1.03, -0.3), "gunmetal")
B("cover_latch", (-0.3, 0.95, -0.1), (0.3, 1.15, 0.5), "steel_dark")
B("cover_latch_top", (-0.2, 1.15, 0.0), (0.2, 1.2, 0.4), "steel")
B("hinge_l", (-0.72, 0.95, -4.62), (-0.4, 1.12, -4.4), "steel_dark")
B("hinge_r", (0.4, 0.95, -4.62), (0.72, 1.12, -4.4), "steel_dark")
B("hinge_pin", (-0.8, 1.0, -4.58), (0.8, 1.08, -4.5), "gunmetal")
B("rear_cap", (-0.8, -0.75, 0.9), (0.8, 0.75, 1.3), "steel_dark")
B("rear_cap_pin", (-0.15, -0.15, 1.3), (0.15, 0.15, 1.38), "gunmetal")
# cocking slot (right) + safety catch
B("bolt_slot", (0.94, 0.08, -3.45), (0.98, 0.42, -0.85), "steel_dark")
B("safety_base", (0.94, 0.0, -0.8), (1.02, 0.5, -0.45), "steel_dark")
B("safety_catch", (1.02, 0.12, -0.75), (1.3, 0.38, -0.5), "gunmetal")
# rivets
for i, z in enumerate((-4.2, -3.2, -2.2, -1.2, -0.2)):
    B(f"rivet_r{i}", (0.95, -0.5, z - 0.07), (1.01, -0.36, z + 0.07), "gunmetal")
    B(f"rivet_l{i}", (-1.01, -0.5, z - 0.07), (-0.95, -0.36, z + 0.07), "gunmetal")
# ejection port on the left? (PPSh ejects right-up through the receiver cut): dark inset at top-right
B("eject_cut", (0.2, 0.96, -2.7), (0.58, 1.0, -1.6), "steel_dark")

# ---------------------------------------------------------------- barrel shroud
m.rod("shroud", 0.8, -8.7, -4.9, "parkerized", ch=0.25)
m.rod("collar_rear", 0.9, -4.9, -4.6, "steel_dark", ch=0.3)
m.rod("collar_front", 0.9, -9.0, -8.7, "steel_dark", ch=0.3)
m.rod("collar_mid", 0.86, -6.95, -6.75, "steel_dark", ch=0.28)
for k in range(6):
    z0 = -5.15 - 0.6 * k
    z1 = z0 - 0.36
    for sgn, (xa, xb) in ((1, (0.8, 0.83)), (-1, (-0.83, -0.8))):
        for row, yc in enumerate((0.3, -0.3)):
            sh = 0.3 if row else 0.0
            if k == 5 and row:
                continue
            B(f"slot_{sgn}_{row}_{k}", (xa, yc - 0.14, z1 - sh), (xb, yc + 0.14, z0 - sh), "steel_dark")
    B(f"slot_top_{k}", (-0.14, 0.8, z1), (0.14, 0.83, z0), "steel_dark")
# muzzle brake / compensator
m.rod("comp", 0.85, -9.55, -9.0, "steel_dark", ch=0.25)
B("comp_lip", (-0.8, 0.6, -9.95), (0.8, 0.77, -9.5), "gunmetal", rotation=(22.5, 0, 0))
B("comp_cheek_l", (-0.85, -0.45, -9.8), (-0.68, 0.45, -9.55), "gunmetal")
B("comp_cheek_r", (0.68, -0.45, -9.8), (0.85, 0.45, -9.55), "gunmetal")
B("comp_bottom", (-0.6, -0.85, -9.7), (0.6, -0.62, -9.55), "gunmetal")
B("bore", (-0.22, -0.22, -9.575), (0.22, 0.22, -9.555), "steel_dark")

# ---------------------------------------------------------------- sights
B("rs_base", (-0.55, 1.02, -4.25), (0.55, 1.15, -3.75), "steel")
B("rs_bar", (-0.45, 1.15, -4.1), (0.45, 1.28, -3.95), "steel_dark")
B("rs_post_l", (-0.45, 1.28, -4.1), (-0.12, 1.75, -3.95), "steel_dark")
B("rs_post_r", (0.12, 1.28, -4.1), (0.45, 1.75, -3.95), "steel_dark")
B("rs_ear_l", (-0.68, 1.15, -4.3), (-0.55, 1.6, -3.85), "steel")
B("rs_ear_r", (0.55, 1.15, -4.3), (0.68, 1.6, -3.85), "steel")
B("rs_screw", (-0.1, 1.15, -3.78), (0.1, 1.22, -3.72), "gunmetal")
B("fs_base", (-0.35, 0.9, -8.95), (0.35, 1.05, -8.5), "steel")
B("fs_post", (-0.07, 1.05, -8.8), (0.07, 1.45, -8.7), "steel_dark")
B("fs_hood_l", (-0.4, 1.05, -9.0), (-0.27, 1.65, -8.5), "steel")
B("fs_hood_r", (0.27, 1.05, -9.0), (0.4, 1.65, -8.5), "steel")
B("fs_hood_top", (-0.4, 1.58, -9.0), (0.4, 1.68, -8.5), "steel")

# ---------------------------------------------------------------- stock
B("stock_fore", (-0.82, -1.8, -1.3), (0.82, -0.2, 0.7), "birch")
B("stock_wrist", (-0.6, -1.5, 0.7), (0.6, -0.22, 2.8), "birch")
B("stock_a", (-0.65, -1.85, 2.8), (0.65, -0.3, 3.8), "birch")
B("stock_b", (-0.72, -2.3, 3.8), (0.72, -0.45, 4.8), "birch")
B("stock_c", (-0.8, -2.95, 4.8), (0.8, -0.6, 5.4), "birch")
B("butt_plate", (-0.85, -3.05, 5.4), (0.85, -0.55, 5.55), "steel_dark")
B("butt_screw_t", (-0.2, -1.15, 5.55), (0.2, -0.85, 5.6), "gunmetal")
B("butt_screw_b", (-0.2, -2.7, 5.55), (0.2, -2.4, 5.6), "gunmetal")
B("fore_band", (-0.86, -1.85, -1.4), (0.86, -0.15, -1.2), "steel_dark")
B("wrist_band", (-0.66, -1.55, 2.0), (0.66, -0.18, 2.12), "steel_dark")
B("grain_l", (-0.64, -1.4, 0.9), (-0.6, -0.5, 2.6), "wood")
B("grain_r", (0.6, -1.4, 0.9), (0.64, -0.5, 2.6), "wood")
B("stock_inlay_l", (-0.76, -2.1, 3.9), (-0.7, -0.6, 4.75), "wood_light")
B("stock_inlay_r", (0.7, -2.1, 3.9), (0.76, -0.6, 4.75), "wood_light")
B("sling_rear", (-0.76, -1.5, 3.0), (-0.62, -1.2, 3.35), "gunmetal")
B("sling_rear_ring", (-0.92, -1.55, 2.95), (-0.76, -1.15, 3.4), "steel")
B("sling_front", (-0.98, -0.1, -4.95), (-0.88, 0.12, -4.7), "gunmetal")
B("sling_front_ring", (-1.2, -0.18, -4.98), (-0.98, 0.2, -4.68), "steel")
B("sling_butt", (-0.12, -3.1, 4.9), (0.12, -2.9, 5.3), "gunmetal")

# ---------------------------------------------------------------- trigger guard, trigger, selector
B("tg_front", (-0.2, -2.8, -1.2), (0.2, -1.8, -1.0), "steel_dark")
B("tg_bottom", (-0.2, -2.8, -1.2), (0.2, -2.6, 0.8), "steel_dark")
B("tg_rear", (-0.2, -2.8, 0.6), (0.2, -1.8, 0.8), "steel_dark")
B("selector", (-0.1, -2.35, -0.95), (0.1, -1.8, -0.7), "gunmetal")
B("selector_knob", (-0.16, -2.45, -0.99), (0.16, -2.3, -0.66), "steel")
B("trig_blade", (-0.12, -2.45, -0.32), (0.12, -1.8, -0.14), "steel_dark", group="trigger")
B("trig_hook", (-0.12, -2.5, -0.44), (0.12, -2.2, -0.3), "steel_dark", group="trigger")

# ---------------------------------------------------------------- drum magazine
B("magwell", (-0.85, -1.75, -4.4), (0.85, -0.9, -2.6), "steel_dark")
B("magwell_catch", (-0.25, -1.7, -4.55), (0.25, -1.3, -4.4), "gunmetal")
B("magwell_rail_l", (-0.9, -1.5, -4.0), (-0.82, -1.0, -3.0), "steel")
B("magwell_rail_r", (0.82, -1.5, -4.0), (0.9, -1.0, -3.0), "steel")
DY, DZ = -3.5, -3.5
for k, (R, x0, x1, mat) in enumerate(((1.85, -0.7, 0.7, "parkerized"),)):
    w = R * 0.416
    for i, (hy, hz, rot) in enumerate(((R, w, 0), (w, R, 0), (R, w, 45), (w, R, 45))):
        e = 0.014 * i
        B(f"drum_{i}", (-0.7 + e, DY - hy, DZ - hz), (0.7 - e, DY + hy, DZ + hz), mat, group="magazine",
          rotation=(rot, 0, 0) if rot else None, origin=(0, DY, DZ) if rot else None)
B("drum_neck", (-0.5, -1.95, -3.9), (0.5, -1.2, -3.1), "steel_dark", group="magazine")
m.ring_x("drum_plate_r", DY, DZ, 1.5, 0.7, 0.77, "steel", "magazine", 0)
m.ring_x("drum_plate_l", DY, DZ, 1.5, -0.7, -0.77, "steel", "magazine", 0)
m.ring_x("drum_cap_r", DY, DZ, 0.95, 0.77, 0.82, "gunmetal", "magazine", 0)
B("drum_hub_a", (0.82, DY - 0.42, DZ - 0.17), (0.98, DY + 0.42, DZ + 0.17), "steel_dark", group="magazine")
B("drum_hub_b", (0.82, DY - 0.17, DZ - 0.42), (0.98, DY + 0.17, DZ + 0.42), "steel_dark", group="magazine")
B("drum_key", (0.98, DY - 0.18, DZ - 0.8), (1.14, DY + 0.18, DZ + 0.8), "steel", group="magazine")
B("drum_key_tip", (0.98, DY - 0.3, DZ + 0.6), (1.14, DY + 0.3, DZ + 0.85), "steel", group="magazine")
for i, (dy, dz) in enumerate(((1.2, 0.0), (-1.2, 0.0), (0.0, 1.2), (0.0, -1.2),
                              (0.85, 0.85), (-0.85, 0.85), (0.85, -0.85), (-0.85, -0.85))):
    B(f"drum_rivet_{i}", (0.77, DY + dy - 0.08, DZ + dz - 0.08), (0.83, DY + dy + 0.08, DZ + dz + 0.08),
      "gunmetal", group="magazine")

# ---------------------------------------------------------------- bolt handle (right side)
B("bolt_stem", (0.9, 0.12, -3.2), (1.5, 0.38, -2.95), "steel_dark", group="bolt")
B("bolt_knob", (1.5, -0.05, -3.3), (1.85, 0.55, -2.85), "steel", group="bolt")
B("bolt_knob_tip", (1.85, 0.05, -3.2), (1.95, 0.45, -2.95), "gunmetal", group="bolt")

# ---------------------------------------------------------------- points + placement
m.point("grip", (0, -1.4, 1.6))
m.point("support", (-1.0, -3.2, -3.5))
m.point("sight_rear", (0, 1.45, -4.03))
m.point("sight_front", (0, 1.45, -8.75))
m.point("muzzle", (0, 0, -9.95))

m.casing((0.45, 1.0, -2.15))   # ejection port, right side of the receiver (local build space)
OFS = m.place_gun_at_hip()
m.muzzle_flash(size=2.2)
m.build_arms()
m.standard_animations(fire_interval=0.1, kick=0.4, climb=1.8, roll=0.6, casing=True, bolt="bolt", bolt_travel=1.0, eye_relief=5.0,
                      ads_kick_scale=0.5)


def P(x, y, z):
    return (x + OFS[0], y + OFS[1], z + OFS[2])


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


DRUM_SIDE = P(-1.0, -3.2, -3.5)    # left face of the drum (left hand)
DRUM_BOTTOM = P(0.0, -5.5, -3.5)   # underside of the drum (slap)
CATCH = P(0.0, -1.5, -4.5)         # drum catch on the magwell front
KNOB = P(1.7, 0.25, -3.1)          # bolt handle knob
PULL = (0.5, -0.9, 1.1)            # gun drawn toward the shoulder for the bolt handle
FETCH = (-4.5, -12.5, -6.5)        # off-screen, down-left


def bolt_cycle(a, t0, back=1.9):
    """Right hand to the handle, pull back, release, back to the grip. 1.0 s long."""
    a.hand("right", t0, "grip")
    a.hand("right", t0 + 0.12, ("bone", "bolt", KNOB))
    a.ease("bolt", t0 + 0.12, t0 + 0.55, pos0=(0, 0, 0), pos1=(0, 0, back), curve="smooth")
    a.key("bolt", t0 + 0.7, pos=(0, 0, back))
    a.hand("right", t0 + 0.7, ("bone", "bolt", KNOB))
    a.ease("bolt", t0 + 0.7, t0 + 0.82, pos0=(0, 0, back), pos1=(0, 0, 0), curve="in")
    a.hand("right", t0 + 0.82, ("bone", "bolt", KNOB))
    a.hand("right", t0 + 1.0, "grip")


# ---------------------------------------------------------------- reload (5.2 s)
def reload_anim(name, length, bolt_after):
    a = m.anim(name, length, "once")
    T = ((6, 4, -10), (-1.1, 0.5, 2.1))     # canted up so the drum and left hand are on screen
    T2 = ((6, 3, -9), (-1.1, 0.4, 2.1))
    a.key("gun", 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
    a.ease("gun", 0.0, 0.7, rot0=(0, 0, 0), rot1=T[0], pos0=(0, 0, 0), pos1=T[1])
    a.key("gun", 2.3, rot=T[0], pos=T[1])
    a.ease("gun", 2.3, 3.2, rot0=T[0], rot1=T2[0], pos0=T[1], pos1=T2[1])
    a.key("gun", 3.9, rot=T2[0], pos=T2[1])
    a.ease("gun", 3.9, 4.4, rot0=T2[0], rot1=(2, 0, -6), pos0=T2[1], pos1=(0, 0.4, 0.2))
    if bolt_after:
        # gun is drawn in toward the shoulder while the right hand reaches the bolt handle
        a.ease("gun", 4.4, 4.95, rot0=(2, 0, -6), rot1=(0, 0, 0), pos0=(0, 0.4, 0.2), pos1=PULL)
        a.key("gun", 5.75, rot=(0, 0, 0), pos=PULL)
        a.ease("gun", 5.75, 6.1, rot0=(0, 0, 0), rot1=(0, 0, 0), pos0=PULL, pos1=(0, 0, 0))
    else:
        a.ease("gun", 4.4, 5.2, rot0=(2, 0, -6), rot1=(0, 0, 0), pos0=(0, 0.4, 0.2), pos1=(0, 0, 0))
    # left hand
    a.hand("left", 0.0, "support")
    a.hand("left", 0.7, ("bone", "magazine", CATCH))
    a.hand("left", 0.95, ("bone", "magazine", CATCH))
    a.hand("left", 1.2, ("bone", "magazine", DRUM_SIDE))
    a.hand("left", 2.4, ("bone", "magazine", DRUM_SIDE))
    a.hand("left", 2.9, FETCH)
    a.hand("left", 3.2, FETCH)
    a.hand("left", 3.9, ("bone", "magazine", DRUM_SIDE))
    a.hand("left", 4.1, ("bone", "magazine", DRUM_BOTTOM))
    a.hand("left", 4.4, ("bone", "magazine", DRUM_BOTTOM))
    a.hand("left", 5.2, "support")
    # drum: catch click, pulled down and away, off-screen, new drum appears at the fetching hand
    a.key("magazine", 0.0, pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0)
    a.key("magazine", 0.95, pos=(0, 0, 0), rot=(0, 0, 0))
    a.ease("magazine", 0.95, 1.2, pos0=(0, 0, 0), pos1=(0, -0.3, 0), curve="out")
    a.ease("magazine", 1.2, 1.9, pos0=(0, -0.3, 0), pos1=(-1.0, -3.2, 0.8), rot0=(0, 0, 0), rot1=(0, 0, -12),
           curve="smooth")
    a.ease("magazine", 1.9, 2.4, pos0=(-1.0, -3.2, 0.8), pos1=(-3.0, -6.5, 1.0), rot0=(0, 0, -12),
           rot1=(0, 0, -25), curve="in")
    a.key("magazine", 2.4, scale=1.0)
    a.key("magazine", 2.41, scale=0.0)
    a.key("magazine", 3.19, scale=0.0)
    carry0 = sub(FETCH, DRUM_SIDE)  # hand holds the drum at its left face
    carry0 = tuple(carry0[i] for i in range(3))
    a.key("magazine", 3.2, scale=1.0, pos=carry0, rot=(0, 0, -15))
    seat0 = (0.0, -3.0, 0.4)
    a.ease("magazine", 3.2, 3.9, pos0=carry0, pos1=seat0, rot0=(0, 0, -15), rot1=(0, 0, 0), curve="smooth")
    a.key("magazine", 4.1, pos=(0.0, -2.9, 0.3), rot=(0, 0, 0))
    a.ease("magazine", 4.1, 4.28, pos0=(0.0, -2.9, 0.3), pos1=(0, 0.12, 0), curve="in")
    a.ease("magazine", 4.28, 4.4, pos0=(0, 0.12, 0), pos1=(0, 0, 0), curve="out")
    a.key("magazine", 5.2, pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0)
    # right hand stays on the grip
    if bolt_after:
        a.hand("right", 0.0, "grip")
        bolt_cycle(a, 4.9, back=1.9)
    return a


reload_anim("reload", 5.2, False)
reload_anim("reload_empty", 6.1, True)

# ---------------------------------------------------------------- inspect (3.2 s)
a = m.anim("inspect", 3.2, "once")
a.ease("gun", 0.0, 0.5, rot0=(0, 0, 0), rot1=(-4, -20, 4), pos0=(0, 0, 0), pos1=(-1.2, 0.8, 1.2))
a.ease("gun", 0.5, 1.4, rot0=(-4, -20, 4), rot1=(-6, -48, 8), pos0=(-1.2, 0.8, 1.2), pos1=(-2.2, 1.0, 1.6))
a.ease("gun", 1.4, 1.7, rot0=(-6, -48, 8), rot1=(-6, -48, 8), pos0=(-2.2, 1.0, 1.6), pos1=(-2.2, 1.0, 1.6))
a.ease("gun", 1.7, 2.4, rot0=(-6, -48, 8), rot1=(20, -15, 0), pos0=(-2.2, 1.0, 1.6), pos1=(-0.9, 0.5, 1.8))
a.ease("gun", 2.4, 2.6, rot0=(20, -15, 0), rot1=(20, -15, 0), pos0=(-0.9, 0.5, 1.8), pos1=(-0.9, 0.5, 1.8))
a.ease("gun", 2.6, 3.2, rot0=(20, -15, 0), rot1=(0, 0, 0), pos0=(-0.9, 0.5, 1.8), pos1=(0, 0, 0))
# left hand lets go of the support point briefly toward the drum while it turns
a.hand("left", 0.0, "support")
a.hand("left", 3.2, "support")
a.hand("right", 0.0, "grip")
a.hand("right", 3.2, "grip")

# ---------------------------------------------------------------- firearm (bolt handle pulled back, 1.0 s)
a = m.anim("firearm", 1.0, "once")
a.key("bolt", 0.0, pos=(0, 0, 0))
a.ease("bolt", 0.1, 0.65, pos0=(0, 0, 0), pos1=(0, 0, 1.9), curve="smooth")
a.key("bolt", 0.75, pos=(0, 0, 1.9))
a.ease("bolt", 0.75, 0.9, pos0=(0, 0, 1.9), pos1=(0, 0, 0), curve="in")
a.key("bolt", 1.0, pos=(0, 0, 0))
a.hand("right", 0.0, "grip")
a.hand("right", 0.12, ("bone", "bolt", KNOB))
a.hand("right", 0.75, ("bone", "bolt", KNOB))
a.hand("right", 0.9, ("bone", "bolt", KNOB))
a.hand("right", 1.0, "grip")
a.key("gun", 0.0, rot=(0, 0, 0), pos=(0, 0, 0))
a.ease("gun", 0.0, 0.12, rot0=(0, 0, 0), rot1=(1, 4, -3), pos0=(0, 0, 0), pos1=PULL)
a.key("gun", 0.9, rot=(1, 4, -3), pos=PULL)
a.ease("gun", 0.9, 1.0, rot0=(1, 4, -3), rot1=(0, 0, 0), pos0=PULL, pos1=(0, 0, 0))

# reload with no magazine in the inventory (shared "pat the pouch" beat, see GunModel.reload_fail)
m.reload_fail()

m.write(item_name="ppsh_41")
print("OFS", OFS, "ads", m.flags["ads"])
