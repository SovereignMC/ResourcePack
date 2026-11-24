# Tools

Scripts are grouped by what they do, not by language. Run them from the repository root
unless a command says otherwise.

```
tools/
├── generate/
│   ├── argentum/      Argentum item, block, machine and consumable art
│   ├── bettermodel/   BetterModel -> assets/bettermodel release pipeline
│   ├── effects/       Aim beam and explosion particle art
│   ├── gui/           GUI skins and dialogue-panel art
│   ├── items/         Flag holder textures
│   └── structures/    Structure bbmodel renderer, state-animation injector, preview font
├── verify/            Pack and Argentum integrity checks
├── render/            Offline Minecraft text renderer and metric reference
├── migrate/           One-shot Argentum texture migration
├── art/               Source screenshots and Blockbench models
└── wiki-art/          In-game wiki art generator and allocations
```

## Generate

```bash
python3 tools/generate/argentum/component_art.py --pack-dir .
python3 tools/generate/argentum/consumable_art.py --pack-dir .
python3 tools/generate/argentum/machine_art.py --pack-dir .
python3 tools/generate/argentum/metallurgy_art.py --pack-dir .
python3 tools/generate/effects/aim_beam.py --pack-dir .
python3 tools/generate/effects/explosion_textures.py --src <frames> --pack-dir .
python3 tools/generate/gui/menu_background.py --pack-dir . [--client-jar JAR]
node tools/generate/gui/skins/generate.mjs
python3 tools/generate/items/flag_holder_textures.py --pack-dir .
python3 tools/generate/structures/previews.py --pack-dir .
tools/generate/bettermodel/generate.sh
```

`generate/bettermodel/generate.sh` downloads Paper and BetterModel, so it needs Java 25+
and network access. The other generators are deterministic and only need Python/Pillow or
Node built-ins.

## Verify

```bash
tools/verify/pack.sh
python3 tools/verify/argentum_refs.py
```

`pack.sh` is the CI check and needs bash + jq. `argentum_refs.py` mirrors its Argentum
checks without jq and adds texture-tile audits.

## Render

```bash
python3 tools/render/render_text.py --client-jar <client.jar> --self-test
```

See `render/render_text.md` for flags and font metrics.

## Art and migration

`art/` holds generator inputs and reference sheets. `migrate/textures.ps1` is a one-shot,
idempotent migration; do not run it for normal content work.
