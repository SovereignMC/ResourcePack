# ResourcePack — developer notes

Functional reference for working in this repository. User-facing description, play links,
download and credits live in `README.md`; licensing terms live in `LICENSE`.

## What this is

A static Minecraft resource pack: `pack.mcmeta` + `pack.png` + `assets/**`. There is no
compile step. `pack.mcmeta` declares `pack_format` 64, `supported_formats` `[64, 64]`,
`min_format` `[64, 0]` and `max_format` `[75, 0]`; keep it valid JSON and bump the formats
deliberately when the target client changes.

`pack.zip` is a build artifact. It is gitignored and must not be committed; the published
zip is built by CI (see below).

## Layout

| Path | Contents |
|---|---|
| `assets/minecraft/` | Vanilla overrides: `items/feather.json` (guns + magazines), `items/stick.json` (torpedoes), `sounds.json` + `sounds/custom/` (BigDoors/AnimatedArchitecture), `sounds/radar_*`, `lang/en_us.json`, explosion particles, GUI sprites, `models/torpedo/` |
| `assets/weapons/` | Gun item models and fire sounds. `sounds/original/` keeps the unprocessed recordings. |
| `assets/ammo/` | Shell, torpedo and magazine item definitions, models and textures. |
| `assets/planechase/` | Bomb/bullet/rocket/shell models, ammo sprites, cockpit callout sounds and the G-force blackout font. |
| `assets/argentum/` | Argentum item/block definitions, models and category-foldered textures (the largest namespace). |
| `assets/sovereignflags/` | Flag item definitions, models and textures. |
| `assets/sovereignmc/` | Fonts, dialog/menu/sidebar/plate art, GUI skins, UI icons, effect models and shock animations. |
| `assets/sna/` | SNA HUD icon and UI fonts. |
| `assets/tinsel/` | Spacing and HUD background fonts. |
| `assets/sov/` | Cannon, torpedo and turret sound files. |
| `tools/` | Generators, renderer and verification scripts (see below). |
| `ignored/` | Local Argentum preview sheets; gitignored. |
| `.github/workflows/` | Verification, release and Discord notification jobs. |

Namespace names are API: plugins reference `argentum:`, `planechase:`, `weapons:`,
`ammo:`, `sovereignflags:`, `sovereignmc:`, `sna:`, `tinsel:` and `sov:` directly. Do not
rename a namespace or move assets without updating the consuming plugin.

## Build and install

`build.sh` is a local, gitignored helper — it is not part of the published repository. It
zips `pack.mcmeta`, `pack.png` and `assets/**` with fixed 1980-01-01 timestamps so
repeated builds are byte-identical, then installs the result as `SovereignMC.zip`:

```bash
./build.sh                                   # build + install into Lunar profile "smc"
./build.sh --no-install                      # build only
./build.sh --dest ~/.minecraft/resourcepacks # additional install folder
LUNAR_RESOURCEPACKS=/path ./build.sh         # replace the default install folder
```

The installed file keeps the name `SovereignMC.zip` because each client's `options.txt`
refers to `file/SovereignMC.zip`. The local output is `pack.zip` at the repo root.

## Verification

```bash
tools/verify-pack.sh                     # bash + jq; this is what CI runs
python3 tools/verify_argentum_refs.py    # python3 + Pillow; extra Argentum checks
```

`verify-pack.sh` exits 1 on:

- invalid resource locations (anything outside `a-z 0-9 _ . - /`);
- unresolved `argentum:` parent, model or texture references;
- Argentum texture references outside a folder listed in `TEXTURE_CATEGORIES`;
- unparseable JSON, or a missing/invalid `pack.mcmeta`.

It warns on flat `item/x` / `block/x` references, allowlisted machine model refs and PNGs
that no JSON references. It only walks `assets/argentum/**/*.json`, so a green run does
not validate texture/model references in the other namespaces.

`verify_argentum_refs.py` mirrors the same checks without jq and adds the 16×16 RGBA tile
audit, the item ids StructuresRevamped resolves (`TARGET_IDS`) and an unreferenced-PNG
check. Keep both green before committing.

## CI and releases

- `ci.yml` — on every push and pull request, runs `tools/verify-pack.sh`.
- `squash-release.yml` — on a push to `main` that changes `assets/**` or `pack.mcmeta`:
  verifies, runs PackSquash over the repo root, writes `pack.zip` plus its SHA-1, and
  publishes/updates the latest release as tag `ResourcePack-v<run_number>`.
  Branch pushes only, by design: publishing from a tag would rebuild the old tree and
  overwrite "latest".
- `discord.yml` — posts each commit to `DISCORD_WEBHOOK`. Add `[nodiscord]` to the commit
  message to skip a commit.

Releases are the distribution channel; never commit `pack.zip`.

## Adding content

1. Item definitions use the 1.21.4+ format: `assets/<ns>/items/<id>.json` points at
   `assets/<ns>/models/item/<id>.json`, whose `textures` point at
   `assets/<ns>/textures/...`. Vanilla item overrides live in `assets/minecraft/items/`.
2. `assets/minecraft/items/feather.json` dispatches guns and magazines on
   `minecraft:custom_model_data`: thresholds `10`–`32` map to `weapons:item/*` gun models,
   `1000001`–`1000006` to `weapons:ammo/*` magazines. `assets/minecraft/items/stick.json`
   dispatches torpedoes at thresholds `100`, `101`, `102`. The server plugin must use the
   same numbers; renumbering is a coordinated change with the plugin.
3. Paths must be valid resource locations: lowercase `a-z 0-9 _ . - /` only, no spaces or
   uppercase.
4. Argentum textures must stay inside the category folders declared in
   `TEXTURE_CATEGORIES` in `tools/verify-pack.sh`. To add a category, update that list and
   the mapping tables in `tools/migrate-textures.ps1` first.
5. Texture file names are stable. Item models and plugins bind `argentum:<id>`; moving a
   texture means updating every referencing JSON's `textures.*` value in the same commit.
6. Item icons are 16×16 RGBA with a transparent background. Argentum block tiles are
   16×16 RGBA and fully opaque (enforced by the Python verifier for its target ids).

Argentum item texture categories (`assets/argentum/textures/`):

```
item/
├── sigils/        sigil_of_* + sigil_crucible
├── metallurgy/    ingots, alloys, raw ores, unrefined_gold_ore
├── dust/          impure_* and pure_* dusts, sulfur_dust
├── components/    circuits, electrodes, cores, blades, magnets, buckets, rods
├── consumables/   essences, condensed fluids, sulfate, cooling_salt, carbon chunks
├── tools/         climbing_pickaxe, gold_pan, nether_gold_pan
└── ui/            inputarrow, outputarrow (GUI decoration icons)
block/
├── machines/         machine face sets (brewer, transformer, water_tank, alternator, ...)
├── basic_machines/   Slimefun basic machine icons (2D, item/generated): multiblocks,
│                     enhanced_furnace_1..11, composter, crucible, block_placer, ...
├── capacitors/       *_capacitor_{bottom,side,top}
├── crates/           output_crate face sets
└── supply/           supply_hopper, elevator_block
```

## Sound event names

Sound event names in the `sounds.json` files are the contract with the plugins:

- `assets/minecraft/sounds.json` — `bd.*` maps to `minecraft:custom/*.ogg` for
  BigDoors/AnimatedArchitecture; `turret.servo_*`, `shoot.*` and `torp_*` map to `sov:*`;
  `radar_scan` / `radar_detected` map to `minecraft:radar_*`.
- `assets/weapons/sounds.json` — `*.fire` events and `generic.hitmarker` map to
  `weapons:*` files.
- `assets/planechase/sounds.json` — `cockpit.*` callouts map to
  `planechase:cockpit/*`, with subtitles in `assets/planechase/lang/`.

Renaming an event, file or namespace breaks the calling plugin even though the pack still
loads. `assets/sov/` and `assets/weapons/sounds/original/` follow the same rule; the
`original/` folder keeps the source recordings.

## `assets/minecraft/lang/en_us.json`

The keybind keys (`key.freecam.toggle`, `key.wurst.zoom`, `key.meteor-client.open-gui`,
etc.) are deliberately replaced with opaque `opec-*` strings. This is anti-cheat text, not
a broken translation — do not restore the real names.

## Fonts

Fonts are bitmap providers using private-use codepoints; plugin code writes the
characters. Key fonts:

| Font | Contents |
|---|---|
| `sovereignmc:menu` | Selector dialogue panels: large `U+E00D`–`U+E00F` at 192×216, compact `U+E011`–`U+E013` at 152×180. Generated by `generate_menu_background.py`. |
| `sovereignmc:logo` | `U+E002` 80 px wordmark, `U+E003` mark, `U+E004` 31 px wordmark. |
| `sovereignmc:gui_skins` | Inventory skin backgrounds, structure emblems and LCD overlays/digits (codepoints below). Generated. |
| `sovereignmc:spaces` | Space provider `U+CE000`–`U+D2000`, advances −8192…+8192. |
| `sovereignmc:dialog`, `dialog_art`, `dialog_text` | Dialog chrome, art and bitmap text; `*_offset_<n>` variants shift glyphs by n px. |
| `sovereignmc:plate` | Structure plate panels and glyphs. |
| `sovereignmc:sidebar` (+ `sidebar_row_<n>`) | Sidebar panels and per-row variants. |
| `tinsel:spacing` | Power-of-two steps: `U+E000`–`U+E00A` = +1…+1024, `U+F8FF`–`U+F8F5` = −1…−1024. |
| `tinsel:hud_background` (+ `default_offset_*`, `hud_background_offset_*`) | HUD bar slices, ascent 13 / height 20. |
| `sna:hud_icons`, `hud_ui`, `hud_ui_text` (+ `*_offset_*`) | SNA HUD icons, UI glyphs and compact bitmap text. |
| `planechase:gforce` | G-force blackout overlay, `U+E100`–`U+E103` (four levels), 256 px tall. |

`gui_skins` codepoints:

- `U+E600..U+E63D` — inventory backgrounds (chest/anvil skins);
- `U+E700..U+E710` — structure emblems (32×32 logos copied from SovereignPlates;
  16×16 item icons live under `item/guide/`);
- `U+E6C0..U+E6C2` — LCD segment/lamp overlays;
- `U+E6D0..U+E6DB`, `U+E6E0..U+E6EB`, `U+E6F0..U+E6FB` — LCD digits `0-9 / %` for
  window rows 5, 3 and 0;
- `U+E720..U+E72B` — guide-coloured row 5 digits.

The client draws titles and labels on top of the background glyphs.

## GUI skins generator

`tools/gui-skins/skins.json` is the source of truth (ids, codepoints, grids, decor).
`node tools/gui-skins/generate.mjs` regenerates:

- the 16×16 control icons (`assets/sovereignmc/textures/item/ui/`, item definitions
  `assets/sovereignmc/items/ui/*.json`);
- the guide structure icons (`assets/sovereignmc/textures/item/guide/`);
- the inventory skin backgrounds (`assets/sovereignmc/textures/gui/skins/*.png`);
- `assets/sovereignmc/font/gui_skins.json`.

Icon art lives in `tools/gui-skins/icons.mjs`. The generator uses Node built-ins only and
its output is deterministic. Never edit the generated PNGs or font JSON by hand.

## PlaneChase projectiles

Blocky bomb and bullet models are shown as PacketEvents-sent `ItemDisplay`s whose item has
`item_model` = `planechase:<name>`: `bullet_standard`, `bullet_tracer`, `bullet_ap`,
`bomb_shell`, `bomb_general_purpose`, `bomb_heavy`, `bomb_cluster`,
`bomb_cluster_bomblet` (cluster submunitions), `bomb_incendiary`, `rocket_light`,
`rocket_heavy`, plus `tank_shell` and `heavy_tank_shell`.

Flat 16×16 ammo item sprites for the items the plugin hands out:
`ammo_fighter_round`, `ammo_canister_shell`, `ammo_canister_pellet`,
`ammo_light_rocket`, `ammo_heavy_rocket`.

- Textures: `assets/planechase/textures/item/projectile/`.
- Models: `assets/planechase/models/item/`.
- Blockbench sources and a contact sheet: `tools/art/projectiles/`.
- The nose points to model −Z. On an `ItemDisplay` with the identity `fixed`/`head`
  transform it faces the entity's local +Z. Models are centred on x = y = 8 and z ≈ 8, so
  the display sits at the projectile's middle.

## Generators

Generators take `--pack-dir .` (default `.`) and write committed output. Re-run the
relevant one instead of hand-drawing; output is deterministic.

| Command | Writes |
|---|---|
| `node tools/gui-skins/generate.mjs` | GUI skins, UI/guide icons and `sovereignmc:gui_skins` |
| `python3 tools/generate_menu_background.py [--client-jar JAR]` | `menu_*.png` panels and `sovereignmc:menu` |
| `python3 tools/generate_aim_beam.py` | `sovereignmc:effect/aim_beam` beam and emissive tiles |
| `python3 tools/generate_flag_holder_textures.py` | `argentum` `holder_iron.png` / `holder_brass.png` |
| `python3 tools/generate_explosion_textures.py --src <frames>` | `minecraft:textures/particle/explosion_0..15.png` |
| `python3 tools/generate_argentum_metallurgy_art.py` | Titanium/quantum alloy/carbon fibre icons, items and models |
| `python3 tools/generate_argentum_component_art.py` | Component icons, cordite charge, items and models |
| `python3 tools/generate_argentum_consumable_art.py` | Reinforced/quantum consumable icons, items and models |
| `python3 tools/generate_argentum_machine_art.py` | Machine block tiles, item definitions and block models |

`tools/migrate-textures.ps1` is a one-shot, idempotent migration that moved Argentum
textures into category folders. Do not run it for normal content work.

## Rendering text offline

`tools/render_text.py` draws a Minecraft text component with the client's font metrics
(pack-first resolution) and reports wrapped, clipped or missing glyphs. Read
`tools/render_text.md` for the full flag and metric reference. Requires `python3` with
Pillow and a client jar (or unpacked `assets/`) for `minecraft:default`:

```bash
python3 tools/render_text.py --client-jar ~/client.jar --self-test
python3 tools/render_text.py --client-jar ~/client.jar --json /tmp/dialog.json --width 0
```

`--self-test` must print `0 failure(s)`. Previews are written to `/tmp/text_render.png`
and are not committed.

## Gotchas

- `verify-pack.sh` only resolves Argentum JSON; other namespaces can regress without CI
  noticing. Check their model/texture paths manually.
- `pack.mcmeta` mixes `supported_formats` with `min_format`/`max_format`; test any format
  change in a real client before releasing.
- `pack.zip`, `ignored/`, `__pycache__/` and `build.sh` are gitignored. `pack.zip` must
  stay out of history.
- `*_offset_*` and `*_row_*` font variants are selected by name in plugin code. Adding a
  variant without adding it to the consuming code does nothing.
- Every asset path is case-sensitive in a zip and must remain a valid lowercase resource
  location.
