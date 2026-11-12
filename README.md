# SovereignMC's ResourcePack

The official resource pack for **SovereignMC**, a 1.21+ Minecraft server. It ships the custom content the server depends on: item and block models for guns, ammo and torpedoes, sovereign flags, GUI and HUD graphics, aircraft callouts, and AnimatedArchitecture door sounds.

## Play with us

- Server: `play.sovereignmc.net`
- Website: https://sovereignmc.net
- Minecraft: **1.21+**

## Download

Grab `pack.zip` from the [latest release](https://github.com/SovereignMC/ResourcePack/releases/latest) and drop it into your `resourcepacks` folder — no unzipping needed.

## PlaneChase projectiles

Blocky bomb and bullet models for PlaneChase, meant to be shown as PacketEvents-sent ItemDisplays
whose item has `item_model` = `planechase:<name>`: `bullet_standard`, `bullet_tracer`, `bullet_ap`,
`shell_cannon`, `bomb_gp`, `bomb_heavy`, `bomb_cluster`, `bomb_incendiary`, `bomb_tnt`.

- Textures: `assets/planechase/textures/item/projectile/`. Models: `assets/planechase/models/item/`.
- Blockbench sources and a contact sheet: `tools/art/projectiles/`.
- The nose points to model -Z. On an ItemDisplay with the identity `fixed`/`head` transform, it faces
  the entity's local +Z. Each model is centred on x = y = 8 and z of about 8, so the display sits at the
  projectile's middle.

## Credits

## Textures

Argentum textures are organized into category subfolders — never dump new PNGs
flat into `textures/item/` or `textures/block/`. `tools/verify-pack.ps1` fails
CI on flat or unresolvable references.

```
assets/argentum/textures/
├── item/
│   ├── sigils/        sigil_of_* + sigil_crucible
│   ├── metallurgy/    ingots, alloys, raw ores, unrefined_gold_ore
│   ├── dust/          impure_* and pure_* dusts, sulfur_dust
│   ├── components/    circuits, electrodes, cores, blades, magnets, buckets, rods
│   ├── consumables/   essences, condensed fluids, sulfate, cooling_salt, carbon chunks
│   ├── tools/         climbing_pickaxe, gold_pan, nether_gold_pan
│   └── ui/            inputarrow, outputarrow (GUI decoration icons)
└── block/
    ├── machines/      machine face sets (brewer, transformer, water_tank, alternator, ...)
    ├── basic_machines/ Slimefun basic machine icons (2D, item/generated): multiblocks,
    │                   enhanced_furnace_1..11, composter, crucible, block_placer, ...
    ├── capacitors/    *_capacitor_{bottom,side,top}
    ├── crates/        output_crate face sets
    └── supply/        supply_hopper, elevator_block
```

Rules:
- Paths must be valid resource locations: lowercase `a-z 0-9 _ . - /` only, no spaces
  (verify-pack fails otherwise).
- A new category folder must be added to `TEXTURE_CATEGORIES` in `tools/verify-pack.ps1`
  and to the mapping tables in `tools/migrate-textures.ps1`.
- Texture file NAMES stay stable — code binds `argentum:<id>` via item models.
- Move a texture = update the referencing JSON's `textures.*` values in the same commit.
- `tools/verify-pack.ps1` must stay green (also runs in CI and before PackSquash releases).
- `tools/verify_argentum_refs.py` mirrors those checks (plus the 16x16 RGBA tile audit and
  the Argentum ids StructuresRevamped resolves) for machines without `pwsh`; run
  `python3 tools/verify_argentum_refs.py`. CI still runs `verify-pack.ps1`.

### Horizon's End Resource Pack
Movecraft effects and other assets are taken from the [Horizon's End Resource Pack](https://github.com/HorizonsEndMC/ResourcePack) by [HorizonsEndMC](https://github.com/HorizonsEndMC) and their relevant contributors, licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/).
- Source: https://github.com/HorizonsEndMC/ResourcePack
- License: https://creativecommons.org/licenses/by-sa/4.0/

### Slimefun4 Resource Pack
Textures used by Argentum and other assets are taken from the [Slimefun Resourcepack](https://github.com/Slimefun/Resourcepack) by [TheBusyBiscuit](https://github.com/TheBusyBiscuit), [Slimefun](https://github.com/Slimefun) team and their relevant contributors, licensed under the [MIT License](https://github.com/Slimefun/Resourcepack/blob/master/LICENSE).

Copyright (c) 2019 TheBusyBiscuit
- Source: https://github.com/Slimefun/Resourcepack
- License: MIT

### Tinker's Construct
Textures used by Argentum and other assets are taken from [Tinker's Construct](https://github.com/SlimeKnights/TinkersConstruct) by the [SlimeKnights](https://github.com/SlimeKnights) team and their relevant contributors, licensed under the [MIT License](https://github.com/SlimeKnights/TinkersConstruct/blob/1.20.1/LICENSE).

Copyright (c) 2022 SlimeKnights
- Source: https://github.com/SlimeKnights/TinkersConstruct
- License: MIT

### Animated Architecture
Sound effects used by the pack's BigDoors/AnimatedArchitecture events are taken from the AnimatedArchitecture support pack by [PimvanderLoos](https://github.com/PimvanderLoos/AnimatedArchitecture), licensed under the [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html).
- Source: https://github.com/PimvanderLoos/AnimatedArchitecture
- License: GPL-3.0
