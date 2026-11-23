# Gun generators

One script per gun, `tools/generate/guns/<gun>.py`, built on `gunlib.py`. Run from anywhere:

```bash
python3 tools/generate/guns/ak47.py
```

Each script writes:

| Output | Used by |
|---|---|
| `assets/weapons/{models,textures}/item/objmc/<id>` | first-person sgvm viewmodel incl. skin-texel arm quads (see `viewmodel_bake.py`) |
| `tools/generate/guns/objmc_arm_slots.json` | arm tint slot -> skin pixel table, also copied to `../SovereignGuns` resources |
| `tools/generate/guns/objmc_animations.json` | animation table (frames/loop/length) also copied to `../SovereignGuns` resources |
| `assets/weapons/models/item/<item>.json` | vanilla item model (GUI, ground, third person, frames) |
| `assets/weapons/textures/item/gun/<id>.png` | shared texture of both |
| `tools/generate/guns/preview/<id>_*.png` | offline renders (gitignored) |

Do not hand-edit the outputs; change the script and re-run it.

## Space and scale

- 1 unit = 1 px = 1/16 block. **Scale: 1 px = 55 mm** of the real gun (AK-47 880 mm → 16 px).
- Camera (eye) at the origin, looking **-Z**; **+X = screen right**, **+Y = up**.
- Build the gun muzzle toward -Z, bore along Z, the gun's own right side at +X. It is easiest
  to build around a local origin (e.g. receiver top-rear at `(0,0,0)`) and then call
  `m.place_gun_at_hip()` once (after defining the points). It returns the offset
  (`local point + offset = viewmodel point`, also `m.flags["place_offset"]`).
- Rotations: right-handed degrees, Euler ZYX (Blockbench convention). `+X` tips the muzzle up,
  `+Z` rolls the top of the gun toward -X (screen left). A right-side bolt handle swings UP
  with a positive Z rotation of the bolt bone about the bore axis (e.g. `rot=(0, 0, 70)`).

## Rig standard

```
viewmodel > gun > <parts...>, muzzle > glow_flash
viewmodel > pra_right_arm > prfa_right_forearm > pri_right_item   (skin arms, IK-solved)
viewmodel > pla_left_arm  > plfa_left_forearm  > pli_left_item
camera
```

- Moving parts: `m.part("magazine", pivot)`, `m.part("bolt", pivot)`, ... then put cubes in
  them with `group="magazine"`. Bone names must not start with a BetterModel tag token plus
  `_` (`b_ h_ hi_ p_ sp_ tag_ glow_ li_ ri_ ph_ pra_ pla_ ...`); `bolt`, `magazine`,
  `charging_handle`, `drum`, `dust_cover`, `trigger`, `ejector` are fine.
- Required points (rest space, before or after `place_gun`; `place_gun` moves them):
  `grip` (right hand), `support` (left hand), `sight_rear` + `sight_front` (line of sight; for a
  scope, the eyepiece centre and the objective centre; **must have equal x and y**), `muzzle`.
- **Hip pose (standard):** `m.place_gun_at_hip(nudge=(0,0,0))` puts `grip` at `HIP_GRIP =
  (3.2, -4.8, -8.5)` (+ an optional small, commented nudge) and gives the `gun` bone the rest
  rotation `(0, HIP_YAW, 0)` with `HIP_YAW = 6` degrees about +Y (muzzle toward screen centre).
  `place_gun()` also sets the `gun` bone origin to the placed `grip`: **the gun always pivots at the
  grip**, never set `m.gun.origin` yourself. Script keys on `gun` are offsets about that pivot.
  Check `<id>_fp_hip_ads.png`: gun in the lower right, both hands visible on it, muzzle pointing
  toward the crosshair area. `write()` prints a warning if an arm has to reach more than 11 px in
  an animation (the IK clamps at 11.1); keep hand targets near the gun or the shoulders.
- **Shoulders:** `build_arms()` defaults: right `(5.5,-9.5,-3.0)`, left = rest support point +
  9.5 * norm(-0.55,-0.60,0.58), both pushed below the view if they would be on screen (70 deg
  vertical FOV, 16:9). `right_shoulder=` / `left_shoulder=` are optional overrides; avoid them.
  Targets: rest hand distance left <= 10.3, right <= 9.5, stock rear z <= -1.5.
- **ADS:** `standard_animations(eye_relief=...)` cancels the hip yaw (keys `gun` rotation
  `(0, -HIP_YAW, 0)` in `aiming` / `aiming_shoot`; do not key `gun` rotation there) and moves the rear sight to `(0, 0, -eye_relief)`.
  Iron sights: 4.5–6. Scopes: put the eyepiece 2.5–3.5 px in front of the eye. In the ADS
  preview the front post (or reticle centre) must sit on the crosshair.

## Geometry quality

- **60–150 cubes in the gun** (arms and flash do not count). Spend them on the silhouette and
  what the player sees in first person: receiver shape, sights, handguard, magazine, grip,
  muzzle device, charging handle, trigger guard, selector, rivets/screws, sling swivels.
- Layer parts (a handguard is proud of the barrel, a dust cover sits on the receiver,
  rivets 0.05–0.1 proud). Never let two cubes share a coplanar face with overlap: offset by
  ≥ 0.02 or let one penetrate. `write()` runs `deconflict()`, which pushes the smaller of two coplanar
  overlapping faces (same bone, axis-aligned cubes) 0.02 proud automatically.
- Cube rotations: prefer single-axis multiples of 22.5° (vanilla item models only allow
  -45/-22.5/0/22.5/45 on one axis; other rotations are snapped in the item model with a
  warning). The `gun` bone carries the hip yaw rest rotation; the item model ignores it (it is built in
  gun-local space), but bones below `gun` must not have rest rotations. Curves (AK magazine, stock drop) are
  stepped cubes or 22.5° pieces.
- `m.cylinder_z(name, (x, y), radius, z0, z1, material)` makes a round bar along Z: a real
  octagon (apothem = radius, 4 cubes) for radius >= 0.4, a 2-cube chamfered bar below.
  `m.octa(...)`, `m.rod(name, R, z0, z1, mat, ch=)` (chamfered square bar) and
  `m.ring_x(...)` (disc about X) are available directly. Watch the 150-cube budget.
- Textures are always exactly 128x128. The packer tries texel density 4, 3.5, 3, 2.5, 2 for the
  whole gun until the faces fit (`write()` prints the density used).
- Materials: see `MATERIALS` in `gunlib.py`. A script may add its own:
  `gunlib.MATERIALS["bakelite_red"] = gunlib.Material("#7a2a16", "polymer")`.
  Cubes named `*_core` have no special meaning; muzzle flash uses the `flash` material.

## Animations

Use these names (KBAnimation channels, read by the SovereignGuns plugin):

| Name | Loop | Notes |
|---|---|---|
| `equip`, `unequip`, `standing`, `sprint`, `aiming`, `shoot`, `aiming_shoot` | from `standard_animations(...)` | pass `fire_interval`, `kick`, `climb`, `bolt`, `bolt_travel`, `eye_relief` |
| `reload` | once | length = WeaponMechanics `Reload_Duration` / 20 s |
| `reload_empty` | once | optional: reload + charging handle / bolt release |
| `inspect` | once | ~2.5–3.5 s, show the gun off |
| `firearm` | once | bolt / charging handle cycle; length = (Open.Time + Close.Time) / 20 s |

- Every channel value is relative to the rest pose (hip). `a.key(bone, t, rot=, pos=, scale=)`
  sets a key; `a.ease(bone, t0, t1, rot0=, rot1=, pos0=, pos1=, curve=)` expands eased motion
  into dense linear keys (`smooth`, `in`, `out`, `back`, `linear`). Hold a pose by keying the
  same value at both ends.
- Hands: `a.hand("left", t, target)` with `"grip"`, `"support"`, `("bone", "magazine", point)`
  (a rest-space point carried by that bone, in viewmodel coordinates **after** `place_gun`:
  add the placement offset to a local build point) or a fixed viewmodel point. Arms are IK-solved
  every 0.05 s by `finish()`. Without hand keys a hand stays on `grip` / `support`.
- Hidden bones: `m.part(name, origin, hidden=True)` (the muzzle flash `glow_flash` is one) get
  scale 0 at t=0 in every animation that has no scale channel for them, and are left out of the
  item model and of the static previews.
- If gun keys were tuned about another pivot, `m.repivot_gun_keys()` (call before `write`)
  re-expresses them about the grip so the motion stays the same.
- Check `<id>_anim_<name>.png` (6 frames per animation) for every animation.
