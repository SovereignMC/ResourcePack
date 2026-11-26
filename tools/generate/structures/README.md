# Structure model tools

Pure Python 3 (Pillow + numpy), no Blockbench or BetterModel needed. Run from the repo root.
Conventions: +X east, +Y up, +Z south (north = -Z), 16 px = 1 block, structure origin = ring centre.
Shared contract: the structure styles plan (styles, state animation table, preview font).

| File | Purpose |
|---|---|
| `render.py` | Software renderer for `bbmodels/*.bbmodel` (also a library) |
| `states.py` | Adds the `status` lamps and the 8 state animations to a model |
| `previews.py` | Generates the `sovereignmc:structure_preview` font + manifest (**coordinator only**) |
| `bblib.py`, `bbbuild.py`, `bbmaterials.py`, `industrial_palette.json` | Model editing + construction library (below) |
| `models/` | Build scripts: `industrial_smelter.py` (Builder example), `blocky_smelter_convert.py` (Model editing example) |
| `styles.json` | Style ids, model prefixes and the 17 families (source of truth) |
| `preview_manifest.json` | Generated glyph manifest (copied into StructuresRevamped) |
| `state_overrides/<model name>.json` | Optional per-model overrides for `states.py` |

## render.py

```bash
python3 tools/generate/structures/render.py smelter --view iso_ne --size 256 -o out.png
python3 tools/generate/structures/render.py smelter --sheet -o sheet.png          # 4 iso + top + N/E/S/W
python3 tools/generate/structures/render.py smelter --anim running --frames 6 -o strip.png
python3 tools/generate/structures/render.py smelter --anim needs_input --time 0.25 --view east -o f.png
```

The model argument is a path, a file name in `bbmodels/`, or a bare family name (`smelter` ->
`bbmodels/structure_smelter.bbmodel`; for other styles pass `structure_industrial_smelter`).

* Views: `iso_ne iso_nw iso_se iso_sw` (camera on that corner, 30 deg elevation), `north east south west`
  (camera on that side looking at that face; `north` shows the -Z face), `top` (north up).
* Options: `--ssaa N` supersampling (default 1 = hard nearest-neighbour pixels), `--bg #rrggbb|transparent`
  (single renders are transparent; sheets/strips are grey so lighting is readable).
* `--sheet` uses one common scale for all nine views so sizes are comparable; labels state the viewing side.
  Use it to check "looks finished from every side".
* `--anim NAME --time T` poses bones from the animation (rotation adds to the group rotation, position
  translates, scale scales about the group origin). Interpolation: linear, catmullrom (loop-wrapped), step;
  bezier is rendered as linear (warned). Time wraps for looping animations.
* Library: `render.Model.load(path)`, `model.faces(anim, time)`, `render.fit(points, views, size)`,
  `render.render(model, view, size, scale=, centre=, ssaa=, faces=)`, `render.contact_sheet`, `render.anim_strip`.
  Faces carry `group` (bone name) and `element`.

Supported: cubes (`from/to/inflate`), element rotation (any/multi axis, Euler ZYX about the element origin),
nested groups with origin + rotation, per-face UV (px, any texture size via `uv_width`, flipped UVs, face
`rotation`), several embedded textures, `visibility: false` groups, alpha cut-out (alpha < 8 skipped),
Minecraft face shading (top 1.0, N/S 0.8, E/W 0.6, bottom 0.5, interpolated for rotated faces).

Cannot handle: mesh/locator/null/texture-mesh elements (skipped with a warning; none exist in the 17
structure models), Molang keyframe values (treated as 0, warned), bezier handles, translucent blending
(partially transparent texels are drawn opaque), non-embedded textures, emissive/PBR, per-element
`export:false` / `visible:false` on cubes (all 17 models use neither), BetterModel `scale`
inheritance quirks (scale follows plain parent-matrix composition). Assumption not verified against
Blockbench: keyframe rotation uses the same handedness as a group rotation (the usual Blockbench
behaviour); only the sign of animated rotations could be wrong, never the static pose.

## states.py

```bash
python3 tools/generate/structures/states.py MODEL.bbmodel            # dry run (report only)
python3 tools/generate/structures/states.py MODEL.bbmodel --write    # rewrite in place
python3 tools/generate/structures/states.py MODEL.bbmodel -o out.bbmodel
```

1. `status` group: if missing it is created as a child of `root` (a 2x2 mast, a 6x4x6 housing and a cap
   on the highest point within 12 px of the centre) plus six child bones `lamp_green lamp_amber lamp_red
   lamp_blue lamp_orange lamp_off`, each with 4 lens plates (one per side, so visible from N/E/S/W).
   Lens colours are 1 texel colours written into a free aligned 4x4 block of texture 0 (searched from the
   bottom-right, UV-free with a 1 px margin and transparent); if none is free a second 'status' texture is
   appended. If `status` and all six lamps already exist (hand-made, or from an earlier run) they are used as
   they are; only the texels their lens faces point at are filled with the lamp colour (disable with
   `"paint_lamps": false`, skipped when a face's UV overlaps a non-lamp face).
   Remodelled models may place their own `status` group; keep the six lamp bone names.
2. The motion source is the existing `running` animation, else `idle` (copied to `running` on the first run
   only, with its uuid). Every other state is regenerated from it, so re-running yields an identical file.
3. Animations (all loop, order running, idle, paused, needs_input, output_full, no_power, no_fuel, inactive):

| state | length | motion | lamps (scale keyframes, step) |
|---|---|---|---|
| running | source | source motion untouched | green steady |
| idle | 4x | running motion 4x slower, oscillations at 1/4 amplitude | amber steady |
| paused | 2 s | none | amber blink 1 s on / 1 s off |
| needs_input | 1 s | none; input bones wobble (+-4 deg about Z) | red blink, 0.25 s |
| output_full | 1 s | none; output bones pulse scale 1 -> 1.15 -> 1 | blue blink, 0.5 s |
| no_power | lcm(4x, 4 s) | running motion 4x slower, half amplitude, step interpolation (stutter) | `lamp_off` with a double flicker of `lamp_amber` every cycle |
| no_fuel | 1 s | none | orange blink, 0.5 s |
| inactive | 1 s | none | `lamp_off` steady |

   Closed oscillations (last value == first) are the ones whose amplitude is reduced; "travelling" channels
   (a spinning flywheel 0 -> 360) keep their amplitude and are only slowed, so they still loop seamlessly.
   Bones whose name contains smoke, fire, flame, spark, pour or molten (case-insensitive) get a single scale
   0 keyframe in every state except `running`. Every lamp has a scale keyframe at time 0 in every animation
   (0 when unused), so lamps never overlap. Keyframe uuids are deterministic (uuid5).
4. Keyframes mirror Blockbench's layout: `channel`, `data_points` (string values), `uuid`, `time`, `color`,
   `uniform` (scale only), `interpolation`; animators are keyed by group uuid and exist for every group.
   The file is written minified, exactly like Blockbench writes it.

Override file `tools/generate/structures/state_overrides/<model name>.json` (the bbmodel `name`, e.g.
`smelter`, or the file name without extension), all keys optional, bone names case-insensitive:

```json
{
  "input_bones": ["hopper"],
  "output_bones": ["crate"],
  "hide": ["extra_bone"],
  "idle_visible": ["flames"],
  "lamp_at": [0, 0, 36],
  "full_amplitude": ["held_log"],
  "paint_lamps": true
}
```

`input_bones` / `output_bones` default to bones whose name contains hopper/input/intake/feed/chute resp.
output/crate/pile/outbox; `hide` adds bones to the smoke/fire hiding rule; `idle_visible` keeps listed hidden
bones visible (with the slowed motion) in `idle`; `full_amplitude` bones keep their full amplitude in `idle` / `no_power` (only slowed; use it for
show/hide scale toggles, Builder: `b.full_amplitude([...])`); `lamp_at` = `[x, z, top_y]` of the housing centre and the
height it sits on (only used when `status` is created).

Cannot handle: models without a `root` group get the status group at the top level; animators for Molang
keyframes are copied unchanged in `running` but cannot be scaled in `idle`/`no_power` (left as they are).

## previews.py

```bash
python3 tools/generate/structures/previews.py            # blocky + industrial (missing models are skipped)
```

Renders `iso_ne` of each family (running at t=0 when present, else the rest pose); montage = 6x3 cells of
60x60 with one shared scale per style, hero = 144x144 fitted
per machine. Each image is one PNG cut into a grid of one-line tiles (9 px tall; montage 180 px, hero 144 px
wide) declared by one bitmap provider with a `chars` grid (`\u0000` = empty tile). Why: the client stitches glyphs
into 256x256 pages (wider glyphs show as missing boxes), and a dialog paints line by line, so a glyph taller than
a line is overpainted by panels on later lines. The last column of every tile carries one alpha-1 texel so the glyph
advances exactly width + 1 (a bitmap glyph's advance follows its rightmost non-transparent column). Writes
`assets/sovereignmc/textures/font/structure_preview/*.png`, `assets/sovereignmc/font/structure_preview.json`
(ascent 7, height 9) and `tools/generate/structures/preview_manifest.json` (each tile: char, x, y, width, height).
Output is deterministic and committed, like the gui_skins font. Codepoints: montage `U+E000 + style*0x80 + tile`,
hero `U+E800 + (style*families + family)*32 + tile`; hero codepoints of missing models stay reserved and their tile
list is empty. Re-run after any model change and commit the output.

**Only the coordinator runs `previews.py`** (it writes the shared font, PNGs and manifest). Everyone else may
run `previews.py --check` (writes nothing, exit 1 if the committed output is stale). `states.py` and
`Builder.save()` write only the model file they are given (plus `state_overrides/<name>.json` for a Builder).

## bblib: editing and building models

```python
import sys; sys.path.insert(0, "tools/generate/structures")
from bblib import Model, Builder, industrial_plinth, industrial_status_mast, directionality_report, symmetric_about_center
```

Rotation convention everywhere: `rot` is **clockwise seen from above**, multiples of 90; `rot=90` turns the north
face into the east face (N -> E -> S -> W). Coordinates are model px about the structure centre (0, 0).

### Editing an existing model (`Model`)

| call | what |
|---|---|
| `m = Model.load("smelter")` / `m.save(path=None)` | load / write minified Blockbench JSON, every other field untouched |
| `m.find(name_or_uuid)`, `m.find_all("coal")`, `m.group(name)` | lookup (elements and groups); `find_all` is a case-insensitive substring search |
| `m.elements_in("frame", recursive=True)`, `m.child_groups(g)`, `m.parent_group(x)` | tree queries |
| `m.delete(sel)` | removes elements/groups (children, outliner entries and animators too) |
| `m.translate(sel, dx, dy, dz)` | moves boxes, origins and group pivots |
| `m.scale(sel, f, about=(x,y,z))` | uniform scale of boxes/origins (+ position keyframes of scaled groups); UVs are not changed, so textures stretch slightly |
| `m.resize(element, frm, to)` | set an element's box |
| `m.clone(sel, rot=0, mirror=None, offset=(0,0,0), suffix=None, into=None)` | copy with optional mirror (`"x"`/`"z"`) then Y rotation. Faces and UVs travel with the geometry (N->E ..., up/down get face `rotation`), cube rotation + origin are conjugated, fresh uuids, names get the suffix (`_r90`, `_mx`, ...). Cloned **groups** also copy their animators in every animation (rotation axes/signs, position vectors and scale axes remapped). Returns the new top-level dicts. |
| `m.rotate(sel, rot)` | in place (clone + delete original, names kept) |
| `m.mirror(sel, "x")` | mirrored clone (UVs mirrored so the picture mirrors too) |
| `m.radial4(sel, suffixes)` | original + clones at 90/180/270; returns `[orig, c90, c180, c270]` |
| `symmetric_about_center(model, order=4)` | geometric check of the rest pose (faces + colours); lists the unmatched element names |
| `directionality_report(model)` | renders N/E/S/W unshaded and prints/returns per-side difference scores |
| `m.sheet(path)`, `m.render(view)` | quick renders of the in-memory state |

`directionality_report` scores are 0 = identical. Read `silhouette` first (share of covered pixels that differ in
shape between the side views); `color` is the mean RGB difference over covered pixels. Reference values:
original blocky smelter silhouette 0.44 / color 0.18, converted 0.002 / 0.049, industrial smelter 0 / 0.004
(residual colour is texture noise variants). `python3 tools/generate/structures/bblib.py report MODEL` prints it;
`... bblib.py selftest` checks clone/mirror geometry+UV against the renderer (must report 0 mismatches).

Cloning limits: cube rotations are re-derived exactly (matrix conjugation); animated rotation keyframes are
remapped per axis (exact for single-axis keyframes, approximate for combined ones); Molang keyframe strings are
copied with a sign wrapper only. A cloned group is a child of the same parent as the original unless `into=`.
After cloning, run `states.py` so the state animations include the cloned animators.
Worked example: `models/blocky_smelter_convert.py` (one-shot; reads the git HEAD file).

### Building a model (`Builder`)

```python
b = Builder("industrial_crusher", run_length=4.0)      # name -> bbmodel `name` and state_overrides/<name>.json
industrial_plinth(b)                                    # 32x32 pad, hazard edge, bolted corners; machine starts at y=3.4
b.group("rotor", parent="frame", origin=(0, 20, 0))     # a bone with its pivot
b.cube("body", (-8, 3.4, -8), (8, 12, 8), {"up": "dark_steel", "*": "steel_plate"}, group="frame")
side = b.group("side_n"); ...                           # build one side, then
b.m.radial4([side], ("_e", "_s", "_w"))                 # 4-fold (Model API on b.m); animate AFTER cloning, by clone name
b.spin("rotor", "y", period=2); b.input_bones([...]); b.output_bones([...])
industrial_status_mast(b, 0, 0, base=38.0)              # lamps (optional; default is added at the highest point)
b.sheet("sheet.png"); b.save("bbmodels/structure_industrial_crusher.bbmodel")   # also runs states.py
```

* `b.cube(name, frm, to, mat, group=, rotation=(x,y,z), origin=, hide=(), faces=None, inflate=0)`; `mat` is a
  material name or a dict `{"up": m, "down": m, "side": m, "north": m, "*": m}`. Faces in `hide` get no texels
  (not drawn); the bottom face of cubes at y<=0 is dropped automatically. Every face gets its own texels at 1 px
  = 1 texel (identical size/material/variant tiles are shared), packed by a shelf packer into the 256x256 atlas;
  noise is seeded from the builder name, `variants` (default 3) different noise tiles per material/size.
  `AtlasFull` is raised if it does not fit (reduce detail/variants, use `hide`).
* Materials (`bbmaterials.MATERIALS`, colours only from `industrial_palette.json`): steel_plate, dark_steel,
  galvanized, rusted_steel, hazard_stripe, copper, brass, rubber, concrete, glass, grate, glow_amber, glow_red,
  glow_cyan, warning_paint_yellow, warning_paint_red, wood_plank, brick, stone, dirt, water, leaves.
  Faces are painted in reading orientation (up faces: north at the top). To add a material add a function and a
  `MATERIALS` entry; to retint, edit the palette JSON.
* Vanilla materials (blocky style): `mc:<texture path>[#rrggbb]`, e.g. `mc:block/cobblestone`,
  `mc:block/grass_block_top#79c05a`, tile that texture from the vanilla client jar at 1 px = 1 texel (random offset
  per variant, optional RGB tint for the greyscale grass/leaves/water textures, alpha kept for cut-outs such as
  `mc:block/wheat_stage7`; animated strips use their first frame). The jar is `$MC_CLIENT_JAR`, default
  `~/.minecraft/versions/1.21.11/1.21.11.jar`. Blocky Builder scripts (`models/blocky_<family>.py`) use only these.
* Helpers (all take `group=` and return elements, or the sub-group they create): `cylinder(name, cx, cz, y0, y1, r,
  mat, sides=8, cap_mat=)`, `pipe(name, centre, length, r, axis)` (horizontal cylinder in a rotated sub-group),
  `ring(name, cx, cz, y0, y1, r_out, r_in)`, `taper(...)` (stepped cone), `chimney`, `hopper`, `tank`, `beam(a, b,
  w, h, profile="box"|"I")`, `strut(p0, p1)` (diagonal in an X-Y or Z-Y plane), `truss(x0, z0, x1, z1, y0, y1)`,
  `rivet_strip`, `panel` (framed inset), `ladder`, `railing`, `gear` / `fan` (return the OUTER axis-aligned group:
  spin that), `conveyor` (returns the belt group), `pipe_run(points)` (axis-aligned legs, elbow blocks, flanges),
  `smoke(name, x, y, z)` (bones named `smoke_*`, hidden by states.py outside `running`).
  Wall helpers (`panel`, `ladder`, `rivet_strip`) take a wall point and `facing` north/east/south/west.
* Animation (writes `running`; periods must divide `run_length`): `spin(bone, axis, period)`,
  `oscillate(bone, channel, axis, amplitude, period, phase)`, `bob`, `piston(bone, axis, stroke, period)`,
  `pulse_scale`, `rise` (looping smoke puff). Keyframes are linear and sampled 16x per period. Terms on the same
  bone/channel add; do not mix a looping `rise` with other terms on that channel. Rotation is applied about the
  bone's group pivot; for tilted helpers (pipe/gear/fan) animate the returned outer group.
* `b.input_bones([...])` / `b.output_bones([...])` write `state_overrides/<name>.json` on save.
* `b.save(path)` finalises the atlas, warns when geometry leaves +-17 px on X/Z or exceeds 48 px (smoke and the
  lamp mast are ignored for the check), writes the file and runs `states.py --write` on it. The lamp lens colour
  texels live in the reserved atlas block x=252..255, y=252..255.
* `industrial_status_mast(b, x, z, base)` builds the mast (housing + hoods) and the `status` group with the six
  lamp bones; it replaces the auto housing. `industrial_plinth(b)` is the shared 4-sided base.
* Example: `models/industrial_smelter.py`.

Known limits: cylinders are n-gon prisms of rotated cubes (even `sides` only, 8-16 recommended); a rotated cube
carries one Euler rotation about its own centre/origin; no mesh elements; `Builder` animation does not follow
later `clone` calls (animate clones by their names); the atlas is fixed at 256x256.
